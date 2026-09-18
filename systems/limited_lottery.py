# -*- coding: utf-8 -*-

# ==========================
# 🌕 中秋限定盲盒抽獎系統
# ==========================

import discord
import random
import asyncio
from datetime import datetime
from discord import app_commands

from database import conn, c
from config import BOT_ADMINS


# ==========================
# 🌕 中秋限定盲盒設定
# ==========================

MID_AUTUMN_DATE = "2026-09-25"

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
# 🌕 中秋指定媽咪
# ==========================

MID_AUTUMN_MOMMIES = {
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
# 🌕 正在開盲盒的玩家
# ==========================

limited_lottery_running = set()


# ==========================
# 🌕 判斷是否為中秋活動日
# ==========================

def is_mid_autumn_day():

    # 🧪 測試期間暫時不限日期
    return True


# ==========================
# 🌕 取得玩家正式參與次數
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
        FROM limited_lottery_entries
        WHERE user_id = ?
        AND is_test = 0
        """,
        (str(user_id),),
    )

    result = c.fetchone()

    return result[0] if result else 0


# ==========================
# 🌕 檢查角色獎品是否已完成領獎
# ==========================

def is_prize_claimed(entry_id):

    c.execute(
        """
        SELECT claim_status
        FROM limited_lottery_entries
        WHERE id = ?
        """,
        (entry_id,),
    )

    result = c.fetchone()

    if not result:
        return True

    return int(result["claim_status"]) == 1


# ==========================
# 🌕 鎖定角色獎品
# ==========================

def claim_limited_prize(
    entry_id,
    user_id,
    mommy_key,
    character_name,
):

    mommy_data = MID_AUTUMN_MOMMIES.get(
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
        UPDATE limited_lottery_entries
        SET
            claim_status = 1,
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
# 🌕 角色獎品｜選擇指定媽咪
# ==========================

class MidAutumnMommySelect(
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

        for key, mommy in MID_AUTUMN_MOMMIES.items():

            options.append(
                discord.SelectOption(
                    label=mommy["name"],
                    value=key,
                    description="選擇這位媽咪處理本次角色獎品",
                )
            )

        super().__init__(
            placeholder="🌕 請選擇指定媽咪",
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

        mommy_data = MID_AUTUMN_MOMMIES.get(
            mommy_key
        )

        if not mommy_data:

            await interaction.response.send_message(
                "❌ 找不到指定的媽咪資料，請重新操作。",
                ephemeral=True,
            )

            return

        await interaction.response.send_modal(
            MidAutumnCharacterModal(
                entry_id=self.entry_id,
                mommy_key=mommy_key,
                prize_type=self.prize_type,
                prize_name=self.prize_name,
            )
        )


# ==========================
# 🌕 角色獎品｜選擇指定媽咪 View
# ==========================

class MidAutumnMommyView(
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
            MidAutumnMommySelect(
                entry_id=entry_id,
                prize_type=prize_type,
                prize_name=prize_name,
            )
        )


# ==========================
# 🌕 角色獎品｜輸入角色名稱
# ==========================

class MidAutumnCharacterModal(
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
            title="🌕 中秋限定｜角色資料"
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

        mommy_data = MID_AUTUMN_MOMMIES.get(
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
        # 🌕 建立通知 Embed
        # ==========================

        notification_embed = discord.Embed(
            title="🌕 中秋限定盲盒｜角色獎品通知",
            description=(
                "有玩家抽中了中秋限定角色獎品！\n\n"

                f"👤 **玩家**\n"
                f"{interaction.user.mention}\n\n"

                f"🎭 **角色名稱**\n"
                f"**{character_name}**\n\n"

                f"🎁 **獎品**\n"
                f"**{self.prize_name}**\n\n"

                f"🌕 **指定媽咪**\n"
                f"**{mommy_data['name']}**\n\n"

                "📌 玩家已完成領獎資料填寫，\n"
                "請協助後續獎品安排。"
            ),
            color=0xF5B041,
        )

        notification_embed.set_footer(
            text="🌕 Moon Bot｜中秋限定盲盒｜2026/9/25"
        )

        # ==========================
        # 📩 自動 DM 指定媽咪
        # ==========================

        dm_success = False

        if mommy:

            try:

                await mommy.send(
                    embed=notification_embed
                )

                dm_success = True

            except discord.Forbidden:

                dm_success = False

            except Exception:

                dm_success = False

        # ==========================
        # 🌕 玩家回覆
        # ==========================

        if dm_success:

            await interaction.response.send_message(
                "✅ **領獎資料已成功送出！**\n\n"

                f"🌕 指定媽咪：**{mommy_data['name']}**\n"
                f"🎭 角色名稱：**{character_name}**\n"
                f"🎁 獎品：**{self.prize_name}**\n\n"

                "📩 機器人已自動通知指定媽咪，\n"
                "請等待後續獎品安排。\n\n"

                "🔒 此份獎品的領獎資料已鎖定，"
                "無法再次提交。",
                ephemeral=True,
            )

        else:

            await interaction.response.send_message(
                "⚠️ **領獎資料已成功記錄，但通知媽咪失敗。**\n\n"

                f"🌕 指定媽咪：**{mommy_data['name']}**\n"
                f"🎭 角色名稱：**{character_name}**\n"
                f"🎁 獎品：**{self.prize_name}**\n\n"

                "⚠️ 資料已經鎖定，請聯絡管理員協助通知媽咪。",
                ephemeral=True,
            )


# ==========================
# 🌕 角色獎品｜填寫資料按鈕
# ==========================

class MidAutumnPrizeView(
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
        label="🌕 填寫角色資料",
        style=discord.ButtonStyle.primary,
        custom_id="mid_autumn_prize_info",
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
            "🌕 **中秋限定｜角色獎品資料**\n\n"
            "請選擇這次的**指定媽咪**。\n\n"
            "選擇後再輸入你的角色名稱，"
            "確認送出後機器人會自動通知該媽咪。",
            view=MidAutumnMommyView(
                entry_id=self.entry_id,
                prize_type=self.prize_type,
                prize_name=self.prize_name,
            ),
            ephemeral=True,
        )


# ==========================
# 🌕 執行中秋限定盲盒
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
    # 🔒 防止重複抽獎
    # -------------------------

    if interaction.user.id in limited_lottery_running:

        await interaction.response.send_message(
            "🌕 你的中秋盲盒正在開啟中，\n"
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
            INSERT INTO limited_lottery_entries (
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
        # 🌕 開始盲盒動畫
        # ==========================

        await interaction.response.send_message(
            "🌕 **中秋限定盲盒**\n\n"
            "🎁 你的盲盒正在準備中……",
            ephemeral=True,
        )

        # -------------------------
        # ✨ 第一階段
        # -------------------------

        await asyncio.sleep(1)

        await interaction.edit_original_response(
            content=(
                "🌕 **中秋限定盲盒**\n\n"
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
                "🌕 **中秋限定盲盒**\n\n"
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
                "🌕 **中秋限定盲盒**\n\n"
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

                "🌕 **請完成領獎資料**\n\n"

                "點擊下方按鈕後：\n"
                "① 選擇指定媽咪\n"
                "② 輸入角色名稱\n"
                "③ 按下確認送出\n\n"

                "📩 完成後機器人會自動通知指定媽咪。\n\n"

                "⚠️ **每份角色獎品只能提交一次。**"
            )

            result_view = MidAutumnPrizeView(
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
        # 🌕 最終結果 Embed
        # ==========================

        embed = discord.Embed(
            title="🌕 中秋限定盲盒",
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
                "🌕 Moon Bot｜中秋限定盲盒｜2026/9/25"
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
# 🌕 建立限定盲盒資料表
# ==========================

def init_limited_lottery_database():

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS limited_lottery_entries (
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
            claimed_at TEXT
        )
        """
    )

    # ==========================
    # 🌕 舊資料表補欄位
    # ==========================

    existing_columns = set()

    c.execute(
        """
        PRAGMA table_info(limited_lottery_entries)
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
                ALTER TABLE limited_lottery_entries
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
                ALTER TABLE limited_lottery_entries
                ADD COLUMN claim_status INTEGER DEFAULT 0
                """
            )

        except Exception:

            pass

    # -------------------------
    # 🌕 mommy_key
    # -------------------------

    if "mommy_key" not in existing_columns:

        try:

            c.execute(
                """
                ALTER TABLE limited_lottery_entries
                ADD COLUMN mommy_key TEXT
                """
            )

        except Exception:

            pass

    # -------------------------
    # 🌕 mommy_user_id
    # -------------------------

    if "mommy_user_id" not in existing_columns:

        try:

            c.execute(
                """
                ALTER TABLE limited_lottery_entries
                ADD COLUMN mommy_user_id TEXT
                """
            )

        except Exception:

            pass

    # -------------------------
    # 🌕 mommy_name
    # -------------------------

    if "mommy_name" not in existing_columns:

        try:

            c.execute(
                """
                ALTER TABLE limited_lottery_entries
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
                ALTER TABLE limited_lottery_entries
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
                ALTER TABLE limited_lottery_entries
                ADD COLUMN claimed_at TEXT
                """
            )

        except Exception:

            pass

    conn.commit()


