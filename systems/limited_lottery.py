# -*- coding: utf-8 -*-

# ==========================
# 🎃 萬聖節限定盲盒抽獎系統
# ==========================

import discord
import random
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from discord import app_commands
from discord.ext import tasks

from database import conn, c
from config import BOT_ADMINS


# ==========================
# 🎃 萬聖節限定盲盒設定
# ==========================

# ==========================
# 🎃 萬聖節活動時間設定
# ==========================

HALLOWEEN_START = "2026-10-31 00:00"
HALLOWEEN_END = "2026-11-01 00:00"

# 🎃 萬聖節活動頻道
HALLOWEEN_CHANNEL_ID = 1530174213418123326

# 👥 萬聖節活動指定身分組
HALLOWEEN_ROLE_ID = 1504854895826698392

# 🧪 測試模式
#
# True：
#   可以正常測試盲盒。
#   不受正式活動日期限制。
#   不修改活動頻道權限。
#   不會自動清除任何抽獎資料。
#
# 正式活動前請改成 False。
HALLOWEEN_TEST_MODE = True

# 🇹🇼 使用台灣時間
HALLOWEEN_TIMEZONE = ZoneInfo("Asia/Taipei")

# --------------------------
# 🎟️ 每人最多參與次數
# --------------------------

LIMITED_LOTTERY_MAX_TIMES = 2

# --------------------------
# 💰 參與費用
# --------------------------

LIMITED_LOTTERY_FIRST_PRICE = 500

LIMITED_LOTTERY_SECOND_PRICE = 5000

# --------------------------
# 🎁 獎品機率
# --------------------------

LIMITED_LOTTERY_PRIZES = [
    {
        "type": "money",
        "name": "💰 努努幣 5,000",
        "value": 5000,
        "weight": 40,
    },
    {
        "type": "money",
        "name": "💰 努努幣 8,000",
        "value": 8000,
        "weight": 30,
    },
    {
        "type": "sticker",
        "name": "🎨 角色 Q 版貼圖 ×1",
        "value": 1,
        "weight": 20,
    },
    {
        "type": "couple",
        "name": "💕 角色合照 ×1",
        "value": 1,
        "weight": 10,
    },
]


# ==========================
# 🎃 萬聖節指定媽咪
# ==========================

HALLOWEEN_MOMMIES = {
    "hanxin": {
        "name": "🫧 韓馨媽咪",
        "user_id": 1153640526063607820,
    },
    "xingxian": {
        "name": "☀️ 星弦媽咪",
        "user_id": 1218542666879598613,
    },
    "xier": {
        "name": "🌻 曦兒媽咪",
        "user_id": 1301905168094335028,
    },
    "xiaomao": {
        "name": "🐈 小貓媽咪",
        "user_id": 806960151578804275,
    },
}


# ==========================
# 🎃 正在開盲盒的玩家
# ==========================

limited_lottery_running = set()


# ==========================
# 🎃 判斷是否為萬聖節活動日
# ==========================

def get_halloween_now():

    return datetime.now(
        HALLOWEEN_TIMEZONE
    )


def get_halloween_start():

    return datetime.strptime(
        HALLOWEEN_START,
        "%Y-%m-%d %H:%M",
    ).replace(
        tzinfo=HALLOWEEN_TIMEZONE
    )


def get_halloween_end():

    return datetime.strptime(
        HALLOWEEN_END,
        "%Y-%m-%d %H:%M",
    ).replace(
        tzinfo=HALLOWEEN_TIMEZONE
    )


def is_halloween_day():

    # 🧪 測試模式不限正式日期
    if HALLOWEEN_TEST_MODE:
        return True

    now = get_halloween_now()

    return (
        get_halloween_start()
        <= now
        < get_halloween_end()
    )


# ==========================
# 🔒 跨系統人設圖待辦防呆
# ==========================

def has_pending_character_image(user_id, exclude_halloween_entry_id=None):
    """只要萬聖節或 Moon Club 尚有待交圖片，就暫停新抽獎／新兌換。"""
    user_id = str(user_id)

    try:
        query = """
            SELECT id FROM halloween_lottery_entries
            WHERE user_id = ? AND claim_status = 1
              AND image_status = 'awaiting_image'
        """
        params = [user_id]
        if exclude_halloween_entry_id is not None:
            query += " AND id != ?"
            params.append(int(exclude_halloween_entry_id))
        query += " LIMIT 1"
        c.execute(query, tuple(params))
        if c.fetchone():
            return True
    except Exception:
        # 資料表尚未建立時，不因不存在而阻斷啟動。
        pass

    try:
        c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='moon_achievement_redemptions'"
        )
        if c.fetchone():
            c.execute(
                "SELECT redemption_id FROM moon_achievement_redemptions "
                "WHERE user_id = ? AND status = 'awaiting_image' LIMIT 1",
                (int(user_id),),
            )
            if c.fetchone():
                return True
    except Exception:
        pass

    return False


# ==========================
# 🎃 取得玩家正式參與次數
# ==========================

def get_limited_lottery_count(user_id):

    # -------------------------
    # 👑 管理員測試不計入正式次數
    # -------------------------

    if int(user_id) in BOT_ADMINS:
        return 0

    c.execute(
        """
        SELECT COUNT(*)
        FROM halloween_lottery_entries
        WHERE user_id = ?
        AND is_test = 0
        """,
        (str(user_id),),
    )

    result = c.fetchone()

    return result[0] if result else 0


# ==========================
# 🎃 檢查角色獎品是否已完成領獎
# ==========================

def is_prize_claimed(entry_id):

    c.execute(
        """
        SELECT claim_status
        FROM halloween_lottery_entries
        WHERE id = ?
        """,
        (entry_id,),
    )

    result = c.fetchone()

    if not result:
        return True

    return int(result["claim_status"]) == 1


# ==========================
# 🎃 鎖定角色獎品
# ==========================

