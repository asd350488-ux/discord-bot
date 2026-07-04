import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import View, Button
import sqlite3
from datetime import datetime, timedelta, time
import pytz
import os
import threading
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
import random
import asyncio
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import io
from events import CHECKIN_EVENTS, EVENT_THEMES
import time as pytime
from config import *
from systems.welcome import create_welcome_card
from blessings import (
    CHECKIN_BLESSINGS,
    RARE_BLESSINGS,
    EPIC_BLESSINGS,
    MYTH_BLESSINGS,
)

tz = pytz.timezone(TIMEZONE)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 💾 DB
from database import conn, c

from views.shop import ShopView, BuyButton

# 💜 老公資料表
c.execute("""
CREATE TABLE IF NOT EXISTS husbands (
    husband_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
)
""")

# 💜 玩家收藏老公
c.execute("""
CREATE TABLE IF NOT EXISTS user_husbands (
    user_id TEXT,
    husband_id INTEGER,
    PRIMARY KEY(user_id, husband_id)
)
""")

# 🗡 黑幫系統

c.execute("""
CREATE TABLE IF NOT EXISTS wanted (
    user_id TEXT PRIMARY KEY,
    level INTEGER DEFAULT 0
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS jail (
    user_id TEXT PRIMARY KEY,
    release_time INTEGER
)
""")

# ==========================
# 🌙 抽獎系統
# ==========================

c.execute("""
CREATE TABLE IF NOT EXISTS lotteries (

    message_id TEXT PRIMARY KEY,

    channel_id TEXT NOT NULL,

    host_id TEXT NOT NULL,

    prize_type TEXT NOT NULL,

    prize_value TEXT NOT NULL,

    winner_count INTEGER NOT NULL,

    end_time TEXT NOT NULL,

    status TEXT DEFAULT 'running',

    created_at TEXT NOT NULL

)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS lottery_entries (

    message_id TEXT NOT NULL,

    user_id TEXT NOT NULL,

    PRIMARY KEY (
        message_id,
        user_id
    )

)
""")

conn.commit()

# =========================
# 🚨 通緝系統
# =========================


async def get_wanted_level(user_id):

    c.execute(
        """
        SELECT level
        FROM wanted
        WHERE user_id=?
        """,
        (user_id,),
    )

    data = c.fetchone()

    if data:
        return data[0]

    c.execute(
        """
        INSERT INTO wanted(user_id, level)
        VALUES (?, 0)
        """,
        (user_id,),
    )

    conn.commit()

    return 0


async def add_wanted(user_id, amount=1):

    level = await get_wanted_level(user_id)

    c.execute(
        """
        UPDATE wanted
        SET level=?
        WHERE user_id=?
        """,
        (level + amount, user_id),
    )

    conn.commit()


c.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    money INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    exp INTEGER DEFAULT 0,
    checkin_total INTEGER DEFAULT 0,
    checkin_streak INTEGER DEFAULT 0,
    last_checkin TEXT,
    birthday TEXT,
    birth_year INTEGER,
    last_work TEXT,
    last_adventure TEXT
)
""")

# ==========================
# 🌙 計算抽獎結束時間
# ==========================


def get_lottery_end_time(amount: int, unit: str):

    now = datetime.now()

    unit = unit.upper()

    if unit == "S":
        return now + timedelta(seconds=amount)

    elif unit == "M":
        return now + timedelta(minutes=amount)

    elif unit == "H":
        return now + timedelta(hours=amount)

    elif unit == "D":
        return now + timedelta(days=amount)

    else:
        return None


# ==========================
# 🌙 努努幣抽獎 Modal
# ==========================


class MoneyLotteryModal(discord.ui.Modal, title="💰 努努幣抽獎"):

    money = discord.ui.TextInput(
        label="💰 努努幣數量", placeholder="例如：5000", required=True, max_length=10
    )

    winners = discord.ui.TextInput(
        label="👥 中獎人數", placeholder="例如：3", required=True, max_length=3
    )

    time = discord.ui.TextInput(
        label="⏰ 抽獎時間", placeholder="例如：10", required=True, max_length=5
    )

    unit = discord.ui.TextInput(
        label="🕒 時間單位",
        placeholder="請輸入 S、M、H、D",
        required=True,
        max_length=1,
    )

    # ==========================
    # 🌙 抽獎確認
    # ==========================
    async def on_submit(self, interaction: discord.Interaction):

        # -------------------------
        # 驗證資料
        # -------------------------

        try:
            money = int(self.money.value)
            winners = int(self.winners.value)
            time_amount = int(self.time.value)

        except ValueError:

            await interaction.response.send_message(
                "❌ 請輸入正確的數字。", ephemeral=True
            )
            return

        unit = self.unit.value.upper()

        end_time = get_lottery_end_time(time_amount, unit)

        if end_time is None:

            await interaction.response.send_message(
                "❌ 時間單位只能輸入 S、M、H、D。", ephemeral=True
            )
            return

        timestamp = int(end_time.timestamp())

        # -------------------------
        # 建立 Embed
        # -------------------------

        embed = discord.Embed(title="🎉 Moon Bot 抽獎", color=0xF1C40F)

        embed.add_field(name="🎁 獎品", value=f"💰 努努幣 {money:,}", inline=False)

        embed.add_field(name="👥 中獎人數", value=f"{winners} 人", inline=True)

        embed.add_field(name="👤 主辦人", value=interaction.user.mention, inline=True)

        embed.add_field(
            name="⏰ 抽獎截止",
            value=f"<t:{timestamp}:F>\n<t:{timestamp}:R>",
            inline=False,
        )

        embed.add_field(name="📌 狀態", value="🟢 進行中", inline=False)

        embed.set_footer(text="點擊下方按鈕即可參加抽獎")

        # -------------------------
        # 發送抽獎
        # -------------------------

        message = await interaction.channel.send(
            content=f"<@&{MEMBER_ROLE}>", embed=embed, view=LotteryView()
        )

        # -------------------------
        # 寫入資料庫
        # -------------------------

        c.execute(
            """
            INSERT INTO lotteries (
                message_id,
                channel_id,
                host_id,
                prize_type,
                prize_value,
                winner_count,
                end_time,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(message.id),
                str(interaction.channel.id),
                str(interaction.user.id),
                "money",
                str(money),
                winners,
                end_time.isoformat(),
                "running",
                datetime.now().isoformat(),
            ),
        )

        conn.commit()

        # -------------------------
        # 完成
        # -------------------------

        await interaction.response.send_message("✅ 抽獎建立成功！", ephemeral=True)


# ==========================
# 🌙 抽獎按鈕
# ==========================