# ==========================
# 🌕 中秋限定盲盒面板
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
        custom_id="mid_autumn_lottery_first",
        row=0,
    )
    async def first_draw(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        if not is_mid_autumn_day():

            await interaction.response.send_message(
                "🌕 中秋限定盲盒目前沒有開放喔！\n"
                "本活動僅限 **2026/9/25** 當日參與。",
                ephemeral=True,
            )

            return

        count = get_limited_lottery_count(
            interaction.user.id
        )

        if count >= LIMITED_LOTTERY_MAX_TIMES:

            await interaction.response.send_message(
                "❌ 你已經完成本次中秋限定盲盒的 **2 次抽獎**。",
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
        label="🌕 第二次抽獎｜5,000 努努幣",
        style=discord.ButtonStyle.success,
        custom_id="mid_autumn_lottery_second",
        row=1,
    )
    async def second_draw(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        if not is_mid_autumn_day():

            await interaction.response.send_message(
                "🌕 中秋限定盲盒目前沒有開放喔！\n"
                "本活動僅限 **2026/9/25** 當日參與。",
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
                "❌ 你已經完成本次中秋限定盲盒的 **2 次抽獎**。",
                ephemeral=True,
            )

            return

        await run_limited_lottery(
            interaction,
            draw_number=2,
            price=LIMITED_LOTTERY_SECOND_PRICE,
        )


# ==========================
# 🌕 中秋限定盲盒 Embed
# ==========================

def create_limited_lottery_embed():

    embed = discord.Embed(
        title="🌕 中秋限定盲盒",
        description=(
            "🌕 **一年一度的中秋限定活動！**\n\n"
            "9/25 中秋當日限定開放，\n"
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

            "🌕 **中秋限定，只有一天！**"
        ),
        color=0xF5B041,
    )

    embed.set_footer(
        text="🌕 Moon Bot｜中秋限定盲盒｜2026/9/25"
    )

    return embed


# ==========================
# 🌕 發送中秋限定盲盒面板
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
# 🧪 中秋限定盲盒｜管理員測試指令
# ==========================

@app_commands.command(
    name="mid_autumn_test",
    description="🌕 發送中秋限定盲盒測試面板",
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
        "✅ 中秋限定盲盒測試面板已發送！",
        ephemeral=True,
    )


# ==========================
# 🌕 啟動限定盲盒系統
# ==========================

def setup_limited_lottery(bot):

    init_limited_lottery_database()

    # -------------------------
    # 🌕 註冊永久盲盒按鈕
    # -------------------------

    bot.add_view(
        LimitedLotteryView()
    )

    # -------------------------
    # 🧪 註冊管理員測試指令
    # -------------------------

    if bot.tree.get_command(
        "mid_autumn_test"
    ) is None:

        bot.tree.add_command(
            limited_lottery_test
        )

    print(
        "✅ 中秋限定盲盒系統已載入"
    )