def claim_limited_prize(
    entry_id,
    user_id,
    mommy_key,
    character_name,
):

    mommy_data = HALLOWEEN_MOMMIES.get(
        mommy_key
    )

    if not mommy_data:
        return False

    # ==========================
    # 🔒 原子鎖定
    # ==========================
    #
    # 只有 claim_status = 0
    # 才能成功修改。
    #
    # 如果有人已經提交過，
    # 這裡的 UPDATE 不會成功。
    # ==========================

    c.execute(
        """
        UPDATE halloween_lottery_entries
        SET
            claim_status = 1,
            image_status = 'awaiting_image',
            mommy_key = ?,
            mommy_user_id = ?,
            mommy_name = ?,
            character_name = ?,
            claimed_at = ?
        WHERE id = ?
        AND user_id = ?
        AND prize_type IN ('sticker', 'couple')
        AND claim_status = 0
        """,
        (
            mommy_key,
            str(mommy_data["user_id"]),
            mommy_data["name"],
            character_name,
            datetime.now().isoformat(),
            entry_id,
            str(user_id),
        ),
    )

    # ==========================
    # 🔒 檢查是否真的成功
    # ==========================

    if c.rowcount != 1:

        conn.rollback()

        return False

    conn.commit()

    return True


# ==========================
# 🎃 角色獎品｜選擇指定媽咪
# ==========================

class HalloweenMommySelect(
    discord.ui.Select
):

    def __init__(
        self,
        entry_id,
        prize_type,
        prize_name,
    ):

        self.entry_id = entry_id
        self.prize_type = prize_type
        self.prize_name = prize_name

        options = []

        for key, mommy in HALLOWEEN_MOMMIES.items():

            options.append(
                discord.SelectOption(
                    label=mommy["name"],
                    value=key,
                    description="選擇這位媽咪處理本次角色獎品",
                )
            )

        super().__init__(
            placeholder="🎃 請選擇指定媽咪",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):

        # ==========================
        # 🔒 再次檢查獎品狀態
        # ==========================

        if is_prize_claimed(
            self.entry_id
        ):

            await interaction.response.send_message(
                "❌ 這份角色獎品已經完成領獎資料填寫。\n\n"
                "同一份獎品只能提交一次，"
                "無法再次更換指定媽咪。",
                ephemeral=True,
            )

            return

        mommy_key = self.values[0]

        mommy_data = HALLOWEEN_MOMMIES.get(
            mommy_key
        )

        if not mommy_data:

            await interaction.response.send_message(
                "❌ 找不到指定的媽咪資料，請重新操作。",
                ephemeral=True,
            )

            return

        await interaction.response.send_modal(
            HalloweenCharacterModal(
                entry_id=self.entry_id,
                mommy_key=mommy_key,
                prize_type=self.prize_type,
                prize_name=self.prize_name,
            )
        )


# ==========================
# 🎃 角色獎品｜選擇指定媽咪 View
# ==========================

class HalloweenMommyView(
    discord.ui.View
):

    def __init__(
        self,
        entry_id,
        prize_type,
        prize_name,
    ):

        super().__init__(
            timeout=300
        )

        self.add_item(
            HalloweenMommySelect(
                entry_id=entry_id,
                prize_type=prize_type,
                prize_name=prize_name,
            )
        )


# ==========================
# 🎃 玩家自願取消角色圖片資格
# ==========================

class HalloweenCancelImageView(discord.ui.View):
    """萬聖節圖片獎品取消入口：第一次點擊只顯示確認，不修改資料。"""

    def __init__(self, entry_id, user_id):
        super().__init__(timeout=48 * 60 * 60)
        self.entry_id = int(entry_id)
        self.user_id = int(user_id)

    @discord.ui.button(
        label="🚫 自願取消資格",
        style=discord.ButtonStyle.danger,
        custom_id="halloween_cancel_image_qualification",
    )
    async def cancel_qualification(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ 這不是你的領獎通知，無法替其他玩家取消。", ephemeral=True
            )
            return

        row = c.execute(
            "SELECT image_status FROM halloween_lottery_entries WHERE id=? AND user_id=?",
            (self.entry_id, str(self.user_id)),
        ).fetchone()
        if not row or row[0] != "awaiting_image":
            await interaction.response.send_message(
                "ℹ️ 這筆圖片提交已完成、已取消，或目前不需要提交圖片。",
                ephemeral=True,
            )
            return

        await interaction.response.edit_message(
            content=(
                "⚠️ **請再次確認是否放棄這份萬聖節角色獎品。**\\n\\n"
                "確認後，這份獎品資格將永久取消，無法恢復或重新領取。\\n"
                "如果是不小心按到，請選擇「↩️ 返回，保留資格」。"
            ),
            view=HalloweenCancelConfirmView(
                self.entry_id, self.user_id, interaction.message.content
            ),
        )


class HalloweenCancelConfirmView(discord.ui.View):
    """只有第二次明確確認才會取消萬聖節獎品資格。"""

    def __init__(self, entry_id, user_id, original_content):
        super().__init__(timeout=180)
        self.entry_id = int(entry_id)
        self.user_id = int(user_id)
        self.original_content = original_content

    @discord.ui.button(
        label="⚠️ 確認放棄",
        style=discord.ButtonStyle.danger,
        custom_id="halloween_confirm_cancel_image_qualification",
    )
    async def confirm_cancel(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ 這不是你的領獎通知，無法替其他玩家取消。", ephemeral=True
            )
            return

        c.execute(
            "UPDATE halloween_lottery_entries SET image_status='cancelled' "
            "WHERE id=? AND user_id=? AND image_status='awaiting_image'",
            (self.entry_id, str(self.user_id)),
        )
        changed = c.rowcount == 1
        conn.commit()

        if not changed:
            await interaction.response.send_message(
                "ℹ️ 這筆圖片提交已完成、已取消或已逾期，資格沒有再次變更。",
                ephemeral=True,
            )
            return

        await interaction.response.edit_message(
            content=(
                "🚫 **已自願取消本次角色獎品領取資格。**\\n\\n"
                "這份角色獎品將視為放棄，無法恢復或重新領取。\\n"
                "你現在可以繼續使用其他抽獎功能。"
            ),
            view=None,
        )

    @discord.ui.button(
        label="↩️ 返回，保留資格",
        style=discord.ButtonStyle.secondary,
        custom_id="halloween_keep_image_qualification",
    )
    async def keep_qualification(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ 這不是你的領獎通知，無法替其他玩家操作。", ephemeral=True
            )
            return

        row = c.execute(
            "SELECT image_status FROM halloween_lottery_entries WHERE id=? AND user_id=?",
            (self.entry_id, str(self.user_id)),
        ).fetchone()
        if not row or row[0] != "awaiting_image":
            await interaction.response.send_message(
                "ℹ️ 這筆圖片提交已完成、已取消或已逾期，無法恢復原操作。",
                ephemeral=True,
            )
            return

        await interaction.response.edit_message(
            content=self.original_content,
            view=HalloweenCancelImageView(self.entry_id, self.user_id),
        )


