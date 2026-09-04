# -*- coding: utf-8 -*-
import discord
from systems.test_achievement_box_discord_ready_v2 import setup as setup_achievement_box_test
from systems.moon_life import setup_moon_life
from systems.streak_lottery import setup_streak_lottery
from character_birthday import setup_character_birthday
from systems.limited_lottery import setup_limited_lottery
from systems.character_test import setup_character_test
from systems.mommy_roles import setup_mommy_roles
from systems.character_exam import setup_character_exam
from systems.bigsmall import setup_bigsmall
from systems.duel import setup_duel
from systems.slot import setup_slot
from config import EXCLUDED_USERS
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
from config import *
from systems.welcome import create_welcome_card
from blessings import (
    CHECKIN_BLESSINGS,
    RARE_BLESSINGS,
    EPIC_BLESSINGS,
    MYTH_BLESSINGS,
    BIRTHDAY_BLESSINGS,
    CHECKIN_REMINDERS,
)

tz = pytz.timezone(TIMEZONE)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ð¾ DB
from database import conn, c

# ==========================
# ð° ç¶æ¿ç³»çµ±
# ==========================


def ensure_user(user_id):

    c.execute(
        """
        INSERT OR IGNORE INTO users (user_id)
        VALUES (?)
        """,
        (str(user_id),),
    )

    conn.commit()


def get_money(user_id):

    ensure_user(user_id)

    c.execute(
        """
        SELECT money
        FROM users
        WHERE user_id = ?
        """,
        (str(user_id),),
    )

    row = c.fetchone()

    return row[0] if row else 0


def add_money(user_id, amount):

    ensure_user(user_id)

    c.execute(
        """
        UPDATE users
        SET money = money + ?
        WHERE user_id = ?
        """,
        (amount, str(user_id)),
    )

    conn.commit()


def remove_money(user_id, amount):

    ensure_user(user_id)

    c.execute(
        """
        UPDATE users
        SET money = CASE
            WHEN money >= ? THEN money - ?
            ELSE 0
        END
        WHERE user_id = ?
        """,
        (amount, amount, str(user_id)),
    )

    conn.commit()


# ð èå¬è³æè¡¨
c.execute("""
CREATE TABLE IF NOT EXISTS husbands (
    husband_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
)
""")

# ð ç©å®¶æ¶èèå¬
c.execute("""
CREATE TABLE IF NOT EXISTS user_husbands (
    user_id TEXT,
    husband_id INTEGER,
    PRIMARY KEY(user_id, husband_id)
)
""")


# ==========================
# ð æ½çç³»çµ±
# ==========================

c.execute("""
CREATE TABLE IF NOT EXISTS lotteries (

    message_id TEXT PRIMARY KEY,

    channel_id TEXT NOT NULL,

    host_id TEXT NOT NULL,

    prize_value TEXT NOT NULL,

    note TEXT,

    message TEXT,

    winner_count INTEGER NOT NULL,

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
try:
    c.execute("ALTER TABLE lotteries ADD COLUMN note TEXT")
except sqlite3.OperationalError:
    pass

try:
    c.execute("ALTER TABLE lotteries ADD COLUMN message TEXT")
except sqlite3.OperationalError:
    pass

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
# ð è¨ç®æ½ççµææé
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
# ð åªåªå¹£æ½ç Modal
# ==========================


class MoneyLotteryModal(discord.ui.Modal, title="ð° åªåªå¹£æ½ç"):

    money = discord.ui.TextInput(
        label="ð° åªåªå¹£æ¸é", placeholder="ä¾å¦ï¼5000", required=True, max_length=10
    )

    winners = discord.ui.TextInput(
        label="ð¥ ä¸­çäººæ¸", placeholder="ä¾å¦ï¼3", required=True, max_length=3
    )

    time = discord.ui.TextInput(
        label="â° æ½çæé", placeholder="ä¾å¦ï¼10", required=True, max_length=5
    )

    unit = discord.ui.TextInput(
        label="ð æéå®ä½",
        placeholder="è«è¼¸å¥ SãMãHãD",
        required=True,
        max_length=1,
    )

    # ==========================
    # ð æ½çç¢ºèª
    # ==========================
    async def on_submit(self, interaction: discord.Interaction):

        # -------------------------
        # é©è­è³æ
        # -------------------------

        try:
            money = int(self.money.value)
            winners = int(self.winners.value)
            time_amount = int(self.time.value)

        except ValueError:

            await interaction.response.send_message(
                "â è«è¼¸å¥æ­£ç¢ºçæ¸å­ã", ephemeral=True
            )
            return

        unit = self.unit.value.upper()

        end_time = get_lottery_end_time(time_amount, unit)

        if end_time is None:

            await interaction.response.send_message(
                "â æéå®ä½åªè½è¼¸å¥ SãMãHãDã", ephemeral=True
            )
            return

        timestamp = int(end_time.timestamp())

        # -------------------------
        # å»ºç« Embed
        # -------------------------

        embed = discord.Embed(title="ð Moon Bot æ½ç", color=0xF1C40F)

        embed.add_field(name="ð çå", value=f"ð° åªåªå¹£ {money:,}", inline=False)

        embed.add_field(name="ð¥ ä¸­çäººæ¸", value=f"{winners} äºº", inline=True)

        embed.add_field(name="ð¤ ä¸»è¾¦äºº", value=interaction.user.mention, inline=True)

        embed.add_field(
            name="â° æ½çæªæ­¢",
            value=f"<t:{timestamp}:F>",
            inline=False,
        )

        embed.add_field(name="ð çæ", value="ð¢ é²è¡ä¸­", inline=False)

        embed.set_footer(text="é»æä¸æ¹æéå³å¯åå æ½ç")

        # -------------------------
        # ç¼éæ½ç
        # -------------------------

        message = await interaction.channel.send(
            content=f"<@&{LOTTERY_PING_ROLE}>", embed=embed, view=LotteryView()
        )

        # -------------------------
        # å¯«å¥è³æåº«
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
        # å®æ
        # -------------------------

        await interaction.response.send_message("â æ½çå»ºç«æåï¼", ephemeral=True)


# ==========================
# ð æ½çæé
# ==========================


class LotteryView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    # ==========================
    # ð åå æ½ç
    # ==========================

    @discord.ui.button(
        label="ð åå æ½çï¼0ï¼",
        style=discord.ButtonStyle.success,
        custom_id="lottery_join",
    )
    async def join_lottery(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        # -------------------------
        # åå¾æ½ç ID
        # -------------------------

        message_id = str(interaction.message.id)
        user_id = str(interaction.user.id)

        # -------------------------
        # æ¯å¦å·²åå 
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
                "â ï¸ ä½ å·²ç¶åå éæ¬æ¬¡æ½çã", ephemeral=True
            )
            return

        # -------------------------
        # å å¥æ½ç
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
        # æ´æ°åå äººæ¸
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

        self.children[0].label = f"ð åå æ½çï¼{total}ï¼"

        await interaction.message.edit(view=self)

        # -------------------------
        # å®æ
        # -------------------------

        await interaction.response.send_message(
            "â å·²æååå æ½çï¼\n\nç¥ä½ å¥½é ð", ephemeral=True
        )

    # ==========================
    # ð¥ æ¥çåå®
    # ==========================

    @discord.ui.button(
        label="ð¥ æ¥çåå®",
        style=discord.ButtonStyle.secondary,
        custom_id="lottery_list",
    )
    async def view_members(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        # -------------------------
        # åå¾æ½ç ID
        # -------------------------

        message_id = str(interaction.message.id)

        # -------------------------
        # æ¥è©¢åå è
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
                "ð ç®åéæ²æäººåå æ¬æ¬¡æ½çã", ephemeral=True
            )
            return

        member_list = []

        for index, (user_id,) in enumerate(rows, start=1):

            member = interaction.guild.get_member(int(user_id))

            if member:

                member_list.append(f"`{index:02}`ï½{member.mention}")

        text = "\n".join(member_list)

        embed = discord.Embed(title="ð¥ æ½çåå åå®", description=text, color=0x5865F2)

        embed.add_field(
            name="ð åå äººæ¸", value=f"**{len(member_list)} äºº**", inline=False
        )

        embed.set_footer(text="Moon Bot Lottery")

        await interaction.response.send_message(embed=embed, ephemeral=True)


    # ==========================
    # ð çµææ½çï¼åç®¡çå¡ï¼
    # ==========================

    @discord.ui.button(
        label="ð çµææ½ç",
        style=discord.ButtonStyle.danger,
        custom_id="lottery_manual_end",
    )
    async def manual_end_lottery(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        if interaction.user.id not in LOTTERY_MANAGERS:
            await interaction.response.send_message(
                "â åªææ½çç®¡çå¡å¯ä»¥çµææ½çã", ephemeral=True
            )
            return

        message_id = str(interaction.message.id)

        c.execute(
            "SELECT status FROM lotteries WHERE message_id=?",
            (message_id,),
        )
        lottery = c.fetchone()

        if not lottery:
            await interaction.response.send_message(
                "â æ¾ä¸å°æ¬æ¬¡æ½çè³æã", ephemeral=True
            )
            return

        if lottery[0] != "running":
            await interaction.response.send_message(
                "ð æ¬æ¬¡æ½çå·²ç¶çµæã", ephemeral=True
            )
            return

        await interaction.response.send_message(
            "â ï¸ ç¢ºå®è¦æåçµææ¬æ¬¡æ½çåï¼\n"
            "ç¢ºèªå¾æç«å³æ½åºä¸­çèï¼ä¸ç¡æ³æ¢å¾©ã",
            view=ConfirmManualLotteryEndView(message_id),
            ephemeral=True,
        )


# ==========================
# â ï¸ ç¢ºèªæåçµææ½ç
# ==========================

class ConfirmManualLotteryEndView(discord.ui.View):

    def __init__(self, message_id):
        super().__init__(timeout=60)
        self.message_id = str(message_id)

    @discord.ui.button(label="â ç¢ºèªçµæä¸¦éç", style=discord.ButtonStyle.danger)
    async def confirm_end(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user.id not in LOTTERY_MANAGERS:
            await interaction.response.send_message(
                "â åªææ½çç®¡çå¡å¯ä»¥çµææ½çã", ephemeral=True
            )
            return

        c.execute(
            "SELECT status FROM lotteries WHERE message_id=?",
            (self.message_id,),
        )
        lottery = c.fetchone()

        if not lottery or lottery[0] != "running":
            await interaction.response.edit_message(
                content="ð æ¬æ¬¡æ½çå·²ç¶çµææä¸å­å¨ã", view=None
            )
            return

        await interaction.response.edit_message(
            content="â³ æ­£å¨æåçµææ½çä¸¦éçâ¦â¦", view=None
        )

        await finish_lottery(self.message_id)

    @discord.ui.button(label="â åæ¶", style=discord.ButtonStyle.secondary)
    async def cancel_end(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="â å·²åæ¶çµææ½çã", view=None
        )


# ==========================
# ð æ½ççåé¸æ
# ==========================


class PrizeSelectView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=180)

    # -------------------------
    # ð° åªåªå¹£
    # -------------------------

    @discord.ui.button(
        label="ð° åªåªå¹£",
        style=discord.ButtonStyle.success,
        row=0,
    )
    async def money(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        await interaction.response.send_modal(MoneyLotteryModal())

    # -------------------------
    # ð¨ äººè¨­å
    # -------------------------

    @discord.ui.button(
        label="ð¨ äººè¨­å",
        style=discord.ButtonStyle.primary,
        row=0,
    )
    async def image(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        await interaction.response.send_modal(ImageLotteryModal())

    # -------------------------
    # ð åç§
    # -------------------------

    @discord.ui.button(
        label="ð åç§",
        style=discord.ButtonStyle.primary,
        row=0,
    )
    async def couple(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        await interaction.response.send_modal(CoupleLotteryModal())

    # -------------------------
    # ð èªè¨
    # -------------------------

    @discord.ui.button(
        label="ð èªè¨",
        style=discord.ButtonStyle.secondary,
        row=0,
    )
    async def custom(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        await interaction.response.send_modal(CustomLotteryModal())


# ==========================
# ð äººè¨­åæ½ç Modal
# ==========================


class ImageLotteryModal(discord.ui.Modal, title="ð¨ äººè¨­åæ½ç"):

    winners = discord.ui.TextInput(
        label="ð¥ ä¸­çäººæ¸",
        placeholder="ä¾å¦ï¼1",
        required=True,
        max_length=3,
    )

    time = discord.ui.TextInput(
        label="â° æ½çæé",
        placeholder="ä¾å¦ï¼10",
        required=True,
        max_length=5,
    )

    unit = discord.ui.TextInput(
        label="ð æéå®ä½",
        placeholder="è«è¼¸å¥ SãMãHãD",
        required=True,
        max_length=1,
    )

    # ==========================
    # ð å»ºç«æ½ç
    # ==========================

    async def on_submit(self, interaction: discord.Interaction):

        # -------------------------
        # é©è­è³æ
        # -------------------------

        try:

            winners = int(self.winners.value)
            time_amount = int(self.time.value)

        except ValueError:

            await interaction.response.send_message(
                "â è«è¼¸å¥æ­£ç¢ºçæ¸å­ã",
                ephemeral=True,
            )
            return

        unit = self.unit.value.upper()

        end_time = get_lottery_end_time(time_amount, unit)

        if end_time is None:

            await interaction.response.send_message(
                "â æéå®ä½åªè½è¼¸å¥ SãMãHãDã",
                ephemeral=True,
            )
            return

        timestamp = int(end_time.timestamp())

        # -------------------------
        # å»ºç« Embed
        # -------------------------

        embed = discord.Embed(
            title="ð Moon Bot æ½ç",
            color=0xF1C40F,
        )

        embed.add_field(
            name="ð çå",
            value="ð¨ é¨æ©é¢¨æ ¼äººè¨­å",
            inline=False,
        )

        embed.add_field(
            name="ð¥ ä¸­çäººæ¸",
            value=f"{winners} äºº",
            inline=True,
        )

        embed.add_field(
            name="ð¤ ä¸»è¾¦äºº",
            value=interaction.user.mention,
            inline=True,
        )

        embed.add_field(
            name="â° æ½çæªæ­¢",
            value=f"<t:{timestamp}:F>\n<t:{timestamp}:R>",
            inline=False,
        )

        embed.add_field(
            name="ð çæ",
            value="ð¢ é²è¡ä¸­",
            inline=False,
        )

        embed.set_footer(text="é»æä¸æ¹æéå³å¯åå æ½ç")

        # -------------------------
        # ç¼éæ½ç
        # -------------------------

        message = await interaction.channel.send(
            content=f"<@&{LOTTERY_PING_ROLE}>",
            embed=embed,
            view=LotteryView(),
        )

        # -------------------------
        # å¯«å¥è³æåº«
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
                "image",
                "é¨æ©é¢¨æ ¼äººè¨­å",
                winners,
                end_time.isoformat(),
                "running",
                datetime.now().isoformat(),
            ),
        )

        conn.commit()

        # -------------------------
        # å®æ
        # -------------------------

        await interaction.response.send_message(
            "â äººè¨­åæ½çå»ºç«æåï¼",
            ephemeral=True,
        )


# ==========================
# ð åç§æ½ç Modal
# ==========================


class CoupleLotteryModal(discord.ui.Modal, title="ð åç§æ½ç"):

    winners = discord.ui.TextInput(
        label="ð¥ ä¸­çäººæ¸",
        placeholder="ä¾å¦ï¼1",
        required=True,
        max_length=3,
    )

    time = discord.ui.TextInput(
        label="â° æ½çæé",
        placeholder="ä¾å¦ï¼10",
        required=True,
        max_length=5,
    )

    unit = discord.ui.TextInput(
        label="ð æéå®ä½",
        placeholder="è«è¼¸å¥ SãMãHãD",
        required=True,
        max_length=1,
    )

    note = discord.ui.TextInput(
        label="ð åè¨»ï¼é¸å¡«ï¼",
        placeholder="ä¾å¦ï¼å¿«éæ½çãéå®åªä½åª½åªè§è²ç­...",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=500,
    )

    # ==========================
    # ð å»ºç«æ½ç
    # ==========================

    async def on_submit(self, interaction: discord.Interaction):

        # -------------------------
        # é©è­è³æ
        # -------------------------

        try:

            winners = int(self.winners.value)
            time_amount = int(self.time.value)

        except ValueError:

            await interaction.response.send_message(
                "â è«è¼¸å¥æ­£ç¢ºçæ¸å­ã",
                ephemeral=True,
            )
            return

        unit = self.unit.value.upper()
        note = self.note.value.strip()

        end_time = get_lottery_end_time(time_amount, unit)

        if end_time is None:

            await interaction.response.send_message(
                "â æéå®ä½åªè½è¼¸å¥ SãMãHãDã",
                ephemeral=True,
            )
            return

        timestamp = int(end_time.timestamp())

        # -------------------------
        # å»ºç« Embed
        # -------------------------

        embed = discord.Embed(
            title="ð Moon Bot æ½ç",
            color=0xF1C40F,
        )

        embed.add_field(
            name="ð çå",
            value="ð èåæè§è²åç§",
            inline=False,
        )

        if note:
            embed.add_field(
                name="ð åè¨»",
                value=note,
                inline=False,
            )

        embed.add_field(
            name="ð¥ ä¸­çäººæ¸",
            value=f"{winners} äºº",
            inline=True,
        )

        embed.add_field(
            name="ð¤ ä¸»è¾¦äºº",
            value=interaction.user.mention,
            inline=True,
        )

        embed.add_field(
            name="â° æ½çæªæ­¢",
            value=f"<t:{timestamp}:F>\n<t:{timestamp}:R>",
            inline=False,
        )

        embed.add_field(
            name="ð çæ",
            value="ð¢ é²è¡ä¸­",
            inline=False,
        )

        embed.set_footer(text="é»æä¸æ¹æéå³å¯åå æ½ç")

        # -------------------------
        # ç¼éæ½ç
        # -------------------------

        message = await interaction.channel.send(
            content=f"<@&{LOTTERY_PING_ROLE}>",
            embed=embed,
            view=LotteryView(),
        )

        # -------------------------
        # å¯«å¥è³æåº«
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
                "couple",
                "èåæè§è²åç§",
                winners,
                end_time.isoformat(),
                "running",
                datetime.now().isoformat(),
            ),
        )

        conn.commit()

        # -------------------------
        # å®æ
        # -------------------------

        await interaction.response.send_message(
            "â åç§æ½çå»ºç«æåï¼",
            ephemeral=True,
        )


# ==========================
# ð èªè¨æ½ç Modal
# ==========================


class CustomLotteryModal(discord.ui.Modal, title="ð èªè¨æ½ç"):

    prize = discord.ui.TextInput(
        label="ð çåå§å®¹",
        placeholder="ä¾å¦ï¼Discord Nitro ä¸åæ",
        required=True,
        max_length=100,
    )

    winners = discord.ui.TextInput(
        label="ð¥ ä¸­çäººæ¸",
        placeholder="ä¾å¦ï¼1",
        required=True,
        max_length=3,
    )

    time = discord.ui.TextInput(
        label="â° æ½çæé",
        placeholder="ä¾å¦ï¼10",
        required=True,
        max_length=5,
    )

    unit = discord.ui.TextInput(
        label="ð æéå®ä½",
        placeholder="è«è¼¸å¥ SãMãHãD",
        required=True,
        max_length=1,
    )

    message = discord.ui.TextInput(
        label="ð© ä¸­çéç¥ï¼é¸å¡«ï¼",
        placeholder="éæ®µæå­å°ç§è¨çµ¦ä¸­çè...",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=1000,
    )

    async def on_submit(self, interaction: discord.Interaction):

        # -------------------------
        # åå¾è¼¸å¥è³æ
        # -------------------------

        try:
            winners = int(self.winners.value)
            duration = int(self.time.value)
        except ValueError:
            await interaction.response.send_message(
                "â ä¸­çäººæ¸èæéå¿é æ¯æ¸å­ï¼",
                ephemeral=True,
            )
            return

        unit = self.unit.value.upper()
        custom_message = self.message.value.strip()

        # -------------------------
        # è¨ç®çµææé
        # -------------------------

        if unit == "S":
            end_time = datetime.utcnow() + timedelta(seconds=duration)
        elif unit == "M":
            end_time = datetime.utcnow() + timedelta(minutes=duration)
        elif unit == "H":
            end_time = datetime.utcnow() + timedelta(hours=duration)
        elif unit == "D":
            end_time = datetime.utcnow() + timedelta(days=duration)
        else:
            await interaction.response.send_message(
                "â æéå®ä½åªè½è¼¸å¥ SãMãHãDï¼",
                ephemeral=True,
            )
            return

        timestamp = int(end_time.timestamp())

        # -------------------------
        # å»ºç« Embed
        # -------------------------

        embed = discord.Embed(
            title="ð Moon Bot æ½ç",
            color=0xF1C40F,
        )

        embed.add_field(
            name="ð çå",
            value=self.prize.value,
            inline=False,
        )

        embed.add_field(
            name="ð¥ ä¸­çäººæ¸",
            value=f"{winners} äºº",
            inline=True,
        )

        embed.add_field(
            name="ð¤ ä¸»è¾¦äºº",
            value=interaction.user.mention,
            inline=True,
        )

        embed.add_field(
            name="â° æ½çæªæ­¢",
            value=f"<t:{timestamp}:F>\n<t:{timestamp}:R>",
            inline=False,
        )

        embed.add_field(
            name="ð çæ",
            value="ð¢ é²è¡ä¸­",
            inline=False,
        )

        embed.set_footer(text="é»æä¸æ¹æéå³å¯åå æ½ç")

        # -------------------------
        # ç¼éæ½ç
        # -------------------------

        lottery_message = await interaction.channel.send(
            content=f"<@&{LOTTERY_PING_ROLE}>",
            embed=embed,
            view=LotteryView(),
        )

        # -------------------------
        # å¯«å¥è³æåº«
        # -------------------------

        c.execute(
            """
            INSERT INTO lotteries (
                message_id,
                channel_id,
                host_id,
                prize_type,
                prize_value,
                message,
                winner_count,
                end_time,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(lottery_message.id),
                str(interaction.channel.id),
                str(interaction.user.id),
                "custom",
                self.prize.value,
                custom_message,
                winners,
                end_time.isoformat(),
                "running",
                datetime.now().isoformat(),
            ),
        )

        conn.commit()

        # -------------------------
        # å®æ
        # -------------------------

        await interaction.response.send_message(
            "â èªè¨æ½çå»ºç«æåï¼",
            ephemeral=True,
        )


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
    "é»æ",
    "æº«å·ç´",
    "è«¾è¶Â·å¡ç±³ç¾",
    "çå®",
    "ç©æ¢èµ«",
    "ç©ç¦¹æ",
    "éæ²",
    "è·¯è¥¿æ©",
    "è³½ææ¯",
    "ç¶­åæ",
    "å¥§ç¾ç»",
    "ä¼èäºæ¯",
    "ç©å®æ",
    "ç©å®è¾°",
    "å¸å¾¡è®",
    "æçé",
    "å¤é·¹ç¨",
    "æåéç",
    "é»ç¨é·¹å¤",
    "å¾¡å½±è®å¸",
    "è¥ç¡",
    "é»æ²æ",
    "ææ´",
    "ææ¥",
    "é¾ç·¹æ­",
    "ä½ç¡¯å¸",
    "ç©å½¥ç©",
    "ç©è©ç¾",
    "æ¢å±",
    "æå­æ´",
    "é¢å­è¨",
    "å½æ·æ",
    "ç¥å®",
    "ç¥ç¾¯",
    "æ¨å¤®",
    "èæ¸ç¦¾",
    "å¸­éå®¥",
    "éå­æ°",
    "èµ«é",
    "çé¸",
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
# ð Moon å¥ç¾¤å¯©æ ¸ç³»çµ±
# ===============================


class ReviewPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="ð éå§ç³è«", style=discord.ButtonStyle.green, custom_id="review_start"
    )
    async def review_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        await create_review_ticket(interaction)


# ==========================
# ð å»ºç«å¥ç¾¤å¯©æ ¸ Ticket
# ==========================


async def create_review_ticket(interaction: discord.Interaction):

    guild = interaction.guild
    member = interaction.user

    # åå¾åé¡
    category = guild.get_channel(REVIEW_CATEGORY)

    if category is None:
        await interaction.response.send_message("â æ¾ä¸å°å¯©æ ¸åé¡ã", ephemeral=True)
        return

    # ==========================
    # é²æ­¢éè¤å»ºç« Ticket
    # ==========================

    for channel in category.text_channels:

        if channel.topic is None:
            continue

        if f"Applicant={member.id}" in channel.topic:

            await interaction.response.send_message(
                "â ä½ ç®åå·²æä¸å¼µå¯©æ ¸ Ticketï¼è«ç­å¾ç®¡çå¡èçã", ephemeral=True
            )
            return

    # ==========================
    # å»ºç«æ¬é
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
    # å¯©æ ¸çµ
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
    # å»ºç« Ticket
    # ==========================

    ticket = await guild.create_text_channel(
        name=f"ðï½å¯©æ ¸-{member.display_name}",
        category=category,
        overwrites=overwrites,
        topic=(f"Applicant={member.id}\n" f"Status=Pending"),
    )

    # -------------------------
    # ç¼éå¯©æ ¸è¨æ¯
    # -------------------------

    message = await send_review_message(ticket, member)

    # -------------------------
    # æ´æ° Ticket Topic
    # -------------------------

    await ticket.edit(
        topic=(f"Applicant={member.id}\n" f"Status=Pending\n" f"Message={message.id}")
    )

    # -------------------------
    # åè¦ä½¿ç¨è
    # -------------------------

    await interaction.response.send_message(
        f"â å·²æåå»ºç«å¯©æ ¸ Ticketï¼{ticket.mention}", ephemeral=True
    )


# ==========================
# ð åå¾ Ticket ç³è«äºº
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
# ð åå¾å¯©æ ¸ Embed è¨æ¯
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
# ð æ´æ°å¯©æ ¸ Embed
# ==========================


async def update_review_embed(
    channel: discord.TextChannel, reviewer: discord.Member, status: str
):

    message = await get_review_message(channel)

    if message is None:
        return

    embed = message.embeds[0]

    timestamp = int(datetime.now().timestamp())

    # ð¤ ç³è«äººï¼ä¿æä¸è®ï¼
    applicant = embed.fields[0].value

    # ð å¯©æ ¸çæ
    embed.set_field_at(1, name="ð å¯©æ ¸çæ", value=status, inline=True)

    # ð® å¯©æ ¸äºº
    embed.set_field_at(2, name="ð® å¯©æ ¸äºº", value=reviewer.mention, inline=True)

    # ð å»ºç«æéï¼ä¿æåæ¬ï¼
    created_time = embed.fields[3].value

    embed.set_field_at(3, name="ð å»ºç«æé", value=created_time, inline=False)

    # â ééæé
    if len(embed.fields) == 4:

        embed.add_field(name="â ééæé", value=f"<t:{timestamp}:F>", inline=False)

    else:

        embed.set_field_at(
            4, name="â ééæé", value=f"<t:{timestamp}:F>", inline=False
        )

    await message.edit(embed=embed, view=ReviewManageView(disabled=True))


# ==========================
# ð ç¼éå¯©æ ¸è¨æ¯
# ==========================


async def send_review_message(channel: discord.TextChannel, member: discord.Member):

    review_role = channel.guild.get_role(REVIEW_ROLE)

    # --------------------------
    # éç¥ç³è«èèå¯©æ ¸çµ
    # --------------------------

    if review_role:
        mention_message = await channel.send(f"{member.mention} {review_role.mention}")
    else:
        mention_message = await channel.send(member.mention)

    await mention_message.delete(delay=3)

    # --------------------------
    # å¥ç¾¤å¯©æ ¸ Embed
    # --------------------------

    timestamp = int(datetime.now().timestamp())

    review_embed = discord.Embed(title="ð æ¥µææèµï½è³ææäº¤", color=0xC77DFF)

    review_embed.add_field(name="ð¤ ç³è«äºº", value=member.mention, inline=False)

    review_embed.add_field(name="ð å¯©æ ¸çæ", value="ð¡ ç­å¾å¯©æ ¸", inline=True)

    review_embed.add_field(name="ð® å¯©æ ¸äºº", value="ç­å¾å¯©æ ¸", inline=True)

    review_embed.add_field(name="ð å»ºç«æé", value=f"<t:{timestamp}:F>", inline=False)

    review_embed.description = (
        "ââââââââââââââââââââ\n\n"
        "ð¤ **è«å°ä»¥ä¸è³æä¸å³è³æ­¤é »é**\n\n"
        "ð¸ åä½åª½åªå¶ä¸­ä¸ä½è§è²èå¤©æªå\n\n"
        "ð¸ C å° **15 ç­** æ T å° **2 ç­** è§è²èå¤©æªå\n\n"
        "ð¸ åä½åª½åªIGçãå·²è¿½è¹¤æªåãï¼è«æ³¨æåä½é½è¦è¿½è¹¤å¦ï¼\n\n"
        "ââââââââââââââââââââ\n\n"
        "ð ä¸å³å®æå¾ï¼\n"
        "è«èå¿ç­å¾ç®¡çå¡å¯©æ ¸å³å¯ã"
    )
    message = await channel.send(embed=review_embed, view=ReviewManageView())

    return message