class LotteryView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    # ==========================
    # 🎉 參加抽獎
    # ==========================

    @discord.ui.button(
        label="🎉 參加抽獎（0）",
        style=discord.ButtonStyle.success,
        custom_id="lottery_join",
    )
    async def join_lottery(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        # -------------------------
        # 取得抽獎 ID
        # -------------------------

        message_id = str(interaction.message.id)
        user_id = str(interaction.user.id)

        # -------------------------
        # 是否已參加
        # -------------------------

        c.execute(
            """
            SELECT 1
            FROM lottery_entries
            WHERE message_id = ?
            AND user_id = ?
            """,
            (message_id, user_id),
        )

        if c.fetchone():

            await interaction.response.send_message(
                "⚠️ 你已經參加過本次抽獎。", ephemeral=True
            )
            return

        # -------------------------
        # 加入抽獎
        # -------------------------

        c.execute(
            """
            INSERT INTO lottery_entries (
                message_id,
                user_id
            )
            VALUES (?, ?)
            """,
            (message_id, user_id),
        )

        conn.commit()

        # -------------------------
        # 更新參加人數
        # -------------------------

        c.execute(
            """
            SELECT COUNT(*)
            FROM lottery_entries
            WHERE message_id = ?
            """,
            (message_id,),
        )

        total = c.fetchone()[0]

        self.children[0].label = f"🎉 參加抽獎（{total}）"

        await interaction.message.edit(view=self)

        # -------------------------
        # 完成
        # -------------------------

        await interaction.response.send_message(
            "✅ 已成功參加抽獎！\n\n祝你好運 🍀", ephemeral=True
        )

        # ==========================

    # 👥 查看名單
    # ==========================

    @discord.ui.button(
        label="👥 查看名單",
        style=discord.ButtonStyle.secondary,
        custom_id="lottery_list",
    )
    async def view_members(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        # -------------------------
        # 取得抽獎 ID
        # -------------------------

        message_id = str(interaction.message.id)

        # -------------------------
        # 查詢參加者
        # -------------------------

        c.execute(
            """
            SELECT user_id
            FROM lottery_entries
            WHERE message_id = ?
            ORDER BY rowid ASC
            """,
            (message_id,),
        )

        rows = c.fetchall()

        if not rows:

            await interaction.response.send_message(
                "📋 目前還沒有人參加本次抽獎。", ephemeral=True
            )
            return

        member_list = []

        for index, (user_id,) in enumerate(rows, start=1):

            member = interaction.guild.get_member(int(user_id))

            if member:

                member_list.append(f"`{index:02}`｜{member.mention}")

        text = "\n".join(member_list)

        embed = discord.Embed(title="👥 抽獎參加名單", description=text, color=0x5865F2)

        embed.add_field(
            name="📊 參加人數", value=f"**{len(member_list)} 人**", inline=False
        )

        embed.set_footer(text="Moon Bot Lottery")

        await interaction.response.send_message(embed=embed, ephemeral=True)


# ==========================
# 🌙 抽獎獎品選擇
# ==========================


class PrizeSelectView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=180)

    # -------------------------
    # 🎨 人設圖
    # -------------------------

    @discord.ui.button(label="🎨 人設圖", style=discord.ButtonStyle.primary)
    async def image(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.send_message(
            "🎨 人設圖 Modal（建置中）", ephemeral=True
        )

    # -------------------------
    # 💕 合照
    # -------------------------

    @discord.ui.button(label="💕 合照", style=discord.ButtonStyle.primary)
    async def couple(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.send_message(
            "💕 合照 Modal（建置中）", ephemeral=True
        )

    # -------------------------
    # 💰 努努幣
    # -------------------------

    @discord.ui.button(label="💰 努努幣", style=discord.ButtonStyle.success)
    async def money(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.send_modal(MoneyLotteryModal())

        try:
            await interaction.delete_original_response()
        except:
            pass

    # -------------------------
    # 📝 自訂
    # -------------------------

    @discord.ui.button(label="📝 自訂", style=discord.ButtonStyle.secondary)
    async def custom(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.send_message(
            "📝 自訂 Modal（建置中）", ephemeral=True
        )


class DuelView(discord.ui.View):

    def __init__(self, challenger, target, amount):
        super().__init__(timeout=60)

        self.challenger = challenger
        self.target = target
        self.amount = amount

    @discord.ui.button(label="⚔️ 接受對賭", style=discord.ButtonStyle.danger)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user.id != self.target.id:

            await interaction.response.send_message("❌ 這不是你的對賭", ephemeral=True)
            return

        challenger_id = str(self.challenger.id)

        target_id = str(self.target.id)

        # 餘額檢查
        c.execute("SELECT money FROM users WHERE user_id=?", (challenger_id,))

        challenger_money = c.fetchone()

        c.execute("SELECT money FROM users WHERE user_id=?", (target_id,))

        target_money = c.fetchone()

        if not challenger_money or not target_money:
            await interaction.response.send_message("❌ 帳戶不存在")
            return

        challenger_money = challenger_money[0]
        target_money = target_money[0]

        if challenger_money < self.amount:

            await interaction.response.send_message(
                f"❌ {self.challenger.display_name} 的努努幣不足\n"
                f"需要：{self.amount:,}\n"
                f"目前：{challenger_money:,}",
                ephemeral=True,
            )
            return

        if target_money < self.amount:

            await interaction.response.send_message(
                f"❌ {self.target.display_name} 的努努幣不足\n"
                f"需要：{self.amount:,}\n"
                f"目前：{target_money:,}",
                ephemeral=True,
            )
            return

        # 🎲 勝負
        await interaction.response.edit_message(content="⚔️ 決鬥準備中...", view=None)

        await asyncio.sleep(1)

        await interaction.edit_original_response(content="🎲 擲骰中...")

        await asyncio.sleep(1)

        await interaction.edit_original_response(content="💥 勝負判定中...")

        await asyncio.sleep(1)

        winner = random.choice([self.challenger, self.target])

        loser = self.target if winner == self.challenger else self.challenger

        winner_id = str(winner.id)
        loser_id = str(loser.id)

        # 💰 雙方下注
        pot = self.amount * 2

        roll = random.randint(1, 100)

        if roll <= 5:

            title = "⭐ 神運"
            reward = int(pot * 2.5)

        elif roll <= 25:

            title = "✨ 大勝"
            reward = int(pot * 1.5)

        else:

            title = "🎉 小勝"
            reward = pot

        # 💸 雙方先扣下注
        c.execute(
            """
            UPDATE users
            SET money = money - ?
            WHERE user_id=?
            """,
            (self.amount, challenger_id),
        )

        c.execute(
            """
            UPDATE users
            SET money = money - ?
            WHERE user_id=?
            """,
            (self.amount, target_id),
        )

        # 🎁 勝者獲得獎池
        c.execute(
            """
            UPDATE users
            SET money = money + ?
            WHERE user_id=?
            """,
            (reward, winner_id),
        )

        conn.commit()

        embed = discord.Embed(title="⚔️ 星月對賭結果", color=discord.Color.red())

        embed.add_field(name="🏆 勝者", value=winner.mention, inline=False)

        embed.add_field(name="✨ 結果", value=title, inline=False)

        embed.add_field(name="🏦 獎池", value=f"{NUNU_EMOJI} `{pot:,}`", inline=False)

        embed.add_field(
            name="🎁 最終獎勵", value=f"{NUNU_EMOJI} `{reward:,}`", inline=False
        )

        embed.add_field(name="💀 敗者", value=loser.mention, inline=False)

        await interaction.edit_original_response(content=None, embed=embed, view=None)

    @discord.ui.button(label="❌ 拒絕對賭", style=discord.ButtonStyle.secondary)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user.id != self.target.id:

            await interaction.response.send_message("❌ 這不是你的對賭", ephemeral=True)
            return

        embed = discord.Embed(
            title="❌ 對賭取消",
            description=f"{self.target.display_name} 拒絕了這場對賭",
            color=discord.Color.greyple(),
        )

        await interaction.response.edit_message(embed=embed, view=None)


c.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    user_id TEXT,
    item_id INTEGER,
    amount INTEGER
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS money_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id TEXT,
    target_id TEXT,
    amount INTEGER,
    type TEXT,
    time TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS daily_event (
    date TEXT PRIMARY KEY,
    game TEXT,
    multiplier INTEGER
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

husband_list = [
    "黎晝",
    "溫執紃",
    "諾耶·卡米爾",
    "瑟安",
    "穆梓赫",
    "穆禹昂",
    "韓沉",
    "路西恩",
    "賽拉斯",
    "維克托",
    "奧爾登",
    "伊萊亞斯",
    "穆宇曄",
    "穆宇辰",
    "司御蓮",
    "月真靜",
    "夜鷹瀨",
    "月城靜真",
    "黑瀨鷹夜",
    "御影蓮司",
    "若無",
    "黎沐昊",
    "杜洛",
    "杜楓",
    "鍾緹歐",
    "何硯希",
    "穆彥珩",
    "穆薩爾",
    "梁凱",
    "戚孟洋",
    "邢子言",
    "彌愷揚",
    "祁安",
    "祁羯",
    "樂央",
    "藍書禾",
    "席靖宥",
    "閔孝杰",
]

for husband in husband_list:

    c.execute(
        """
        INSERT OR IGNORE INTO husbands (name)
        VALUES (?)
    """,
        (husband,),
    )

conn.commit()

# ===============================
# 🌙 Moon 入群審核系統
# ===============================


class ReviewPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="📝 開始申請", style=discord.ButtonStyle.green, custom_id="review_start"
    )
    async def review_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        await create_review_ticket(interaction)


# ==========================
# 🌙 建立入群審核 Ticket
# ==========================


async def create_review_ticket(interaction: discord.Interaction):

    guild = interaction.guild
    member = interaction.user

    # 取得分類
    category = guild.get_channel(REVIEW_CATEGORY)

    if category is None:
        await interaction.response.send_message("❌ 找不到審核分類。", ephemeral=True)
        return

    # ==========================
    # 防止重複建立 Ticket
    # ==========================

    for channel in category.text_channels:

        if channel.topic is None:
            continue

        if f"Applicant={member.id}" in channel.topic:

            await interaction.response.send_message(
                "❌ 你目前已有一張審核 Ticket，請等待管理員處理。", ephemeral=True
            )
            return

    # ==========================
    # 建立權限
    # ==========================

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        member: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            attach_files=True,
            embed_links=True,
            read_message_history=True,
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_channels=True,
            manage_messages=True,
            read_message_history=True,
        ),
    }

    # ==========================
    # 審核組
    # ==========================

    review_role = guild.get_role(REVIEW_ROLE)

    if review_role:

        overwrites[review_role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_messages=True,
            read_message_history=True,
        )

    # ==========================
    # 建立 Ticket
    # ==========================

    ticket = await guild.create_text_channel(
        name=f"📋｜審核-{member.display_name}",
        category=category,
        overwrites=overwrites,
        topic=(f"Applicant={member.id}\n" f"Status=Pending"),
    )

    # -------------------------
    # 發送審核訊息
    # -------------------------

    message = await send_review_message(ticket, member)

    # -------------------------
    # 更新 Ticket Topic
    # -------------------------

    await ticket.edit(
        topic=(f"Applicant={member.id}\n" f"Status=Pending\n" f"Message={message.id}")
    )

    # -------------------------
    # 回覆使用者
    # -------------------------

    await interaction.response.send_message(
        f"✅ 已成功建立審核 Ticket：{ticket.mention}", ephemeral=True
    )


# ==========================
# 🌙 取得 Ticket 申請人
# ==========================


async def get_ticket_member(channel: discord.TextChannel):

    if channel.topic is None:
        return None

    user_id = None

    for line in channel.topic.split("\n"):
        if line.startswith("Applicant="):
            user_id = int(line.replace("Applicant=", ""))
            break

    if user_id is None:
        return None

    return channel.guild.get_member(user_id)


# ==========================
# 🌙 取得審核 Embed 訊息
# ==========================


async def get_review_message(channel: discord.TextChannel):

    if channel.topic is None:
        return None

    message_id = None

    for line in channel.topic.split("\n"):

        if line.startswith("Message="):
            message_id = int(line.replace("Message=", ""))
            break

    if message_id is None:
        return None

    try:
        message = await channel.fetch_message(message_id)
        return message

    except discord.NotFound:
        return None


# ==========================
# 🌙 更新審核 Embed
# ==========================


async def update_review_embed(
    channel: discord.TextChannel, reviewer: discord.Member, status: str
):

    message = await get_review_message(channel)

    if message is None:
        return

    embed = message.embeds[0]

    timestamp = int(datetime.now().timestamp())

    # 👤 申請人（保持不變）
    applicant = embed.fields[0].value

    # 📌 審核狀態
    embed.set_field_at(1, name="📌 審核狀態", value=status, inline=True)

    # 👮 審核人
    embed.set_field_at(2, name="👮 審核人", value=reviewer.mention, inline=True)

    # 🕒 建立時間（保持原本）
    created_time = embed.fields[3].value

    embed.set_field_at(3, name="🕒 建立時間", value=created_time, inline=False)

    # ✅ 通過時間
    if len(embed.fields) == 4:

        embed.add_field(name="✅ 通過時間", value=f"<t:{timestamp}:F>", inline=False)

    else:

        embed.set_field_at(
            4, name="✅ 通過時間", value=f"<t:{timestamp}:F>", inline=False
        )

    await message.edit(embed=embed, view=ReviewManageView(disabled=True))


# ==========================
# 🌙 發送審核訊息
# ==========================


async def send_review_message(channel: discord.TextChannel, member: discord.Member):

    review_role = channel.guild.get_role(REVIEW_ROLE)

    # --------------------------
    # 通知申請者與審核組
    # --------------------------

    if review_role:
        mention_message = await channel.send(f"{member.mention} {review_role.mention}")
    else:
        mention_message = await channel.send(member.mention)

    await mention_message.delete(delay=3)

    # --------------------------
    # 入群審核 Embed
    # --------------------------

    timestamp = int(datetime.now().timestamp())

    review_embed = discord.Embed(title="📂 極曜月葵｜資料提交", color=0xC77DFF)

    review_embed.add_field(name="👤 申請人", value=member.mention, inline=False)

    review_embed.add_field(name="📌 審核狀態", value="🟡 等待審核", inline=True)

    review_embed.add_field(name="👮 審核人", value="等待審核", inline=True)

    review_embed.add_field(name="🕒 建立時間", value=f"<t:{timestamp}:F>", inline=False)

    review_embed.description = (
        "════════════════════\n\n"
        "📤 **請將以下資料上傳至此頻道**\n\n"
        "📸 四位媽咪其中一位角色聊天截圖\n\n"
        "📸 C 台 **30 等** 或 T 台 **2 等** 角色聊天截圖\n\n"
        "════════════════════\n\n"
        "📌 上傳完成後，\n"
        "請耐心等待管理員審核即可。"
    )
    message = await channel.send(embed=review_embed, view=ReviewManageView())

    return message


# ==========================
# 🌙 審核管理按鈕
# ==========================


class ReviewManageView(discord.ui.View):

    def __init__(self, disabled=False):

        super().__init__(timeout=None)

        if disabled:

            for item in self.children:

                if item.custom_id == "review_approve":
                    item.disabled = True

    @discord.ui.button(
        label="🟢 通過", style=discord.ButtonStyle.success, custom_id="review_approve"
    )
    async def approve(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        # -------------------------
        # 除錯（暫時）
        # -------------------------

        print("使用者：", interaction.user)
        print("使用者角色：")
        print([(r.name, r.id) for r in interaction.user.roles])

        # -------------------------
        # 權限檢查
        # -------------------------

        if not any(role.id in ALLOWED_ROLES for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ 只有管理員可以使用此按鈕。", ephemeral=True
            )
            return

        member = await get_ticket_member(interaction.channel)

        if member is None:
            await interaction.response.send_message("❌ 找不到申請者。", ephemeral=True)
            return

        # -------------------------
        # 身分組
        # -------------------------

        pending_role = interaction.guild.get_role(PENDING_ROLE)
        member_role = interaction.guild.get_role(MEMBER_ROLE)

        try:

            if pending_role:
                await member.remove_roles(pending_role, reason="入群審核通過")

            if member_role:
                await member.add_roles(member_role, reason="入群審核通過")

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Bot 沒有權限修改身分組。", ephemeral=True
            )
            return

        # -------------------------
        # 更新 Topic
        # -------------------------

        if interaction.channel.topic:
            await interaction.channel.edit(
                topic=interaction.channel.topic.replace(
                    "Status=Pending", "Status=Approved"
                )
            )

        # -------------------------
        # 更新審核 Embed
        # -------------------------

        await update_review_embed(interaction.channel, interaction.user, "🟢 已通過")

        # -------------------------
        # 完成
        # -------------------------

        await interaction.response.defer()

    @discord.ui.button(
        label="⚫ 關閉", style=discord.ButtonStyle.danger, custom_id="review_close"
    )
    async def close_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        if not any(role.id in ALLOWED_ROLES for role in interaction.user.roles):

            await interaction.response.send_message(
                "❌ 只有管理員可以使用此按鈕。", ephemeral=True
            )
            return

        await interaction.response.send_message(
            "⚠️ 確定要關閉這張 Ticket 嗎？", view=CloseTicketView(), ephemeral=True
        )


# ==========================
# 🌙 關閉 Ticket 確認
# ==========================


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="✅ 確認關閉", style=discord.ButtonStyle.danger)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        if not any(role.id in ALLOWED_ROLES for role in interaction.user.roles):

            await interaction.response.send_message(
                "❌ 只有管理員可以關閉 Ticket。", ephemeral=True
            )
            return

        await interaction.response.send_message(
            "⚫ Ticket 將於 **5 秒後** 關閉。", ephemeral=True
        )

        await asyncio.sleep(5)

        await interaction.channel.delete(reason=f"{interaction.user} 關閉入群審核")

    @discord.ui.button(label="取消", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.edit_message(content="✅ 已取消關閉。", view=None)


# 🚀 啟動
@bot.event
async def on_ready():
    print(f"已登入：{bot.user}")

    await bot.tree.sync()

    if not birthday_check.is_running():
        birthday_check.start()

    if not lottery_checker.is_running():
        lottery_checker.start()


@bot.tree.command(name="審核面板", description="發送入群審核面板")
async def review_panel(interaction: discord.Interaction):

    # 管理員限制
    if not any(role.id in ALLOWED_ROLES for role in interaction.user.roles):
        await interaction.response.send_message(
            "❌ 你沒有權限使用此指令。", ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🌙 極曜月葵｜新成員審核",
        description=(
            "歡迎加入 **極曜月葵 Discord**！\n\n"
            "為了維護社群品質，請先確認符合以下條件後，"
            "再點擊下方按鈕開始申請。\n\n"
            "════════════════════\n\n"
            "📸 **請提供以下四位媽咪其中一位角色的聊天截圖：**\n\n"
            "🌸 星弦媽咪\n"
            "🌸 韓馨媽咪\n"
            "🌸 小貓媽咪\n"
            "🌸 若曦璃媽咪\n\n"
            "════════════════════\n\n"
            "🎮 **角色等級需求**\n\n"
            "✅ C 台角色需達 **30 等**\n"
            "✅ T 台角色需達 **2 等**\n\n"
            "📌 **符合其中一項即可，**\n"
            "請提供符合條件角色的聊天截圖。\n\n"
            "════════════════════\n\n"
            "⚠️ **為維護審核公平性**\n\n"
            "請勿提供不實資訊或使用他人截圖，\n"
            "經查證屬實將取消審核資格。\n\n"
            "審核通過後，\n"
            "將由管理員協助修改正式身分組。"
        ),
        color=0xC77DFF,
    )

    embed.set_thumbnail(
        url=(
            interaction.guild.icon.url
            if interaction.guild.icon
            else discord.Embed.Empty
        )
    )

    embed.set_footer(text="Moon Bot v2｜入群審核系統")

    await interaction.channel.send(embed=embed, view=ReviewPanelView())

    await interaction.response.send_message(
        "✅ 已成功發送入群審核面板！", ephemeral=True
    )


# 🐰 簽到
@bot.tree.command(name="簽到")
async def checkin(interaction: discord.Interaction):

    # 🔒 限制頻道
    if interaction.channel.id != 1516120502127694027:
        await interaction.response.send_message(
            "❌ 請到指定簽到頻道使用此指令", ephemeral=True
        )
        return

    await interaction.response.defer()

    user_id = str(interaction.user.id)
    now = datetime.now(tz)
    today = now.date()

    c.execute(
        "SELECT last_checkin, checkin_total, checkin_streak, money FROM users WHERE user_id=?",
        (user_id,),
    )
    data = c.fetchone()

    # ❗ 今日已簽到
    if data and data[0] == str(today):

        tomorrow = datetime.combine(today + timedelta(days=1), datetime.min.time())
        tomorrow = tz.localize(tomorrow)

        remaining = tomorrow - now
        total_seconds = int(remaining.total_seconds())

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        embed = discord.Embed(
            title="🌙 𝑴𝒐𝒐𝒏 𝑪𝒉𝒆𝒄𝒌𝒊𝒏", color=discord.Color.from_rgb(186, 85, 211)
        )

        embed.description = (
            "⏳ **今日已完成簽到**\n\n"
            "══════════════════════\n\n"
            "🌙 月神正在等待下一次相遇\n\n"
            f"⏰ **距離下次簽到**\n"
            f"```{hours} 小時 {minutes} 分鐘```\n"
            "══════════════════════"
        )

        embed.set_footer(text="✦ 明天再來接受月神的祝福吧 ✦")

        await interaction.followup.send(embed=embed)
        return

    # 🌸 節日活動
    today_str = str(today)
    event = CHECKIN_EVENTS.get(today_str)

    if event:

        reward = event["reward"]
        rarity = "event"
        blessing = event["message"]

    else:

        roll = random.randint(1, 100)

        if roll == 1:
            reward = 5000
            rarity = "myth"
            blessing = random.choice(MYTH_BLESSINGS)

        elif roll <= 5:
            reward = 2000
            rarity = "epic"
            blessing = random.choice(EPIC_BLESSINGS)

        elif roll <= 20:
            reward = 500
            rarity = "rare"
            blessing = random.choice(RARE_BLESSINGS)

        else:
            reward = 100
            rarity = "normal"
            blessing = random.choice(CHECKIN_BLESSINGS)

    if data:

        total = data[1] + 1

        if data[0] == str(today - timedelta(days=1)):
            streak = data[2] + 1
        else:
            streak = 1

        money = data[3] + reward

        c.execute(
            """
            UPDATE users
            SET last_checkin=?,
                checkin_total=?,
                checkin_streak=?,
                money=?
            WHERE user_id=?
            """,
            (str(today), total, streak, money, user_id),
        )

    else:

        total = 1
        streak = 1
        money = reward

        c.execute(
            """
            INSERT INTO users
            (user_id, money, checkin_total, checkin_streak, last_checkin)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, money, total, streak, str(today)),
        )

    conn.commit()

    # 🌙 Moon Checkin UI
    embed = discord.Embed(
        title="🌙 𝑴𝒐𝒐𝒏 𝑪𝒉𝒆𝒄𝒌𝒊𝒏",
        description=("✨ **星月的祝福再次降臨**\n" "歡迎再次踏入 **星月之境**。"),
        color=discord.Color.from_rgb(186, 85, 211),
    )

    # 🎁 今日獎勵
    if rarity == "event":

        theme = EVENT_THEMES[event["event"]]

        reward_box = (
            f"{theme['emoji']}══════════════{theme['emoji']}\n\n"
            f"## {theme['name']}\n\n"
            f"{blessing}\n\n"
            f" {NUNU_EMOJI} +{reward:,}\n\n"
            f"{theme['emoji']}══════════════{theme['emoji']}"
        )

        footer_text = theme["footer"]

        embed.color = discord.Color(theme["color"])

    elif rarity == "myth":

        reward_box = (
            "👑🌙══════════════🌙👑\n\n"
            f"{blessing}\n\n"
            "🌙 **月神降臨！**\n\n"
            f"{NUNU_EMOJI} +{reward:,}\n\n"
            "👑🌙══════════════🌙👑"
        )

        footer_text = "✦ 月神親自賜予了你祝福 ✦"

    elif rarity == "epic":

        reward_box = (
            "✨🌙══════════════🌙✨\n\n"
            f"{blessing}\n\n"
            "✨ **稀有獎勵！**\n\n"
            f"{NUNU_EMOJI} +{reward:,}\n\n"
            "✨🌙══════════════🌙✨"
        )

        footer_text = "✦ 星與月共同為你送上祝福 ✦"

    elif rarity == "rare":

        reward_box = (
            "🌟✨══════════════✨🌟\n\n"
            f"{blessing}\n\n"
            "🍀 **幸運降臨！**\n\n"
            f"{NUNU_EMOJI} +{reward:,}\n\n"
            "🌟✨══════════════✨🌟"
        )

        footer_text = "✦ 今晚的星空格外閃耀 ✦"

    else:

        reward_box = (
            "✨══════════════✨\n\n"
            f"{blessing}\n\n"
            f"{NUNU_EMOJI} +{reward:,}\n\n"
            "✨══════════════✨"
        )

        footer_text = "✦ 願星月永遠照耀著你 ✦"

    embed.add_field(name="🎁 今日獎勵", value=reward_box, inline=False)

    embed.add_field(name="🔥 連續簽到", value=f"```{streak} 天```", inline=True)

    embed.add_field(name="📅 累積簽到", value=f"```{total} 天```", inline=True)

    embed.set_footer(text=footer_text)

    await interaction.followup.send(embed=embed)


# 💰 錢包
@bot.tree.command(name="錢包")
async def wallet(interaction: discord.Interaction):

    user_id = str(interaction.user.id)

    # 🔒 頻道限制
    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="🛒 星月商會",
            description=("✨ 商會區域限定\n\n" f"請前往 <#{SHOP_CHANNEL}> 使用此指令"),
            color=discord.Color.gold(),
        )

        embed.add_field(
            name="📦 商會功能", value="商店｜購買｜背包｜錢包", inline=False
        )

        embed.set_footer(text="極曜月葵 ✦ 星月商會")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    c.execute(
        "SELECT money, checkin_total, checkin_streak FROM users WHERE user_id=?",
        (user_id,),
    )

    data = c.fetchone()

    if data:
        money, total, streak = data
    else:
        money, total, streak = 0, 0, 0

    embed = discord.Embed(
        title="🌙 𝑳𝒖𝒏𝒂 𝑾𝒂𝒍𝒍𝒆𝒕",
        description="✨ 星月銀行帳戶資訊",
        color=discord.Color.from_rgb(186, 85, 211),
    )

    embed.set_author(
        name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url
    )

    embed.add_field(name=f"{NUNU_EMOJI} 努努幣", value=f"```{money:,}```", inline=False)

    embed.add_field(name="📅 累積簽到", value=f"```{total:,} 天```", inline=True)

    embed.add_field(name="🔥 連續簽到", value=f"```{streak:,} 天```", inline=True)

    embed.set_thumbnail(url=interaction.user.display_avatar.url)

    embed.set_footer(text="極曜月葵 ✦ 星月同行")

    await interaction.response.send_message(embed=embed)
    return


# 🏆 富豪排行榜
@bot.tree.command(name="富豪排行榜")
async def leaderboard(interaction: discord.Interaction):

    # 🔒 頻道限制
    if interaction.channel.id != INFO_CHANNEL:

        embed = discord.Embed(
            title="🌙 星月指令限制",
            description=(
                "📊 排行查詢僅能於指定區域使用\n\n" f"請前往 <#{INFO_CHANNEL}>"
            ),
            color=discord.Color.from_rgb(186, 85, 211),
        )

        embed.add_field(name="✨ 可使用功能", value="等級｜排行榜｜查詢", inline=False)

        embed.set_footer(text="極曜月葵 ✦ 星月同行")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    c.execute("""
        SELECT user_id, money
        FROM users
        ORDER BY money DESC
        LIMIT 10
    """)

    ranking = c.fetchall()

    embed = discord.Embed(
        title="🏆 𝑳𝒖𝒏𝒂 𝑻𝒉𝒓𝒐𝒏𝒆",
        description="✨ 努努幣富豪排行榜 ✨",
        color=discord.Color.gold(),
    )

    medals = {1: "👑", 2: "🥈", 3: "🥉"}

    for index, (user_id, money) in enumerate(ranking, start=1):

        member = interaction.guild.get_member(int(user_id))

        if member:
            name = member.display_name
        else:
            name = f"未知使用者 ({user_id})"

        icon = medals.get(index, f"#{index}")

        embed.add_field(
            name=f"{icon} {name}", value=f"{NUNU_EMOJI} `{money:,}`", inline=False
        )

    embed.set_footer(text="極曜月葵 ✦ 星月同行")

    await interaction.response.send_message(embed=embed)
    return


# 🌟 聊天等級排行榜
@bot.tree.command(name="聊天等級排行榜")
async def level_leaderboard(interaction: discord.Interaction):

    # 🔒 頻道限制
    if interaction.channel.id != INFO_CHANNEL:

        embed = discord.Embed(
            title="🌙 星月指令限制",
            description=(
                "📊 排行查詢僅能於指定區域使用\n\n" f"請前往 <#{INFO_CHANNEL}>"
            ),
            color=discord.Color.from_rgb(186, 85, 211),
        )

        embed.add_field(name="✨ 可使用功能", value="等級｜排行榜｜查詢", inline=False)

        embed.set_footer(text="極曜月葵 ✦ 星月同行")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    c.execute("SELECT user_id, level, exp FROM users ORDER BY level DESC, exp DESC")
    data = c.fetchall()

    text = ""

    for i, (uid, level, exp) in enumerate(data[:10]):
        user = bot.get_user(int(uid)) or await bot.fetch_user(int(uid))

        if i == 0:
            text += f"👑 {user.display_name} ｜ Lv.{level} ✨\n"
        elif i == 1:
            text += f"🌟 {user.display_name} ｜ Lv.{level}\n"
        elif i == 2:
            text += f"💫 {user.display_name} ｜ Lv.{level}\n"
        else:
            text += f"{i+1}. {user.display_name} ｜ Lv.{level}\n"

    embed = discord.Embed(
        title="🏆 等級排行榜",
        description=text,
        color=discord.Color.from_rgb(186, 85, 211),
    )

    await interaction.response.send_message(embed=embed)


# 📈 等級
@bot.tree.command(name="等級")
async def level(interaction: discord.Interaction):

    # 🔒 頻道限制
    if interaction.channel.id != INFO_CHANNEL:

        embed = discord.Embed(
            title="🌙 星月指令限制",
            description=(
                "📊 等級查詢僅能於指定區域使用\n\n" f"請前往 <#{INFO_CHANNEL}>"
            ),
            color=discord.Color.from_rgb(186, 85, 211),
        )

        embed.add_field(name="✨ 可使用功能", value="等級｜排行榜｜查詢", inline=False)

        embed.set_footer(text="極曜月葵 ✦ 星月同行")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    user_id = str(interaction.user.id)

    c.execute(
        """
        SELECT level, exp
        FROM users
        WHERE user_id=?
    """,
        (user_id,),
    )

    result = c.fetchone()

    if not result:
        level = 1
        exp = 0
    else:
        level, exp = result

    next_exp = level * 100

    c.execute(
        """
        SELECT COUNT(*)
        FROM users
        WHERE level > ?
           OR (level = ? AND exp > ?)
    """,
        (level, level, exp),
    )

    rank = c.fetchone()[0] + 1

    percent = min(int((exp / next_exp) * 100), 100)

    bar_length = 10
    filled = int(percent / 10)

    progress_bar = "🟪" * filled + "⬜" * (bar_length - filled)

    embed = discord.Embed(
        title="🌙 𝑳𝒖𝒏𝒂 𝑷𝒓𝒐𝒇𝒊𝒍𝒆",
        description="✨ 星月旅人的成長紀錄",
        color=discord.Color.from_rgb(138, 43, 226),
    )

    embed.set_author(
        name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url
    )

    embed.set_thumbnail(url=interaction.user.display_avatar.url)

    embed.add_field(name="📈 等級", value=f"```Lv.{level}```", inline=True)

    embed.add_field(name="🏆 排名", value=f"```#{rank}```", inline=True)

    embed.add_field(
        name="✨ 經驗值",
        value=(f"{progress_bar}\n" f"`{exp:,} / {next_exp:,}`\n" f"完成度：{percent}%"),
        inline=False,
    )

    embed.set_footer(text="極曜月葵 ✦ 星月同行")

    await interaction.response.send_message(embed=embed)
    return


# 📈 個人資料


@bot.tree.command(name="個人資料")
async def profile(interaction: discord.Interaction):

    await interaction.response.defer()

    # 🔒 頻道限制
    if interaction.channel.id != INFO_CHANNEL:

        embed = discord.Embed(
            title="🌙 星月指令限制",
            description=(
                "📊 個人資料僅能於指定區域使用\n\n" f"請前往 <#{INFO_CHANNEL}>"
            ),
            color=discord.Color.from_rgb(186, 85, 211),
        )

        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    user_id = str(interaction.user.id)

    c.execute(
        """
        SELECT level, exp
        FROM users
        WHERE user_id=?
    """,
        (user_id,),
    )

    result = c.fetchone()

    if not result:
        level = 1
        exp = 0
    else:
        level, exp = result

    next_exp = level * 100

    c.execute(
        """
        SELECT COUNT(*)
        FROM users
        WHERE level > ?
           OR (level = ? AND exp > ?)
    """,
        (level, level, exp),
    )

    rank = c.fetchone()[0] + 1

    bg = Image.open("images/rank_bg.jpg").convert("RGBA")

    bg = bg.resize((800, 450))

    # 下載頭像
    async with aiohttp.ClientSession() as session:

        async with session.get(interaction.user.display_avatar.url) as resp:

            avatar_bytes = await resp.read()

    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")

    avatar = avatar.resize((150, 150))

    # 圓形頭像
    mask = Image.new("L", (150, 150), 0)

    draw_mask = ImageDraw.Draw(mask)

    draw_mask.ellipse((0, 0, 150, 150), fill=255)

    avatar.putalpha(mask)

    bg.paste(avatar, (30, 110), avatar)

    # 金色頭像框
    draw_avatar = ImageDraw.Draw(bg)

    draw_avatar.ellipse((25, 105, 185, 265), outline="#FFD700", width=5)

    # 半透明資訊底板
    glass = Image.new("RGBA", bg.size, (0, 0, 0, 0))

    glass_draw = ImageDraw.Draw(glass)

    glass_draw.rounded_rectangle((15, 60, 760, 350), radius=25, fill=(20, 20, 20, 150))

    bg = Image.alpha_composite(bg, glass)

    draw = ImageDraw.Draw(bg)

    # 字型
    font_name = ImageFont.truetype("fonts/NotoSansTC-Regular.ttf", 28)

    font_level = ImageFont.truetype("fonts/NotoSansTC-Regular.ttf", 42)

    font_small = ImageFont.truetype("fonts/NotoSansTC-Regular.ttf", 22)

    # 名稱
    draw.text((210, 90), interaction.user.display_name, fill="white", font=font_name)

    # 等級
    draw.text((210, 145), f"Lv.{level}", fill="#FFD700", font=font_level)

    # 排名徽章底板
    draw.rounded_rectangle((600, 80, 760, 170), radius=20, fill=(40, 40, 40, 180))

    # 排名標題
    draw.text((625, 90), "排名", fill="#FFD700", font=font_small)

    # 排名數字
    draw.text((625, 115), f"#{rank}", fill="white", font=font_level)

    # 經驗值比例
    percent = exp / max(next_exp, 1)

    percent_text = int(percent * 100)

    # 背景條
    draw.rounded_rectangle((210, 250, 720, 285), radius=15, fill=(60, 60, 60))

    # 經驗條
    draw.rounded_rectangle(
        (210, 250, 210 + int(510 * percent), 285), radius=15, fill=(180, 100, 255)
    )

    # XP文字
    draw.text(
        (210, 305),
        f"{exp:,} / {next_exp:,} XP ({percent_text}%)",
        fill="white",
        font=font_small,
    )
    output = io.BytesIO()

    bg.save(output, format="PNG")

    output.seek(0)

    await interaction.followup.send(file=discord.File(output, filename="profile.png"))


# 🎮 聊天經驗系統
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    user_id = str(message.author.id)

    c.execute(
        """
        INSERT OR IGNORE INTO users
        (user_id,money,exp,level)
        VALUES (?,0,0,1)
        """,
        (user_id,),
    )

    c.execute("SELECT exp, level FROM users WHERE user_id=?", (user_id,))

    data = c.fetchone()

    if not data:
        await bot.process_commands(message)
        return

    exp, level = data

    gain = random.randint(5, 10)
    exp += gain

    need_exp = level * 100
    level_up = False

    while exp >= need_exp:

        exp -= need_exp
        level += 1

        need_exp = level * 100
        level_up = True

    c.execute(
        """
        UPDATE users
        SET exp=?, level=?
        WHERE user_id=?
        """,
        (exp, level, user_id),
    )

    conn.commit()

    if level_up:

        channel = bot.get_channel(LEVEL_UP_CHANNEL)

        embed = discord.Embed(
            title="🌙 等級提升",
            description=(f"{message.author.mention}\n\n" f"✨ 已提升至 Lv.{level}"),
            color=discord.Color.from_rgb(186, 85, 211),
        )

        embed.set_footer(text="極曜月葵 ✦ 星月同行")

        if channel:
            await channel.send(embed=embed)

    await bot.process_commands(message)


# ⚙️ 管理員設定等級
@bot.tree.command(name="設定等級")
@app_commands.default_permissions(administrator=True)
@app_commands.rename(member="成員", level="等級")
async def set_level(
    interaction: discord.Interaction, member: discord.Member, level: int
):

    c.execute(
        "UPDATE users SET level=?, exp=0 WHERE user_id=?", (level, str(member.id))
    )
    conn.commit()

    await interaction.response.send_message(f"✅ 已將 {member.mention} 設為 Lv.{level}")


# ⚙️ 頻道設定
@bot.tree.command(name="設定生日頻道")
@app_commands.default_permissions(administrator=True)
@app_commands.rename(channel="頻道")
async def set_birthday_channel(
    interaction: discord.Interaction, channel: discord.TextChannel
):

    c.execute(
        "REPLACE INTO settings VALUES ('birthday_channel', ?)", (str(channel.id),)
    )
    conn.commit()

    await interaction.response.send_message(
        f"✅ 生日通知頻道已設定為 {channel.mention}"
    )


@bot.tree.command(name="設定歡迎頻道")
@app_commands.default_permissions(administrator=True)
@app_commands.rename(channel="頻道")
async def set_welcome_channel(
    interaction: discord.Interaction, channel: discord.TextChannel
):
    c.execute("REPLACE INTO settings VALUES ('welcome_channel', ?)", (str(channel.id),))
    conn.commit()
    await interaction.response.send_message(f"✅ 已設定：{channel.mention}")


@bot.tree.command(name="設定管理員頻道")
@app_commands.default_permissions(administrator=True)
@app_commands.rename(channel="頻道")
async def set_admin_channel(
    interaction: discord.Interaction, channel: discord.TextChannel
):
    c.execute("REPLACE INTO settings VALUES ('admin_channel', ?)", (str(channel.id),))
    conn.commit()
    await interaction.response.send_message(f"✅ 已設定：{channel.mention}")


# 🎂 生日系統（最終穩定版）
@tasks.loop(time=time(hour=8, minute=0, tzinfo=tz))
async def birthday_check():

    now = datetime.now(tz)
    today_str = now.strftime("%Y-%m-%d")

    c.execute("SELECT value FROM settings WHERE key='last_birthday'")
    data = c.fetchone()
    if data and data[0] == today_str:
        return

    if now.hour != 8 or now.minute != 0:
        return

    c.execute("REPLACE INTO settings VALUES ('last_birthday', ?)", (today_str,))
    conn.commit()

    today = now.strftime("%m-%d")

    c.execute("SELECT user_id FROM users WHERE birthday=?", (today,))
    users = c.fetchall()

    if not users:
        return

    # 🎂 生日頻道（直接綁定）
    channel = bot.get_channel(1516119757383008479)

    # 🔐 管理員頻道
    c.execute("SELECT value FROM settings WHERE key='admin_channel'")
    admin_data = c.fetchone()
    admin_channel = bot.get_channel(int(admin_data[0])) if admin_data else None

    for (uid,) in users:
        user = bot.get_user(int(uid)) or await bot.fetch_user(int(uid))

        # 🎰 抽卡
        roll = random.random()
        if roll < 0.70:
            reward = 1000
            reward_text = "✨ 星月祝福"
        elif roll < 0.95:
            reward = 2000
            reward_text = "🌟 閃耀祝福"
        else:
            reward = 5000
            reward_text = "💎 極光降臨"

        # 💰 發錢
        c.execute("UPDATE users SET money = money + ? WHERE user_id=?", (reward, uid))
        conn.commit()

        # 🔐 管理員
        if admin_channel:
            c.execute("SELECT birth_year FROM users WHERE user_id=?", (uid,))
            year_data = c.fetchone()

            age_text = "未提供"
            if year_data and year_data[0]:
                age = now.year - year_data[0]
                age_text = f"{age}歲（{year_data[0]}）"

            admin_embed = discord.Embed(
                title="🎂 壽星資料", color=discord.Color.orange()
            )

            admin_embed.add_field(name="👤 使用者", value=user.display_name)
            admin_embed.add_field(name="🎁 獎勵", value=f"{reward_text} +{reward}")
            admin_embed.add_field(name="🎂 年齡", value=age_text)

            await admin_channel.send(embed=admin_embed)

        # 🎬 動畫（完整三段）
        if channel:
            msg = await channel.send("🌙 星門正在開啟...")
            await asyncio.sleep(1.2)

            await msg.edit(content="✨ 正在編織誕生日祝福...")
            await asyncio.sleep(1.2)

            await msg.edit(content="🎂 星月祝福降臨")
            await asyncio.sleep(1.2)

            embed = discord.Embed(
                title="🌙 𝑩𝒊𝒓𝒕𝒉𝒅𝒂𝒚 𝑩𝒍𝒆𝒔𝒔𝒊𝒏𝒈",
                description=f"✨ 今天是 {user.mention} 的誕生日 ✨\n\n願星光與月影都為你停留 🌙\n願這一刻，被世界溫柔記住",
                color=discord.Color.from_rgb(186, 85, 211),
            )

            embed.set_author(
                name=f"{user.display_name} ✦ 星月之子", icon_url=user.display_avatar.url
            )

            embed.add_field(
                name="🎁 星月贈禮",
                value=f"{reward_text}\n<a:emoji40:1510362334026268713> +{reward}",
                inline=False,
            )

            embed.set_thumbnail(url=user.display_avatar.url)

            if reward == 5000:
                embed.add_field(
                    name="💎 極光降臨",
                    value="✨ 罕見祝福降臨，全服見證 ✨",
                    inline=False,
                )

            await asyncio.sleep(0.8)
            await msg.edit(content=None, embed=embed)

    # 🔔 明天提醒
    tomorrow = (now + timedelta(days=1)).strftime("%m-%d")

    c.execute("SELECT user_id FROM users WHERE birthday=?", (tomorrow,))
    tomorrow_users = c.fetchall()

    if tomorrow_users and admin_channel:
        text = ""
        for (uid,) in tomorrow_users:
            user = bot.get_user(int(uid)) or await bot.fetch_user(int(uid))
            text += f"{user.display_name}\n"

        await admin_channel.send(f"⚠️ 明天壽星：\n{text}")


# ==========================
# 🌙 抽獎背景檢查
# ==========================


@tasks.loop(seconds=10)
async def lottery_checker():

    print("🌙 lottery_checker 執行中")

    now = datetime.now()

    c.execute("""
        SELECT
            message_id,
            channel_id,
            end_time
        FROM lotteries
        WHERE status='running'
    """)

    lotteries = c.fetchall()

    print(f"找到 {len(lotteries)} 場進行中的抽獎")

    for message_id, channel_id, end_time in lotteries:

        print(f"檢查抽獎：{message_id}")

        end_time = datetime.fromisoformat(end_time)

        if end_time <= now:

            print("✅ 已到截止時間")


# ==========================================
# # 🌸 歡迎系統 #
# ==========================================


@bot.event
async def on_member_join(member):

    # ==========================
    # 自動給予新人成員身分組
    # ==========================

    role = member.guild.get_role(1505110931300941844)

    if role is not None:
        await member.add_roles(role, reason="新成員自動加入")

    # 取得歡迎頻道
    c.execute("""
        SELECT value
        FROM settings
        WHERE key='welcome_channel'
    """)

    data = c.fetchone()

    if not data:
        return

    channel = bot.get_channel(int(data[0]))

    if channel is None:
        return

    # ==========================
    # Welcome Card
    # ==========================

    card = await create_welcome_card(member)

    # ==========================
    # 歡迎 Embed
    # ==========================

    embed = discord.Embed(title="🌙 歡迎加入極曜月葵", color=discord.Color.dark_grey())

    embed.description = f"""
歡迎 {member.mention} 寶寶加入我們𖤐⋆₊˚ 𝒳 ⋆ 𝒳 ⋆ 𝒳 ⋆ 𝒳 極 曜 月 葵 ˚₊⋆𖤐

很開心你來到這個小小的粉絲交流空間！<a:emoji_32:1508529055832739911>

<a:emoji_1:1506013957905846372> 請 {member.mention} 寶寶至 <#1506198162724094074>

提供與角色聊天的截圖。

📌 **C 台角色等級需達到 30 等**

📌 **T 台角色等級需達到 3 等**

我們進行審核通過後，
會再人工修改身分組唷<a:emoji_2:1506043914115879014>
"""

    embed.set_footer(text="極曜月葵 ✦ Welcome")

    # 先送文字（灰底）
    await channel.send(embed=embed)

    # 再送 Welcome Card
    await channel.send(file=card)


@bot.tree.command(name="生日登記", description="設定你的生日")
@app_commands.rename(month="月份", day="日期", year="出生年")
@app_commands.describe(month="生日月份", day="生日日期", year="選填")
async def set_birthday(
    interaction: discord.Interaction, month: int, day: int, year: int = None
):

    user_id = str(interaction.user.id)

    # 格式：MM-DD
    birthday = f"{month:02d}-{day:02d}"

    c.execute(
        """
    UPDATE users
    SET birthday=?, birth_year=?
    WHERE user_id=?
    """,
        (birthday, year, user_id),
    )

    conn.commit()

    await interaction.response.send_message(
        f"🎂 已設定生日為 {birthday}" + (f"（{year}）" if year else ""), ephemeral=True
    )


@bot.tree.command(name="生日查詢", description="查看你的生日")
async def check_birthday(interaction: discord.Interaction):

    user_id = str(interaction.user.id)

    c.execute("SELECT birthday, birth_year FROM users WHERE user_id=?", (user_id,))
    data = c.fetchone()

    if not data or not data[0]:
        await interaction.response.send_message("❌ 你還沒有設定生日", ephemeral=True)
        return

    birthday, year = data

    text = f"🎂 你的生日：{birthday}"
    if year:
        text += f"\n📅 出生年：{year}"

    await interaction.response.send_message(text, ephemeral=True)


@bot.tree.command(name="本月壽星", description="查看本月壽星")
async def birthday_list(interaction: discord.Interaction):

    now = datetime.now(tz)
    month = now.strftime("%m")

    c.execute(
        "SELECT user_id, birthday FROM users WHERE birthday LIKE ?", (f"{month}-%",)
    )
    users = c.fetchall()

    if not users:
        await interaction.response.send_message("📭 本月沒有壽星", ephemeral=True)
        return

    text = ""

    for uid, bday in users:
        user = await bot.fetch_user(int(uid))
        text += f"{user.display_name} ｜ {bday}\n"

    embed = discord.Embed(
        title="🎂 本月壽星", description=text, color=discord.Color.pink()
    )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="生日刪除", description="刪除你的生日資料")
async def delete_birthday(interaction: discord.Interaction):

    user_id = str(interaction.user.id)

    c.execute(
        "UPDATE users SET birthday=NULL, birth_year=NULL WHERE user_id=?", (user_id,)
    )
    conn.commit()

    await interaction.response.send_message("🗑️ 生日資料已刪除", ephemeral=True)


# 💼 打工
@bot.tree.command(name="打工")
async def work(interaction: discord.Interaction):

    # 🔒 頻道限制
    if interaction.channel.id != WORK_CHANNEL:

        embed = discord.Embed(
            title="💼 星月委託中心",
            description=f"請前往 <#{WORK_CHANNEL}> 接取委託任務",
            color=discord.Color.green(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    user_id = str(interaction.user.id)

    # 👤 建立資料
    c.execute(
        """
        INSERT OR IGNORE INTO users
        (user_id,money,exp,level)
        VALUES (?,0,0,1)
        """,
        (user_id,),
    )
    conn.commit()

    # ⏳ 冷卻
    c.execute("SELECT last_work,money FROM users WHERE user_id=?", (user_id,))

    data = c.fetchone()

    last_work = data[0]
    money = data[1]

    if last_work:

        last_time = datetime.fromisoformat(last_work)

        remain = timedelta(hours=1) - (datetime.now(tz) - last_time)

        if remain.total_seconds() > 0:

            minutes = int(remain.total_seconds() // 60)
            seconds = int(remain.total_seconds() % 60)

            embed = discord.Embed(
                title="⏳ 星月委託冷卻中",
                description=f"剩餘時間：{minutes}分 {seconds}秒",
                color=discord.Color.orange(),
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

    # 📜 工作列表
    jobs = [
        ("整理月神圖書館", 120, 250),
        ("護送星月商隊", 180, 320),
        ("照顧月光花園", 100, 220),
        ("清理古代遺跡", 200, 380),
        ("協助魔法研究", 220, 450),
        ("採集月光礦石", 150, 300),
        ("巡邏星空城區", 180, 350),
    ]

    job_name, low, high = random.choice(jobs)

    # 🎲 事件
    roll = random.randint(1, 100)

    if roll <= 5:

        reward = random.randint(low, high) * 3

        title = "🌟 月神眷顧"
        desc = "獲得三倍報酬"
        event_type = "success"

    elif roll <= 75:

        reward = random.randint(low, high)

        title = "✨ 委託成功"
        desc = "順利完成任務"
        event_type = "success"

    elif roll <= 90:

        reward = int(random.randint(low, high) * 0.5)

        title = "⚠️ 工作失誤"
        desc = "只獲得部分報酬"
        event_type = "success"

    elif roll <= 97:

        reward = random.randint(100, 500)

        title = "💸 工作意外"
        desc = "損壞設備需要賠償"
        event_type = "loss"

    else:

        reward = random.randint(500, 1500)

        title = "☠️ 災難事件"
        desc = "任務失敗造成重大損失"
        event_type = "loss"

    # 💰 結算
    if event_type == "success":
        money += reward
    else:
        money = max(0, money - reward)

    # 💾 更新
    c.execute(
        """
        UPDATE users
        SET money=?,
            last_work=?
        WHERE user_id=?
        """,
        (money, datetime.now(tz).isoformat(), user_id),
    )

    conn.commit()

    # 🌙 Embed
    embed = discord.Embed(
        title="🌙 𝑴𝒐𝒐𝒏 𝑾𝒐𝒓𝒌",
        description=desc,
        color=discord.Color.from_rgb(186, 85, 211),
    )

    embed.set_author(
        name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url
    )

    embed.add_field(name="📜 委託內容", value=f"```{job_name}```", inline=False)

    embed.add_field(name="✨ 事件結果", value=f"```{title}```", inline=False)

    if event_type == "success":

        embed.add_field(
            name="🎁 本次收入", value=f"{NUNU_EMOJI} `{reward:,}`", inline=True
        )

    else:

        embed.add_field(
            name="💸 本次損失", value=f"{NUNU_EMOJI} `{reward:,}`", inline=True
        )

    embed.add_field(name="💰 錢包餘額", value=f"{NUNU_EMOJI} `{money:,}`", inline=True)

    embed.set_footer(text="極曜月葵 ✦ 星月同行")

    await interaction.response.send_message(embed=embed)


# 🛒 商店
@bot.tree.command(name="商店")
async def shop(interaction: discord.Interaction):

    # 🔒 頻道限制
    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="🛒 星月商會",
            description=("✨ 商會區域限定\n\n" f"請前往 <#{SHOP_CHANNEL}>"),
            color=discord.Color.gold(),
        )

        embed.add_field(
            name="📦 商會功能", value="商店｜購買｜背包｜錢包", inline=False
        )

        embed.set_footer(text="極曜月葵 ✦ 星月商會")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    c.execute("SELECT item_id, name, price, stock, description, image FROM shop")

    items = c.fetchall()

    if not items:
        await interaction.response.send_message("🛒 商店目前沒有商品")
        return

    view = ShopView(items)

    embed = discord.Embed(
        title="🛒 星月商會",
        description="✨ 點擊按鈕瀏覽商品",
        color=discord.Color.gold(),
    )

    await interaction.response.send_message(embed=embed, view=view)


# 💜 老公商店
@bot.tree.command(name="老公商店")
async def husband_shop(interaction: discord.Interaction):

    # 🔒 頻道限制
    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="💜 星月婚姻介紹所",
            description=(
                "✨ 老公商店僅能於指定區域使用\n\n" f"請前往 <#{SHOP_CHANNEL}>"
            ),
            color=discord.Color.from_rgb(255, 105, 180),
        )

        embed.add_field(name="💍 功能", value="老公商店｜購買老公", inline=False)

        embed.set_footer(text="極曜月葵 ✦ 命定之人")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    c.execute("""
        SELECT name
        FROM husbands
        ORDER BY husband_id
    """)

    husbands = c.fetchall()

    if not husbands:

        await interaction.response.send_message("💔 目前沒有可購買的老公")
        return

    husband_text = ""

    for i, husband in enumerate(husbands, start=1):

        husband_text += f"{i}. {husband[0]}\n"

    embed = discord.Embed(
        title="💜 星月婚姻介紹所",
        description=("歡迎挑選你的命定老公 ✨\n\n" f"{husband_text}"),
        color=discord.Color.from_rgb(255, 105, 180),
    )

    embed.set_footer(text="輸入 /購買老公 名稱")

    await interaction.response.send_message(embed=embed)


# 💜 購買老公
@bot.tree.command(name="購買老公")
async def buy_husband(interaction: discord.Interaction, 名稱: str):

    # 🔒 頻道限制
    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="💜 星月婚姻介紹所",
            description=(
                "✨ 購買老公僅能於指定區域使用\n\n" f"請前往 <#{SHOP_CHANNEL}>"
            ),
            color=discord.Color.from_rgb(255, 105, 180),
        )

        embed.add_field(
            name="💍 功能", value="老公商店｜購買老公｜我的老公", inline=False
        )

        embed.set_footer(text="極曜月葵 ✦ 命定之人")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    user_id = str(interaction.user.id)

    # 查老公是否存在
    c.execute(
        """
        SELECT husband_id
        FROM husbands
        WHERE name=?
    """,
        (名稱,),
    )

    husband = c.fetchone()

    if not husband:

        await interaction.response.send_message("❌ 查無此老公", ephemeral=True)
        return

    husband_id = husband[0]

    # 是否已擁有
    c.execute(
        """
        SELECT *
        FROM user_husbands
        WHERE user_id=?
        AND husband_id=?
    """,
        (user_id, husband_id),
    )

    if c.fetchone():

        await interaction.response.send_message(f"💜 你已經擁有 {名稱}", ephemeral=True)
        return

    # 查錢
    c.execute(
        """
        SELECT money
        FROM users
        WHERE user_id=?
    """,
        (user_id,),
    )

    data = c.fetchone()

    money = data[0] if data else 0

    if money < HUSBAND_PRICE:

        await interaction.response.send_message(
            (f"❌ 努努幣不足\n\n" f"需要：{HUSBAND_PRICE:,}\n" f"目前：{money:,}"),
            ephemeral=True,
        )
        return

    # 扣款
    c.execute(
        """
        UPDATE users
        SET money = money - ?
        WHERE user_id=?
    """,
        (HUSBAND_PRICE, user_id),
    )

    # 收藏
    c.execute(
        """
        INSERT INTO user_husbands
        (user_id, husband_id)
        VALUES (?, ?)
    """,
        (user_id, husband_id),
    )

    conn.commit()

    embed = discord.Embed(
        title="💜 收藏成功",
        description=(f"恭喜獲得\n\n" f"✨ {名稱} ✨"),
        color=discord.Color.from_rgb(255, 105, 180),
    )

    embed.add_field(name="💰 消耗", value=f"{HUSBAND_PRICE:,} 努努幣", inline=False)

    embed.set_footer(text="極曜月葵 ✦ 命定之人")

    await interaction.response.send_message(embed=embed)


# 💜 我的老公
@bot.tree.command(name="我的老公")
async def my_husbands(interaction: discord.Interaction):
    # 🔒 頻道限制
    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="💜 我的老公",
            description=("✨ 此功能僅能於指定區域使用\n\n" f"請前往 <#{SHOP_CHANNEL}>"),
            color=discord.Color.from_rgb(255, 105, 180),
        )

        embed.add_field(
            name="💍 功能", value="老公商店｜購買老公｜我的老公", inline=False
        )

        embed.set_footer(text="極曜月葵 ✦ 命定之人")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    user_id = str(interaction.user.id)

    c.execute(
        """
        SELECT h.name
        FROM user_husbands uh
        JOIN husbands h
        ON uh.husband_id = h.husband_id
        WHERE uh.user_id=?
        ORDER BY h.husband_id
    """,
        (user_id,),
    )

    husbands = c.fetchall()

    if not husbands:

        await interaction.response.send_message("💔 你目前還沒有收藏任何老公")
        return

    husband_text = "\n".join([f"💜 {h[0]}" for h in husbands])

    embed = discord.Embed(
        title="💜 我的老公",
        description=husband_text,
        color=discord.Color.from_rgb(255, 105, 180),
    )

    embed.set_footer(text=f"共收藏 {len(husbands)} 位老公")

    await interaction.response.send_message(embed=embed)


# 🎲 猜大小
@bot.tree.command(name="猜大小")
@app_commands.rename(choice="選擇", amount="金額")
@app_commands.describe(choice="選擇大小", amount="下注金額")
@app_commands.choices(
    choice=[
        app_commands.Choice(name="🔺 大", value="大"),
        app_commands.Choice(name="🔻 小", value="小"),
    ]
)
async def guess_big_small(interaction: discord.Interaction, choice: str, amount: int):
    if interaction.channel.id != BIGSMALL_CHANNEL:

        embed = discord.Embed(
            title="🎲 星月賭場",
            description=f"請前往 <#{BIGSMALL_CHANNEL}> 使用猜大小",
            color=discord.Color.red(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    choice = choice.strip()

    if choice not in ["大", "小"]:

        await interaction.response.send_message("❌ 請輸入：大 或 小", ephemeral=True)
        return

    # 💰 賭注限制
    if amount < MIN_BET or amount > MAX_BET:
        await interaction.response.send_message(
            f"❌ 賭注必須介於 {NUNU_EMOJI} `{MIN_BET:,}` ~ `{MAX_BET:,}`",
            ephemeral=True,
        )
        return

    user_id = str(interaction.user.id)

    c.execute("SELECT money FROM users WHERE user_id=?", (user_id,))

    data = c.fetchone()

    if not data:

        await interaction.response.send_message("❌ 找不到帳戶資料", ephemeral=True)
        return

    money = data[0]

    if money < amount:

        await interaction.response.send_message("❌ 努努幣不足", ephemeral=True)
        return

    # 🎲 骰子
    dice = random.randint(1, 6)

    result = "大" if dice >= 4 else "小"

    win = choice == result

    # ⭐ 結果池
    roll = random.randint(1, 100)

    event_name = ""
    change = 0

    if win:

        if roll <= 5:

            event_name = "⭐ 神運"
            change = int(amount * 5)

        elif roll <= 25:

            event_name = "✨ 大勝"
            change = int(amount * 2)

        else:

            event_name = "🎉 小勝"
            change = int(amount * 1.5)

    else:

        if roll <= 70:

            event_name = "💀 失敗"
            change = -amount

        else:

            event_name = "☠️ 爆死"
            change = -(amount * 2)

    money += change

    if money < 0:
        money = 0

    c.execute(
        """
        UPDATE users
        SET money=?
        WHERE user_id=?
        """,
        (money, user_id),
    )

    conn.commit()

    embed = discord.Embed(
        title="🎲 星月賭場・猜大小", color=discord.Color.from_rgb(186, 85, 211)
    )

    embed.set_author(
        name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url
    )

    embed.add_field(name="🎯 你的選擇", value=f"```{choice}```", inline=True)

    embed.add_field(name="🎲 骰子結果", value=f"```{dice}```", inline=True)

    embed.add_field(name="✨ 判定", value=f"```{event_name}```", inline=False)

    if change >= 0:

        embed.add_field(
            name="🎉 本次獲得", value=f"{NUNU_EMOJI} `{change:,}`", inline=False
        )

    else:

        embed.add_field(
            name="💸 本次損失", value=f"{NUNU_EMOJI} `{abs(change):,}`", inline=False
        )

    embed.add_field(name="💰 錢包餘額", value=f"{NUNU_EMOJI} `{money:,}`", inline=False)

    embed.set_footer(text="極曜月葵 ✦ 星月賭場")
    await interaction.response.send_message("🎲 擲骰準備中...")

    msg = await interaction.original_response()

    await asyncio.sleep(1)

    await msg.edit(content="🎲 骰子滾動中...")

    await asyncio.sleep(1)

    await msg.edit(content="🎲 🎲 ...")

    await asyncio.sleep(1)

    await msg.edit(content="👀 正在判定大小...")

    await asyncio.sleep(1)

    if result == "大":

        await msg.edit(content=f"🎲 骰子停在 {dice} 點（大）")

    else:

        await msg.edit(content=f"🎲 骰子停在 {dice} 點（小）")

    await asyncio.sleep(1)

    await msg.edit(content=None, embed=embed)


# ⚔️ 對賭
@bot.tree.command(name="對賭")
@app_commands.rename(target="玩家", amount="金額")
@app_commands.describe(target="要挑戰的玩家", amount="下注金額")
async def duel(interaction: discord.Interaction, target: discord.Member, amount: int):

    if interaction.channel.id != DUEL_CHANNEL:

        await interaction.response.send_message(
            f"❌ 請前往 <#{DUEL_CHANNEL}>", ephemeral=True
        )
        return

    if target.bot:

        await interaction.response.send_message("❌ 不能挑戰機器人")
        return

    if target.id == interaction.user.id:

        await interaction.response.send_message("❌ 不能挑戰自己")
        return

    # 💰 賭注限制
    if amount < MIN_BET or amount > MAX_BET:
        await interaction.response.send_message(
            f"❌ 賭注必須介於 {NUNU_EMOJI} `{MIN_BET:,}` ~ `{MAX_BET:,}`",
            ephemeral=True,
        )
        return

    embed = discord.Embed(title="⚔️ 星月對賭", color=discord.Color.red())

    embed.add_field(name="挑戰者", value=interaction.user.mention, inline=False)

    embed.add_field(name="被挑戰者", value=target.mention, inline=False)

    embed.add_field(name="賭注", value=f"{NUNU_EMOJI} `{amount:,}`", inline=False)

    embed.set_footer(text="60秒內接受挑戰")

    await interaction.response.send_message(
        embed=embed, view=DuelView(interaction.user, target, amount)
    )

    embed = discord.Embed(title="⚔️ 星月對賭", color=discord.Color.red())

    embed.add_field(name="挑戰者", value=interaction.user.mention, inline=False)

    embed.add_field(name="被挑戰者", value=target.mention, inline=False)

    embed.add_field(name="賭注", value=f"{NUNU_EMOJI} `{amount:,}`", inline=False)

    embed.set_footer(text="60秒內接受挑戰")


# 🎰 老虎機
@bot.tree.command(name="老虎機")
@app_commands.rename(amount="金額")
@app_commands.describe(amount="請輸入下注金額")
async def slot_machine(interaction: discord.Interaction, amount: int):

    if interaction.channel.id != SLOT_CHANNEL:

        embed = discord.Embed(
            title="🎰 星月賭場",
            description=f"請前往 <#{SLOT_CHANNEL}> 使用老虎機",
            color=discord.Color.red(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # 💰 賭注限制
    if amount < MIN_BET or amount > MAX_BET:
        await interaction.response.send_message(
            f"❌ 賭注必須介於 {NUNU_EMOJI} `{MIN_BET:,}` ~ `{MAX_BET:,}`",
            ephemeral=True,
        )
        return

    user_id = str(interaction.user.id)

    c.execute("SELECT money FROM users WHERE user_id=?", (user_id,))

    data = c.fetchone()

    if not data:

        await interaction.response.send_message("❌ 找不到帳戶資料", ephemeral=True)
        return

    money = data[0]

    if money < amount:

        await interaction.response.send_message("❌ 努努幣不足", ephemeral=True)
        return

    symbols = ["🍒", "🌙", "⭐", "💎"]

    slot = [random.choice(symbols), random.choice(symbols), random.choice(symbols)]

    result_text = " ".join(slot)

    reward = 0
    title = ""

    # ☠️ 爆機事件
    if random.randint(1, 100) <= 10:

        title = "☠️ 爆機"
        reward = -(amount * 2)

        slot = ["💀", "💀", "💀"]

        result_text = " ".join(slot)

    elif slot == ["💎", "💎", "💎"]:

        title = "⭐ 神運 JACKPOT"
        reward = amount * 10

    elif slot[0] == slot[1] == slot[2]:

        title = "✨ 大勝"
        reward = amount * 5

    elif slot[0] == slot[1] or slot[0] == slot[2] or slot[1] == slot[2]:

        title = "🎉 小勝"
        reward = amount * 2

    else:

        title = "💀 失敗"
        reward = -amount

    money += reward

    if money < 0:
        money = 0

    c.execute(
        """
        UPDATE users
        SET money=?
        WHERE user_id=?
        """,
        (money, user_id),
    )

    conn.commit()

    embed = discord.Embed(title="🎰 星月老虎機", color=discord.Color.gold())

    embed.set_author(
        name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url
    )

    embed.add_field(name="🎰 結果", value=f"```{result_text}```", inline=False)

    embed.add_field(name="✨ 判定", value=f"```{title}```", inline=False)

    if reward >= 0:

        embed.add_field(
            name="🎉 本次獲得", value=f"{NUNU_EMOJI} `{reward:,}`", inline=False
        )

    else:

        embed.add_field(
            name="💸 本次損失", value=f"{NUNU_EMOJI} `{abs(reward):,}`", inline=False
        )

    embed.add_field(name="💰 錢包餘額", value=f"{NUNU_EMOJI} `{money:,}`", inline=False)

    embed.set_footer(text="極曜月葵 ✦ 星月賭場")

    await interaction.response.send_message("🎰 啟動老虎機...")

    msg = await interaction.original_response()

    await asyncio.sleep(1)

    await msg.edit(content="🎰 🍒 ❔ ❔")

    await asyncio.sleep(1)

    await msg.edit(content="🎰 🍒 🌙 ❔")

    await asyncio.sleep(1)

    await msg.edit(content=f"🎰 {result_text}")

    await asyncio.sleep(1)

    await msg.edit(content=None, embed=embed)


# 🎁 驚喜箱
@bot.tree.command(name="驚喜箱")
@app_commands.rename(amount="金額")
@app_commands.describe(amount="請輸入開箱金額")
async def surprise_box(interaction: discord.Interaction, amount: int):

    if interaction.channel.id != SURPRISE_CHANNEL:

        embed = discord.Embed(
            title="🎁 星月驚喜箱",
            description=f"請前往 <#{SURPRISE_CHANNEL}> 使用驚喜箱",
            color=discord.Color.orange(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # 💰 賭注限制
    if amount < MIN_BET or amount > MAX_BET:
        await interaction.response.send_message(
            f"❌ 賭注必須介於 {NUNU_EMOJI} `{MIN_BET:,}` ~ `{MAX_BET:,}`",
            ephemeral=True,
        )
        return

    user_id = str(interaction.user.id)

    c.execute("SELECT money FROM users WHERE user_id=?", (user_id,))

    data = c.fetchone()

    if not data:

        await interaction.response.send_message("❌ 找不到帳戶資料", ephemeral=True)
        return

    money = data[0]

    if money < amount:

        await interaction.response.send_message("❌ 努努幣不足", ephemeral=True)
        return

    roll = random.randint(1, 100)

    if roll == 1:

        title = "🌌 星神祝福"
        reward = amount * 20

    elif roll <= 5:

        title = "👑 月神寶藏"
        reward = amount * 10

    elif roll <= 20:

        title = "💎 星光寶箱"
        reward = amount * 5

    elif roll <= 60:

        title = "🎉 意外之喜"
        reward = amount * 2

    elif roll <= 85:

        title = "📦 普通補給"
        reward = amount

    else:

        title = "💀 空箱子"
        reward = 0

    # 扣本金再發獎勵
    money = money - amount + reward

    if money < 0:
        money = 0

    c.execute(
        """
        UPDATE users
        SET money=?
        WHERE user_id=?
        """,
        (money, user_id),
    )

    conn.commit()

    net = reward - amount

    embed = discord.Embed(title="🎁 星月驚喜箱", color=discord.Color.orange())

    embed.set_author(
        name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url
    )

    embed.add_field(name="🎊 開箱結果", value=f"```{title}```", inline=False)

    if net >= 0:

        embed.add_field(
            name="🎉 淨收益", value=f"{NUNU_EMOJI} `+{net:,}`", inline=False
        )

    else:

        embed.add_field(
            name="💸 淨損失", value=f"{NUNU_EMOJI} `-{abs(net):,}`", inline=False
        )

    embed.add_field(name="💰 錢包餘額", value=f"{NUNU_EMOJI} `{money:,}`", inline=False)

    embed.set_footer(text="極曜月葵 ✦ 星月驚喜箱")
    await interaction.response.send_message("🎁 正在尋找神秘寶箱...")

    msg = await interaction.original_response()

    await asyncio.sleep(1)

    await msg.edit(content="📦 發現寶箱...")

    await asyncio.sleep(1)

    await msg.edit(content="🔓 正在開啟中...")

    await asyncio.sleep(1)

    await msg.edit(content="✨ 檢查獎勵中...")

    await asyncio.sleep(1)

    if roll == 1:

        await msg.edit(content="🌌 星神降臨...")

    elif roll <= 5:

        await msg.edit(content="👑 月神寶藏出現...")

    elif roll <= 20:

        await msg.edit(content="💎 稀有寶箱發光中...")

    elif roll <= 60:

        await msg.edit(content="🎉 發現意外驚喜...")

    elif roll <= 85:

        await msg.edit(content="📦 普通補給箱")

    else:

        await msg.edit(content="💀 裡面好像空空的...")

    await asyncio.sleep(1)

    await msg.edit(content=None, embed=embed)


# 🧭 探險
@bot.tree.command(name="探險")
async def adventure(interaction: discord.Interaction):

    if interaction.channel.id != ADVENTURE_CHANNEL:

        embed = discord.Embed(
            title="🧭 星月探險",
            description=f"請前往 <#{ADVENTURE_CHANNEL}> 使用探險",
            color=discord.Color.blurple(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    user_id = str(interaction.user.id)

    c.execute(
        """
        SELECT money,last_adventure
        FROM users
        WHERE user_id=?
        """,
        (user_id,),
    )

    data = c.fetchone()

    if not data:

        await interaction.response.send_message("❌ 找不到帳戶資料", ephemeral=True)
        return

    money, last_adventure = data

    now = datetime.now()

    if last_adventure:

        last_time = datetime.fromisoformat(last_adventure)

        remain = 1800 - int((now - last_time).total_seconds())

        if remain > 0:

            minutes = remain // 60
            seconds = remain % 60

            await interaction.response.send_message(
                f"⏳ 探險冷卻中\n還需 {minutes}分 {seconds}秒", ephemeral=True
            )
            return

    roll = random.randint(1, 100)

    title = ""
    reward = 0

    # 🌌 神級
    if roll <= 5:

        title = random.choice(["🌌 星神降臨", "🌌 月神祝福", "🌌 時空裂縫"])

        reward = random.randint(5000, 20000)

    # 👑 Boss
    elif roll <= 15:

        title = random.choice(["👑 深淵魔狼", "👑 星辰巨龍", "👑 月影騎士"])

        reward = random.randint(1000, 8000)

    # ⚔️ 危險
    elif roll <= 35:

        title = random.choice(["⚔️ 流浪盜賊", "⚔️ 深林陷阱", "⚔️ 魔物襲擊"])

        reward = -random.randint(100, 1000)

    # 🌿 普通
    else:

        title = random.choice(["🌿 補給箱", "🌿 旅行商人", "🌿 遺失財寶"])

        reward = random.randint(100, 1000)

    money += reward

    if money < 0:
        money = 0

    c.execute(
        """
        UPDATE users
        SET money=?,
            last_adventure=?
        WHERE user_id=?
        """,
        (money, now.isoformat(), user_id),
    )

    conn.commit()

    embed = discord.Embed(title="🧭 星月探險", color=discord.Color.blurple())

    embed.set_author(
        name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url
    )

    embed.add_field(name="📖 探險結果", value=f"```{title}```", inline=False)

    if reward >= 0:

        embed.add_field(
            name="🎉 獲得", value=f"{NUNU_EMOJI} `{reward:,}`", inline=False
        )

    else:

        embed.add_field(
            name="💸 損失", value=f"{NUNU_EMOJI} `{abs(reward):,}`", inline=False
        )

    embed.add_field(name="💰 錢包餘額", value=f"{NUNU_EMOJI} `{money:,}`", inline=False)

    embed.set_footer(text="極曜月葵 ✦ 星月探險")
    await interaction.response.send_message("🧭 正在離開月葵城...")

    msg = await interaction.original_response()

    await asyncio.sleep(1)

    await msg.edit(content="🌲 穿越迷霧森林...")

    await asyncio.sleep(1)

    await msg.edit(content="👀 搜尋遺跡蹤跡...")

    await asyncio.sleep(1)

    if roll <= 5:

        await msg.edit(content="🌌 神級氣息降臨...")

    elif roll <= 15:

        await msg.edit(content="👑 發現世界Boss...")

    elif roll <= 35:

        await msg.edit(content="⚔️ 遭遇危險事件...")

    else:

        await msg.edit(content="🎁 發現神秘寶箱...")

    await asyncio.sleep(1)

    await msg.edit(content=None, embed=embed)


# 💳 購買
@bot.tree.command(name="購買")
@app_commands.rename(item_id="商品編號")
@app_commands.describe(item_id="商店商品編號")
async def buy(interaction: discord.Interaction, item_id: int):

    # 🔒 頻道限制
    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="🛒 星月商會",
            description=f"請前往 <#{SHOP_CHANNEL}> 使用購買功能",
            color=discord.Color.gold(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    name, price, stock = item

    if stock <= 0:
        await interaction.response.send_message("❌ 商品已售完", ephemeral=True)
        return

    # 💰 查餘額
    c.execute("SELECT money FROM users WHERE user_id=?", (user_id,))

    data = c.fetchone()

    if not data:
        await interaction.response.send_message(
            "❌ 請先簽到或打工建立資料", ephemeral=True
        )
        return

    money = data[0]

    if money < price:
        await interaction.response.send_message("❌ 努努幣不足", ephemeral=True)
        return

    # 💰 扣款
    c.execute("UPDATE users SET money = money - ? WHERE user_id=?", (price, user_id))

    # 📦 扣庫存
    c.execute("UPDATE shop SET stock = stock - 1 WHERE item_id=?", (item_id,))

    # 🎒 加入背包
    c.execute(
        "SELECT amount FROM inventory WHERE user_id=? AND item_id=?", (user_id, item_id)
    )

    inv = c.fetchone()

    if inv:

        c.execute(
            """
            UPDATE inventory
            SET amount = amount + 1
            WHERE user_id=? AND item_id=?
            """,
            (user_id, item_id),
        )

    else:

        c.execute(
            """
            INSERT INTO inventory
            (user_id,item_id,amount)
            VALUES (?,?,1)
            """,
            (user_id, item_id),
        )

    conn.commit()

    embed = discord.Embed(title="🛍️ 購買成功", color=discord.Color.green())

    embed.add_field(name="📦 商品", value=f"```{name}```", inline=False)

    embed.add_field(name="💰 花費", value=f"{NUNU_EMOJI} `{price:,}`", inline=False)

    embed.set_footer(text="極曜月葵 ✦ 星月商會")

    await interaction.response.send_message(embed=embed)


# 🎒 背包
@bot.tree.command(name="背包")
async def inventory_cmd(interaction: discord.Interaction):

    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="🛒 星月商會",
            description=f"請前往 <#{SHOP_CHANNEL}> 使用背包功能",
            color=discord.Color.gold(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    user_id = str(interaction.user.id)

    c.execute(
        """
        SELECT shop.name, inventory.amount
        FROM inventory
        JOIN shop ON inventory.item_id = shop.item_id
        WHERE inventory.user_id=?
    """,
        (user_id,),
    )

    items = c.fetchall()

    if not items:
        await interaction.response.send_message("🎒 你的背包是空的")
        return

    text = ""

    for name, amount in items:
        text += f"🎁 {name} × {amount}\n"

    embed = discord.Embed(
        title="🎒 星月背包", description=text, color=discord.Color.purple()
    )

    embed.set_footer(text="極曜月葵 ✦ 星月商會")

    await interaction.response.send_message(embed=embed)


# 🎁 贈送道具
@bot.tree.command(name="贈送道具")
@app_commands.rename(member="成員", item_name="道具名稱", amount="數量")
@app_commands.describe(
    member="接收道具的玩家", item_name="要贈送的道具", amount="贈送數量"
)
async def give_item(
    interaction: discord.Interaction,
    member: discord.Member,
    item_name: str,
    amount: int,
):

    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="🛒 星月商會",
            description=f"請前往 <#{SHOP_CHANNEL}> 使用贈送功能",
            color=discord.Color.gold(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    sender_id = str(interaction.user.id)
    target_id = str(member.id)

    c.execute("SELECT item_id FROM shop WHERE name=?", (item_name,))

    item = c.fetchone()

    if not item:

        await interaction.response.send_message("❌ 沒有這個商品", ephemeral=True)
        return

    item_id = item[0]

    c.execute(
        """
        SELECT amount
        FROM inventory
        WHERE user_id=? AND item_id=?
        """,
        (sender_id, item_id),
    )

    data = c.fetchone()

    if not data or data[0] < amount:

        await interaction.response.send_message("❌ 道具不足", ephemeral=True)
        return

    # 扣除自己
    c.execute(
        """
        UPDATE inventory
        SET amount = amount - ?
        WHERE user_id=? AND item_id=?
        """,
        (amount, sender_id, item_id),
    )

    # 對方背包
    c.execute(
        """
        SELECT amount
        FROM inventory
        WHERE user_id=? AND item_id=?
        """,
        (target_id, item_id),
    )

    target_data = c.fetchone()

    if target_data:

        c.execute(
            """
            UPDATE inventory
            SET amount = amount + ?
            WHERE user_id=? AND item_id=?
            """,
            (amount, target_id, item_id),
        )

    else:

        c.execute(
            """
            INSERT INTO inventory
            (user_id,item_id,amount)
            VALUES (?,?,?)
            """,
            (target_id, item_id, amount),
        )

    conn.commit()

    embed = discord.Embed(title="🎁 贈送成功", color=discord.Color.green())

    embed.add_field(name="📦 道具", value=f"```{item_name}```", inline=False)

    embed.add_field(name="👤 收件人", value=member.mention, inline=False)

    embed.add_field(name="📦 數量", value=f"`{amount}`", inline=False)

    embed.set_footer(text="極曜月葵 ✦ 星月商會")

    await interaction.response.send_message(embed=embed)


# ⚙️ 增加努努幣


@bot.tree.command(name="發努努幣")
@app_commands.default_permissions(administrator=True)
@app_commands.rename(amount="金額", member="成員", role="身分組", everyone="發送全體")
@app_commands.describe(
    amount="發送金額", member="指定成員", role="指定身分組", everyone="是否發送給全體"
)
async def give_money(
    interaction: discord.Interaction,
    amount: int,
    member: discord.Member = None,
    role: discord.Role = None,
    everyone: bool = False,
):

    await interaction.response.defer()

    # 🔒 限制頻道
    if interaction.channel.id != 1510930723924611163:
        await interaction.followup.send("❌ 請到管理員頻道使用", ephemeral=True)
        return

    # 🔒 管理員權限
    ALLOWED_ROLES = [
        1504824446769172602,
        1504833586807967914,
        1504863173168074823,
        1504863370552152124,
        1504864390388776992,
        1505616537296310492,
    ]

    if not any(r.id in ALLOWED_ROLES for r in interaction.user.roles):
        await interaction.followup.send("❌ 你沒有權限", ephemeral=True)
        return

    # 💰 賭注限制
    if amount < MIN_BET or amount > MAX_BET:
        await interaction.response.send_message(
            f"❌ 賭注必須介於 {NUNU_EMOJI} `{MIN_BET:,}` ~ `{MAX_BET:,}`",
            ephemeral=True,
        )
        return

    # 🔒 至少選一個對象
    if not member and not role and not everyone:
        await interaction.followup.send("❌ 請選擇發送對象", ephemeral=True)
        return

    count = 0

    # 👤 單人
    if member:

        user_id = str(member.id)

        c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))

        c.execute(
            "UPDATE users SET money = money + ? WHERE user_id=?", (amount, user_id)
        )

        count = 1

    # 👥 身分組
    elif role:

        for m in role.members:

            if m.bot:
                continue

            user_id = str(m.id)

            c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))

            c.execute(
                "UPDATE users SET money = money + ? WHERE user_id=?", (amount, user_id)
            )

            count += 1

    # 🌍 全體
    elif everyone:

        for m in interaction.guild.members:

            if m.bot:
                continue

            user_id = str(m.id)

            c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))

            c.execute(
                "UPDATE users SET money = money + ? WHERE user_id=?", (amount, user_id)
            )

            count += 1

    conn.commit()

    embed = discord.Embed(title="💰 發錢完成", color=discord.Color.green())

    embed.add_field(
        name="💵 發送金額", value=f"{NUNU_EMOJI} `{amount:,}`", inline=False
    )

    if member:
        embed.add_field(name="👤 發送對象", value=member.mention, inline=False)

    elif role:
        embed.add_field(name="🎭 發送對象", value=role.mention, inline=False)

    elif everyone:
        embed.add_field(name="🌍 發送對象", value="`全體成員`", inline=False)

    embed.add_field(name="👥 發送人數", value=f"`{count}` 人", inline=False)

    await interaction.followup.send(embed=embed)


# 💣 黑市投資
@bot.tree.command(name="黑市投資")
@app_commands.rename(amount="金額")
@app_commands.describe(amount="投資金額")
async def black_market(interaction: discord.Interaction, amount: int):

    # 🔒 頻道限制
    if interaction.channel.id != BLACKMARKET_CHANNEL:

        embed = discord.Embed(
            title="💣 黑市投資",
            description=("🌙 黑市交易區限定\n\n" f"請前往 <#{BLACKMARKET_CHANNEL}>"),
            color=discord.Color.dark_red(),
        )

        embed.add_field(
            name="📦 黑市業務", value="黑市投資｜高風險高報酬", inline=False
        )

        embed.set_footer(text="極曜月葵 ✦ 地下交易所")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # 💰 賭注限制
    if amount < MIN_BET or amount > MAX_BET:
        await interaction.response.send_message(
            f"❌ 賭注必須介於 {NUNU_EMOJI} `{MIN_BET:,}` ~ `{MAX_BET:,}`",
            ephemeral=True,
        )
        return

    user_id = str(interaction.user.id)

    # 💰 查錢包
    c.execute("SELECT money FROM users WHERE user_id=?", (user_id,))

    data = c.fetchone()

    if not data:

        await interaction.response.send_message("❌ 找不到帳戶資料", ephemeral=True)
        return

    money = data[0]

    if money < amount:

        await interaction.response.send_message("❌ 努努幣不足", ephemeral=True)
        return

    # 🎬 黑市動畫
    await interaction.response.send_message("💣 正在聯繫黑市商人...")

    msg = await interaction.original_response()

    await asyncio.sleep(1.2)

    await msg.edit(content="📦 正在驗貨...")

    await asyncio.sleep(1.2)

    await msg.edit(content="💰 正在結算...")

    await asyncio.sleep(1.2)

    # 🎲 投資結果
    roll = random.randint(1, 100)

    if roll <= 5:

        event = "🚀 暴富"
        change = amount * 5

    elif roll <= 25:

        event = "📈 大賺"
        change = amount * 2

    elif roll <= 50:

        event = "💰 小賺"
        change = int(amount * 1.5)

    elif roll <= 85:

        event = "📉 虧損"
        change = -amount

    else:

        event = "💥 捲款跑路"
        change = -(amount * 2)

    money += change

    if money < 0:
        money = 0

    # 💾 更新資料
    c.execute(
        """
        UPDATE users
        SET money=?
        WHERE user_id=?
        """,
        (money, user_id),
    )

    conn.commit()

    # 🎨 結果 Embed
    embed = discord.Embed(title="💣 黑市投資結果", color=discord.Color.dark_red())

    embed.set_author(
        name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url
    )

    embed.add_field(
        name="💵 投資金額", value=f"{NUNU_EMOJI} `{amount:,}`", inline=False
    )

    embed.add_field(name="📊 投資結果", value=f"```{event}```", inline=False)

    if change >= 0:

        embed.add_field(
            name="🎉 本次獲利", value=f"{NUNU_EMOJI} `{change:,}`", inline=False
        )

    else:

        embed.add_field(
            name="💸 本次損失", value=f"{NUNU_EMOJI} `{abs(change):,}`", inline=False
        )

    embed.add_field(name="🏦 錢包餘額", value=f"{NUNU_EMOJI} `{money:,}`", inline=False)

    embed.set_footer(text="極曜月葵 ✦ 地下交易所")

    await msg.edit(content=None, embed=embed)


# 🎯 猜心情


@bot.tree.command(name="猜心情")
@app_commands.rename(mood="心情", amount="金額")
@app_commands.describe(mood="選擇心情", amount="下注金額")
@app_commands.choices(
    mood=[
        app_commands.Choice(name="😊 開心", value="開心"),
        app_commands.Choice(name="😡 生氣", value="生氣"),
        app_commands.Choice(name="😴 想睡", value="想睡"),
        app_commands.Choice(name="😢 難過", value="難過"),
        app_commands.Choice(name="🤪 發瘋", value="發瘋"),
    ]
)
async def mood_game(interaction: discord.Interaction, mood: str, amount: int):

    # 🔒 頻道限制
    if interaction.channel.id != MOOD_CHANNEL:

        embed = discord.Embed(
            title="🎯 月神心情屋",
            description=("🌙 心情占卜區限定\n\n" f"請前往 <#{MOOD_CHANNEL}>"),
            color=discord.Color.fuchsia(),
        )

        embed.add_field(
            name="🎭 可猜測心情", value="開心｜生氣｜想睡｜難過｜發瘋", inline=False
        )

        embed.set_footer(text="極曜月葵 ✦ 月神心情屋")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    moods = ["開心", "生氣", "想睡", "難過", "發瘋"]

    if mood not in moods:

        await interaction.response.send_message(
            "❌ 可選：開心、生氣、想睡、難過、發瘋", ephemeral=True
        )
        return

    # 💰 賭注限制
    if amount < MIN_BET or amount > MAX_BET:
        await interaction.response.send_message(
            f"❌ 賭注必須介於 {NUNU_EMOJI} `{MIN_BET:,}` ~ `{MAX_BET:,}`",
            ephemeral=True,
        )
        return

    user_id = str(interaction.user.id)

    c.execute("SELECT money FROM users WHERE user_id=?", (user_id,))

    data = c.fetchone()

    if not data:

        await interaction.response.send_message("❌ 找不到帳戶資料", ephemeral=True)
        return

    money = data[0]

    if money < amount:

        await interaction.response.send_message("❌ 努努幣不足", ephemeral=True)
        return

    # 🎬 動畫
    await interaction.response.send_message("🌙 正在偷看月神心情...")

    msg = await interaction.original_response()

    await asyncio.sleep(1.2)

    await msg.edit(content="✨ 正在翻閱今日心情...")

    await asyncio.sleep(1.2)

    await msg.edit(content="🎭 正在確認答案...")

    await asyncio.sleep(1.2)

    real_mood = random.choice(moods)

    special = random.randint(1, 100)

    if mood == real_mood:

        result = "🎉 猜中了"
        change = amount * 3

    else:

        if special <= 5:

            result = "🌙 月神偏愛"
            change = 0

        elif special >= 96:

            result = "💀 月神暴怒"
            change = -(amount * 2)

        else:

            result = "❌ 猜錯了"
            change = -amount

    money += change

    if money < 0:
        money = 0

    c.execute(
        """
        UPDATE users
        SET money=?
        WHERE user_id=?
        """,
        (money, user_id),
    )

    conn.commit()

    embed = discord.Embed(title="🎯 月神心情屋", color=discord.Color.fuchsia())

    embed.set_author(
        name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url
    )

    embed.add_field(name="🎭 你的猜測", value=f"```{mood}```", inline=True)

    embed.add_field(name="🌙 真實心情", value=f"```{real_mood}```", inline=True)

    embed.add_field(name="✨ 結果", value=f"```{result}```", inline=False)

    if change >= 0:

        embed.add_field(
            name="🎉 本次獲得", value=f"{NUNU_EMOJI} `{change:,}`", inline=False
        )

    else:

        embed.add_field(
            name="💸 本次損失", value=f"{NUNU_EMOJI} `{abs(change):,}`", inline=False
        )

    embed.add_field(name="🏦 錢包餘額", value=f"{NUNU_EMOJI} `{money:,}`", inline=False)

    embed.set_footer(text="極曜月葵 ✦ 月神心情屋")

    await msg.edit(content=None, embed=embed)


# 🧪 實驗
@bot.tree.command(name="實驗")
@app_commands.rename(amount="金額")
@app_commands.describe(amount="投入金額")
async def experiment(interaction: discord.Interaction, amount: int):

    # 🔒 頻道限制
    if interaction.channel.id != LAB_CHANNEL:

        embed = discord.Embed(
            title="🧪 禁忌實驗室",
            description=("⚗️ 實驗區域限定\n\n" f"請前往 <#{LAB_CHANNEL}>"),
            color=discord.Color.teal(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # 💰 賭注限制
    if amount < MIN_BET or amount > MAX_BET:
        await interaction.response.send_message(
            f"❌ 賭注必須介於 {NUNU_EMOJI} `{MIN_BET:,}` ~ `{MAX_BET:,}`",
            ephemeral=True,
        )
        return

    user_id = str(interaction.user.id)

    c.execute("SELECT money FROM users WHERE user_id=?", (user_id,))

    data = c.fetchone()

    if not data:

        await interaction.response.send_message("❌ 找不到帳戶資料", ephemeral=True)
        return

    money = data[0]

    if money < amount:

        await interaction.response.send_message("❌ 努努幣不足", ephemeral=True)
        return

    # 🎬 動畫
    await interaction.response.send_message("🧪 準備實驗材料...")

    msg = await interaction.original_response()

    await asyncio.sleep(1.2)

    await msg.edit(content="⚗️ 正在混合藥劑...")

    await asyncio.sleep(1.2)

    await msg.edit(content="🌙 注入月神能量...")

    await asyncio.sleep(1.2)

    roll = random.randint(1, 100)

    if roll == 1:

        result = "🌌 神之造物"
        new_money = money - amount + (amount * 20)

    elif roll <= 5:

        result = "⚡ 超級成功"
        new_money = money - amount + (amount * 10)

    elif roll <= 20:

        result = "🧬 成功"
        new_money = money - amount + (amount * 5)

    elif roll <= 50:

        result = "✨ 穩定反應"
        new_money = money - amount + (amount * 2)

    elif roll <= 80:

        result = "💨 實驗失敗"
        new_money = money - amount

    elif roll <= 95:

        result = "☠️ 實驗爆炸"
        new_money = money - (amount * 2)

    else:

        result = "💀 虛空湮滅"
        new_money = 0

    if new_money < 0:
        new_money = 0

    diff = new_money - money

    c.execute(
        """
        UPDATE users
        SET money=?
        WHERE user_id=?
        """,
        (new_money, user_id),
    )

    conn.commit()

    embed = discord.Embed(title="🧪 禁忌實驗室", color=discord.Color.teal())

    embed.set_author(
        name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url
    )

    embed.add_field(name="⚗️ 實驗結果", value=f"```{result}```", inline=False)

    if diff >= 0:

        embed.add_field(name="🎉 收益", value=f"{NUNU_EMOJI} `+{diff:,}`", inline=False)

    else:

        embed.add_field(
            name="💸 損失", value=f"{NUNU_EMOJI} `-{abs(diff):,}`", inline=False
        )

    embed.add_field(
        name="🏦 錢包餘額", value=f"{NUNU_EMOJI} `{new_money:,}`", inline=False
    )

    if result == "💀 虛空湮滅":

        embed.add_field(
            name="🌑 虛空吞噬", value="你的所有努努幣被虛空徹底吞噬了...", inline=False
        )

    embed.set_footer(text="極曜月葵 ✦ 禁忌實驗室")

    await msg.edit(content=None, embed=embed)


# 🎰 賭命
@bot.tree.command(name="賭命")
@app_commands.rename(amount="金額")
@app_commands.describe(amount="下注金額")
async def gamble_life(interaction: discord.Interaction, amount: int):

    # 🔒 頻道限制
    if interaction.channel.id != LIFEBET_CHANNEL:

        embed = discord.Embed(
            title="🎰 命運審判所",
            description=("⚖️ 命運之輪區域限定\n\n" f"請前往 <#{LIFEBET_CHANNEL}>"),
            color=discord.Color.dark_purple(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # 💰 賭注限制
    if amount < MIN_BET or amount > MAX_BET:
        await interaction.response.send_message(
            f"❌ 賭注必須介於 {NUNU_EMOJI} `{MIN_BET:,}` ~ `{MAX_BET:,}`",
            ephemeral=True,
        )
        return

    user_id = str(interaction.user.id)

    c.execute("SELECT money FROM users WHERE user_id=?", (user_id,))

    data = c.fetchone()

    if not data:

        await interaction.response.send_message("❌ 找不到帳戶資料", ephemeral=True)
        return

    money = data[0]

    if money < amount:

        await interaction.response.send_message("❌ 努努幣不足", ephemeral=True)
        return

    # 🎬 動畫
    await interaction.response.send_message("🎰 命運之輪啟動...")

    msg = await interaction.original_response()

    await asyncio.sleep(1.2)

    await msg.edit(content="🌙 月神正在審判...")

    await asyncio.sleep(1.2)

    await msg.edit(content="⚖️ 命運正在選擇...")

    await asyncio.sleep(1.2)

    roll = random.randint(1, 100)

    if roll <= 50:

        result = "🌙 命運眷顧"
        new_money = money + amount

    elif roll <= 98:

        result = "💀 命運終結"
        new_money = money - amount

    elif roll == 99:

        result = "🌌 月神憐憫"
        new_money = money

    else:

        result = "☠️ 虛空吞噬"
        new_money = money - (amount * 2)

    if new_money < 0:
        new_money = 0

    diff = new_money - money

    c.execute(
        """
        UPDATE users
        SET money=?
        WHERE user_id=?
        """,
        (new_money, user_id),
    )

    conn.commit()

    embed = discord.Embed(title="🎰 命運審判所", color=discord.Color.dark_purple())

    embed.set_author(
        name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url
    )

    embed.add_field(name="⚖️ 審判結果", value=f"```{result}```", inline=False)

    if diff >= 0:

        embed.add_field(name="🎉 收益", value=f"{NUNU_EMOJI} `+{diff:,}`", inline=False)

    else:

        embed.add_field(
            name="💸 損失", value=f"{NUNU_EMOJI} `-{abs(diff):,}`", inline=False
        )

    embed.add_field(
        name="🏦 錢包餘額", value=f"{NUNU_EMOJI} `{new_money:,}`", inline=False
    )

    embed.set_footer(text="極曜月葵 ✦ 命運審判所")

    await msg.edit(content=None, embed=embed)


# 🗡 搶劫
@bot.tree.command(name="搶劫")
@app_commands.rename(amount="金額")
@app_commands.describe(amount="要投入的搶劫資金")
async def rob(interaction: discord.Interaction, amount: int):

    if interaction.channel.id != GANG_CHANNEL:

        await interaction.response.send_message(
            f"❌ 請前往 <#{GANG_CHANNEL}> 使用", ephemeral=True
        )
        return

    # 💰 賭注限制
    if amount < MIN_BET or amount > MAX_BET:
        await interaction.response.send_message(
            f"❌ 賭注必須介於 {NUNU_EMOJI} `{MIN_BET:,}` ~ `{MAX_BET:,}`",
            ephemeral=True,
        )
        return

    user_id = str(interaction.user.id)

    # 🔒 坐牢檢查
    c.execute(
        """
        SELECT release_time
        FROM jail
        WHERE user_id=?
        """,
        (user_id,),
    )

    jail_data = c.fetchone()

    if jail_data:

        if int(pytime.time()) < jail_data[0]:

            remain = jail_data[0] - int(pytime.time())

            await interaction.response.send_message(
                f"🔒 你正在坐牢中\n剩餘 {remain//60} 分鐘", ephemeral=True
            )
            return

        else:

            c.execute(
                """
                DELETE FROM jail
                WHERE user_id=?
                """,
                (user_id,),
            )

            conn.commit()

    c.execute(
        """
        SELECT money
        FROM users
        WHERE user_id=?
        """,
        (user_id,),
    )

    data = c.fetchone()

    if not data:

        await interaction.response.send_message("❌ 找不到帳戶", ephemeral=True)
        return

    money = data[0]

    if money < amount:

        await interaction.response.send_message("❌ 努努幣不足", ephemeral=True)
        return

    await interaction.response.send_message("🗡 潛入黑市據點...")

    msg = await interaction.original_response()

    await asyncio.sleep(1)

    await msg.edit(content="🔍 尋找金庫...")

    await asyncio.sleep(1)

    await msg.edit(content="💰 正在搬運戰利品...")

    await asyncio.sleep(1)

    wanted = await get_wanted_level(user_id)

    success_rate = max(ROBBERY_MIN_RATE, ROBBERY_MAX_RATE - (wanted * 0.05))

    roll = random.random()

    if roll < success_rate:

        jackpot = random.randint(1, 100)

        if jackpot <= 5:

            gain = random.randint(amount * 5, amount * 10)

            result = "💎 黑市金庫"

        else:

            gain = random.randint(amount, amount * 2)

            result = "💰 搶劫成功"

        money += gain

        c.execute(
            """
            UPDATE users
            SET money=?
            WHERE user_id=?
            """,
            (money, user_id),
        )

        await add_wanted(user_id)

    else:

        fine = int(amount * 1.5)

        money -= fine

        if money < 0:
            money = 0

        c.execute(
            """
            UPDATE users
            SET money=?
            WHERE user_id=?
            """,
            (money, user_id),
        )

        c.execute(
            """
            INSERT OR REPLACE INTO jail
            VALUES (?, ?)
            """,
            (user_id, int(pytime.time()) + JAIL_TIME),
        )

        result = "👮 被逮捕"
        gain = -fine

    conn.commit()

    embed = discord.Embed(title="🗡 黑市搶劫結果", color=discord.Color.red())

    embed.add_field(name="📜 結果", value=result, inline=False)

    embed.add_field(
        name="🚨 通緝", value=f"{await get_wanted_level(user_id)}", inline=False
    )

    embed.add_field(name="🏦 餘額", value=f"{NUNU_EMOJI} `{money:,}`", inline=False)

    if gain >= 0:

        embed.add_field(
            name="🎉 本次獲得", value=f"{NUNU_EMOJI} `{gain:,}`", inline=False
        )

    else:

        embed.add_field(
            name="💸 罰款", value=f"{NUNU_EMOJI} `{abs(gain):,}`", inline=False
        )

    await msg.edit(
        content=None,
        embed=embed,
    )


# =========================
# 📋 我的通緝
# =========================


@bot.tree.command(name="我的通緝")
async def my_wanted(interaction: discord.Interaction):

    if interaction.channel.id != GANG_CHANNEL:

        await interaction.response.send_message(
            f"❌ 請前往 <#{GANG_CHANNEL}> 使用", ephemeral=True
        )
        return

    user_id = str(interaction.user.id)

    wanted_level = await get_wanted_level(user_id)

    success_rate = max(20, int((0.60 - (wanted_level * 0.05)) * 100))

    if wanted_level == 0:

        status = "😇 目前沒有被通緝"

    elif wanted_level <= 3:

        status = "👀 警方正在注意你"

    elif wanted_level <= 6:

        status = "🚓 警方正在追查你"

    elif wanted_level <= 10:

        status = "🚨 警方正在全城追捕你"

    else:

        status = "☠️ 你已成為頭號通緝犯"

    embed = discord.Embed(title="📋 我的通緝資料", color=discord.Color.red())

    embed.add_field(name="🚨 通緝等級", value=f"`{wanted_level}`", inline=False)

    embed.add_field(name="📜 狀態", value=status, inline=False)

    embed.add_field(name="🎯 下次搶劫成功率", value=f"`{success_rate}%`", inline=False)

    await interaction.response.send_message(embed=embed)


# ==========================
# 🌙 建立抽獎
# ==========================


@bot.tree.command(name="抽獎建立", description="建立一場新的抽獎")
async def lottery_create(interaction: discord.Interaction):

    # -------------------------
    # 頻道限制
    # -------------------------

    if interaction.channel.id != LOTTERY_CHANNEL:

        await interaction.response.send_message(
            "❌ 請至抽獎頻道使用此指令。", ephemeral=True
        )
        return

    # -------------------------
    # 權限限制
    # -------------------------

    if not any(role.id in ALLOWED_ROLES for role in interaction.user.roles):

        await interaction.response.send_message(
            "❌ 只有管理員可以建立抽獎。", ephemeral=True
        )
        return

    # -------------------------
    # 選擇獎品
    # -------------------------

    embed = discord.Embed(
        title="🎁 建立抽獎",
        description=("請選擇本次抽獎的獎品類型。\n\n" "選擇後將會開啟對應的設定視窗。"),
        color=0xF1C40F,
    )

    await interaction.response.send_message(
        embed=embed, view=PrizeSelectView(), ephemeral=True
    )


# ⚙️ 設定歡迎訊息
@bot.tree.command(name="設定歡迎訊息")
@app_commands.default_permissions(administrator=True)
@app_commands.rename(message="訊息內容")
@app_commands.describe(message="新會員加入時顯示的歡迎訊息")
async def set_welcome_message(interaction: discord.Interaction, message: str):

    c.execute("REPLACE INTO settings VALUES ('welcome_message', ?)", (message,))
    conn.commit()

    await interaction.response.send_message("✅ 歡迎訊息已更新")


# 🌐 保活
def run_web():
    port = int(os.environ.get("PORT", 10000))
    with TCPServer(("", port), SimpleHTTPRequestHandler) as httpd:
        httpd.serve_forever()


threading.Thread(target=run_web, daemon=True).start()

bot.run(os.getenv("TOKEN"))