# ==========================
# 🎃 角色獎品｜輸入角色名稱
# ==========================

class HalloweenCharacterModal(
    discord.ui.Modal
):

    def __init__(
        self,
        entry_id,
        mommy_key,
        prize_type,
        prize_name,
    ):

        super().__init__(
            title="🎃 萬聖節限定｜角色資料"
        )

        self.entry_id = entry_id
        self.mommy_key = mommy_key
        self.prize_type = prize_type
        self.prize_name = prize_name

        self.character_name = discord.ui.TextInput(
            label="角色名稱",
            placeholder="請輸入你的角色名稱",
            required=True,
            min_length=1,
            max_length=50,
        )

        self.add_item(
            self.character_name
        )

    async def on_submit(
        self,
        interaction: discord.Interaction,
    ):

        character_name = (
            self.character_name.value.strip()
        )

        if not character_name:

            await interaction.response.send_message(
                "❌ 角色名稱不能是空白。",
                ephemeral=True,
            )

            return

        # ==========================
        # 🔒 跨系統待交圖片防呆
        # ==========================

        if has_pending_character_image(
            interaction.user.id,
            exclude_halloween_entry_id=self.entry_id,
        ):
            await interaction.response.send_message(
                "⏳ 你目前還有另一筆人設圖尚未提交。\n\n"
                "請先完成圖片提交，或在原本的提醒私訊按下「自願取消資格」，"
                "才能建立新的圖片領獎流程。",
                ephemeral=True,
            )
            return

        # ==========================
        # 🔒 提交前再次檢查
        # ==========================

        if is_prize_claimed(
            self.entry_id
        ):

            await interaction.response.send_message(
                "❌ 這份角色獎品已經完成領獎資料填寫。\n\n"
                "同一份獎品只能提交一次。",
                ephemeral=True,
            )

            return

        mommy_data = HALLOWEEN_MOMMIES.get(
            self.mommy_key
        )

        if not mommy_data:

            await interaction.response.send_message(
                "❌ 找不到指定的媽咪資料。",
                ephemeral=True,
            )

            return

        # ==========================
        # 🔒 正式鎖定這份獎品
        # ==========================

        success = claim_limited_prize(
            entry_id=self.entry_id,
            user_id=interaction.user.id,
            mommy_key=self.mommy_key,
            character_name=character_name,
        )

        # ==========================
        # ❌ 如果已經有人提交過
        # ==========================

        if not success:

            await interaction.response.send_message(
                "❌ **這份獎品已經完成領獎資料填寫！**\n\n"
                "同一份角色獎品只能提交一次，"
                "無法再次選擇其他媽咪或修改角色名稱。",
                ephemeral=True,
            )

            return

        # ==========================
        # 📩 先請玩家私訊提交角色圖片
        # ==========================

        try:
            await interaction.user.send(
                "🎃 **萬聖節限定盲盒｜請提交角色圖片**\n\n"
                f"🎁 獎品：**{self.prize_name}**\n"
                f"🎭 角色名稱：**{character_name}**\n"
                f"🧡 指定媽咪：**{mommy_data['name']}**\n\n"
                "請直接在這則私訊中附上一張角色圖片並送出。\n"
                "在圖片成功轉交或自願取消資格前，不能開始其他需要提交人設圖的領獎流程。\n"
                "若不想領取，請按下方「自願取消資格」。",
                view=HalloweenCancelImageView(self.entry_id, interaction.user.id),
            )
        except Exception:
            await interaction.response.send_message(
                "⚠️ 領獎資料已記錄，但我無法私訊你。請先開啟伺服器成員的私訊功能，"
                "再聯絡管理員協助重新通知提交圖片。",
                ephemeral=True,
            )
            return

        # ==========================
        # 📩 取得指定媽咪
        # ==========================

        mommy = interaction.client.get_user(
            mommy_data["user_id"]
        )

        if mommy is None:

            try:

                mommy = await interaction.client.fetch_user(
                    mommy_data["user_id"]
                )

            except Exception:

                mommy = None

        # ==========================
        # 🎃 領獎資料已記錄
        # 此階段不通知媽咪；只有玩家圖片成功轉交後才通知。
        # ==========================

        dm_success = True

        # ==========================
        # 🎃 玩家回覆
        # ==========================

        if dm_success:

            await interaction.response.send_message(
                "✅ **領獎資料已成功送出！**\n\n"

                f"🎃 指定媽咪：**{mommy_data['name']}**\n"
                f"🎭 角色名稱：**{character_name}**\n"
                f"🎁 獎品：**{self.prize_name}**\n\n"

                "📩 機器人已通知指定媽咪，並私訊你提交角色圖片。\n"
                "請依照私訊指示傳送圖片，完成後才會轉交給媽咪。\n\n"

                "🔒 此份獎品的領獎資料已鎖定，"
                "無法再次提交。",
                ephemeral=True,
            )

        else:

            await interaction.response.send_message(
                "⚠️ **領獎資料已成功記錄，但通知媽咪失敗。**\n\n"

                f"🎃 指定媽咪：**{mommy_data['name']}**\n"
                f"🎭 角色名稱：**{character_name}**\n"
                f"🎁 獎品：**{self.prize_name}**\n\n"

                "📩 請依照機器人私訊指示提交角色圖片；圖片成功轉交後才會通知媽咪。",
                ephemeral=True,
            )


# ==========================
# 🎃 角色獎品｜填寫資料按鈕
# ==========================