# ==========================
# ð å¯©æ ¸ç®¡çæé
# ==========================


class ReviewManageView(discord.ui.View):

    def __init__(self, disabled=False):

        super().__init__(timeout=None)

        if disabled:

            for item in self.children:

                if item.custom_id == "review_approve":
                    item.disabled = True

    @discord.ui.button(
        label="ð¢ éé", style=discord.ButtonStyle.success, custom_id="review_approve"
    )
    async def approve(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        # -------------------------
        # æ¬éæª¢æ¥
        # -------------------------

        if interaction.user.id not in BOT_ADMINS:
            await interaction.response.send_message(
                "â åªæç®¡çå¡å¯ä»¥ä½¿ç¨æ­¤æéã", ephemeral=True
            )
            return

        member = await get_ticket_member(interaction.channel)

        if member is None:
            await interaction.response.send_message("â æ¾ä¸å°ç³è«èã", ephemeral=True)
            return

        # -------------------------
        # èº«åçµ
        # -------------------------

        pending_role = interaction.guild.get_role(PENDING_ROLE)

        member_roles = [interaction.guild.get_role(role_id) for role_id in MEMBER_ROLES]

        try:

            if pending_role:
                await member.remove_roles(pending_role, reason="å¥ç¾¤å¯©æ ¸éé")

            roles_to_add = [role for role in member_roles if role is not None]

            if roles_to_add:
                await member.add_roles(*roles_to_add, reason="å¥ç¾¤å¯©æ ¸éé")

        except discord.Forbidden:

            await interaction.response.send_message(
                "â Bot æ²ææ¬éä¿®æ¹èº«åçµã",
                ephemeral=True,
            )
            return

        # -------------------------
        # æ´æ° Topic
        # -------------------------

        if interaction.channel.topic:
            await interaction.channel.edit(
                topic=interaction.channel.topic.replace(
                    "Status=Pending", "Status=Approved"
                )
            )

        # -------------------------
        # æ´æ°å¯©æ ¸ Embed
        # -------------------------

        await update_review_embed(interaction.channel, interaction.user, "ð¢ å·²éé")

        # -------------------------
        # å®æ
        # -------------------------

        await interaction.response.defer()

    @discord.ui.button(
        label="â« éé", style=discord.ButtonStyle.danger, custom_id="review_close"
    )
    async def close_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        if interaction.user.id not in BOT_ADMINS:

            await interaction.response.send_message(
                "â åªæç®¡çå¡å¯ä»¥ä½¿ç¨æ­¤æéã", ephemeral=True
            )
            return

        await interaction.response.send_message(
            "â ï¸ ç¢ºå®è¦éééå¼µ Ticket åï¼", view=CloseTicketView(), ephemeral=True
        )


# ==========================
# ð éé Ticket ç¢ºèª
# ==========================


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="â ç¢ºèªéé", style=discord.ButtonStyle.danger)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        if interaction.user.id not in BOT_ADMINS:

            await interaction.response.send_message(
                "â åªæç®¡çå¡å¯ä»¥éé Ticketã", ephemeral=True
            )
            return

        await interaction.response.send_message(
            "â« Ticket å°æ¼ **5 ç§å¾** ééã", ephemeral=True
        )

        await asyncio.sleep(5)

        await interaction.channel.delete(reason=f"{interaction.user} ééå¥ç¾¤å¯©æ ¸")

    @discord.ui.button(label="åæ¶", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.edit_message(content="â å·²åæ¶ééã", view=None)


# ð åå

@bot.event
async def on_ready():

    print(f"å·²ç»å¥ï¼{bot.user}")

    # -------------------------
    # æ°¸ä¹ Viewï¼Persistent Viewï¼
    # -------------------------

    bot.add_view(ReviewPanelView())
    bot.add_view(ReviewManageView())
    bot.add_view(LotteryView())

    # ð ä¸å¤éå®ç²ç
    setup_limited_lottery(bot)

    # ð åª½åªå°å±¬èº«åçµ
    setup_mommy_roles(bot)

    # ð è§è²èè©¦ç³»çµ±
    setup_character_exam(bot)
    
    # ð Moon Life
    setup_moon_life(bot, add_money=add_money)

    # ð§ª æå°±ç²ç Discord æ¸¬è©¦ç³»çµ±
    await setup_achievement_box_test(bot)
    
    # ð è§è²èè©¦ç³»çµ±
    setup_character_test(bot)

    try:
        synced = await bot.tree.sync()
        print(f"â å·²åæ­¥ {len(synced)} å Slash Commands")
    except Exception as e:
        print(f"â æä»¤åæ­¥å¤±æï¼{e}")

    # ð è§è²çæ¥ç³»çµ±
    await setup_character_birthday(bot)

    try:
        synced = await bot.tree.sync()
        print(f"â å·²åæ­¥ {len(synced)} å Slash Commands")
    except Exception as e:
        print(f"â æä»¤åæ­¥å¤±æï¼{e}")

    # ð çæ¥ç³»çµ±
    if not birthday_check.is_running():
        birthday_check.start()

    # ð æ¯æ¥ç°½å°æé
    if not checkin_reminder.is_running():
        checkin_reminder.start()

    # ð æ½çç³»çµ±
    if not lottery_checker.is_running():
        lottery_checker.start()

    # ðï¸ äººè¨­åå¬åç³»çµ±
    if not photo_event_check.is_running():
        photo_event_check.start()
        print("â photo_event_check å·²åå")
        
@bot.tree.command(name="å¯©æ ¸é¢æ¿", description="ç¼éå¥ç¾¤å¯©æ ¸é¢æ¿")
async def review_panel(interaction: discord.Interaction):

    # ç®¡çå¡éå¶
    if interaction.user.id not in BOT_ADMINS:

        await interaction.response.send_message(
            "â åªæç®¡çå¡å¯ä»¥ä½¿ç¨æ­¤æä»¤ã",
            ephemeral=True,
        )
        return
    embed = discord.Embed(
        title="ð æ¥µææèµï½æ°æå¡å¯©æ ¸",
        description=(
            "æ­¡è¿å å¥ **æ¥µææèµ Discord**ï¼\n\n"
            "çºäºç¶­è­·ç¤¾ç¾¤åè³ªï¼è«åç¢ºèªç¬¦åä»¥ä¸æ¢ä»¶å¾ï¼"
            "åé»æä¸æ¹æééå§ç³è«ã\n\n"
            "ââââââââââââââââââââ\n\n"
            "ð¸ **è«æä¾ä»¥ä¸åä½åª½åªå¶ä¸­ä¸ä½è§è²çèå¤©æªåï¼**\n\n"
            "ð¸ æå¼¦åª½åª\n"
            "ð¸ éé¦¨åª½åª\n"
            "ð¸ å°è²åª½åª\n"
            "ð¸ è¥æ¦çåª½åª\n\n"
            "ââââââââââââââââââââ\n\n"
            "ð® **è§è²ç­ç´éæ±**\n\n"
            "â C å°è§è²éé **15 ç­**\n"
            "â T å°è§è²éé **2 ç­**\n\n"
            "ð **ç¬¦åå¶ä¸­ä¸é å³å¯ï¼**\n"
            "è«æä¾ç¬¦åæ¢ä»¶è§è²çèå¤©æªåã\n\n"
            "ââââââââââââââââââââ\n\n"
            "ð± **è¿½è¹¤åª½åªåç Instagramï¼åä½é½è¦è¿½è¹¤å¦ï¼è«æä¾å·²è¿½è¹¤çæªå**\n\n"
            "<a:emoji_16:1506410360335372299> "
            "[éé¦¨åª½åªç ðð¾](https://www.instagram.com/hanxin_0410_?igsh=czBnczRwbXdnNmht&utm_source=qr)\n\n"
            "<a:emoji_16:1506410360335372299> "
            "[æå¼¦åª½åªç ðð¾](https://www.instagram.com/xingxian1226?igsh=bTV5NTUzZ3Q0bHFr&utm_source=qr)\n\n"
            "<a:emoji_16:1506410360335372299> "
            "[å°å°è²åª½åªç ðð¾](https://www.instagram.com/ha.na_999?igsh=bDBvc24zbW82dWF1&utm_source=qr)\n\n"
            "<a:emoji_16:1506410360335372299> "
            "[è¥æ¦çåª½åªç ðð¾](https://www.instagram.com/cixli042?igsh=MTkweDQ5cTgxMWg2MQ%3D%3D&utm_source=qr)\n\n"
            "ââââââââââââââââââââ\n\n"
            "â ï¸ **çºç¶­è­·å¯©æ ¸å¬å¹³æ§**\n\n"
            "è«å¿æä¾ä¸å¯¦è³è¨æä½¿ç¨ä»äººæªåï¼\n"
            "ç¶æ¥è­å±¬å¯¦å°åæ¶å¯©æ ¸è³æ ¼ã\n\n"
            "å¯©æ ¸ééå¾ï¼\n"
            "å°ç±ç®¡çå¡åå©ä¿®æ¹æ­£å¼èº«åçµã"
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

    embed.set_footer(text="Moon Bot v2ï½å¥ç¾¤å¯©æ ¸ç³»çµ±")

    await interaction.channel.send(embed=embed, view=ReviewPanelView())

    await interaction.response.send_message(
        "â å·²æåç¼éå¥ç¾¤å¯©æ ¸é¢æ¿ï¼", ephemeral=True
    )


# ð° ç°½å°
@bot.tree.command(name="ç°½å°")
async def checkin(interaction: discord.Interaction):

    # ð éå¶é »é
    if interaction.channel.id != 1516120502127694027:
        await interaction.response.send_message(
            "â è«å°æå®ç°½å°é »éä½¿ç¨æ­¤æä»¤", ephemeral=True
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

    # â ä»æ¥å·²ç°½å°
    if data and data[0] == str(today):

        tomorrow = datetime.combine(today + timedelta(days=1), datetime.min.time())
        tomorrow = tz.localize(tomorrow)

        remaining = tomorrow - now
        total_seconds = int(remaining.total_seconds())

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        embed = discord.Embed(
            title="ð ð´ððð ðªðððððð", color=discord.Color.from_rgb(186, 85, 211)
        )

        embed.description = (
            "â³ **ä»æ¥å·²å®æç°½å°**\n\n"
            "ââââââââââââââââââââââ\n\n"
            "ð æç¥æ­£å¨ç­å¾ä¸ä¸æ¬¡ç¸é\n\n"
            f"â° **è·é¢ä¸æ¬¡ç°½å°**\n"
            f"```{hours} å°æ {minutes} åé```\n"
            "ââââââââââââââââââââââ"
        )

        embed.set_footer(text="â¦ æå¤©åä¾æ¥åæç¥çç¥ç¦å§ â¦")

        await interaction.followup.send(embed=embed)
        return

    # ð¸ ç¯æ¥æ´»å
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

    # ð Moon Checkin UI
    embed = discord.Embed(
        title="ð ð´ððð ðªðððððð",
        description=("â¨ **ææçç¥ç¦åæ¬¡éè¨**\n" "æ­¡è¿åæ¬¡è¸å¥ **ææä¹å¢**ã"),
        color=discord.Color.from_rgb(186, 85, 211),
    )

    # ð ä»æ¥çåµ
    if rarity == "event":

        theme = EVENT_THEMES[event["event"]]

        reward_box = (
            f"{theme['emoji']}ââââââââââââââ{theme['emoji']}\n\n"
            f"## {theme['name']}\n\n"
            f"{blessing}\n\n"
            f" {NUNU_EMOJI} +{reward:,}\n\n"
            f"{theme['emoji']}ââââââââââââââ{theme['emoji']}"
        )

        footer_text = theme["footer"]

        embed.color = discord.Color(theme["color"])

    elif rarity == "myth":

        reward_box = (
            "ððââââââââââââââðð\n\n"
            f"{blessing}\n\n"
            "ð **æç¥éè¨ï¼**\n\n"
            f"{NUNU_EMOJI} +{reward:,}\n\n"
            "ððââââââââââââââðð"
        )

        footer_text = "â¦ æç¥è¦ªèªè³äºäºä½ ç¥ç¦ â¦"

    elif rarity == "epic":

        reward_box = (
            "â¨ðââââââââââââââðâ¨\n\n"
            f"{blessing}\n\n"
            "â¨ **ç¨æçåµï¼**\n\n"
            f"{NUNU_EMOJI} +{reward:,}\n\n"
            "â¨ðââââââââââââââðâ¨"
        )

        footer_text = "â¦ æèæå±åçºä½ éä¸ç¥ç¦ â¦"

    elif rarity == "rare":

        reward_box = (
            "ðâ¨âââââââââââââââ¨ð\n\n"
            f"{blessing}\n\n"
            "ð **å¹¸ééè¨ï¼**\n\n"
            f"{NUNU_EMOJI} +{reward:,}\n\n"
            "ðâ¨âââââââââââââââ¨ð"
        )

        footer_text = "â¦ ä»æçæç©ºæ ¼å¤éè â¦"

    else:

        reward_box = (
            "â¨âââââââââââââââ¨\n\n"
            f"{blessing}\n\n"
            f"{NUNU_EMOJI} +{reward:,}\n\n"
            "â¨âââââââââââââââ¨"
        )

        footer_text = "â¦ é¡æææ°¸é ç§èèä½  â¦"

    embed.add_field(name="ð ä»æ¥çåµ", value=reward_box, inline=False)

    embed.add_field(name="ð¥ é£çºç°½å°", value=f"```{streak} å¤©```", inline=True)

    embed.add_field(name="ð ç´¯ç©ç°½å°", value=f"```{total} å¤©```", inline=True)

    embed.set_footer(text=footer_text)

    await interaction.followup.send(embed=embed)


# ð° é¢å
@bot.tree.command(name="é¢å")
async def wallet(interaction: discord.Interaction):

    user_id = str(interaction.user.id)

    # ð é »ééå¶
    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="ð ææåæ",
            description=("â¨ åæååéå®\n\n" f"è«åå¾ <#{SHOP_CHANNEL}> ä½¿ç¨æ­¤æä»¤"),
            color=discord.Color.gold(),
        )

        embed.add_field(
            name="ð¦ åæåè½", value="ååºï½è³¼è²·ï½èåï½é¢å", inline=False
        )

        embed.set_footer(text="æ¥µææèµ â¦ ææåæ")
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
        title="ð ð³ððð ð¾ððððð",
        description="â¨ ææéè¡å¸³æ¶è³è¨",
        color=discord.Color.from_rgb(186, 85, 211),
    )

    embed.add_field(name=f"{NUNU_EMOJI} åªåªå¹£", value=f"```{money:,}```", inline=False)

    embed.add_field(name="ð ç´¯ç©ç°½å°", value=f"```{total:,} å¤©```", inline=True)

    embed.add_field(name="ð¥ é£çºç°½å°", value=f"```{streak:,} å¤©```", inline=True)

    embed.set_footer(text="æ¥µææèµ â¦ ææåè¡")

    await interaction.response.send_message(embed=embed)
    return


# ð å¯è±ªæè¡æ¦
@bot.tree.command(name="å¯è±ªæè¡æ¦")
async def leaderboard(interaction: discord.Interaction):

    # ð é »ééå¶
    if interaction.channel.id != INFO_CHANNEL:

        embed = discord.Embed(
            title="ð æææä»¤éå¶",
            description=(
                "ð æè¡æ¥è©¢åè½æ¼æå®ååä½¿ç¨\n\n" f"è«åå¾ <#{INFO_CHANNEL}>"
            ),
            color=discord.Color.from_rgb(186, 85, 211),
        )

        embed.add_field(
            name="â¨ å¯ä½¿ç¨åè½",
            value="ç­ç´ï½æè¡æ¦ï½æ¥è©¢",
            inline=False,
        )

        embed.set_footer(text="æ¥µææèµ â¦ ææåè¡")

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    c.execute("""
        SELECT user_id, money
        FROM users
        ORDER BY money DESC
    """)

    ranking = c.fetchall()

    embed = discord.Embed(
        title="ð ð³ððð ð»ððððð",
        description="â¨ åªåªå¹£å¯è±ªæè¡æ¦ â¨",
        color=discord.Color.gold(),
    )

    medals = {
        1: "ð",
        2: "ð¥",
        3: "ð¥",
    }

    rank = 1

    for user_id, money in ranking:

        # ð« æé¤æå®ç©å®¶
        if int(user_id) in EXCLUDED_USERS:
            continue

        member = interaction.guild.get_member(int(user_id))

        if member is None:
            continue

        icon = medals.get(rank, f"#{rank}")

        embed.add_field(
            name=f"{icon} {member.display_name}",
            value=f"{NUNU_EMOJI} `{money:,}`",
            inline=False,
        )

        rank += 1

        if rank > 10:
            break

    embed.set_footer(text="æ¥µææèµ â¦ ææåè¡")

    await interaction.response.send_message(embed=embed)


# ð èå¤©ç­ç´æè¡æ¦
@bot.tree.command(name="èå¤©ç­ç´æè¡æ¦")
async def level_leaderboard(interaction: discord.Interaction):

    # ð é »ééå¶
    if interaction.channel.id != INFO_CHANNEL:

        embed = discord.Embed(
            title="ð æææä»¤éå¶",
            description=(
                "ð æè¡æ¥è©¢åè½æ¼æå®ååä½¿ç¨\n\n" f"è«åå¾ <#{INFO_CHANNEL}>"
            ),
            color=discord.Color.from_rgb(186, 85, 211),
        )

        embed.add_field(
            name="â¨ å¯ä½¿ç¨åè½",
            value="ç­ç´ï½æè¡æ¦ï½æ¥è©¢",
            inline=False,
        )

        embed.set_footer(text="æ¥µææèµ â¦ ææåè¡")

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    c.execute("""
        SELECT user_id, level, exp
        FROM users
        ORDER BY level DESC, exp DESC
    """)

    ranking = c.fetchall()

    embed = discord.Embed(
        title="ð ð³ððð ð¹ðððððð",
        description="â¨ ææèå¤©ç­ç´æè¡æ¦ â¨",
        color=discord.Color.from_rgb(186, 85, 211),
    )

    medals = {
        1: "ð",
        2: "ð¥",
        3: "ð¥",
    }

    rank = 1

    for uid, level, exp in ranking:

        # ð« æé¤æå®ç©å®¶
        if int(uid) in EXCLUDED_USERS:
            continue

        member = interaction.guild.get_member(int(uid))

        if member is None:
            continue

        icon = medals.get(rank, f"#{rank}")

        embed.add_field(
            name=f"{icon} {member.display_name}",
            value=(f"ð **Lv.{level}**\n" f"â¨ XPï¼`{exp:,}`"),
            inline=False,
        )

        rank += 1

        if rank > 10:
            break

    embed.set_footer(text="æ¥µææèµ â¦ ææåè¡")

    await interaction.response.send_message(embed=embed)


# ð ç­ç´
@bot.tree.command(name="ç­ç´")
async def level(interaction: discord.Interaction):

    # ð é »ééå¶
    if interaction.channel.id != INFO_CHANNEL:

        embed = discord.Embed(
            title="ð æææä»¤éå¶",
            description=(
                "ð ç­ç´æ¥è©¢åè½æ¼æå®ååä½¿ç¨\n\n" f"è«åå¾ <#{INFO_CHANNEL}>"
            ),
            color=discord.Color.from_rgb(186, 85, 211),
        )

        embed.add_field(name="â¨ å¯ä½¿ç¨åè½", value="ç­ç´ï½æè¡æ¦ï½æ¥è©¢", inline=False)

        embed.set_footer(text="æ¥µææèµ â¦ ææåè¡")

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

    progress_bar = "ðª" * filled + "â¬" * (bar_length - filled)

    embed = discord.Embed(
        title="ð ð³ððð ð·ðððððð",
        description="â¨ æææäººçæé·ç´é",
        color=discord.Color.from_rgb(138, 43, 226),
    )

    embed.add_field(name="ð ç­ç´", value=f"```Lv.{level}```", inline=True)

    embed.add_field(name="ð æå", value=f"```#{rank}```", inline=True)

    embed.add_field(
        name="â¨ ç¶é©å¼",
        value=(f"{progress_bar}\n" f"`{exp:,} / {next_exp:,}`\n" f"å®æåº¦ï¼{percent}%"),
        inline=False,
    )

    embed.set_footer(text="æ¥µææèµ â¦ ææåè¡")

    await interaction.response.send_message(embed=embed)
    return


# ð åäººè³æ


@bot.tree.command(name="åäººè³æ")
async def profile(interaction: discord.Interaction):

    await interaction.response.defer()

    # ð é »ééå¶
    if interaction.channel.id != INFO_CHANNEL:

        embed = discord.Embed(
            title="ð æææä»¤éå¶",
            description=(
                "ð åäººè³æåè½æ¼æå®ååä½¿ç¨\n\n" f"è«åå¾ <#{INFO_CHANNEL}>"
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

    # ä¸è¼é ­å
    async with aiohttp.ClientSession() as session:

        async with session.get(interaction.user.display_avatar.url) as resp:

            avatar_bytes = await resp.read()

    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")

    avatar = avatar.resize((150, 150))

    # åå½¢é ­å
    mask = Image.new("L", (150, 150), 0)

    draw_mask = ImageDraw.Draw(mask)

    draw_mask.ellipse((0, 0, 150, 150), fill=255)

    avatar.putalpha(mask)

    bg.paste(avatar, (30, 110), avatar)

    # éè²é ­åæ¡
    draw_avatar = ImageDraw.Draw(bg)

    draw_avatar.ellipse((25, 105, 185, 265), outline="#FFD700", width=5)

    # åéæè³è¨åºæ¿
    glass = Image.new("RGBA", bg.size, (0, 0, 0, 0))

    glass_draw = ImageDraw.Draw(glass)

    glass_draw.rounded_rectangle((15, 60, 760, 350), radius=25, fill=(20, 20, 20, 150))

    bg = Image.alpha_composite(bg, glass)

    draw = ImageDraw.Draw(bg)

    # å­å
    font_name = ImageFont.truetype("fonts/NotoSansTC-Regular.ttf", 28)

    font_level = ImageFont.truetype("fonts/NotoSansTC-Regular.ttf", 42)

    font_small = ImageFont.truetype("fonts/NotoSansTC-Regular.ttf", 22)

    # åç¨±
    draw.text((210, 90), interaction.user.display_name, fill="white", font=font_name)

    # ç­ç´
    draw.text((210, 145), f"Lv.{level}", fill="#FFD700", font=font_level)

    # æåå¾½ç« åºæ¿
    draw.rounded_rectangle((600, 80, 760, 170), radius=20, fill=(40, 40, 40, 180))

    # æåæ¨é¡
    draw.text((625, 90), "æå", fill="#FFD700", font=font_small)

    # æåæ¸å­
    draw.text((625, 115), f"#{rank}", fill="white", font=font_level)

    # ç¶é©å¼æ¯ä¾
    percent = exp / max(next_exp, 1)

    percent_text = int(percent * 100)

    # èæ¯æ¢
    draw.rounded_rectangle((210, 250, 720, 285), radius=15, fill=(60, 60, 60))

    # ç¶é©æ¢
    draw.rounded_rectangle(
        (210, 250, 210 + int(510 * percent), 285), radius=15, fill=(180, 100, 255)
    )

    # XPæå­
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


# ð® èå¤©ç¶é©ç³»çµ±
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # ==========================
    # ðº éå®èå¤©é »éåç­
    # ==========================

    if message.channel.id != EVENT_CHANNEL:
        await bot.process_commands(message)
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
            title="ð ç­ç´æå",
            description=(f"{message.author.mention}\n\n" f"â¨ å·²æåè³ Lv.{level}"),
            color=discord.Color.from_rgb(186, 85, 211),
        )

        embed.set_footer(text="æ¥µææèµ â¦ ææåè¡")

        if channel:
            await channel.send(embed=embed)

    await bot.process_commands(message)


# âï¸ ç®¡çå¡è¨­å®ç­ç´
@bot.tree.command(name="è¨­å®ç­ç´")
@app_commands.default_permissions(administrator=True)
@app_commands.rename(member="æå¡", level="ç­ç´")
async def set_level(
    interaction: discord.Interaction, member: discord.Member, level: int
):

    c.execute(
        "UPDATE users SET level=?, exp=0 WHERE user_id=?", (level, str(member.id))
    )
    conn.commit()

    await interaction.response.send_message(f"â å·²å° {member.mention} è¨­çº Lv.{level}")


@bot.tree.command(name="è¨­å®æ­¡è¿é »é")
@app_commands.default_permissions(administrator=True)
@app_commands.rename(channel="é »é")
async def set_welcome_channel(
    interaction: discord.Interaction, channel: discord.TextChannel
):
    c.execute("REPLACE INTO settings VALUES ('welcome_channel', ?)", (str(channel.id),))
    conn.commit()
    await interaction.response.send_message(f"â å·²è¨­å®ï¼{channel.mention}")


@bot.tree.command(name="è¨­å®ç®¡çå¡é »é")
@app_commands.default_permissions(administrator=True)
@app_commands.rename(channel="é »é")
async def set_admin_channel(
    interaction: discord.Interaction, channel: discord.TextChannel
):
    c.execute("REPLACE INTO settings VALUES ('admin_channel', ?)", (str(channel.id),))
    conn.commit()
    await interaction.response.send_message(f"â å·²è¨­å®ï¼{channel.mention}")


# ==========================
# ð æ¯æ¥ç°½å°æé
# ==========================


@tasks.loop(time=time(hour=23, minute=0, tzinfo=tz))
async def checkin_reminder():

    channel = bot.get_channel(EVENT_CHANNEL)

    if channel is None:
        return
    reminder = random.choice(CHECKIN_REMINDERS)

    role = f"<@&{LOTTERY_PING_ROLE}>"

    embed = discord.Embed(
        title="ð æ¯æ¥ç°½å°æé",
        description=(
            f"{reminder}\n\n"
            "ââââââââââââââââââ\n\n"
            "â° æ¯æ¥ **00:00** éç½®\n"
            "ð è¨å¾åå¾æ¯æ¥ç°½å°é ååªåªå¹£èç¥ç¦ï¼\n\n"
            f"ð ç°½å°é »éï¼<#{CHECKIN_CHANNEL}>"
        ),
        color=discord.Color.purple(),
    )

    embed.add_field(
        name="ð æ¯æ¥çåµ",
        value=("â¢ æ¯æ¥åªåªå¹£\n" "â¢ é£çºç°½å°çåµ\n" "â¢ ç¯æ¥éå®ç¥ç¦"),
        inline=False,
    )

    embed.set_footer(text="Moon Bot v2ï½æ¯æ¥æé")

    await channel.send(
        content=role,
        embed=embed,
    )

# ==========================
# ð¸ è§è²åç§æ´»åç³»çµ±
# ==========================

@tasks.loop(minutes=1)
async def photo_event_check():

    now = datetime.now(tz)

    month = now.month
    day = now.day
    hour = now.hour
    minute = now.minute

    # ==========================
    # ð¸ éæ¾æ´»å
    # ==========================
    
    if (
        day in [2, 16]
        and hour == 0
        and minute == 0
    ):
        today = now.strftime("%Y-%m-%d")

        c.execute(
            "SELECT value FROM settings WHERE key=?",
            ("photo_open",)
        )
        row = c.fetchone()

        if row and row["value"] == today:
            return

        channel = bot.get_channel(1504815515795853432)

        if channel is None:
            return

        await channel.send(
            "<@&1504854895826698392>\n\n"
            "ð¸ **è§è²åç§è¨±é¡æ´»åéå§ï¼**\n\n"
            "â¨ **æ´»åè¦å**\n\n"
            "ã»æ¯æå **2 æ¥ã16 æ¥** éæ¾è¨±é¡ã\n"
            "ã»æ¯äººæ¯æ¬¡åè½è¨±é¡ **1 é»è§è²** çåç§ã\n"
            "ã»æ¯ä½è§è²çææä¾ **2 å¼µåç§**ã\n"
            "ã»è«èå¿ç­å¾è£½ä½å®æã\n"
            "ã»å¶é¤è¨±é¡è¦åè«è³æ´»åç½®é æç« è§çã\n\n"
            "â° **æ¬æ¬¡æ´»åå°æ¼éæ¥ 00:00 ééè¨±é¡åã**"
        )
        # éæ¾è§è²åç§è¨±é¡å
        photo_channel = bot.get_channel(1504820063344267305)
        photo_role = photo_channel.guild.get_role(1504854895826698392)

        if photo_channel and photo_role:

            overwrite = photo_channel.overwrites_for(photo_role)
            overwrite.view_channel = True

            await photo_channel.set_permissions(
                photo_role,
                overwrite=overwrite
            )
            
        c.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            ("photo_open", today)
        )
        conn.commit()
        
    # ==========================
    # ð æ´»åå³å°çµæ
    # ==========================

    if (
        day in [2, 16]
        and hour == 23
        and minute == 30
    ):
    
        today = now.strftime("%Y-%m-%d")

        c.execute(
            "SELECT value FROM settings WHERE key=?",
            ("photo_notice",)
        )
        row = c.fetchone()

        if row and row["value"] == today:
            return

        channel = bot.get_channel(1504815515795853432)

        if channel is None:
            return

        await channel.send(
            "â° **è§è²åç§è¨±é¡æ´»åå³å°çµæï¼**\n\n"
            "<@&1504854895826698392>\n\n"
            "è·é¢æ¬æ¬¡è§è²åç§è¨±é¡æ´»åçµæéæ **30 åé**ã\n\n"
            "â¨ **å°æªè¨±é¡çæå¡è«ææ¡æå¾æ©æï¼**\n\n"
            "ð è§è²åç§è¨±é¡åå°æ¼ä»æ¥ **00:00** æºæééã"
        )
        
        c.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            ("photo_notice", today)
        )
        conn.commit()
        
    # ==========================
    # ð« ééè§è²åç§è¨±é¡å
    # ==========================

    if (
        day in [3, 17]
        and hour == 0
        and minute == 0
    ):
        today = now.strftime("%Y-%m-%d")

        c.execute(
            "SELECT value FROM settings WHERE key=?",
            ("photo_close",)
        )
        row = c.fetchone()

        if row and row["value"] == today:
            return

        photo_channel = bot.get_channel(1504820063344267305)

        if photo_channel is None:
            return

        photo_role = photo_channel.guild.get_role(1504854895826698392)

        if photo_role is None:
            return

        overwrite = photo_channel.overwrites_for(photo_role)
        overwrite.view_channel = False

        await photo_channel.set_permissions(
            photo_role,
            overwrite=overwrite
        )

        c.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            ("photo_close", today)
        )
        conn.commit()

