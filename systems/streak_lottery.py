# ==========================
# 🌙 Moon Bot｜簽到條件抽獎系統
# systems/streak_lottery.py
# ==========================

import asyncio
import random
from datetime import datetime, timedelta

import discord

from database import conn, c


# ==========================
# 🌙 系統設定
# ==========================

STREAK_LOTTERY_TABLE = "streak_lotteries"
STREAK_ENTRY_TABLE = "streak_lottery_entries"

LOTTERY_CHANNEL = None
LOTTERY_MANAGERS = []
LOTTERY_PING_ROLE = None

_checker_started = False


# ==========================
# 💾 建立資料表
# ==========================

def setup_streak_lottery_database():

    c.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {STREAK_LOTTERY_TABLE} (

            message_id TEXT PRIMARY KEY,
            channel_id TEXT NOT NULL,
            host_id TEXT NOT NULL,

            prize TEXT NOT NULL,
            winner_count INTEGER NOT NULL,

            end_time TEXT NOT NULL,

            check_type TEXT NOT NULL,
            required_days INTEGER NOT NULL,

            extra_condition TEXT,

            status TEXT NOT NULL DEFAULT 'running',
            winners TEXT,

            created_at TEXT NOT NULL
        )
        """
    )

    c.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {STREAK_ENTRY_TABLE} (

            message_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            joined_at TEXT NOT NULL,

            PRIMARY KEY (message_id, user_id)
        )
        """
    )

    conn.commit()


# ==========================
# ⏰ 計算抽獎結束時間
# ==========================

def get_streak_lottery_end_time(
    amount,
    unit,
):

    unit = unit.upper()

    if amount <= 0:
        return None

    if unit == "S":

        return datetime.now() + timedelta(
            seconds=amount
        )

    elif unit == "M":

        return datetime.now() + timedelta(
            minutes=amount
        )

    elif unit == "H":

        return datetime.now() + timedelta(
            hours=amount
        )

    elif unit == "D":

        return datetime.now() + timedelta(
            days=amount
        )

    return None


# ==========================
# 👤 取得玩家簽到資料
# ==========================

def get_user_checkin_data(user_id):

    c.execute(
        """
        SELECT
            checkin_total,
            checkin_streak
        FROM users
        WHERE user_id=?
        """,
        (str(user_id),),
    )

    row = c.fetchone()

    if not row:
        return 0, 0

    return (
        row["checkin_total"] or 0,
        row["checkin_streak"] or 0,
    )


# ==========================
# 👥 取得參加者
# ==========================

def get_streak_lottery_entries(message_id):

    c.execute(
        f"""
        SELECT user_id
        FROM {STREAK_ENTRY_TABLE}
        WHERE message_id=?
        ORDER BY joined_at ASC
        """,
        (str(message_id),),
    )

    rows = c.fetchall()

    return [
        row["user_id"]
        for row in rows
    ]


# ==========================
# 👑 檢查抽獎管理權限
# ==========================

def is_streak_lottery_manager(user_id):

    return user_id in LOTTERY_MANAGERS


# ==========================
# 🎨 建立抽獎 Embed
# ==========================