class HalloweenPrizeView(
    discord.ui.View
):

    def __init__(
        self,
        entry_id,
        prize_type,
        prize_name,
    ):

        super().__init__(
            timeout=300
        )

        self.entry_id = entry_id
        self.prize_type = prize_type
        self.prize_name = prize_name

    @discord.ui.button(
        label="🎃 填寫角色資料",
        style=discord.ButtonStyle.primary,
        custom_id="halloween_prize_info",
    )
    async def fill_character_info(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        # ==========================
        # 🔒 按鈕層級防重複
        # ==========================

        if is_prize_claimed(
            self.entry_id
        ):

            await interaction.response.send_message(
                "❌ 這份角色獎品已經完成領獎資料填寫。\n\n"
                "同一份獎品只能提交一次。",
                ephemeral=True,
            )

            return

        await interaction.response.send_message(
            "🎃 **萬聖節限定｜角色獎品資料**\n\n"
            "請選擇這次的**指定媽咪**。\n\n"
            "選擇後再輸入你的角色名稱。\n\n"
            "確認送出後，機器人會私訊你提交角色圖片，"
            "並在收到圖片後轉交給指定媽咪。",
            view=HalloweenMommyView(
                entry_id=self.entry_id,
                prize_type=self.prize_type,
                prize_name=self.prize_name,
            ),
            ephemeral=True,
        )


# ==========================
# 🎃 執行萬聖節限定盲盒
# ==========================

async def run_limited_lottery(
    interaction: discord.Interaction,
    draw_number: int,
    price: int,
):

    user_id = str(
        interaction.user.id
    )

    # -------------------------
    # 👑 管理員測試模式
    # -------------------------

    is_test = (
        interaction.user.id in BOT_ADMINS
    )

    # -------------------------
    # 🔒 跨系統人設圖待辦防呆
    # -------------------------

    if has_pending_character_image(interaction.user.id):
        await interaction.response.send_message(
            "⏳ 你還有一筆人設圖尚未提交成功。\n\n"
            "請先傳送圖片，或在機器人的提醒私訊中按下「自願取消資格」，"
            "完成後才能繼續抽獎。",
            ephemeral=True,
        )
        return

    # -------------------------
    # 🔒 防止重複抽獎
    # -------------------------

    if interaction.user.id in limited_lottery_running:

        await interaction.response.send_message(
            "🎃 你的萬聖節盲盒正在開啟中，\n"
            "請稍等一下再操作喔！",
            ephemeral=True,
        )

        return

    limited_lottery_running.add(
        interaction.user.id
    )

    try:

        # ==========================
        # 💰 查詢努努幣
        # ==========================

        c.execute(
            """
            SELECT money
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        )

        data = c.fetchone()

        if not data:

            await interaction.response.send_message(
                "❌ 找不到你的努努幣帳戶資料。",
                ephemeral=True,
            )

            return

        money = data["money"]

        # ==========================
        # 💰 檢查餘額
        # ==========================

        if money < price:

            await interaction.response.send_message(
                "❌ 你的努努幣不足！\n\n"
                f"💰 本次需要：**{price:,} 努努幣**\n"
                f"💰 目前餘額：**{money:,} 努努幣**",
                ephemeral=True,
            )

            return

        # ==========================
        # 🎲 抽取獎品
        # ==========================

        prizes = []

        for prize_data in LIMITED_LOTTERY_PRIZES:

            prizes.extend(
                [prize_data] * prize_data["weight"]
            )

        prize = random.choice(
            prizes
        )

        prize_type = prize["type"]
        prize_name = prize["name"]
        prize_value = prize["value"]

        # ==========================
        # 💰 扣除參與費
        # ==========================

        money -= price

        # ==========================
        # 💰 努努幣獎品
        # ==========================

        if prize_type == "money":

            money += int(
                prize_value
            )

        # ==========================
        # 💾 更新玩家餘額
        # ==========================

        c.execute(
            """
            UPDATE users
            SET money = ?
            WHERE user_id = ?
            """,
            (
                money,
                user_id,
            ),
        )

        # ==========================
        # 💾 記錄抽獎結果
        # ==========================

        c.execute(
            """
            INSERT INTO halloween_lottery_entries (
                user_id,
                draw_number,
                price,
                prize_type,
                prize_value,
                is_test,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                draw_number,
                price,
                prize_type,
                str(prize_value),
                1 if is_test else 0,
                datetime.now().isoformat(),
            ),
        )

        # ==========================
        # 🔎 取得這次抽獎紀錄 ID
        # ==========================

        entry_id = c.lastrowid

        conn.commit()

        # ==========================
        # 🎃 開始盲盒動畫
        # ==========================

        await interaction.response.send_message(
            "🎃 **萬聖節限定盲盒**\n\n"
            "🎁 你的盲盒正在準備中……",
            ephemeral=True,
        )

        # -------------------------
        # ✨ 第一階段
        # -------------------------

        await asyncio.sleep(1)

        await interaction.edit_original_response(
            content=(
                "🎃 **萬聖節限定盲盒**\n\n"
                "🎁 盲盒正在晃動……\n"
                "✨ 裡面好像有東西！"
            ),
            embed=None,
            view=None,
        )

        # -------------------------
        # ✨ 第二階段
        # -------------------------

        await asyncio.sleep(1)

        await interaction.edit_original_response(
            content=(
                "🎃 **萬聖節限定盲盒**\n\n"
                "✨✨✨\n"
                "月光正在聚集……"
            ),
            embed=None,
            view=None,
        )

        # -------------------------
        # ✨ 第三階段
        # -------------------------

        await asyncio.sleep(1)

        await interaction.edit_original_response(
            content=(
                "🎃 **萬聖節限定盲盒**\n\n"
                "💫 **砰！**\n\n"
                "🎁 盲盒已經打開！"
            ),
            embed=None,
            view=None,
        )

        # -------------------------
        # ✨ 最後揭曉
        # -------------------------

        await asyncio.sleep(1)

        # ==========================
        # 🎁 建立最終結果
        # ==========================

        result_view = None

        if prize_type == "money":

            result_description = (
                "🎉 **恭喜你！**\n\n"
                f"## {prize_name}\n\n"
                "💰 獎勵已經自動加入你的錢包！"
            )

        elif prize_type in (
            "sticker",
            "couple",
        ):

            result_description = (
                "🎉 **恭喜你！**\n\n"
                f"## {prize_name}\n\n"

                "🎃 **請完成領獎資料**\n\n"

                "點擊下方按鈕後：\n"
                "① 選擇指定媽咪\n"
                "② 輸入角色名稱\n"
                "③ 按下確認送出\n"
                "④ 依照機器人私訊，傳送一張角色圖片\n\n"

                "📩 機器人收到圖片後會轉交給指定媽咪。\n\n"

                "⚠️ **每份角色獎品只能提交一次。**"
            )

            result_view = HalloweenPrizeView(
                entry_id=entry_id,
                prize_type=prize_type,
                prize_name=prize_name,
            )

        else:

            result_description = (
                "🎉 **恭喜你！**\n\n"
                f"## {prize_name}"
            )

        # ==========================
        # 🎃 最終結果 Embed
        # ==========================

        embed = discord.Embed(
            title="🎃 萬聖節限定盲盒",
            description=result_description,
            color=0xF5B041,
        )

        embed.add_field(
            name="🎟️ 本次抽獎",
            value=(
                f"第 **{draw_number} 次**"
            ),
            inline=True,
        )

        embed.add_field(
            name="💸 抽獎費用",
            value=(
                f"{price:,} 努努幣"
            ),
            inline=True,
        )

        embed.add_field(
            name="💰 目前餘額",
            value=(
                f"{money:,} 努努幣"
            ),
            inline=False,
        )

        # -------------------------
        # 👑 管理員測試提示
        # -------------------------

        if is_test:

            embed.add_field(
                name="🧪 測試模式",
                value=(
                    "👑 管理員測試\n"
                    "本次不計入正式抽獎次數。"
                ),
                inline=False,
            )

        embed.set_footer(
            text=(
                "🎃 Moon Bot｜萬聖節限定盲盒｜2026/10/31"
            )
        )

        # ==========================
        # 🎁 顯示最終結果
        # ==========================

        await interaction.edit_original_response(
            content=None,
            embed=embed,
            view=result_view,
        )

    finally:

        # ==========================
        # 🔓 解開玩家抽獎鎖
        # ==========================

        limited_lottery_running.discard(
            interaction.user.id
        )


# ==========================
# 🎃 建立限定盲盒資料表
# ==========================

def init_limited_lottery_database():

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS halloween_lottery_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            draw_number INTEGER NOT NULL,
            price INTEGER NOT NULL,
            prize_type TEXT NOT NULL,
            prize_value TEXT NOT NULL,
            is_test INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            claim_status INTEGER DEFAULT 0,
            mommy_key TEXT,
            mommy_user_id TEXT,
            mommy_name TEXT,
            character_name TEXT,
            claimed_at TEXT,
            image_status TEXT DEFAULT 'not_required',
            image_message_id TEXT
        )
        """
    )

    # ==========================
    # 🎃 舊資料表補欄位
    # ==========================

    existing_columns = set()

    c.execute(
        """
        PRAGMA table_info(halloween_lottery_entries)
        """
    )

    columns = c.fetchall()

    for column in columns:

        existing_columns.add(
            column["name"]
        )

    # -------------------------
    # 🧪 is_test
    # -------------------------

    if "is_test" not in existing_columns:

        try:

            c.execute(
                """
                ALTER TABLE halloween_lottery_entries
                ADD COLUMN is_test INTEGER DEFAULT 0
                """
            )

        except Exception:

            pass

    # -------------------------
    # 🔒 claim_status
    # -------------------------

    if "claim_status" not in existing_columns:

        try:

            c.execute(
                """
                ALTER TABLE halloween_lottery_entries
                ADD COLUMN claim_status INTEGER DEFAULT 0
                """
            )

        except Exception:

            pass

    # -------------------------
    # 🎃 mommy_key
    # -------------------------

    if "mommy_key" not in existing_columns:

        try:

            c.execute(
                """
                ALTER TABLE halloween_lottery_entries
                ADD COLUMN mommy_key TEXT
                """
            )

        except Exception:

            pass

    # -------------------------
    # 🎃 mommy_user_id
    # -------------------------

    if "mommy_user_id" not in existing_columns:

        try:

            c.execute(
                """
                ALTER TABLE halloween_lottery_entries
                ADD COLUMN mommy_user_id TEXT
                """
            )

        except Exception:

            pass

    # -------------------------
    # 🎃 mommy_name
    # -------------------------

    if "mommy_name" not in existing_columns:

        try:

            c.execute(
                """
                ALTER TABLE halloween_lottery_entries
                ADD COLUMN mommy_name TEXT
                """
            )

        except Exception:

            pass

    # -------------------------
    # 🎭 character_name
    # -------------------------

    if "character_name" not in existing_columns:

        try:

            c.execute(
                """
                ALTER TABLE halloween_lottery_entries
                ADD COLUMN character_name TEXT
                """
            )

        except Exception:

            pass

    # -------------------------
    # 🕐 claimed_at
    # -------------------------

    if "claimed_at" not in existing_columns:

        try:

            c.execute(
                """
                ALTER TABLE halloween_lottery_entries
                ADD COLUMN claimed_at TEXT
                """
            )

        except Exception:

            pass

    # -------------------------
    # 🖼️ 圖片提交狀態
    # -------------------------

    if "image_status" not in existing_columns:

        c.execute(
            """
            ALTER TABLE halloween_lottery_entries
            ADD COLUMN image_status TEXT DEFAULT 'not_required'
            """
        )

    if "image_message_id" not in existing_columns:

        c.execute(
            """
            ALTER TABLE halloween_lottery_entries
            ADD COLUMN image_message_id TEXT
            """
        )

    conn.commit()


# ==========================
# 🎃 萬聖節限定盲盒面板
# ==========================

class LimitedLotteryView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    # ==========================
    # 🎟️ 第一次抽獎
    # ==========================

    @discord.ui.button(
        label="🎁 第一次抽獎｜500 努努幣",
        style=discord.ButtonStyle.primary,
        custom_id="halloween_lottery_first",
        row=0,
    )
    async def first_draw(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        if not is_halloween_day():

            await interaction.response.send_message(
                "🎃 萬聖節限定盲盒目前沒有開放喔！\n"
                "本活動僅限 **2026/10/31** 當日參與。",
                ephemeral=True,
            )

            return

        count = get_limited_lottery_count(
            interaction.user.id
        )

        if count >= LIMITED_LOTTERY_MAX_TIMES:

            await interaction.response.send_message(
                "❌ 你已經完成本次萬聖節限定盲盒的 **2 次抽獎**。",
                ephemeral=True,
            )

            return

        if count != 0:

            await interaction.response.send_message(
                "⚠️ 你已經使用過第一次抽獎機會了。\n"
                "如果還有剩餘次數，請使用 **第二次抽獎｜5,000 努努幣**。",
                ephemeral=True,
            )

            return

        await run_limited_lottery(
            interaction,
            draw_number=1,
            price=LIMITED_LOTTERY_FIRST_PRICE,
        )

    # ==========================
    # 🎟️ 第二次抽獎
    # ==========================

    @discord.ui.button(
        label="🎃 第二次抽獎｜5,000 努努幣",
        style=discord.ButtonStyle.success,
        custom_id="halloween_lottery_second",
        row=1,
    )
    async def second_draw(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        if not is_halloween_day():

            await interaction.response.send_message(
                "🎃 萬聖節限定盲盒目前沒有開放喔！\n"
                "本活動僅限 **2026/10/31** 當日參與。",
                ephemeral=True,
            )

            return

        count = get_limited_lottery_count(
            interaction.user.id
        )

        if (
            count == 0
            and interaction.user.id not in BOT_ADMINS
        ):

            await interaction.response.send_message(
                "❌ 你還沒有進行第一次抽獎。\n\n"
                "請先完成 **第一次抽獎｜500 努努幣**，"
                "才能進行第二次抽獎。",
                ephemeral=True,
            )

            return

        if count >= LIMITED_LOTTERY_MAX_TIMES:

            await interaction.response.send_message(
                "❌ 你已經完成本次萬聖節限定盲盒的 **2 次抽獎**。",
                ephemeral=True,
            )

            return

        await run_limited_lottery(
            interaction,
            draw_number=2,
            price=LIMITED_LOTTERY_SECOND_PRICE,
        )


# ==========================
# 🎃 萬聖節限定盲盒 Embed
# ==========================

def create_limited_lottery_embed():

    embed = discord.Embed(
        title="🎃 萬聖節限定盲盒",
        description=(
            "🎃 **一年一度的萬聖節限定活動！**\n\n"
            "10/31 萬聖節當日限定開放，\n"
            "每位成員最多可以參與 **2 次**。\n\n"

            "━━━━━━━━━━━━━━━━━━\n\n"

            "🎁 **盲盒獎品**\n\n"
            "💰 努努幣 5,000　｜　40%\n"
            "💰 努努幣 8,000　｜　30%\n"
            "🎨 角色 Q 版貼圖 ×1　｜　20%\n"
            "💕 角色合照 ×1　｜　10%\n\n"

            "━━━━━━━━━━━━━━━━━━\n\n"

            "📌 **角色獎品領取方式**\n\n"

            "🎨 **角色 Q 版貼圖**\n"
            "💕 **角色合照**\n\n"

            "抽到角色獎品後，\n"
            "點擊抽獎結果中的按鈕，\n"
            "選擇指定媽咪，\n"
            "再輸入角色名稱。\n\n"

            "📩 確認後機器人會自動通知指定媽咪。\n\n"

            "⚠️ **每份角色獎品只能提交一次。**\n\n"

            "━━━━━━━━━━━━━━━━━━\n\n"

            "🎟️ **抽獎費用**\n\n"
            "第一次　→　💰 **500 努努幣**\n"
            "第二次　→　💰 **5,000 努努幣**\n\n"

            "每人最多 **2 次**，每次皆為獨立抽獎。\n\n"

            "🎃 **萬聖節限定，只有一天！**"
        ),
        color=0xF5B041,
    )

    embed.set_footer(
        text="🎃 Moon Bot｜萬聖節限定盲盒｜2026/10/31"
    )

    return embed


# ==========================
# 🎃 發送萬聖節限定盲盒面板
# ==========================

async def send_limited_lottery_panel(
    channel
):

    embed = create_limited_lottery_embed()

    await channel.send(
        embed=embed,
        view=LimitedLotteryView(),
    )


# ==========================
# 🧪 萬聖節限定盲盒｜管理員測試指令
# ==========================

@app_commands.command(
    name="halloween_test",
    description="🎃 發送萬聖節限定盲盒測試面板",
)
async def limited_lottery_test(
    interaction: discord.Interaction,
):

    if interaction.user.id not in BOT_ADMINS:

        await interaction.response.send_message(
            "❌ 只有管理員可以使用這個測試指令。",
            ephemeral=True,
        )

        return

    await send_limited_lottery_panel(
        interaction.channel
    )

    await interaction.response.send_message(
        "✅ 萬聖節限定盲盒測試面板已發送！",
        ephemeral=True,
    )


# ==========================
# 🗑️ 清空盲盒抽獎紀錄｜確認視窗
# ==========================

class ClearLimitedLotteryConfirmView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=60
        )

    @discord.ui.button(
        label="🗑️ 確定清空",
        style=discord.ButtonStyle.danger,
    )
    async def confirm_clear(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        # ==========================
        # 🔒 再次確認管理員權限
        # ==========================

        if interaction.user.id not in BOT_ADMINS:

            await interaction.response.send_message(
                "❌ 只有管理員可以執行這個操作。",
                ephemeral=True,
            )

            return

        # ==========================
        # 🗑️ 清除正式玩家紀錄
        # ==========================

        try:

            c.execute(
                """
                SELECT COUNT(*)
                FROM halloween_lottery_entries
                WHERE is_test = 0
                """
            )

            result = c.fetchone()

            deleted_count = (
                result[0]
                if result
                else 0
            )

            c.execute(
                """
                DELETE FROM halloween_lottery_entries
                WHERE is_test = 0
                """
            )

            conn.commit()

        except Exception as e:

            conn.rollback()

            await interaction.response.edit_message(
                content=(
                    "❌ **清空盲盒抽獎紀錄失敗。**\n\n"
                    f"錯誤：`{e}`"
                ),
                embed=None,
                view=None,
            )

            return

        # ==========================
        # ✅ 清空完成
        # ==========================

        await interaction.response.edit_message(
            content=(
                "✅ **盲盒抽獎紀錄已清空！**\n\n"
                f"🗑️ 已清除正式玩家紀錄："
                f"**{deleted_count} 筆**\n"
                "🧪 管理員測試紀錄：**保留**\n\n"
                "現在所有玩家都會重新從第 1 次抽獎開始計算。"
            ),
            embed=None,
            view=None,
        )

    @discord.ui.button(
        label="❌ 取消",
        style=discord.ButtonStyle.secondary,
    )
    async def cancel_clear(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        if interaction.user.id not in BOT_ADMINS:

            await interaction.response.send_message(
                "❌ 只有管理員可以操作這個視窗。",
                ephemeral=True,
            )

            return

        await interaction.response.edit_message(
            content="✅ 已取消，盲盒抽獎紀錄沒有被清除。",
            embed=None,
            view=None,
        )


# ==========================
# 🗑️ 清空盲盒抽獎紀錄
# ==========================

@app_commands.command(
    name="clear_lottery_records",
    description="🗑️ 清空盲盒抽獎紀錄",
)
async def clear_limited_lottery_records(
    interaction: discord.Interaction,
):

    if interaction.user.id not in BOT_ADMINS:

        await interaction.response.send_message(
            "❌ 只有管理員可以使用這個指令。",
            ephemeral=True,
        )

        return

    await interaction.response.send_message(
        "⚠️ **清空盲盒抽獎紀錄**\n\n"
        "確定要清除所有玩家的正式盲盒抽獎紀錄嗎？\n\n"
        "🗑️ 會刪除：**正式玩家抽獎紀錄**\n"
        "🧪 不會刪除：**管理員測試紀錄**\n\n"
        "這個操作完成後無法復原。",
        view=ClearLimitedLotteryConfirmView(),
        ephemeral=True,
    )


# ==========================
# 🎃 萬聖節活動｜自動開關頻道
# ==========================

_halloween_bot = None


async def update_halloween_channel():

    global _halloween_bot

    bot = _halloween_bot

    if bot is None:
        return

    # 🧪 測試模式完全不修改頻道權限
    if HALLOWEEN_TEST_MODE:
        return

    channel = bot.get_channel(
        HALLOWEEN_CHANNEL_ID
    )

    if channel is None:

        try:

            channel = await bot.fetch_channel(
                HALLOWEEN_CHANNEL_ID
            )

        except Exception as e:

            print(
                f"⚠️ 無法取得萬聖節活動頻道：{e}"
            )

            return

    if not isinstance(
        channel,
        discord.TextChannel,
    ):
        print(
            "⚠️ 萬聖節活動頻道不是文字頻道，"
            "無法自動控制查看權限。"
        )

        return

    role = channel.guild.get_role(
        HALLOWEEN_ROLE_ID
    )

    if role is None:

        print(
            f"⚠️ 找不到萬聖節活動指定身分組："
            f"{HALLOWEEN_ROLE_ID}"
        )

        return

    now = get_halloween_now()
    start = get_halloween_start()
    end = get_halloween_end()

    # ==========================
    # 🔓 活動期間｜開放指定身分組
    # ==========================

    if start <= now < end:

        try:

            overwrite = channel.overwrites_for(
                role
            )

            overwrite.view_channel = True

            await channel.set_permissions(
                role,
                overwrite=overwrite,
                reason="🎃 萬聖節限定盲盒活動開始",
            )

        except Exception as e:

            print(
                f"⚠️ 開放萬聖節活動頻道失敗：{e}"
            )

        return

    # ==========================
    # ⏳ 尚未開始｜關閉指定身分組
    # ==========================

    if now < start:

        try:

            overwrite = channel.overwrites_for(
                role
            )

            overwrite.view_channel = False

            await channel.set_permissions(
                role,
                overwrite=overwrite,
                reason="🎃 萬聖節限定盲盒活動尚未開始",
            )

        except Exception as e:

            print(
                f"⚠️ 設定萬聖節活動未開始權限失敗：{e}"
            )

        return

    # ==========================
    # 🔒 活動結束｜關閉指定身分組
    # ==========================

    try:

        overwrite = channel.overwrites_for(
            role
        )

        overwrite.view_channel = False

        await channel.set_permissions(
            role,
            overwrite=overwrite,
            reason="🎃 萬聖節限定盲盒活動結束",
        )

    except Exception as e:

        print(
            f"⚠️ 關閉萬聖節活動頻道失敗：{e}"
        )


@tasks.loop(minutes=1)
async def halloween_activity_loop():

    await update_halloween_channel()


@halloween_activity_loop.before_loop
async def before_halloween_activity_loop():

    global _halloween_bot

    if _halloween_bot is not None:

        await _halloween_bot.wait_until_ready()


# ==========================
# 🖼️ 萬聖節角色獎品｜接收玩家圖片
# ==========================



# ==========================
# 🎃 媽咪處理圖片｜完成並刪除案件訊息
# ==========================

class HalloweenImageCompleteView(discord.ui.View):
    """媽咪確認完成後，刪除收到的案件訊息與圖片附件。"""

    def __init__(self, entry_id: int, mommy_user_id: int):
        super().__init__(timeout=None)
        self.entry_id = int(entry_id)
        self.mommy_user_id = int(mommy_user_id)

        button = discord.ui.Button(
            label="✅ 完成並關閉（刪除圖片）",
            style=discord.ButtonStyle.success,
            custom_id=f"halloween_image_complete:{self.entry_id}",
        )
        button.callback = self.complete
        self.add_item(button)

    async def complete(self, interaction: discord.Interaction):
        if interaction.user.id != self.mommy_user_id and interaction.user.id not in BOT_ADMINS:
            await interaction.response.send_message(
                "❌ 只有這筆紀錄指定的媽咪或授權管理員可以完成並關閉。",
                ephemeral=True,
            )
            return

        c.execute(
            "SELECT image_status, mommy_user_id FROM halloween_lottery_entries WHERE id=?",
            (self.entry_id,),
        )
        row = c.fetchone()
        if not row or row["image_status"] != "forwarded":
            await interaction.response.send_message(
                "ℹ️ 這筆圖片案件已處理，或目前不需要處理。",
                ephemeral=True,
            )
            return

        if int(row["mommy_user_id"]) != interaction.user.id and interaction.user.id not in BOT_ADMINS:
            await interaction.response.send_message(
                "❌ 你不是這筆圖片案件指定的媽咪，無法完成。",
                ephemeral=True,
            )
            return

        c.execute(
            """
            UPDATE halloween_lottery_entries
            SET image_status='completed'
            WHERE id=? AND image_status='forwarded'
            """,
            (self.entry_id,),
        )
        changed = c.rowcount == 1
        conn.commit()
        if not changed:
            await interaction.response.send_message(
                "ℹ️ 這筆圖片案件已由其他人處理。",
                ephemeral=True,
            )
            return

        # 刪除媽咪收到的機器人訊息，圖片附件副本會隨訊息一起刪除。
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await interaction.message.delete()
            await interaction.followup.send(
                "✅ 已完成並關閉這筆萬聖節圖片案件，收到的圖片訊息已刪除。",
                ephemeral=True,
            )
        except discord.NotFound:
            await interaction.followup.send(
                "✅ 已標記完成；圖片案件訊息已不存在。",
                ephemeral=True,
            )
        except (discord.Forbidden, discord.HTTPException):
            await interaction.followup.send(
                "⚠️ 已標記完成，但機器人無法刪除這則訊息。請確認機器人仍有刪除訊息的權限。",
                ephemeral=True,
            )

async def halloween_image_submission_listener(message: discord.Message):

    # 只接收玩家傳給機器人的私訊圖片
    if message.author.bot or message.guild is not None:
        return

    if not message.attachments:
        return

    user_id = str(message.author.id)

    # 如果玩家的 Moon Club 成就盲盒有待交圖片，讓原本的成就系統處理，避免兩個監聽器重複轉交同一張圖。
    try:
        c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='moon_achievement_redemptions'"
        )
        if c.fetchone():
            c.execute(
                "SELECT redemption_id FROM moon_achievement_redemptions "
                "WHERE user_id=? AND status='awaiting_image' LIMIT 1",
                (message.author.id,),
            )
            if c.fetchone():
                return
    except Exception:
        pass

    c.execute(
        """
        SELECT id, prize_type, mommy_user_id, mommy_name,
               character_name, prize_value
        FROM halloween_lottery_entries
        WHERE user_id = ?
          AND is_test = ?
          AND claim_status = 1
          AND image_status = 'awaiting_image'
          AND prize_type IN ('sticker', 'couple')
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id, 1 if message.author.id in BOT_ADMINS else 0),
    )
    entry = c.fetchone()

    if not entry:
        return

    if len(message.attachments) != 1:
        await message.channel.send(
            "🎃 請一次只傳送 **一張圖片**，目前這筆領獎資料仍在等待圖片。"
        )
        return

    attachment = message.attachments[0]
    content_type = (attachment.content_type or "").lower()
    filename = (attachment.filename or "").lower()
    image_extensions = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")
    if not content_type.startswith("image/") and not filename.endswith(image_extensions):
        await message.channel.send(
            "❌ 這個檔案不是圖片，請重新傳送 PNG、JPG 或其他圖片格式。"
        )
        return

    mommy = message.guild.get_member(int(entry["mommy_user_id"])) if message.guild else None
    if mommy is None:
        try:
            mommy = await _halloween_bot.fetch_user(int(entry["mommy_user_id"]))
        except Exception:
            mommy = None

    if mommy is None:
        await message.channel.send(
            "⚠️ 目前無法找到指定媽咪，圖片尚未轉交。請稍後再試或聯絡管理員。"
        )
        return

    prize_display = {
        "sticker": "🎨 角色 Q 版貼圖 ×1",
        "couple": "💕 角色合照 ×1",
    }.get(entry["prize_type"], entry["prize_type"])

    embed = discord.Embed(
        title="🎃 萬聖節限定盲盒｜角色圖片提交",
        description=(
            f"👤 **玩家**：{message.author.mention}\n"
            f"🎁 **獎品**：{prize_display}\n"
            f"🎭 **角色名稱**：{entry['character_name']}\n"
            f"🧡 **指定媽咪**：{entry['mommy_name']}\n\n"
            "玩家已提交角色圖片，請協助後續獎品安排。"
        ),
        color=0xFF7518,
    )
    embed.set_footer(text=f"Moon Bot｜萬聖節限定盲盒｜紀錄編號 {entry['id']}")

    try:
        await mommy.send(
            embed=embed,
            file=await attachment.to_file(),
            view=HalloweenImageCompleteView(
                int(entry["id"]),
                int(entry["mommy_user_id"]),
            ),
        )
    except Exception as e:
        print(f"⚠️ 萬聖節角色圖片轉交失敗（紀錄 {entry['id']}）：{e}")
        await message.channel.send(
            "⚠️ 圖片目前沒有成功轉交給指定媽咪，這筆資料仍保留等待狀態。請稍後重新傳送圖片。"
        )
        return

    c.execute(
        """
        UPDATE halloween_lottery_entries
        SET image_status = 'forwarded', image_message_id = ?
        WHERE id = ? AND image_status = 'awaiting_image'
        """,
        (str(message.id), entry["id"]),
    )
    conn.commit()

    await message.channel.send(
        f"✅ 角色圖片已成功轉交給 **{entry['mommy_name']}**！\n"
        "請等待媽咪後續安排，謝謝你參與萬聖節限定盲盒。"
    )