# ==========================
# ð çæ¥ç³»çµ±ï¼Birthday v2ï¼
# ==========================


@tasks.loop(time=time(hour=8, minute=0, tzinfo=tz))
async def birthday_check():

    now = datetime.now(tz)
    today = now.strftime("%m-%d")
    today_str = now.strftime("%Y-%m-%d")

    # ==========================
    # ð é²æ­¢éè¤å·è¡
    # ==========================

    c.execute("""
        SELECT value
        FROM settings
        WHERE key = 'last_birthday'
        """)

    data = c.fetchone()

    if data and data["value"] == today_str:
        return

    c.execute(
        """
        REPLACE INTO settings(key, value)
        VALUES('last_birthday', ?)
        """,
        (today_str,),
    )

    conn.commit()

    # ==========================
    # ð ä»æ¥å£½æ
    # ==========================

    c.execute(
        """
        SELECT
            user_id,
            birth_year
        FROM users
        WHERE birthday = ?
        ORDER BY birthday
        """,
        (today,),
    )

    birthday_users = c.fetchall()

    # ==========================
    # ð¢ å¬åé »é
    # ==========================

    birthday_channel = bot.get_channel(BIRTHDAY_CHANNEL)

    # ==========================
    # ð ç®¡çå¡é »é
    # ==========================

    admin_channel = bot.get_channel(BIRTHDAY_ADMIN_CHANNEL)

    if birthday_users:

        # ==========================
        # ð æºåå¬åè³æ
        # ==========================

        birthday_members = []

        total_reward = 0
        normal_count = 0
        rare_count = 0
        myth_count = 0

        # ==========================
        # ð ç¼éçæ¥çåµ
        # ==========================

        for row in birthday_users:

            user_id = row["user_id"]
            birth_year = row["birth_year"]

            member = bot.get_user(int(user_id))

            if member is None:
                try:
                    member = await bot.fetch_user(int(user_id))
                except Exception:
                    continue

            # ==========================
            # ð² æ½åçæ¥çåµ
            # ==========================

            roll = random.random()

            if roll < 0.70:

                reward = 1000
                reward_text = "â¨ ææç¥ç¦"
                normal_count += 1

            elif roll < 0.95:

                reward = 2000
                reward_text = "ð éèç¥ç¦"
                rare_count += 1

            else:

                reward = 5000
                reward_text = "ð æ¥µåéè¨"
                myth_count += 1

            # ==========================
            # ð° ç¼æ¾çåµ
            # ==========================

            c.execute(
                """
                UPDATE users
                SET money = money + ?
                WHERE user_id = ?
                """,
                (
                    reward,
                    user_id,
                ),
            )

            total_reward += reward

            # ==========================
            # ð å¹´é½¡
            # ==========================

            age_text = ""

            if birth_year:

                age = now.year - birth_year
                age_text = f"ï¼{age}æ­²ï¼"

            # ==========================
            # ð å¬åè³æ
            # ==========================

            birthday_members.append(
                {
                    "mention": member.mention,
                    "name": member.display_name,
                    "age": age_text,
                    "reward": reward,
                    "reward_text": reward_text,
                }
            )

        conn.commit()
        # ==========================
        # ð ä»æ¥å£½æå¬å
        # ==========================

        if birthday_channel:

            description = ""

            for member in birthday_members:

                description += f"ð {member['mention']} {member['age']}\n"

            birthday_blessing = random.choice(BIRTHDAY_BLESSINGS)

            embed = discord.Embed(
                title="ð ä»æ¥å£½æ",
                description=(
                    f"{description}" "\nââââââââââââââââââ\n\n" f"{birthday_blessing}"
                ),
                color=discord.Color.from_rgb(255, 105, 180),
            )

            gift_text = ""

            if normal_count:
                gift_text += f"â¨ ææç¥ç¦ Ã {normal_count}\n"

            if rare_count:
                gift_text += f"ð éèç¥ç¦ Ã {rare_count}\n"

            if myth_count:
                gift_text += f"ð æ¥µåéè¨ Ã {myth_count}\n"

            gift_text += f"\nð° ä»æ¥å±ç¼æ¾ **{total_reward:,} åªåªå¹£**"

            embed.add_field(
                name="ð å·²ç¼éçæ¥ç¦®ç©",
                value=gift_text,
                inline=False,
            )

            embed.set_footer(text="Moon Bot v2ï½Birthday System")

            await birthday_channel.send(embed=embed)
    # ==========================
    # â° ææ¥å£½ææé
    # ==========================

    tomorrow = (now + timedelta(days=1)).strftime("%m-%d")

    c.execute(
        """
        SELECT
            user_id,
            birth_year
        FROM users
        WHERE birthday = ?
        ORDER BY birthday
        """,
        (tomorrow,),
    )

    tomorrow_users = c.fetchall()

    if admin_channel and tomorrow_users:

        guild = bot.get_guild(GUILD_ID)

        if guild is not None:

            reminder_text = ""
            count = 0

            for row in tomorrow_users:

                member = guild.get_member(int(row["user_id"]))

                if member is None:
                    try:
                        member = await guild.fetch_member(int(row["user_id"]))
                    except Exception:
                        continue

                reminder_text += f"ð {member.mention}\n"
                count += 1

            if count:

                reminder = discord.Embed(
                    title="ð ææ¥å£½ææé",
                    description=(
                        f"{reminder_text}"
                        "\nââââââââââââââââââ\n\n"
                        "â¨ è«è¨å¾æåéä¸çæ¥ç¥ç¦ï¼"
                    ),
                    color=discord.Color.gold(),
                )

                reminder.set_footer(text=f"Moon Bot v2ï½å± {count} ä½å£½æ")

                await admin_channel.send(embed=reminder)


