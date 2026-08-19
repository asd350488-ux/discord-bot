# ==========================
# 🎂 Moon Bot v2｜角色生日系統
# ==========================

import discord
from discord.ext import tasks
from discord.ui import View, Select, Modal, TextInput

import sqlite3
from datetime import datetime, timedelta
import calendar
import pytz

from database import DB_PATH


# ==========================
# 🎂 基本設定
# ==========================

CHARACTER_BIRTHDAY_CHANNEL = 1510930723924611163

TIMEZONE = pytz.timezone("Asia/Taipei")


# ==========================
# 👑 可使用的媽咪
# ==========================

MOMMY_LIST = {
    "小貓媽咪": 1513814405585047622,
    "韓馨媽咪": 1153640526063607820,
    "星弦媽咪": 1218542666879598613,
    "曦兒媽咪": 1301905168094335028,
}


# ==========================
# 🗄️ 初始化資料庫
# ==========================


def init_character_birthday_db():

    conn = sqlite3.connect(DB_PATH)

    c = conn.cursor()

    # ==========================
    # 🎂 角色生日資料
    # ==========================

    c.execute("""
        CREATE TABLE IF NOT EXISTS character_birthdays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mommy_name TEXT NOT NULL,
            character_name TEXT NOT NULL,
            month INTEGER NOT NULL,
            day INTEGER NOT NULL,
            UNIQUE(mommy_name, character_name)
        )
    """)

    # ==========================
    # 🔔 提醒紀錄
    # ==========================

    c.execute("""
        CREATE TABLE IF NOT EXISTS character_birthday_reminders (
            reminder_date TEXT PRIMARY KEY
        )
    """)

    conn.commit()
    conn.close()


# 啟動時初始化資料表
init_character_birthday_db()


# ==========================
# 👑 媽咪選擇
# ==========================