def create_streak_lottery_embed(
    lottery,
    entries=None,
    winners=None,
):

    if entries is None:
        entries = []

    if winners is None:
        winners = []

    end_time = datetime.fromisoformat(
        lottery["end_time"]
    )

    timestamp = int(
        end_time.timestamp()
    )

    embed = discord.Embed(
        title="🎉 Moon Bot｜簽到抽獎",
        color=0xF1C40F,
    )

    # ==========================
    # 🎁 獎品
    # ==========================

    embed.add_field(
        name="🎁 獎品",
        value=lottery["prize"],
        inline=False,
    )

    # ==========================
    # 👥 中獎人數
    # ==========================

    embed.add_field(
        name="👥 中獎人數",
        value=f'{lottery["winner_count"]} 人',
        inline=True,
    )

    # ==========================
    # 👤 主辦人
    # ==========================

    embed.add_field(
        name="👤 主辦人",
        value=f'<@{lottery["host_id"]}>',
        inline=True,
    )

    # ==========================
    # 🎯 簽到資格
    # ==========================

    if lottery["check_type"] == "streak":

        qualification = (
            f'🔥 連續簽到 **{lottery["required_days"]} 天以上**'
        )

    else:

        qualification = (
            f'📅 總簽到 **{lottery["required_days"]} 天以上**'
        )

    embed.add_field(
        name="🎯 參加資格",
        value=qualification,
        inline=False,
    )


    # ==========================
    # ⏰ 抽獎截止
    # ==========================

    embed.add_field(
        name="⏰ 抽獎截止",
        value=(
            f"<t:{timestamp}:F>\n"
            f"<t:{timestamp}:R>"
        ),
        inline=False,
    )

    # ==========================
    # 🟢 進行中
    # ==========================

    if lottery["status"] == "running":

        embed.add_field(
            name="👥 目前參加人數",
            value=f"{len(entries)} 人",
            inline=True,
        )

        embed.add_field(
            name="📌 狀態",
            value="🟢 進行中",
            inline=True,
        )

        embed.set_footer(
            text="點擊下方按鈕即可參加抽獎"
        )

    # ==========================
    # 🔴 已結束
    # ==========================

    else:

        # -------------------------
        # 👥 參加者
        # -------------------------

        if entries:

            entry_mentions = "\n".join(
                f"• <@{user_id}>"
                for user_id in entries
            )

        else:

            entry_mentions = (
                "📭 本次沒有玩家參加抽獎。"
            )

        # Discord Embed 欄位限制
        if len(entry_mentions) > 1000:

            entry_mentions = (
                entry_mentions[:950]
                + "\n……參加者過多，部分未顯示"
            )

        # -------------------------
        # 🏆 中獎者
        # -------------------------

        if winners:

            winner_mentions = "\n".join(
                f"🏆 <@{user_id}>"
                for user_id in winners
            )

        else:

            winner_mentions = (
                "📭 本次沒有中獎者。"
            )

        embed.add_field(
            name="👥 參加人數",
            value=f"{len(entries)} 人",
            inline=True,
        )

        embed.add_field(
            name="📌 狀態",
            value="🔴 已結束",
            inline=True,
        )

        embed.add_field(
            name="👥 參加者",
            value=entry_mentions,
            inline=False,
        )

        embed.add_field(
            name="🏆 中獎者",
            value=winner_mentions,
            inline=False,
        )

        embed.set_footer(
            text="🌙 本次簽到抽獎已結束"
        )

    return embed


# ==========================
# 🎉 進行中抽獎 View
# ==========================