# ==========================
# ð æ½çèæ¯æª¢æ¥
# ==========================


async def finish_lottery(message_id):

    c.execute(
        """
        SELECT channel_id, host_id, prize_type, prize_value, message, winner_count, end_time
        FROM lotteries
        WHERE message_id=? AND status='running'
        """,
        (str(message_id),),
    )

    lottery = c.fetchone()

    if not lottery:
        return False

    (channel_id, host_id, prize_type, prize_value, custom_message, winner_count, end_time) = lottery
    end_time = datetime.fromisoformat(end_time)

    c.execute(
        "SELECT user_id FROM lottery_entries WHERE message_id=?",
        (str(message_id),),
    )
    rows = c.fetchall()

    if len(rows) == 0:
        winners = []
    elif len(rows) <= winner_count:
        winners = rows
    else:
        winners = random.sample(rows, winner_count)

    winner_mentions = []

    for (winner_id,) in winners:
        winner_id = str(winner_id)
        winner_mentions.append(f"<@{winner_id}>")

        if prize_type == "money":
            add_money(winner_id, int(prize_value))

        await send_lottery_dm(
            winner_id, host_id, prize_type, prize_value, custom_message
        )

    # åæ¨è¨çµæï¼é¿åèæ¯æª¢æ¥èæåçµæéè¤éç
    c.execute(
        "UPDATE lotteries SET status='ended' WHERE message_id=? AND status='running'",
        (str(message_id),),
    )
    conn.commit()

    channel = bot.get_channel(int(channel_id))
    if channel is None:
        return True

    try:
        message = await channel.fetch_message(int(message_id))
    except (discord.NotFound, discord.Forbidden):
        return True

    if prize_type == "money":
        prize_text = f"ð° åªåªå¹£ {int(prize_value):,}"
    elif prize_type == "image":
        prize_text = "ð¨ é¨æ©é¢¨æ ¼äººè¨­å"
    elif prize_type == "couple":
        prize_text = "ð èåæè§è²åç§"
    else:
        prize_text = f"ð {prize_value}"

    timestamp = int(end_time.timestamp())

    embed = discord.Embed(title="ð Moon Bot æ½ç", color=0xF1C40F)
    embed.add_field(name="ð çå", value=prize_text, inline=False)
    embed.add_field(name="ð¥ ä¸­çäººæ¸", value=f"{winner_count} äºº", inline=True)
    embed.add_field(name="ð¤ ä¸»è¾¦äºº", value=f"<@{host_id}>", inline=True)
    embed.add_field(name="â° æ½çæªæ­¢", value=f"<t:{timestamp}:F>", inline=False)
    embed.add_field(
        name="ð ä¸­çè",
        value="\n".join(winner_mentions) if winner_mentions else "ð­ æ¬æ¬¡æ½çç¡äººåå ",
        inline=False,
    )
    embed.add_field(name="ð çæ", value="ð´ å·²çµæ", inline=False)
    embed.set_footer(text="ð æ¬æ¬¡æ½çå·²çµæï¼æè¬å¤§å®¶åèï¼")

    ended_view = LotteryView()
    c.execute("SELECT COUNT(*) FROM lottery_entries WHERE message_id=?", (str(message_id),))
    total = c.fetchone()[0]
    ended_view.children[0].label = f"ð åå æ½çï¼{total}ï¼"
    ended_view.children[0].disabled = True
    # æ¥çåå®ä¿çå¯ä½¿ç¨ï¼çµææ½çæééå®
    for child in ended_view.children:
        if getattr(child, "custom_id", None) == "lottery_manual_end":
            child.disabled = True

    await message.edit(embed=embed, view=ended_view)
    return True


# ==========================
# ð æ½çèæ¯æª¢æ¥
# ==========================

@tasks.loop(seconds=10)
async def lottery_checker():

    now = datetime.now()

    c.execute(
        "SELECT message_id, end_time FROM lotteries WHERE status='running'"
    )

    lotteries = c.fetchall()

    for message_id, end_time in lotteries:
        if datetime.fromisoformat(end_time) <= now:
            await finish_lottery(str(message_id))


# ==========================
# ð æ½çä¸­çéç¥
# ==========================


