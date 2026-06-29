import random
from datetime import datetime, timedelta

import discord
import pytz
from discord import app_commands

from config import *
from database import c, conn
from blessings import (
    CHECKIN_BLESSINGS,
    RARE_BLESSINGS,
    EPIC_BLESSINGS,
    MYTH_BLESSINGS
)
from events import (
    CHECKIN_EVENTS,
    EVENT_THEMES
)

tz = pytz.timezone(TIMEZONE)

MOON_PHASES = [
    ("🌑", "新月", "新的旅程即將開始。"),
    ("🌒", "娥眉月", "希望正在慢慢成長。"),
    ("🌓", "上弦月", "勇敢向前，努力會有回報。"),
    ("🌔", "盈凸月", "距離成功只差一步。"),
    ("🌕", "滿月", "今晚月神的力量達到巔峰。"),
    ("🌖", "虧凸月", "收穫今天努力的成果。"),
    ("🌗", "下弦月", "整理心情，迎接新的開始。"),
    ("🌘", "殘月", "黑夜終將迎來黎明。"),
]


def get_reward():

    event = None

    roll = random.randint(1, 100)

    if roll <= 1:

        reward = 5000
        rarity = "myth"
        blessing = random.choice(MYTH_BLESSINGS)

    elif roll <= 5:

        reward = random.randint(2000, 3000)
        rarity = "epic"
        blessing = random.choice(EPIC_BLESSINGS)

    elif roll <= 20:

        reward = random.randint(500, 1000)
        rarity = "rare"
        blessing = random.choice(RARE_BLESSINGS)

    else:

        reward = random.randint(100, 200)
        rarity = "normal"
        blessing = random.choice(CHECKIN_BLESSINGS)

    return reward, rarity, blessing, event