class MommySelect(Select):

    def __init__(self):

        options = [
            discord.SelectOption(
                label=mommy_name,
                value=str(user_id),
                emoji="👑"
            )
            for mommy_name, user_id in MOMMY_LIST.items()
        ]

        super().__init__(
            placeholder="👑 請選擇要設定哪位媽咪",
            options=options
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        # ==========================
        # 🔐 頻道限制
        # ==========================

        if interaction.channel_id != CHARACTER_BIRTHDAY_CHANNEL:

            await interaction.response.send_message(
                "❌ 請至角色生日專用頻道使用此功能。",
                ephemeral=True
            )
            return

        # ==========================
        # 🔐 媽咪本人驗證
        # ==========================

        selected_user_id = int(self.values[0])

        if interaction.user.id != selected_user_id:

            await interaction.response.send_message(
                "❌ 你不能替其他媽咪設定角色生日。",
                ephemeral=True
            )
            return

        # ==========================
        # 👑 找到媽咪名稱
        # ==========================

        mommy_name = next(
            name
            for name, user_id in MOMMY_LIST.items()
            if user_id == selected_user_id
        )

        # ==========================
        # 🎂 開啟設定表單
        # ==========================

        await interaction.response.send_modal(
            CharacterBirthdayModal(mommy_name)
        )


# ==========================
# 🎂 角色生日 Modal
# ==========================


class CharacterBirthdayModal(Modal):

    def __init__(self, mommy_name):

        super().__init__(
            title="🎂 設定角色生日"
        )

        self.mommy_name = mommy_name

        # ==========================
        # 🎭 角色名稱
        # ==========================

        self.character_name = TextInput(
            label="🎭 角色名稱",
            placeholder="例如：黎沐昊",
            required=True,
            max_length=50
        )

        # ==========================
        # 🎂 角色生日
        # ==========================

        self.birthday = TextInput(
            label="🎂 角色生日",
            placeholder="例如：8/25",
            required=True,
            max_length=5
        )

        self.add_item(self.character_name)
        self.add_item(self.birthday)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        # ==========================
        # 📝 取得資料
        # ==========================

        character_name = self.character_name.value.strip()
        birthday_text = self.birthday.value.strip()

        # ==========================
        # ❌ 角色名稱檢查
        # ==========================

        if not character_name:

            await interaction.response.send_message(
                "❌ 角色名稱不能為空白。",
                ephemeral=True
            )
            return

        # ==========================
        # 🎂 生日格式檢查
        # ==========================

        try:

            parts = birthday_text.split("/")

            if len(parts) != 2:
                raise ValueError

            month = int(parts[0])
            day = int(parts[1])

        except (ValueError, TypeError):

            await interaction.response.send_message(
                "❌ 生日格式錯誤。\n\n"
                "請使用 **月/日** 格式，例如：`8/25`。",
                ephemeral=True
            )
            return

        # ==========================
        # 📅 月份檢查
        # ==========================

        if month < 1 or month > 12:

            await interaction.response.send_message(
                "❌ 月份必須介於 **1～12 月**。",
                ephemeral=True
            )
            return

        # ==========================
        # 📅 日期檢查
        # ==========================

        max_day = calendar.monthrange(
            2000,
            month
        )[1]

        if day < 1 or day > max_day:

            await interaction.response.send_message(
                f"❌ **{month}月** 沒有 **{day}日**。",
                ephemeral=True
            )
            return

        # ==========================
        # 💾 儲存資料
        # ==========================

        conn = sqlite3.connect(DB_PATH)

        c = conn.cursor()

        c.execute(
            """
            INSERT INTO character_birthdays
            (
                mommy_name,
                character_name,
                month,
                day
            )
            VALUES (?, ?, ?, ?)

            ON CONFLICT(mommy_name, character_name)
            DO UPDATE SET
                month = excluded.month,
                day = excluded.day
            """,
            (
                self.mommy_name,
                character_name,
                month,
                day
            )
        )

        conn.commit()
        conn.close()

        # ==========================
        # 🎉 完成
        # ==========================

        await interaction.response.send_message(
            "🎉 **角色生日設定完成！**\n\n"
            f"👑 媽咪：**{self.mommy_name}**\n"
            f"🎭 角色：**{character_name}**\n"
            f"🎂 生日：**{month}月{day}日**\n\n"
            "💾 生日資料已成功保存。",
            ephemeral=True
        )


# ==========================
# 🎂 設定生日 View
# ==========================


class CharacterBirthdaySettingView(View):

    def __init__(self):

        super().__init__(
            timeout=180
        )

        self.add_item(
            MommySelect()
        )


# ==========================
# 🎂 設定角色生日指令
# ==========================


async def setup_character_birthday_commands(bot):

    @bot.tree.command(
        name="設定角色生日",
        description="設定角色的生日"
    )
    async def set_character_birthday(
        interaction: discord.Interaction
    ):

        # ==========================
        # 🔐 頻道限制
        # ==========================

        if interaction.channel_id != CHARACTER_BIRTHDAY_CHANNEL:

            await interaction.response.send_message(
                "❌ 請至角色生日專用頻道使用此功能。",
                ephemeral=True
            )
            return

        # ==========================
        # 🎂 開始設定
        # ==========================

        await interaction.response.send_message(
            "🎂 **角色生日設定**\n\n"
            "請先選擇要設定哪位媽咪的角色生日。",
            view=CharacterBirthdaySettingView(),
            ephemeral=True
        )


# ==========================
# 🔍 查詢角色生日
# ==========================


async def show_character_birthdays(
    interaction: discord.Interaction
):

    conn = sqlite3.connect(DB_PATH)

    c = conn.cursor()

    c.execute(
        """
        SELECT mommy_name, character_name, month, day
        FROM character_birthdays
        ORDER BY month ASC, day ASC, mommy_name ASC
        """
    )

    rows = c.fetchall()

    conn.close()

    # ==========================
    # ❌ 沒有資料
    # ==========================

    if not rows:

        await interaction.response.send_message(
            "🎂 目前還沒有登記任何角色生日。",
            ephemeral=True
        )
        return

    # ==========================
    # 🎂 整理生日資料
    # ==========================

    birthday_text = ""

    for mommy_name, character_name, month, day in rows:

        birthday_text += (
            f"👑 **{mommy_name}**\n"
            f"└ 🎭 **{character_name}**　"
            f"🎂 {month}月{day}日\n\n"
        )

    # ==========================
    # 📋 Embed
    # ==========================

    embed = discord.Embed(
        title="🎂 角色生日一覽",
        description=birthday_text,
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="🌙 角色生日紀錄"
    )

    await interaction.response.send_message(
        embed=embed
    )


# ==========================
# 🎂 角色生日查詢指令
# ==========================


async def setup_character_birthday_query(bot):

    @bot.tree.command(
        name="角色生日",
        description="查看所有角色生日"
    )
    async def character_birthday(
        interaction: discord.Interaction
    ):

        # ==========================
        # 🔐 頻道限制
        # ==========================

        if interaction.channel_id != CHARACTER_BIRTHDAY_CHANNEL:

            await interaction.response.send_message(
                "❌ 請至角色生日專用頻道使用此功能。",
                ephemeral=True
            )
            return

        await show_character_birthdays(
            interaction
        )


# ==========================
# 🔔 檢查明日生日
# ==========================


async def check_character_birthdays(bot):

    now = datetime.now(TIMEZONE)

    # ==========================
    # 📅 計算明天
    # ==========================

    tomorrow = now + timedelta(days=1)

    tomorrow_month = tomorrow.month
    tomorrow_day = tomorrow.day

    reminder_date = tomorrow.strftime("%Y-%m-%d")

    # ==========================
    # 🗄️ 開啟資料庫
    # ==========================

    conn = sqlite3.connect(DB_PATH)

    c = conn.cursor()

    # ==========================
    # 🔔 是否已經提醒
    # ==========================

    c.execute(
        """
        SELECT 1
        FROM character_birthday_reminders
        WHERE reminder_date = ?
        """,
        (reminder_date,)
    )

    if c.fetchone():

        conn.close()
        return

    # ==========================
    # 🎂 查詢明日生日
    # ==========================

    c.execute(
        """
        SELECT mommy_name, character_name
        FROM character_birthdays
        WHERE month = ?
        AND day = ?
        ORDER BY mommy_name ASC, character_name ASC
        """,
        (
            tomorrow_month,
            tomorrow_day
        )
    )

    rows = c.fetchall()

    # ==========================
    # ❌ 沒有生日
    # ==========================

    if not rows:

        conn.close()
        return

    # ==========================
    # 📢 找到提醒頻道
    # ==========================

    channel = bot.get_channel(
        CHARACTER_BIRTHDAY_CHANNEL
    )

    if channel is None:

        conn.close()
        return

    # ==========================
    # 🎂 整理提醒內容
    # ==========================

    birthday_text = ""

    for mommy_name, character_name in rows:

        birthday_text += (
            f"👑 **{mommy_name}**\n"
            f"└ 🎭 **{character_name}**\n\n"
        )

    # ==========================
    # 🔔 發送提醒
    # ==========================

    embed = discord.Embed(
        title="🎂 明日角色生日提醒",
        description=(
            f"明天是 **{tomorrow_month}月{tomorrow_day}日**！\n\n"
            f"{birthday_text}"
            "💕 媽咪們可以考慮安排生日活動喔！"
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(
        text="🌙 角色生日提醒"
    )

    await channel.send(
        embed=embed
    )

    # ==========================
    # 💾 記錄提醒
    # ==========================

    c.execute(
        """
        INSERT OR IGNORE INTO character_birthday_reminders
        (reminder_date)
        VALUES (?)
        """,
        (reminder_date,)
    )

    conn.commit()
    conn.close()


# ==========================
# ⏰ 每日生日檢查
# ==========================


@tasks.loop(
    minutes=1
)
async def character_birthday_check_loop(bot):

    now = datetime.now(TIMEZONE)

    # ==========================
    # 🕗 每天 08:00 檢查
    # ==========================

    if now.hour != 7 or now.minute != 0:

        return

    await check_character_birthdays(bot)


# ==========================
# 🔄 啟動生日提醒
# ==========================


def start_character_birthday_loop(bot):

    if not character_birthday_check_loop.is_running():

        character_birthday_check_loop.start(bot)


# ==========================
# 🌙 角色生日系統啟動
# ==========================


_character_birthday_setup_done = False


async def setup_character_birthday(bot):

    global _character_birthday_setup_done

    # ==========================
    # 🔒 防止重複註冊
    # ==========================

    if _character_birthday_setup_done:

        return

    _character_birthday_setup_done = True

    # ==========================
    # 🎂 註冊設定指令
    # ==========================

    await setup_character_birthday_commands(bot)

    # ==========================
    # 🔍 註冊查詢指令
    # ==========================

    await setup_character_birthday_query(bot)

    # ==========================
    # 🔔 啟動提醒
    # ==========================

    start_character_birthday_loop(bot)