async def send_lottery_dm(
    user_id,
    host_id,
    prize_type,
    prize_value,
    custom_message=None,
):

    try:

        user = await bot.fetch_user(int(user_id))

        embed = discord.Embed(
            title="ð Moon Botï½æ½çéç¥",
            description="ð æ­åä½ å¨æ¬æ¬¡æ½çä¸­å¹¸éä¸­çï¼",
            color=0xF1C40F,
        )

        # -------------------------
        # ð° åªåªå¹£
        # -------------------------

        if prize_type == "money":

            embed.add_field(
                name="ð çå",
                value=f"ð° åªåªå¹£ {int(prize_value):,}",
                inline=False,
            )

            embed.description += (
                "\n\nââââââââââââââââââ\n\n"
                "Moon Bot å·²èªåå°çåµç¼æ¾è³ä½ çå¸³æ¶ã\n\n"
                "å¯ä½¿ç¨ `/é¢å` æ¥çç®åé¤é¡ã"
            )

        # -------------------------
        # ð¨ äººè¨­å
        # -------------------------

        elif prize_type == "image":

            embed.add_field(
                name="ð çå",
                value="ð¨ é¨æ©é¢¨æ ¼äººè¨­å",
                inline=False,
            )

            embed.add_field(
                name="ð¤ ä¸»è¾¦äºº",
                value=f"<@{host_id}>",
                inline=False,
            )

            embed.description += (
                "\n\nââââââââââââââââââ\n\n"
                "è«ç§è¨ä¸»è¾¦äººï¼ä¸¦æä¾ä½ çäººè¨­åç§çã\n\n"
                "ä¸»è¾¦äººå°åå©è£½ä½æ¬æ¬¡æ½ççåã"
            )

        # -------------------------
        # ð åç§
        # -------------------------

        elif prize_type == "couple":

            embed.add_field(
                name="ð çå",
                value="ð èåæè§è²åç§",
                inline=False,
            )

            embed.add_field(
                name="ð¤ ä¸»è¾¦äºº",
                value=f"<@{host_id}>",
                inline=False,
            )

            embed.description += (
                "\n\nââââââââââââââââââ\n\n"
                "è«ç§è¨ä¸»è¾¦äººï¼ä¸¦æä¾ï¼\n\n"
                "ð¸ ä½ çäººè¨­åç§ç\n"
                "ð æ³è¦åç§çè§è²åç¨±\n\n"
                "ð æº«é¦¨æé ð\n"
                "ð å¨ä»»ä½å¬éå¹³å°ç¼å¸èè§è²ç¸éçåçæå½±çæï¼è«å ä¸æµ®æ°´å°ã\n"
                "ð è¥éç¼å¸å½±çï¼è«åç§è¨è§è²åµä½èç¢ºèªå§å®¹ï¼ç¶åµä½èåæå¾åå¬éç¼å¸ã\n"
                "ð è¥ä¸ç¥éå¦ä½è£½ä½æµ®æ°´å°ï¼å¯è«ç®¡çå¡åå©èçã"
            )

        # -------------------------
        # ð èªè¨
        # -------------------------

        elif prize_type == "custom":

            embed.add_field(
                name="ð çå",
                value=prize_value,
                inline=False,
            )

            embed.add_field(
                name="ð¤ ä¸»è¾¦äºº",
                value=f"<@{host_id}>",
                inline=False,
            )

            if custom_message:

                embed.description += (
                    "\n\nââââââââââââââââââ\n\n"
                    f"{custom_message}\n\n"
                    "ð æº«é¦¨æé ð\n"
                    "ð å¨ä»»ä½å¬éå¹³å°ç¼å¸èè§è²ç¸éçåçæå½±çæï¼è«å ä¸æµ®æ°´å°ã\n"
                    "ð è¥éç¼å¸å½±çï¼è«åç§è¨è§è²åµä½èç¢ºèªå§å®¹ï¼ç¶åµä½èåæå¾åå¬éç¼å¸ã\n"
                    "ð è¥ä¸ç¥éå¦ä½è£½ä½æµ®æ°´å°ï¼å¯è«ç®¡çå¡åå©èçã"
                )

            else:

                embed.description += (
                    "\n\nââââââââââââââââââ\n\n"
                    "è«ç§è¨ä¸»è¾¦äººé åæ¬æ¬¡æ½ççåã\n\n"
                    "ð æº«é¦¨æé ð\n"
                    "ð å¨ä»»ä½å¬éå¹³å°ç¼å¸èè§è²ç¸éçåçæå½±çæï¼è«å ä¸æµ®æ°´å°ã\n"
                    "ð è¥éç¼å¸å½±çï¼è«åç§è¨è§è²åµä½èç¢ºèªå§å®¹ï¼ç¶åµä½èåæå¾åå¬éç¼å¸ã\n"
                    "ð è¥ä¸ç¥éå¦ä½è£½ä½æµ®æ°´å°ï¼å¯è«ç®¡çå¡åå©èçã"
                )

        embed.set_footer(text="ð æ¬è¨æ¯ç± Moon Bot èªåç¼é")

        await user.send(embed=embed)

    except discord.Forbidden:
        print(f"â ï¸ ç¡æ³ç§è¨ {user_id}ï¼å°æ¹å·²ééç§è¨ã")

    except Exception as e:
        print(f"â ï¸ ç¼éæ½çç§è¨å¤±æï¼{e}")


# ==========================================
# # ð¸ æ­¡è¿ç³»çµ± #
# ==========================================


@bot.event
async def on_member_join(member):

    # ==========================
    # èªåçµ¦äºæ°äººæå¡èº«åçµ
    # ==========================

    role = member.guild.get_role(1505110931300941844)

    if role is not None:
        await member.add_roles(role, reason="æ°æå¡èªåå å¥")

    # åå¾æ­¡è¿é »é
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
    # æ­¡è¿ Embed
    # ==========================

    embed = discord.Embed(title="ð æ­¡è¿å å¥æ¥µææèµ", color=discord.Color.dark_grey())

    embed.description = f"""
æ­¡è¿ {member.mention} å¯¶å¯¶å å¥æåð¤ââË ð³ â ð³ â ð³ â ð³ æ¥µ æ æ èµ Ëââð¤

å¾éå¿ä½ ä¾å°éåå°å°çç²çµ²äº¤æµç©ºéï¼<a:emoji_32:1508529055832739911>

<a:emoji_1:1506013957905846372> è« {member.mention} å¯¶å¯¶è³ <#1506198162724094074>

æä¾æåéè¦çæªåã

æåé²è¡å¯©æ ¸ééå¾ï¼
æåä¿®æ¹èº«åçµå·<a:emoji_2:1506043914115879014>
"""

    embed.set_footer(text="æ¥µææèµ â¦ Welcome")

    # åéæå­ï¼ç°åºï¼
    await channel.send(embed=embed)

    # åé Welcome Card
    await channel.send(file=card)


# ==========================
# ð çæ¥ç»è¨
# ==========================


@bot.tree.command(name="çæ¥ç»è¨", description="ç»è¨ä½ ççæ¥")
@app_commands.rename(month="æä»½", day="æ¥æ", year="åºçå¹´")
@app_commands.describe(
    month="çæ¥æä»½",
    day="çæ¥æ¥æ",
    year="åºçå¹´ï¼é¸å¡«ï¼",
)
async def set_birthday(
    interaction: discord.Interaction,
    month: int,
    day: int,
    year: int = None,
):

    user_id = str(interaction.user.id)

    # ==========================
    # ð æ¥æé©è­
    # ==========================

    try:
        datetime(2000, month, day)
    except ValueError:
        await interaction.response.send_message(
            "â çæ¥æ¥æé¯èª¤ï¼è«éæ°ç¢ºèªã",
            ephemeral=True,
        )
        return

    # ==========================
    # ð æ¯å¦å·²ç»è¨
    # ==========================

    c.execute(
        """
        SELECT birthday
        FROM users
        WHERE user_id = ?
        """,
        (user_id,),
    )

    data = c.fetchone()

    if data and data["birthday"]:

        await interaction.response.send_message(
            "â ä½ å·²ç¶å®æçæ¥ç»è¨ã\n\n" "å¦éä¿®æ¹çæ¥è³æï¼è«è¯çµ¡ç®¡çå¡åå©èçã",
            ephemeral=True,
        )
        return

    # ==========================
    # ð æ´æ°çæ¥è³æ
    # ==========================

    birthday = f"{month:02d}-{day:02d}"

    c.execute(
        """
        UPDATE users
        SET birthday = ?, birth_year = ?
        WHERE user_id = ?
        """,
        (
            birthday,
            year,
            user_id,
        ),
    )

    conn.commit()

    # ==========================
    # ð ç»è¨ç´é
    # ==========================

    log_channel = bot.get_channel(BIRTHDAY_LOG_CHANNEL)

    if log_channel:

        embed = discord.Embed(
            title="ð çæ¥ç»è¨",
            color=discord.Color.pink(),
            timestamp=datetime.now(tz),
        )

        embed.add_field(
            name="ð¤ ä½¿ç¨è",
            value=interaction.user.mention,
            inline=False,
        )

        embed.add_field(
            name="ð çæ¥",
            value=f"{month:02d} / {day:02d}",
            inline=True,
        )

        embed.add_field(
            name="ð åºçå¹´",
            value=str(year) if year else "æªå¡«å¯«",
            inline=True,
        )

        embed.set_footer(text="Moon Bot v2ï½çæ¥ç³»çµ±")

        await log_channel.send(embed=embed)

    # ==========================
    # â å®æ
    # ==========================

    await interaction.response.send_message(
        "â çæ¥ç»è¨æåï¼",
        ephemeral=True,
    )


# ==========================
# ð çæ¥ä¿®æ¹
# ==========================


@bot.tree.command(name="çæ¥ä¿®æ¹", description="ä¿®æ¹ç©å®¶çæ¥")
@app_commands.rename(
    member="ç©å®¶",
    month="æä»½",
    day="æ¥æ",
    year="åºçå¹´",
)
@app_commands.describe(
    member="è¦ä¿®æ¹çæ¥çç©å®¶",
    month="çæ¥æä»½",
    day="çæ¥æ¥æ",
    year="åºçå¹´ï¼é¸å¡«ï¼",
)
async def edit_birthday(
    interaction: discord.Interaction,
    member: discord.Member,
    month: int,
    day: int,
    year: int = None,
):

    # ==========================
    # ð ç®¡çå¡éå¶
    # ==========================

    if interaction.user.id not in BOT_ADMINS:

        await interaction.response.send_message(
            "â åªæç®¡çå¡å¯ä»¥ä½¿ç¨æ­¤æä»¤ã",
            ephemeral=True,
        )
        return

    # ==========================
    # ð é »ééå¶
    # ==========================

    if interaction.channel.id != BIRTHDAY_ADMIN_CHANNEL:

        await interaction.response.send_message(
            f"â è«åå¾ <#{BIRTHDAY_ADMIN_CHANNEL}> ä½¿ç¨æ­¤æä»¤ã",
            ephemeral=True,
        )
        return

    # ==========================
    # ð æ¥æé©è­
    # ==========================

    try:
        datetime(2000, month, day)
    except ValueError:

        await interaction.response.send_message(
            "â æ¥ææ ¼å¼é¯èª¤ã",
            ephemeral=True,
        )
        return

    user_id = str(member.id)
    ensure_user(user_id)

    # ==========================
    # ð åå¾èè³æ
    # ==========================

    c.execute(
        """
        SELECT birthday, birth_year
        FROM users
        WHERE user_id = ?
        """,
        (user_id,),
    )

    data = c.fetchone()

    if not data or not data["birthday"]:

        await interaction.response.send_message(
            "â è©²ç©å®¶å°æªç»è¨çæ¥ã",
            ephemeral=True,
        )
        return

    old_birthday = data["birthday"]
    old_year = data["birth_year"]

    new_birthday = f"{month:02d}-{day:02d}"

    # ==========================
    # ð è³æç¸å
    # ==========================

    if old_birthday == new_birthday and old_year == year:

        await interaction.response.send_message(
            "â ï¸ æ°è³æèç®åçæ¥è³æç¸åï¼æªé²è¡ä¿®æ¹ã",
            ephemeral=True,
        )
        return

    # ==========================
    # ð¾ æ´æ°è³æ
    # ==========================

    c.execute(
        """
        UPDATE users
        SET birthday = ?, birth_year = ?
        WHERE user_id = ?
        """,
        (
            new_birthday,
            year,
            user_id,
        ),
    )

    conn.commit()

    # ==========================
    # ð ä¿®æ¹ç´é
    # ==========================

    log_channel = bot.get_channel(BIRTHDAY_LOG_CHANNEL)

    if log_channel:

        embed = discord.Embed(
            title="âï¸ çæ¥è³æä¿®æ¹",
            color=discord.Color.orange(),
            timestamp=datetime.now(tz),
        )

        embed.add_field(
            name="ð¤ ç©å®¶",
            value=member.mention,
            inline=False,
        )

        embed.add_field(
            name="ð ç®¡çå¡",
            value=interaction.user.mention,
            inline=False,
        )

        old_text = old_birthday.replace("-", " / ")
        if old_year:
            old_text += f"\nð {old_year}"

        new_text = new_birthday.replace("-", " / ")
        if year:
            new_text += f"\nð {year}"
        else:
            new_text += "\nð æªå¡«å¯«"
        embed.add_field(
            name="ð èè³æ",
            value=old_text,
            inline=True,
        )

        embed.add_field(
            name="ð æ°è³æ",
            value=new_text,
            inline=True,
        )

        embed.set_footer(text="Moon Bot v2ï½çæ¥ç³»çµ±")

        await log_channel.send(embed=embed)

    # ==========================
    # â å®æ
    # ==========================

    await interaction.response.send_message(
        f"â å·²æåä¿®æ¹ **{member.display_name}** ççæ¥è³æã",
        ephemeral=True,
    )


# ==========================
# ð çæ¥æ¥è©¢
# ==========================


@bot.tree.command(name="çæ¥æ¥è©¢", description="æ¥çææå·²ç»è¨çæ¥")
async def check_birthday(interaction: discord.Interaction):

    # ==========================
    # ð ç®¡çå¡éå¶
    # ==========================

    if interaction.user.id not in BOT_ADMINS:

        await interaction.response.send_message(
            "â åªæç®¡çå¡å¯ä»¥ä½¿ç¨æ­¤æä»¤ã",
            ephemeral=True,
        )
        return

    # ==========================
    # ð é »ééå¶
    # ==========================

    if interaction.channel.id != BIRTHDAY_ADMIN_CHANNEL:

        await interaction.response.send_message(
            f"â è«åå¾ <#{BIRTHDAY_ADMIN_CHANNEL}> ä½¿ç¨æ­¤æä»¤ã",
            ephemeral=True,
        )
        return

    # ==========================
    # ð æ¥è©¢çæ¥
    # ==========================

    c.execute("""
        SELECT user_id, birthday, birth_year
        FROM users
        WHERE birthday IS NOT NULL
        ORDER BY birthday
        """)

    users = c.fetchall()

    if not users:

        await interaction.response.send_message(
            "ð­ ç®åæ²æä»»ä½çæ¥è³æã",
            ephemeral=True,
        )
        return

    embed = discord.Embed(
        title="ð å·²ç»è¨çæ¥",
        color=discord.Color.pink(),
    )

    text = ""

    for row in users:

        user = interaction.guild.get_member(int(row["user_id"]))

        if user is None:
            continue

        birthday = row["birthday"].replace("-", " / ")

        if row["birth_year"]:

            birthday += f"ï¼{row['birth_year']}ï¼"

        text += f"ð¸ {user.display_name}\nð {birthday}\n\n"

    embed.description = text

    embed.set_footer(text=f"å± {len(users)} ä½ç©å®¶")

    await interaction.response.send_message(embed=embed)