def setup(bot):

    @bot.tree.command(
        name="簽到",
        description="每日簽到"
    )
    async def checkin(interaction: discord.Interaction):

        if interaction.channel.id != CHECKIN_CHANNEL:

            await interaction.response.send_message(
                "❌ 請到指定簽到頻道使用。",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        user_id = str(interaction.user.id)

        now = datetime.now(tz)
        today = now.date()

        c.execute(
            """
            SELECT
                last_checkin,
                checkin_total,
                checkin_streak,
                money
            FROM users
            WHERE user_id=?
            """,
            (user_id,)
        )

        data = c.fetchone()

        if data and data["last_checkin"] == str(today):

            tomorrow = tz.localize(
                datetime.combine(
                    today + timedelta(days=1),
                    datetime.min.time()
                )
            )

            remain = tomorrow - now

            hour = int(remain.total_seconds()) // 3600
            minute = (int(remain.total_seconds()) % 3600) // 60

            embed = discord.Embed(
                title="🌙 Moon Checkin",
                description=(
                    "## 今天已完成簽到\n\n"
                    "請明天再回來接受月神祝福。\n\n"
                    f"⏰ **剩餘時間**\n```{hour} 小時 {minute} 分```"
                ),
                color=discord.Color.purple()
            )

            embed.set_footer(
                text="✦ Moon Bot v2 ✦"
            )

            await interaction.followup.send(embed=embed)
            return

        # ==========================
        # 節日活動
        # ==========================

        today_str = str(today)
        event = CHECKIN_EVENTS.get(today_str)

        if event:

            reward = event["reward"]
            rarity = "event"
            blessing = event["message"]

        else:

            reward, rarity, blessing, _ = get_reward()

        # ==========================
        # 流星雨（0.3%）
        # ==========================

        shooting_star = False

        if random.randint(1, 1000) <= 3:

            shooting_star = True
            reward += 5000

        # ==========================
        # 月相
        # ==========================

        moon_emoji, moon_name, moon_desc = random.choice(
            MOON_PHASES
        )

        # ==========================
        # 更新資料
        # ==========================

        if data:

            total = data["checkin_total"] + 1

            if data["last_checkin"] == str(today - timedelta(days=1)):
                streak = data["checkin_streak"] + 1
            else:
                streak = 1

            money = data["money"] + reward

            c.execute(
                """
                UPDATE users
                SET
                    last_checkin=?,
                    checkin_total=?,
                    checkin_streak=?,
                    money=?
                WHERE user_id=?
                """,
                (
                    str(today),
                    total,
                    streak,
                    money,
                    user_id
                )
            )

        else:

            total = 1
            streak = 1
            money = reward

            c.execute(
                """
                INSERT INTO users
                (
                    user_id,
                    money,
                    checkin_total,
                    checkin_streak,
                    last_checkin
                )
                VALUES
                (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    reward,
                    total,
                    streak,
                    str(today)
                )
            )

        conn.commit()

        # ==========================
        # Embed
        # ==========================

        embed = discord.Embed(
            title="🌙 𝑴𝒐𝒐𝒏 𝑪𝒉𝒆𝒄𝒌𝒊𝒏",
            description="✨ **星月再次照耀著你的旅程** ✨",
            color=discord.Color.from_rgb(186, 85, 211)
        )

        # ========= 月相 =========

        embed.add_field(
            name=f"{moon_emoji} 今日月相",
            value=(
                f"```"
                f"{moon_name}\n"
                f"{moon_desc}"
                f"```"
            ),
            inline=False
        )

        # ========= 今日獎勵 =========

        if rarity == "event":

            theme = EVENT_THEMES[event["event"]]

            reward_box = (
                f"{theme['emoji']}══════════════{theme['emoji']}\n\n"
                f"## {theme['name']}\n\n"
                f"{blessing}\n\n"
                f"{NUNU_EMOJI} **+{reward:,}**\n\n"
                f"{theme['emoji']}══════════════{theme['emoji']}"
            )

            embed.color = discord.Color(theme["color"])

            footer = theme["footer"]

        elif rarity == "myth":

            reward_box = (
                "👑════════════════════👑\n\n"
                "## 🌕 月神降臨\n\n"
                f"{blessing}\n\n"
                f"{NUNU_EMOJI} **+{reward:,}**\n\n"
                "👑════════════════════👑"
            )

            footer = "✦ 月神親自賜予了你祝福 ✦"

        elif rarity == "epic":

            reward_box = (
                "✨════════════════════✨\n\n"
                "## ✨ 稀有祝福\n\n"
                f"{blessing}\n\n"
                f"{NUNU_EMOJI} **+{reward:,}**\n\n"
                "✨════════════════════✨"
            )

            footer = "✦ 星月共同為你送上祝福 ✦"

        elif rarity == "rare":

            reward_box = (
                "🌟════════════════════🌟\n\n"
                "## 🍀 幸運降臨\n\n"
                f"{blessing}\n\n"
                f"{NUNU_EMOJI} **+{reward:,}**\n\n"
                "🌟════════════════════🌟"
            )

            footer = "✦ 今晚的星空格外閃耀 ✦"

        else:

            reward_box = (
                "🌙════════════════════🌙\n\n"
                f"{blessing}\n\n"
                f"{NUNU_EMOJI} **+{reward:,}**\n\n"
                "🌙════════════════════🌙"
            )

            footer = "✦ 願月神永遠守護著你 ✦"

        embed.add_field(
            name="🎁 今日獎勵",
            value=reward_box,
            inline=False
        )

        if shooting_star:

            embed.add_field(
                name="🌠 流星雨",
                value=(
                    "```"
                    "今晚流星劃過夜空。\n"
                    "你獲得了額外 5,000 努努幣！"
                    "```"
                ),
                inline=False
            )

        embed.add_field(
            name="🔥 連續簽到",
            value=f"```{streak} 天```",
            inline=True
        )

        embed.add_field(
            name="📅 累積簽到",
            value=f"```{total} 天```",
            inline=True
        )

        embed.set_footer(
            text=footer
        )

        await interaction.followup.send(
            embed=embed
        )