class StreakLotteryView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="🎉 參加抽獎",
        style=discord.ButtonStyle.success,
        custom_id="streak_lottery_join",
    )
    async def join_lottery(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        message_id = str(interaction.message.id)

        c.execute(
            f"""
            SELECT * FROM {STREAK_LOTTERY_TABLE}
            WHERE message_id=?
            """,
            (message_id,),
        )

        lottery = c.fetchone()

        if not lottery:
            await interaction.response.send_message(
                "❌ 找不到本次抽獎資料。",
                ephemeral=True,
            )
            return

        if lottery["status"] != "running":
            await interaction.response.send_message(
                "🔒 本次抽獎已結束。",
                ephemeral=True,
            )
            return

        c.execute(
            f"""
            SELECT 1
            FROM {STREAK_ENTRY_TABLE}
            WHERE message_id=?
            AND user_id=?
            """,
            (
                message_id,
                str(interaction.user.id),
            ),
        )

        if c.fetchone():
            await interaction.response.send_message(
                "⚠️ 你已經參加過本次抽獎了！",
                ephemeral=True,
            )
            return

        checkin_total, checkin_streak = get_user_checkin_data(
            interaction.user.id
        )

        required_days = lottery["required_days"]

        if lottery["check_type"] == "streak":

            current_days = checkin_streak

            if current_days < required_days:

                missing = required_days - current_days

                await interaction.response.send_message(
                    (
                        "❌ 你尚未符合本次抽獎資格！\n\n"
                        f"🔥 目前連續簽到：**{current_days} 天**\n"
                        f"🎯 需要連續簽到：**{required_days} 天**\n\n"
                        f"🌙 還差 **{missing} 天**！"
                    ),
                    ephemeral=True,
                )
                return

        elif lottery["check_type"] == "total":

            current_days = checkin_total

            if current_days < required_days:

                missing = required_days - current_days

                await interaction.response.send_message(
                    (
                        "❌ 你尚未符合本次抽獎資格！\n\n"
                        f"📅 目前總簽到：**{current_days} 天**\n"
                        f"🎯 需要總簽到：**{required_days} 天**\n\n"
                        f"🌙 還差 **{missing} 天**！"
                    ),
                    ephemeral=True,
                )
                return

        c.execute(
            f"""
            INSERT INTO {STREAK_ENTRY_TABLE}
            (
                message_id,
                user_id,
                joined_at
            )
            VALUES (?, ?, ?)
            """,
            (
                message_id,
                str(interaction.user.id),
                datetime.now().isoformat(),
            ),
        )

        conn.commit()

        entries = get_streak_lottery_entries(
            message_id
        )

        embed = create_streak_lottery_embed(
            lottery,
            entries=entries,
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self,
        )

        await interaction.followup.send(
            "🎉 成功參加本次抽獎！祝你好運～",
            ephemeral=True,
        )

    @discord.ui.button(
        label="👥 查看名單",
        style=discord.ButtonStyle.secondary,
        custom_id="streak_lottery_view_entries",
    )
    async def view_entries(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        message_id = str(interaction.message.id)

        entries = get_streak_lottery_entries(
            message_id
        )

        if entries:

            entry_mentions = "\n".join(
                f"• <@{user_id}>"
                for user_id in entries
            )

            if len(entry_mentions) > 3900:

                entry_mentions = (
                    entry_mentions[:3850]
                    + "\n……名單過長，部分未顯示"
                )

        else:

            entry_mentions = (
                "📭 目前還沒有玩家參加抽獎。"
            )

        embed = discord.Embed(
            title="👥 本次抽獎參加名單",
            description=entry_mentions,
            color=0xF1C40F,
        )

        embed.set_footer(
            text=f"目前共有 {len(entries)} 人參加"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    @discord.ui.button(
        label="🛑 結束抽獎",
        style=discord.ButtonStyle.danger,
        custom_id="streak_lottery_manual_end",
    )
    async def manual_end(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        if not is_streak_lottery_manager(
            interaction.user.id
        ):

            await interaction.response.send_message(
                "❌ 只有抽獎管理員可以結束抽獎。",
                ephemeral=True,
            )
            return

        message_id = str(interaction.message.id)

        c.execute(
            f"""
            SELECT status
            FROM {STREAK_LOTTERY_TABLE}
            WHERE message_id=?
            """,
            (message_id,),
        )

        lottery = c.fetchone()

        if not lottery:
            await interaction.response.send_message(
                "❌ 找不到本次抽獎資料。",
                ephemeral=True,
            )
            return

        if lottery["status"] != "running":
            await interaction.response.send_message(
                "🔒 本次抽獎已經結束。",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "⚠️ 確定要提前結束本次抽獎嗎？\n"
            "確認後會立即抽出中獎者，且無法恢復。",
            view=ConfirmEndStreakLotteryView(
                message_id
            ),
            ephemeral=True,
        )


# ==========================
# ⚠️ 確認提前結束抽獎
# ==========================

class ConfirmEndStreakLotteryView(
    discord.ui.View
):

    def __init__(
        self,
        message_id,
    ):

        super().__init__(
            timeout=60
        )

        self.message_id = str(message_id)

    @discord.ui.button(
        label="✅ 確認結束抽獎",
        style=discord.ButtonStyle.danger,
    )
    async def confirm_end(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        if not is_streak_lottery_manager(
            interaction.user.id
        ):

            await interaction.response.send_message(
                "❌ 只有抽獎管理員可以結束抽獎。",
                ephemeral=True,
            )
            return

        c.execute(
            f"""
            SELECT status
            FROM {STREAK_LOTTERY_TABLE}
            WHERE message_id=?
            """,
            (self.message_id,),
        )

        lottery = c.fetchone()

        if not lottery:
            await interaction.response.edit_message(
                content="❌ 找不到本次抽獎資料。",
                view=None,
            )
            return

        if lottery["status"] != "running":
            await interaction.response.edit_message(
                content="🔒 本次抽獎已經結束。",
                view=None,
            )
            return

        await interaction.response.edit_message(
            content="⏳ 正在結束抽獎並抽出中獎者……",
            view=None,
        )

        await finish_streak_lottery(
            interaction.client,
            self.message_id,
        )

    @discord.ui.button(
        label="❌ 取消",
        style=discord.ButtonStyle.secondary,
    )
    async def cancel_end(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        await interaction.response.edit_message(
            content="✅ 已取消結束抽獎。",
            view=None,
        )


# ==========================
# 🔒 已結束 View
# ==========================

class EndedStreakLotteryView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="🔒 抽獎已結束",
        style=discord.ButtonStyle.secondary,
        disabled=True,
        custom_id="streak_lottery_ended",
    )
    async def ended_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        pass


# ==========================
# 📝 建立抽獎 Modal
# ==========================

class StreakLotteryModal(
    discord.ui.Modal,
    title="🎁 建立簽到抽獎",
):

    prize = discord.ui.TextInput(
        label="🎁 抽獎內容",
        placeholder="例如：Discord Nitro 一個月",
        required=True,
        max_length=200,
    )

    winners = discord.ui.TextInput(
        label="👥 中獎人數",
        placeholder="例如：3",
        required=True,
        max_length=3,
    )

    lottery_time = discord.ui.TextInput(
        label="⏰ 抽獎時間",
        placeholder="例如：10 D、30 M、2 H",
        required=True,
        max_length=10,
    )

    required_days = discord.ui.TextInput(
        label="🔢 需要簽到天數",
        placeholder="例如：7",
        required=True,
        max_length=6,
    )

    extra_condition = discord.ui.TextInput(
        label="📋 額外條件／需要的東西",
        placeholder="沒有可留空",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=1000,
    )

    def __init__(self, check_type):

        super().__init__()

        self.check_type = check_type


    async def on_submit(
        self,
        interaction: discord.Interaction,
    ):

        # ==========================
        # 🔢 驗證數字
        # ==========================

        try:

            winner_count = int(
                self.winners.value
            )

            required_days = int(
                self.required_days.value
            )

        except ValueError:

            await interaction.response.send_message(
                "❌ 中獎人數與需要簽到天數必須輸入數字。",
                ephemeral=True,
            )

            return

        # ==========================
        # 🔍 驗證時間
        # ==========================

        try:

            time_parts = (
                self.lottery_time.value
                .strip()
                .upper()
                .split()
            )

            if len(time_parts) != 2:
                raise ValueError

            time_amount = int(
                time_parts[0]
            )

            time_unit = time_parts[1]

        except ValueError:

            await interaction.response.send_message(
                (
                    "❌ 抽獎時間格式錯誤！\n\n"
                    "請使用例如：\n"
                    "`10 D` = 10 天\n"
                    "`30 M` = 30 分鐘\n"
                    "`2 H` = 2 小時\n"
                    "`60 S` = 60 秒"
                ),
                ephemeral=True,
            )

            return

        # ==========================
        # 🔢 數值檢查
        # ==========================

        if winner_count <= 0:

            await interaction.response.send_message(
                "❌ 中獎人數必須大於 0。",
                ephemeral=True,
            )

            return

        if time_amount <= 0:

            await interaction.response.send_message(
                "❌ 抽獎時間必須大於 0。",
                ephemeral=True,
            )

            return

        if required_days <= 0:

            await interaction.response.send_message(
                "❌ 需要簽到天數必須大於 0。",
                ephemeral=True,
            )

            return

        # ==========================
        # ⏰ 計算結束時間
        # ==========================

        end_time = (
            get_streak_lottery_end_time(
                time_amount,
                time_unit,
            )
        )

        if end_time is None:

            await interaction.response.send_message(
                (
                    "❌ 時間單位只能使用：\n\n"
                    "`S` = 秒\n"
                    "`M` = 分鐘\n"
                    "`H` = 小時\n"
                    "`D` = 天"
                ),
                ephemeral=True,
            )

            return

        # ==========================
        # 📋 額外條件
        # ==========================

        extra_condition = (
            self.extra_condition.value or ""
        ).strip()

        # ==========================
        # 🎨 建立抽獎資料
        # ==========================

        temporary_lottery = {

            "prize": (
                self.prize.value.strip()
            ),

            "winner_count": winner_count,

            "host_id": str(
                interaction.user.id
            ),

            "end_time": (
                end_time.isoformat()
            ),

            "check_type": self.check_type,

            "required_days": required_days,

            "extra_condition": extra_condition,

            "status": "running",
        }

        # ==========================
        # 🎨 建立 Embed
        # ==========================

        embed = create_streak_lottery_embed(
            temporary_lottery,
            entries=[],
        )

        # ==========================
        # 📤 發送抽獎
        # ==========================

        message = await interaction.channel.send(
            content=(
                f"<@&{LOTTERY_PING_ROLE}>"
                if LOTTERY_PING_ROLE
                else None
            ),
            embed=embed,
            view=StreakLotteryView(),
        )

        # ==========================
        # 💾 寫入資料庫
        # ==========================

        c.execute(
            f"""
            INSERT INTO {STREAK_LOTTERY_TABLE}
            (
                message_id,
                channel_id,
                host_id,
                prize,
                winner_count,
                end_time,
                check_type,
                required_days,
                extra_condition,
                status,
                winners,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(message.id),
                str(interaction.channel.id),
                str(interaction.user.id),

                self.prize.value.strip(),

                winner_count,

                end_time.isoformat(),

                self.check_type,

                required_days,

                extra_condition,

                "running",

                "",

                datetime.now().isoformat(),
            ),
        )

        conn.commit()

        # ==========================
        # ✅ 完成
        # ==========================

        timestamp = int(
            end_time.timestamp()
        )

        await interaction.response.send_message(
            (
                "✅ 簽到條件抽獎建立成功！\n\n"
                f"🎁 獎品：{self.prize.value}\n"
                f"⏰ 抽獎截止：<t:{timestamp}:F>"
            ),
            ephemeral=True,
        )


# ==========================
# 🎯 簽到類型選擇
# ==========================

class CheckTypeSelectView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=180
        )

    # ==========================
    # 🔥 連續簽到
    # ==========================

    @discord.ui.button(
        label="🔥 連續簽到天數",
        style=discord.ButtonStyle.danger,
    )
    async def streak_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        await interaction.response.send_modal(
            StreakLotteryModal(
                check_type="streak"
            )
        )

    # ==========================
    # 📅 總簽到
    # ==========================

    @discord.ui.button(
        label="📅 總簽到天數",
        style=discord.ButtonStyle.primary,
    )
    async def total_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        await interaction.response.send_modal(
            StreakLotteryModal(
                check_type="total"
            )
        )


# ==========================
# 🎲 結束抽獎
# ==========================

async def finish_streak_lottery(
    bot,
    message_id,
):

    # ==========================
    # 🔍 取得抽獎資料
    # ==========================

    c.execute(
        f"""
        SELECT *
        FROM {STREAK_LOTTERY_TABLE}
        WHERE message_id=?
        """,
        (str(message_id),),
    )

    lottery = c.fetchone()

    if not lottery:
        return

    if lottery["status"] != "running":
        return

    # ==========================
    # 👥 取得參加者
    # ==========================

    entries = get_streak_lottery_entries(
        message_id
    )

    # ==========================
    # 🎲 隨機抽獎
    # ==========================

    if entries:

        actual_winner_count = min(
            lottery["winner_count"],
            len(entries),
        )

        winners = random.sample(
            entries,
            actual_winner_count,
        )

    else:

        winners = []

    # ==========================
    # 💾 更新抽獎狀態
    # ==========================

    winner_text = ",".join(
        winners
    )

    c.execute(
        f"""
        UPDATE {STREAK_LOTTERY_TABLE}
        SET
            status='ended',
            winners=?
        WHERE message_id=?
        """,
        (
            winner_text,
            str(message_id),
        ),
    )

    conn.commit()

    # ==========================
    # 📡 取得頻道
    # ==========================

    channel = bot.get_channel(
        int(lottery["channel_id"])
    )

    if channel is None:

        try:

            channel = await bot.fetch_channel(
                int(lottery["channel_id"])
            )

        except Exception as e:

            print(
                f"⚠️ 找不到簽到抽獎頻道：{e}"
            )

            return

    # ==========================
    # 📨 取得原始訊息
    # ==========================

    try:

        message = await channel.fetch_message(
            int(message_id)
        )

    except Exception as e:

        print(
            f"⚠️ 找不到簽到抽獎訊息：{e}"
        )

        return

    # ==========================
    # 🎨 重新取得結束資料
    # ==========================

    c.execute(
        f"""
        SELECT *
        FROM {STREAK_LOTTERY_TABLE}
        WHERE message_id=?
        """,
        (str(message_id),),
    )

    ended_lottery = c.fetchone()

    embed = create_streak_lottery_embed(
        ended_lottery,
        entries=entries,
        winners=winners,
    )

    await message.edit(
        embed=embed,
        view=EndedStreakLotteryView(),
    )

    # ==========================
    # 💌 私訊中獎者
    # ==========================

    for user_id in winners:

        try:

            user = bot.get_user(
                int(user_id)
            )

            if user is None:

                user = await bot.fetch_user(
                    int(user_id)
                )

            extra_condition = (
                lottery["extra_condition"] or ""
            ).strip()

            if extra_condition:

                provide_text = extra_condition

            else:

                provide_text = (
                    "請提供主辦人要求的品項私訊主辦人"
                )

            dm_embed = discord.Embed(
                title="🌙 Moon Bot｜抽獎通知",
                description=(
                    "🎉 恭喜你在本次抽獎中幸運中獎！\n\n"
                    "━━━━━━━━━━━━━━━━━━\n\n"
                    "請私訊主辦人，並提供：\n\n"
                    f"💬 {provide_text}\n\n"
                    "💌 溫馨提醒 💌\n\n"
                    "📌 在任何公開平台發布與角色相關的圖片或影片時，"
                    "請加上浮水印。\n\n"
                    "📌 若需發布影片，請先私訊角色創作者確認內容，"
                    "經創作者同意後再公開發布。\n\n"
                    "📌 若不知道如何製作浮水印，"
                    "可請管理員協助處理。\n\n"
                    f'🎁 **獎品**\n{lottery["prize"]}\n\n'
                    f'👤 **主辦人**\n<@{lottery["host_id"]}>'
                ),
                color=discord.Color.gold(),
            )

            dm_embed.set_footer(
                text="🌙 本訊息由 Moon Bot 自動發送"
            )

            await user.send(
                embed=dm_embed
            )

        except discord.Forbidden:

            print(
                f"⚠️ 無法私訊中獎者 {user_id}"
            )

        except Exception as e:

            print(
                f"⚠️ 發送中獎通知失敗：{e}"
            )


# ==========================
# ⏰ 自動檢查抽獎
# ==========================

async def streak_lottery_checker(
    bot,
):

    await bot.wait_until_ready()

    while not bot.is_closed():

        try:

            now = datetime.now()

            c.execute(
                f"""
                SELECT
                    message_id,
                    end_time
                FROM {STREAK_LOTTERY_TABLE}
                WHERE status='running'
                """
            )

            lotteries = c.fetchall()

            for lottery in lotteries:

                end_time = (
                    datetime.fromisoformat(
                        lottery["end_time"]
                    )
                )

                if now >= end_time:

                    await finish_streak_lottery(
                        bot,
                        lottery["message_id"],
                    )

        except Exception as e:

            print(
                f"⚠️ 簽到抽獎自動檢查失敗：{e}"
            )

        await asyncio.sleep(10)


# ==========================
# 🌙 系統初始化
# ==========================

def setup_streak_lottery(
    bot,
    lottery_channel,
    lottery_managers,
    lottery_ping_role,
):

    global LOTTERY_CHANNEL
    global LOTTERY_MANAGERS
    global LOTTERY_PING_ROLE
    global _checker_started

    LOTTERY_CHANNEL = lottery_channel
    LOTTERY_MANAGERS = lottery_managers
    LOTTERY_PING_ROLE = lottery_ping_role

    # ==========================
    # 💾 建立資料表
    # ==========================

    setup_streak_lottery_database()

    # ==========================
    # 📌 Slash Command
    # ==========================

    @bot.tree.command(
        name="簽到抽獎",
        description="建立簽到條件抽獎",
    )
    async def streak_lottery_command(
        interaction: discord.Interaction,
    ):

        # ==========================
        # 📍 頻道限制
        # ==========================

        if (
            interaction.channel.id
            != LOTTERY_CHANNEL
        ):

            await interaction.response.send_message(
                "❌ 請至抽獎頻道使用此指令。",
                ephemeral=True,
            )

            return

        # ==========================
        # 👑 管理員限制
        # ==========================

        if (
            interaction.user.id
            not in LOTTERY_MANAGERS
        ):

            await interaction.response.send_message(
                "❌ 只有抽獎管理員可以建立抽獎。",
                ephemeral=True,
            )

            return

        # ==========================
        # 🎯 選擇資格類型
        # ==========================

        embed = discord.Embed(
            title="🎁 建立簽到條件抽獎",
            description=(
                "請選擇本次抽獎的簽到資格。\n\n"

                "🔥 **連續簽到天數**\n"
                "檢查玩家目前的連續簽到天數。\n\n"

                "📅 **總簽到天數**\n"
                "檢查玩家累積的總簽到天數。"
            ),
            color=0xF1C40F,
        )

        await interaction.response.send_message(
            embed=embed,
            view=CheckTypeSelectView(),
            ephemeral=True,
        )

    # ==========================
    # 🎉 註冊永久 View
    # ==========================

    bot.add_view(
        StreakLotteryView()
    )

    bot.add_view(
        EndedStreakLotteryView()
    )

    # ==========================
    # ⏰ Bot 準備完成後啟動檢查器
    # ==========================

    async def start_streak_lottery_checker():

        global _checker_started

        if _checker_started:
            return

        asyncio.create_task(
            streak_lottery_checker(bot)
        )

        _checker_started = True

    bot.add_listener(
        start_streak_lottery_checker,
        "on_ready"
    )

    print(
        "✅ 簽到條件抽獎系統已啟動"
    )