# ==========================
# ð æ¬æå£½æ
# ==========================


@bot.tree.command(name="æ¬æå£½æ", description="æ¥çæ¬æå£½æ")
async def birthday_list(interaction: discord.Interaction):

    # ==========================
    # ð ç®¡çå¡éå¶
    # ==========================

    if interaction.user.id not in BOT_ADMINS:

        await interaction.response.send_message(
            "â åªæç®¡çå¡å¯ä»¥ä½¿ç¨æ­¤æä»¤ã",
            ephemeral=True,
        )
        return

    # ==========================
    # ð é »ééå¶
    # ==========================

    if interaction.channel.id != BIRTHDAY_ADMIN_CHANNEL:

        await interaction.response.send_message(
            f"â è«åå¾ <#{BIRTHDAY_ADMIN_CHANNEL}> ä½¿ç¨æ­¤æä»¤ã",
            ephemeral=True,
        )
        return

    now = datetime.now(tz)
    month = now.strftime("%m")

    c.execute(
        """
        SELECT user_id, birthday, birth_year
        FROM users
        WHERE birthday LIKE ?
        ORDER BY birthday
        """,
        (f"{month}-%",),
    )

    users = c.fetchall()

    if not users:

        await interaction.response.send_message(
            "ð­ æ¬ææ²æå£½æã",
            ephemeral=True,
        )
        return

    embed = discord.Embed(
        title=f"ð {int(month)} æå£½æ",
        color=discord.Color.pink(),
    )

    text = ""

    count = 0

    for row in users:

        member = interaction.guild.get_member(int(row["user_id"]))

        if member is None:
            continue

        birthday = row["birthday"].replace("-", " / ")

        if row["birth_year"]:
            birthday += f"ï¼{row['birth_year']}ï¼"

        text += f"ð¸ **{member.display_name}**\n" f"ð {birthday}\n\n"

        count += 1

    if not text:

        await interaction.response.send_message(
            "ð­ æ¬ææ²æå£½æã",
            ephemeral=True,
        )
        return

    embed.description = text

    embed.set_footer(text=f"æ¬æå± {count} ä½å£½æï½Moon Bot v2")

    await interaction.response.send_message(embed=embed)


# ð¼ æå·¥
@bot.tree.command(name="æå·¥")
async def work(interaction: discord.Interaction):

    # ð é »ééå¶
    if interaction.channel.id != WORK_CHANNEL:

        embed = discord.Embed(
            title="ð¼ ææå§è¨ä¸­å¿",
            description=f"è«åå¾ <#{WORK_CHANNEL}> æ¥åå§è¨ä»»å",
            color=discord.Color.green(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    user_id = str(interaction.user.id)
    ensure_user(user_id)

    # ð¤ å»ºç«è³æ
    c.execute(
        """
        INSERT OR IGNORE INTO users
        (user_id,money,exp,level)
        VALUES (?,0,0,1)
        """,
        (user_id,),
    )
    conn.commit()

    # â³ å·å»
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
                title="â³ ææå§è¨å·å»ä¸­",
                description=f"å©é¤æéï¼{minutes}å {seconds}ç§",
                color=discord.Color.orange(),
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

    # ð å·¥ä½åè¡¨
    jobs = [
        ("æ´çæç¥åæ¸é¤¨", 800, 1300),
        ("è­·éææåé", 1000, 1600),
        ("ç§é¡§æåè±å", 700, 1200),
        ("æ¸çå¤ä»£éºè·¡", 1200, 1900),
        ("åå©é­æ³ç ç©¶", 1300, 2200),
        ("æ¡éæåç¤¦ç³", 900, 1500),
        ("å·¡éæç©ºåå", 1000, 1700),
    ]

    job_name, low, high = random.choice(jobs)

    # ð² äºä»¶
    roll = random.randint(1, 100)

    if roll <= 5:

        reward = random.randint(low, high) * 3

        title = "ð æç¥ç·é¡§"
        desc = "ç²å¾ä¸åå ±é¬"
        event_type = "success"

    elif roll <= 75:

        reward = random.randint(low, high)

        title = "â¨ å§è¨æå"
        desc = "é å©å®æä»»å"
        event_type = "success"

    elif roll <= 90:

        reward = int(random.randint(low, high) * 0.5)

        title = "â ï¸ å·¥ä½å¤±èª¤"
        desc = "åªç²å¾é¨åå ±é¬"
        event_type = "success"

    elif roll <= 97:

        reward = random.randint(100, 500)

        title = "ð¸ å·¥ä½æå¤"
        desc = "æå£è¨­åéè¦è³ å"
        event_type = "loss"

    else:

        reward = random.randint(500, 1500)
        reward = random.randint(1500, 3000)
        title = "â ï¸ ç½é£äºä»¶"
        desc = "ä»»åå¤±æé æéå¤§æå¤±"
        event_type = "loss"

    # ð° çµç®
    if event_type == "success":
        money += reward
    else:
        money = max(0, money - reward)

    # ð¾ æ´æ°
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

    # ð Embed
    embed = discord.Embed(
        title="ð ð´ððð ð¾ððð",
        description=desc,
        color=discord.Color.from_rgb(186, 85, 211),
    )

    embed.add_field(name="ð å§è¨å§å®¹", value=f"```{job_name}```", inline=False)

    embed.add_field(name="â¨ äºä»¶çµæ", value=f"```{title}```", inline=False)

    if event_type == "success":

        embed.add_field(
            name="ð æ¬æ¬¡æ¶å¥", value=f"{NUNU_EMOJI} `{reward:,}`", inline=True
        )

    else:

        embed.add_field(
            name="ð¸ æ¬æ¬¡æå¤±", value=f"{NUNU_EMOJI} `{reward:,}`", inline=True
        )

    embed.add_field(name="ð° é¢åé¤é¡", value=f"{NUNU_EMOJI} `{money:,}`", inline=True)

    embed.set_footer(text="æ¥µææèµ â¦ ææåè¡")

    await interaction.response.send_message(embed=embed)


class BuyButton(discord.ui.Button):
    def __init__(self, item_id, price, name):
        super().__init__(label=f"è³¼è²· {name}", style=discord.ButtonStyle.green)
        self.item_id = item_id
        self.price = price
        self.name = name

    async def callback(self, interaction: discord.Interaction):

        user_id = str(interaction.user.id)

        # ð° æ¥é¢
        c.execute("SELECT money FROM users WHERE user_id=?", (user_id,))
        data = c.fetchone()

        if not data or data[0] < self.price:
            await interaction.response.send_message("â åªåªå¹£ä¸è¶³", ephemeral=True)
            return

        # ð¦ æ¥åº«å­
        c.execute("SELECT stock FROM shop WHERE item_id=?", (self.item_id,))
        stock = c.fetchone()

        if not stock or stock[0] <= 0:
            await interaction.response.send_message("â ååå·²å®å®", ephemeral=True)
            return

        # ð° æ£é¢
        c.execute(
            "UPDATE users SET money = money - ? WHERE user_id=?", (self.price, user_id)
        )

        # ð¦ æ£åº«å­
        c.execute("UPDATE shop SET stock = stock - 1 WHERE item_id=?", (self.item_id,))

        # ð å å¥èå
        c.execute(
            "SELECT amount FROM inventory WHERE user_id=? AND item_id=?",
            (user_id, self.item_id),
        )
        inv = c.fetchone()

        if inv:
            c.execute(
                "UPDATE inventory SET amount = amount + 1 WHERE user_id=? AND item_id=?",
                (user_id, self.item_id),
            )
        else:
            c.execute(
                "INSERT INTO inventory (user_id, item_id, amount) VALUES (?, ?, 1)",
                (user_id, self.item_id),
            )

        conn.commit()

        await interaction.response.send_message(
            f"ðï¸ è³¼è²·æåï¼**{self.name}**\n<a:emoji40:1510362334026268713> -{self.price}"
        )


# ==========================================
# ð ååº View
# ==========================================
class ShopView(discord.ui.View):
    def __init__(self, items, page=0):
        super().__init__(timeout=60)
        self.items = items
        self.page = page
        self.per_page = 3

    def get_page_items(self):
        start = self.page * self.per_page
        end = start + self.per_page
        return self.items[start:end]

    async def update(self, interaction):

        self.clear_items()

        embed = discord.Embed(title="ð ååº", color=discord.Color.gold())

        page_items = self.get_page_items()

        for item_id, name, price, stock, desc, img in page_items:

            embed.add_field(
                name=f"ð {item_id}ï½{name}",
                value=f"{desc}\n<a:emoji40:1510362334026268713> {price}ï½åº«å­:{stock}",
                inline=False,
            )

            self.add_item(BuyButton(item_id, price, name))

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="â¬ ä¸ä¸é ", style=discord.ButtonStyle.gray)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1

        await self.update(interaction)

    @discord.ui.button(label="â¡ ä¸ä¸é ", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if (self.page + 1) * self.per_page < len(self.items):
            self.page += 1

        await self.update(interaction)






# ==========================================
# ð ååº
# ==========================================
@bot.tree.command(name="ååº")
async def shop(interaction: discord.Interaction):

    # ð é »ééå¶
    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="ð ææåæ",
            description=("â¨ åæååéå®\n\n" f"è«åå¾ <#{SHOP_CHANNEL}>"),
            color=discord.Color.gold(),
        )

        embed.add_field(
            name="ð¦ åæåè½", value="ååºï½è³¼è²·ï½èåï½é¢å", inline=False
        )

        embed.set_footer(text="æ¥µææèµ â¦ ææåæ")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    c.execute("SELECT item_id, name, price, stock, description, image FROM shop")

    items = c.fetchall()

    if not items:
        await interaction.response.send_message("ð ååºç®åæ²æåå")
        return

    view = ShopView(items)

    embed = discord.Embed(
        title="ð ææåæ",
        description="â¨ é»ææéçè¦½åå",
        color=discord.Color.gold(),
    )

    await interaction.response.send_message(embed=embed, view=view)


# ð èå¬ååº
@bot.tree.command(name="èå¬ååº")
async def husband_shop(interaction: discord.Interaction):

    # ð é »ééå¶
    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="ð ææå©å§»ä»ç´¹æ",
            description=(
                "â¨ èå¬ååºåè½æ¼æå®ååä½¿ç¨\n\n" f"è«åå¾ <#{SHOP_CHANNEL}>"
            ),
            color=discord.Color.from_rgb(255, 105, 180),
        )

        embed.add_field(name="ð åè½", value="èå¬ååºï½è³¼è²·èå¬", inline=False)

        embed.set_footer(text="æ¥µææèµ â¦ å½å®ä¹äºº")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    c.execute("""
        SELECT name
        FROM husbands
        ORDER BY husband_id
    """)

    husbands = c.fetchall()

    if not husbands:

        await interaction.response.send_message("ð ç®åæ²æå¯è³¼è²·çèå¬")
        return

    husband_text = ""

    for i, husband in enumerate(husbands, start=1):

        husband_text += f"{i}. {husband[0]}\n"

    embed = discord.Embed(
        title="ð ææå©å§»ä»ç´¹æ",
        description=("æ­¡è¿æé¸ä½ çå½å®èå¬ â¨\n\n" f"{husband_text}"),
        color=discord.Color.from_rgb(255, 105, 180),
    )

    embed.set_footer(text="è¼¸å¥ /è³¼è²·èå¬ åç¨±")

    await interaction.response.send_message(embed=embed)


# ð è³¼è²·èå¬
@bot.tree.command(name="è³¼è²·èå¬")
async def buy_husband(interaction: discord.Interaction, åç¨±: str):

    # ð é »ééå¶
    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="ð ææå©å§»ä»ç´¹æ",
            description=(
                "â¨ è³¼è²·èå¬åè½æ¼æå®ååä½¿ç¨\n\n" f"è«åå¾ <#{SHOP_CHANNEL}>"
            ),
            color=discord.Color.from_rgb(255, 105, 180),
        )

        embed.add_field(
            name="ð åè½", value="èå¬ååºï½è³¼è²·èå¬ï½æçèå¬", inline=False
        )

        embed.set_footer(text="æ¥µææèµ â¦ å½å®ä¹äºº")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    user_id = str(interaction.user.id)

    # æ¥èå¬æ¯å¦å­å¨
    c.execute(
        """
        SELECT husband_id
        FROM husbands
        WHERE name=?
    """,
        (åç¨±,),
    )

    husband = c.fetchone()

    if not husband:

        await interaction.response.send_message("â æ¥ç¡æ­¤èå¬", ephemeral=True)
        return

    husband_id = husband[0]

    # æ¯å¦å·²ææ
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

        await interaction.response.send_message(f"ð ä½ å·²ç¶ææ {åç¨±}", ephemeral=True)
        return

    # æ¥é¢
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
            (f"â åªåªå¹£ä¸è¶³\n\n" f"éè¦ï¼{HUSBAND_PRICE:,}\n" f"ç®åï¼{money:,}"),
            ephemeral=True,
        )
        return

    # æ£æ¬¾
    c.execute(
        """
        UPDATE users
        SET money = money - ?
        WHERE user_id=?
    """,
        (HUSBAND_PRICE, user_id),
    )

    # æ¶è
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
        title="ð æ¶èæå",
        description=(f"æ­åç²å¾\n\n" f"â¨ {åç¨±} â¨"),
        color=discord.Color.from_rgb(255, 105, 180),
    )

    embed.add_field(name="ð° æ¶è", value=f"{HUSBAND_PRICE:,} åªåªå¹£", inline=False)

    embed.set_footer(text="æ¥µææèµ â¦ å½å®ä¹äºº")

    await interaction.response.send_message(embed=embed)


# ð æçèå¬
@bot.tree.command(name="æçèå¬")
async def my_husbands(interaction: discord.Interaction):
    # ð é »ééå¶
    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="ð æçèå¬",
            description=("â¨ æ­¤åè½åè½æ¼æå®ååä½¿ç¨\n\n" f"è«åå¾ <#{SHOP_CHANNEL}>"),
            color=discord.Color.from_rgb(255, 105, 180),
        )

        embed.add_field(
            name="ð åè½", value="èå¬ååºï½è³¼è²·èå¬ï½æçèå¬", inline=False
        )

        embed.set_footer(text="æ¥µææèµ â¦ å½å®ä¹äºº")

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

        await interaction.response.send_message("ð ä½ ç®åéæ²ææ¶èä»»ä½èå¬")
        return

    husband_text = "\n".join([f"ð {h[0]}" for h in husbands])

    embed = discord.Embed(
        title="ð æçèå¬",
        description=husband_text,
        color=discord.Color.from_rgb(255, 105, 180),
    )

    embed.set_footer(text=f"å±æ¶è {len(husbands)} ä½èå¬")

    await interaction.response.send_message(embed=embed)


