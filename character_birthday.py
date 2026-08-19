# ==========================
# 🎂 角色生日系統
# ==========================

import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import View, Button, Select, Modal, TextInput

import sqlite3
from datetime import datetime, timedelta
import pytz

from database import DB_PATH


# ==========================
# 🎂 角色生日設定
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
# 🗄️ 角色生日資料表
# ==========================

def init_character_birthday_db():

    conn = sqlite3.connect(DB_PATH)

    c = conn.cursor()

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

    conn.commit()
    conn.close()


# ==========================
# 🎂 初始化
# ==========================

init_character_birthday_db()

# ==========================
# 🎂 角色生日設定
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

    async def callback(self, interaction: discord.Interaction):

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

        mommy_name = next(
            name
            for name, user_id in MOMMY_LIST.items()
            if user_id == selected_user_id
        )

        # ==========================
        # 📝 輸入角色名稱
        # ==========================

        await interaction.response.send_modal(
            CharacterNameModal(mommy_name)
        )


# ==========================
# 📝 角色名稱 Modal
# ==========================


class CharacterNameModal(Modal):

    def __init__(self, mommy_name):

        super().__init__(
            title="🎂 設定角色生日"
        )

        self.mommy_name = mommy_name

        self.character_name = TextInput(
            label="角色名稱",
            placeholder="請輸入角色名稱",
            required=True,
            max_length=50
        )

        self.add_item(self.character_name)

    async def on_submit(self, interaction: discord.Interaction):

        character_name = self.character_name.value.strip()

        if not character_name:

            await interaction.response.send_message(
                "❌ 角色名稱不能為空白。",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"🎂 **{self.mommy_name}**\n\n"
            f"🎭 角色：**{character_name}**\n\n"
            "請選擇角色的生日月份。",
            view=BirthdayMonthView(
                self.mommy_name,
                character_name
            ),
            ephemeral=True
        )


# ==========================
# 📅 月份選單
# ==========================