# ==========================
# 🎃 啟動限定盲盒系統
# ==========================

def setup_limited_lottery(bot):

    global _halloween_bot

    _halloween_bot = bot

    init_limited_lottery_database()

    # 重新啟動後，重新註冊尚未完成的圖片案件按鈕。
    try:
        c.execute(
            "SELECT id, mommy_user_id FROM halloween_lottery_entries "
            "WHERE image_status='forwarded' AND mommy_user_id IS NOT NULL"
        )
        for pending_entry in c.fetchall():
            bot.add_view(
                HalloweenImageCompleteView(
                    int(pending_entry["id"]),
                    int(pending_entry["mommy_user_id"]),
                )
            )
    except Exception as e:
        print(f"⚠️ 萬聖節圖片完成按鈕重新註冊失敗：{e}")

    if not getattr(bot, "_halloween_image_listener_ready", False):
        bot.add_listener(halloween_image_submission_listener, "on_message")
        bot._halloween_image_listener_ready = True

    # -------------------------
    # 🎃 註冊永久盲盒按鈕
    # -------------------------

    bot.add_view(
        LimitedLotteryView()
    )

    # -------------------------
    # 🧪 註冊管理員測試指令
    # -------------------------

    if bot.tree.get_command(
        "halloween_test"
    ) is None:

        bot.tree.add_command(
            limited_lottery_test
        )

    # -------------------------
    # 🗑️ 註冊清空盲盒抽獎紀錄指令
    # -------------------------

    if bot.tree.get_command(
        "clear_lottery_records"
    ) is None:

        bot.tree.add_command(
            clear_limited_lottery_records
        )

    # -------------------------
    # 🎃 啟動活動自動開關
    # -------------------------

    if not HALLOWEEN_TEST_MODE:

        if not halloween_activity_loop.is_running():

            halloween_activity_loop.start()

        print(
            "🎃 萬聖節活動頻道自動開關已啟動"
        )

    else:

        print(
            "🧪 萬聖節盲盒目前為測試模式，"
            "不執行自動頻道開關"
        )

    print(
        "✅ 萬聖節限定盲盒系統已載入"
    )