# ð é©åç®±


# ð§­ æ¢éª
@bot.tree.command(name="æ¢éª")
async def adventure(interaction: discord.Interaction):

    if interaction.channel.id != ADVENTURE_CHANNEL:

        embed = discord.Embed(
            title="ð§­ æææ¢éª",
            description=f"è«åå¾ <#{ADVENTURE_CHANNEL}> ä½¿ç¨æ¢éª",
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

        await interaction.response.send_message("â æ¾ä¸å°å¸³æ¶è³æ", ephemeral=True)
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
                f"â³ æ¢éªå·å»ä¸­\néé {minutes}å {seconds}ç§", ephemeral=True
            )
            return

    roll = random.randint(1, 100)

    title = ""
    reward = 0

    # ð ç¥ç´
    if roll <= 5:

        title = random.choice(["ð æç¥éè¨", "ð æç¥ç¥ç¦", "ð æç©ºè£ç¸«"])

        reward = random.randint(5000, 20000)

    # ð Boss
    elif roll <= 15:

        title = random.choice(["ð æ·±æ·µé­ç¼", "ð æè¾°å·¨é¾", "ð æå½±é¨å£«"])

        reward = random.randint(1000, 8000)

    # âï¸ å±éª
    elif roll <= 35:

        title = random.choice(["âï¸ æµæµªçè³", "âï¸ æ·±æé·é±", "âï¸ é­ç©è¥²æ"])

        reward = -random.randint(100, 1000)

    # ð¿ æ®é
    else:

        title = random.choice(["ð¿ è£çµ¦ç®±", "ð¿ æè¡åäºº", "ð¿ éºå¤±è²¡å¯¶"])

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

    embed = discord.Embed(title="ð§­ æææ¢éª", color=discord.Color.blurple())

    embed.add_field(name="ð æ¢éªçµæ", value=f"```{title}```", inline=False)

    if reward >= 0:

        embed.add_field(
            name="ð ç²å¾", value=f"{NUNU_EMOJI} `{reward:,}`", inline=False
        )

    else:

        embed.add_field(
            name="ð¸ æå¤±", value=f"{NUNU_EMOJI} `{abs(reward):,}`", inline=False
        )

    embed.add_field(name="ð° é¢åé¤é¡", value=f"{NUNU_EMOJI} `{money:,}`", inline=False)

    embed.set_footer(text="æ¥µææèµ â¦ æææ¢éª")
    await interaction.response.send_message("ð§­ æ­£å¨é¢éæèµå...")

    msg = await interaction.original_response()

    await asyncio.sleep(1)

    await msg.edit(content="ð² ç©¿è¶è¿·é§æ£®æ...")

    await asyncio.sleep(1)

    await msg.edit(content="ð æå°éºè·¡è¹¤è·¡...")

    await asyncio.sleep(1)

    if roll <= 5:

        await msg.edit(content="ð ç¥ç´æ°£æ¯éè¨...")

    elif roll <= 15:

        await msg.edit(content="ð ç¼ç¾ä¸çBoss...")

    elif roll <= 35:

        await msg.edit(content="âï¸ é­éå±éªäºä»¶...")

    else:

        await msg.edit(content="ð ç¼ç¾ç¥ç§å¯¶ç®±...")

    await asyncio.sleep(1)

    await msg.edit(content=None, embed=embed)


# ð³ è³¼è²·
@bot.tree.command(name="è³¼è²·")
@app_commands.rename(item_id="ååç·¨è")
@app_commands.describe(item_id="ååºååç·¨è")
async def buy(interaction: discord.Interaction, item_id: int):

    # ð é »ééå¶
    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="ð ææåæ",
            description=f"è«åå¾ <#{SHOP_CHANNEL}> ä½¿ç¨è³¼è²·åè½",
            color=discord.Color.gold(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    name, price, stock = item

    if stock <= 0:
        await interaction.response.send_message("â ååå·²å®å®", ephemeral=True)
        return

    # ð° æ¥é¤é¡
    c.execute("SELECT money FROM users WHERE user_id=?", (user_id,))

    data = c.fetchone()

    if not data:
        await interaction.response.send_message(
            "â è«åç°½å°ææå·¥å»ºç«è³æ", ephemeral=True
        )
        return

    money = data[0]

    if money < price:
        await interaction.response.send_message("â åªåªå¹£ä¸è¶³", ephemeral=True)
        return

    # ð° æ£æ¬¾
    c.execute("UPDATE users SET money = money - ? WHERE user_id=?", (price, user_id))

    # ð¦ æ£åº«å­
    c.execute("UPDATE shop SET stock = stock - 1 WHERE item_id=?", (item_id,))

    # ð å å¥èå
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

    embed = discord.Embed(title="ðï¸ è³¼è²·æå", color=discord.Color.green())

    embed.add_field(name="ð¦ åå", value=f"```{name}```", inline=False)

    embed.add_field(name="ð° è±è²»", value=f"{NUNU_EMOJI} `{price:,}`", inline=False)

    embed.set_footer(text="æ¥µææèµ â¦ ææåæ")

    await interaction.response.send_message(embed=embed)


# ð èå
@bot.tree.command(name="èå")
async def inventory_cmd(interaction: discord.Interaction):

    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="ð ææåæ",
            description=f"è«åå¾ <#{SHOP_CHANNEL}> ä½¿ç¨èååè½",
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
        await interaction.response.send_message("ð ä½ çèåæ¯ç©ºç")
        return

    text = ""

    for name, amount in items:
        text += f"ð {name} Ã {amount}\n"

    embed = discord.Embed(
        title="ð ææèå", description=text, color=discord.Color.purple()
    )

    embed.set_footer(text="æ¥µææèµ â¦ ææåæ")

    await interaction.response.send_message(embed=embed)


# ð è´ééå·
@bot.tree.command(name="è´ééå·")
@app_commands.rename(member="æå¡", item_name="éå·åç¨±", amount="æ¸é")
@app_commands.describe(
    member="æ¥æ¶éå·çç©å®¶", item_name="è¦è´éçéå·", amount="è´éæ¸é"
)
async def give_item(
    interaction: discord.Interaction,
    member: discord.Member,
    item_name: str,
    amount: int,
):

    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="ð ææåæ",
            description=f"è«åå¾ <#{SHOP_CHANNEL}> ä½¿ç¨è´éåè½",
            color=discord.Color.gold(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    sender_id = str(interaction.user.id)
    target_id = str(member.id)

    c.execute("SELECT item_id FROM shop WHERE name=?", (item_name,))

    item = c.fetchone()

    if not item:

        await interaction.response.send_message("â æ²æéååå", ephemeral=True)
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

        await interaction.response.send_message("â éå·ä¸è¶³", ephemeral=True)
        return

    # æ£é¤èªå·±
    c.execute(
        """
        UPDATE inventory
        SET amount = amount - ?
        WHERE user_id=? AND item_id=?
        """,
        (amount, sender_id, item_id),
    )

    # å°æ¹èå
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

    embed = discord.Embed(title="ð è´éæå", color=discord.Color.green())

    embed.add_field(name="ð¦ éå·", value=f"```{item_name}```", inline=False)

    embed.add_field(name="ð¤ æ¶ä»¶äºº", value=member.mention, inline=False)

    embed.add_field(name="ð¦ æ¸é", value=f"`{amount}`", inline=False)

    embed.set_footer(text="æ¥µææèµ â¦ ææåæ")

    await interaction.response.send_message(embed=embed)


# âï¸ å¢å åªåªå¹£

@bot.tree.command(name="ç¼åªåªå¹£")
@app_commands.rename(amount="éé¡", member="æå¡", role="èº«åçµ", everyone="ç¼éå¨é«")
@app_commands.describe(
    amount="ç¼ééé¡", member="æå®æå¡", role="æå®èº«åçµ", everyone="æ¯å¦ç¼éçµ¦å¨é«"
)
async def give_money(
    interaction: discord.Interaction,
    amount: int,
    member: discord.Member = None,
    role: discord.Role = None,
    everyone: bool = False,
):

    await interaction.response.defer()

    # ð éå¶é »é
    if interaction.channel.id != 1510930723924611163:
        await interaction.followup.send("â è«å°ç®¡çå¡é »éä½¿ç¨", ephemeral=True)
        return

    # ð æå®ç®¡çå¡ä½¿ç¨è ID
    ALLOWED_USERS = [
    1153640526063607820,  # éé¦¨
    1218542666879598613,  # æå¼¦
    1301905168094335028,  # æ¦å
    806960151578804275,  # å°è²
    873202145367846942,  # èè
    844778614268100638,  # å°E
]

    if interaction.user.id not in ALLOWED_USERS:
        await interaction.followup.send("â ä½ æ²ææ¬é", ephemeral=True)
        return
    
    # ð è³å°é¸ä¸åå°è±¡
    if not member and not role and not everyone:
        await interaction.followup.send("â è«é¸æç¼éå°è±¡", ephemeral=True)
        return

    count = 0

    # ð¤ å®äºº
    if member:

        add_money(member.id, amount)

        count = 1

    # ð¥ èº«åçµ
    elif role:

        for m in role.members:

            if m.bot:
                continue

            add_money(m.id, amount)

            count += 1

    # ð å¨é«
    elif everyone:

        for m in interaction.guild.members:

            if m.bot:
                continue

            add_money(m.id, amount)

            count += 1

    embed = discord.Embed(title="ð° ç¼é¢å®æ", color=discord.Color.green())

    embed.add_field(
        name="ðµ ç¼ééé¡", value=f"{NUNU_EMOJI} `{amount:,}`", inline=False
    )

    if member:
        embed.add_field(name="ð¤ ç¼éå°è±¡", value=member.mention, inline=False)

    elif role:
        embed.add_field(name="ð­ ç¼éå°è±¡", value=role.mention, inline=False)

    elif everyone:
        embed.add_field(name="ð ç¼éå°è±¡", value="`å¨é«æå¡`", inline=False)

    embed.add_field(name="ð¥ ç¼éäººæ¸", value=f"`{count}` äºº", inline=False)

    await interaction.followup.send(embed=embed)


# ==========================
# ð å»ºç«æ½ç
# ==========================


@bot.tree.command(name="æ½çå»ºç«", description="å»ºç«ä¸å ´æ°çæ½ç")
async def lottery_create(interaction: discord.Interaction):

    # -------------------------
    # é »ééå¶
    # -------------------------

    if interaction.channel.id != LOTTERY_CHANNEL:

        await interaction.response.send_message(
            "â è«è³æ½çé »éä½¿ç¨æ­¤æä»¤ã", ephemeral=True
        )
        return

    # -------------------------
    # æ¬ééå¶
    # -------------------------

    if interaction.user.id not in LOTTERY_MANAGERS:

        await interaction.response.send_message(
            "â åªææ½çç®¡çå¡å¯ä»¥å»ºç«æ½çã",
            ephemeral=True,
        )
        return

    # -------------------------
    # é¸æçå
    # -------------------------

    embed = discord.Embed(
        title="ð å»ºç«æ½ç",
        description=("è«é¸ææ¬æ¬¡æ½çççåé¡åã\n\n" "é¸æå¾å°æéåå°æçè¨­å®è¦çªã"),
        color=0xF1C40F,
    )

    await interaction.response.send_message(
        embed=embed, view=PrizeSelectView(), ephemeral=True
    )


# ==========================
# ð Render ä¿æ´»æå
# ==========================

class ReusableTCPServer(TCPServer):
    allow_reuse_address = True


def run_web():
    port = int(os.environ.get("PORT", 10000))

    with ReusableTCPServer(
        ("0.0.0.0", port),
        SimpleHTTPRequestHandler
    ) as httpd:

        print(f"ð Web Server å·²ååï¼Portï¼{port}")

        httpd.serve_forever()


threading.Thread(
    target=run_web,
    daemon=True
).start()


# ==========================
# ð ç°½å°æ¢ä»¶æ½çç³»çµ±
# ==========================

setup_streak_lottery(
    bot,
    LOTTERY_CHANNEL,
    LOTTERY_MANAGERS,
    LOTTERY_PING_ROLE,
)


# ==========================
# ð²âï¸ ç¨ç«éæ²ç³»çµ±è¼å¥
# ==========================

setup_bigsmall(
    bot,
    get_money=get_money,
    add_money=add_money,
    remove_money=remove_money,
    c=c,
    conn=conn,
    discord=discord,
    app_commands=app_commands,
    random=random,
    asyncio=asyncio,
    datetime=datetime,
    timedelta=timedelta,
    MIN_BET=MIN_BET,
    MAX_BET=MAX_BET,
    CASINO_FEE_RATE=CASINO_FEE_RATE,
    NUNU_EMOJI=NUNU_EMOJI,
    BIGSMALL_CHANNEL=BIGSMALL_CHANNEL,
)

setup_duel(
    bot,
    get_money=get_money,
    add_money=add_money,
    remove_money=remove_money,
    c=c,
    conn=conn,
    discord=discord,
    app_commands=app_commands,
    random=random,
    asyncio=asyncio,
    datetime=datetime,
    timedelta=timedelta,
    MIN_BET=MIN_BET,
    MAX_BET=MAX_BET,
    CASINO_FEE_RATE=CASINO_FEE_RATE,
    NUNU_EMOJI=NUNU_EMOJI,
    DUEL_CHANNEL=DUEL_CHANNEL,
)

setup_slot(
    bot,
    c=c,
    conn=conn,
    discord=discord,
    app_commands=app_commands,
    asyncio=asyncio,
    MIN_BET=MIN_BET,
    MAX_BET=MAX_BET,
    CASINO_FEE_RATE=CASINO_FEE_RATE,
    NUNU_EMOJI=NUNU_EMOJI,
    SLOT_CHANNEL=SLOT_CHANNEL,
)

bot.run(os.getenv("TOKEN"))