class BirthdayMonthSelect(Select):

    def __init__(self, mommy_name, character_name):

        self.mommy_name = mommy_name
        self.character_name = character_name

        options = [
            discord.SelectOption(
                label=f"{month}月",
                value=str(month),
                emoji="📅"
            )
            for month in range(1, 13)
        ]

        super().__init__(
            placeholder="📅 請選擇生日月份",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        month = int(self.values[0])

        await interaction.response.edit_message(
            content=(
                f"🎂 **{self.mommy_name}**\n\n"
                f"🎭 角色：**{self.character_name}**\n"
                f"📅 生日月份：**{month}月**\n\n"
                "請選擇生日日期。"
            ),
            view=BirthdayDayView(
                self.mommy_name,
                self.character_name,
                month
            )
        )


# ==========================
# 📅 月份 View
# ==========================


class BirthdayMonthView(View):

    def __init__(self, mommy_name, character_name):

        super().__init__(timeout=180)

        self.add_item(
            BirthdayMonthSelect(
                mommy_name,
                character_name
            )
        )
        
# ==========================
# 📅 日期選單
# ==========================


class BirthdayDaySelect(Select):

    def __init__(self, mommy_name, character_name, month):

        self.mommy_name = mommy_name
        self.character_name = character_name
        self.month = month

        # ==========================
        # 📅 判斷該月份最大日期
        # ==========================

        if month == 2:
            max_day = 29
        elif month in [4, 6, 9, 11]:
            max_day = 30
        else:
            max_day = 31

        options = [
            discord.SelectOption(
                label=f"{day}日",
                value=str(day),
                emoji="🎂"
            )
            for day in range(1, max_day + 1)
        ]

        super().__init__(
            placeholder="🎂 請選擇生日日期",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        day = int(self.values[0])

        await interaction.response.edit_message(
            content=(
                "🎂 **角色生日設定確認**\n\n"
                f"👑 媽咪：**{self.mommy_name}**\n"
                f"🎭 角色：**{self.character_name}**\n"
                f"🎂 生日：**{self.month}月{day}日**\n\n"
                "請確認以上資料是否正確。"
            ),
            view=BirthdayConfirmView(
                self.mommy_name,
                self.character_name,
                self.month,
                day
            )
        )


# ==========================
# 📅 日期 View
# ==========================


class BirthdayDayView(View):

    def __init__(self, mommy_name, character_name, month):

        super().__init__(timeout=180)

        self.add_item(
            BirthdayDaySelect(
                mommy_name,
                character_name,
                month
            )
        )


# ==========================
# ✅ 確認 View
# ==========================


class BirthdayConfirmView(View):

    def __init__(
        self,
        mommy_name,
        character_name,
        month,
        day
    ):

        super().__init__(timeout=180)

        self.mommy_name = mommy_name
        self.character_name = character_name
        self.month = month
        self.day = day

    # ==========================
    # ✅ 確認
    # ==========================

    @discord.ui.button(
        label="確認儲存",
        emoji="✅",
        style=discord.ButtonStyle.success
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
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
                self.character_name,
                self.month,
                self.day
            )
        )

        conn.commit()
        conn.close()

        # ==========================
        # 🎉 完成
        # ==========================

        await interaction.response.edit_message(
            content=(
                "🎉 **角色生日設定完成！**\n\n"
                f"👑 媽咪：**{self.mommy_name}**\n"
                f"🎭 角色：**{self.character_name}**\n"
                f"🎂 生日：**{self.month}月{self.day}日**\n\n"
                "💾 生日資料已成功保存。"
            ),
            view=None
        )

    # ==========================
    # ❌ 取消
    # ==========================

    @discord.ui.button(
        label="取消",
        emoji="❌",
        style=discord.ButtonStyle.danger
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.edit_message(
            content="❌ 已取消角色生日設定。",
            view=None
        )
        
# ==========================
# 🎂 設定角色生日指令
# ==========================


class CharacterBirthdaySettingView(View):

    def __init__(self):

        super().__init__(timeout=180)

        self.add_item(
            MommySelect()
        )


async def setup_character_birthday_commands(bot):

    # ==========================
    # 🎂 設定角色生日
    # ==========================

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

    # ==========================
    # 🗄️ 讀取資料
    # ==========================

    conn = sqlite3.connect(DB_PATH)

    c = conn.cursor()

    c.execute(
        """
        SELECT mommy_name, character_name, month, day
        FROM character_birthdays
        ORDER BY month ASC, day ASC
        """
    )

    rows = c.fetchall()

    conn.close()

    # ==========================
    # ❌ 尚無資料
    # ==========================

    if not rows:

        await interaction.response.send_message(
            "🎂 目前還沒有登記任何角色生日。",
            ephemeral=True
        )
        return

    # ==========================
    # 🎂 整理資料
    # ==========================

    birthday_text = ""

    for mommy_name, character_name, month, day in rows:

        birthday_text += (
            f"👑 **{mommy_name}**\n"
            f"└ 🎭 {character_name}　"
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
# 🔔 角色生日提醒紀錄
# ==========================


def init_character_birthday_reminder_db():

    conn = sqlite3.connect(DB_PATH)

    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS character_birthday_reminders (
            reminder_date TEXT PRIMARY KEY
        )
    """)

    conn.commit()
    conn.close()


init_character_birthday_reminder_db()


# ==========================
# 🔔 前一天生日提醒
# ==========================


async def check_character_birthdays(bot):

    now = datetime.now(TIMEZONE)

    # ==========================
    # 📅 計算明天日期
    # ==========================

    tomorrow = now + timedelta(days=1)

    tomorrow_month = tomorrow.month
    tomorrow_day = tomorrow.day

    reminder_date = tomorrow.strftime("%Y-%m-%d")

    # ==========================
    # 🗄️ 檢查今天是否已經提醒
    # ==========================

    conn = sqlite3.connect(DB_PATH)

    c = conn.cursor()

    c.execute(
        """
        SELECT 1
        FROM character_birthday_reminders
        WHERE reminder_date = ?
        """,
        (reminder_date,)
    )

    already_sent = c.fetchone()

    if already_sent:

        conn.close()
        return

    # ==========================
    # 🎂 查詢明天生日角色
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
    # ❌ 明天沒有角色生日
    # ==========================

    if not rows:

        conn.close()
        return

    # ==========================
    # 🔔 找到提醒頻道
    # ==========================

    channel = bot.get_channel(
        CHARACTER_BIRTHDAY_CHANNEL
    )

    if channel is None:

        conn.close()
        return

    # ==========================
    # 🎂 整理生日資料
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
            "💕 媽咪們可以考慮安排生日活動或準備生日祝福喔！"
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
    # 💾 記錄已提醒
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

    # 每天早上 08:00 檢查一次
    if now.hour != 8 or now.minute != 0:
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

    # 防止重複註冊指令
    if _character_birthday_setup_done:
        return

    _character_birthday_setup_done = True

    # ==========================
    # 🎂 註冊指令
    # ==========================

    await setup_character_birthday_commands(bot)

    await setup_character_birthday_query(bot)

    # ==========================
    # 🔔 啟動生日提醒
    # ==========================

    start_character_birthday_loop(bot)