import random
from datetime import datetime, timedelta

import discord
import pytz

from config import *
from database import c, conn
from systems.work_data import (
    WORKS,
    BONUS_EVENTS,
    BAD_EVENTS
)

tz = pytz.timezone(TIMEZONE)


def setup(bot):

    @bot.tree.command(
        name="打工",
        description="開始今天的工作"
    )
    async def work(
        interaction: discord.Interaction
    ):

        # ==========================
        # 頻道限制
        # ==========================

        if interaction.channel.id != WORK_CHANNEL:

            await interaction.response.send_message(
                "❌ 請到指定打工頻道使用。",
                ephemeral=True
            )
            return

        user_id = str(interaction.user.id)

        c.execute(
            """
            SELECT
                money,
                last_work
            FROM users
            WHERE user_id=?
            """,
            (user_id,)
        )

        data = c.fetchone()

        if data is None:

            await interaction.response.send_message(
                "❌ 請先使用 `/簽到` 建立帳號。",
                ephemeral=True
            )
            return

        now = datetime.now(tz)

        # ==========================
        # 一小時冷卻
        # ==========================

        if data["last_work"]:

            last_work = datetime.fromisoformat(
                data["last_work"]
            )

            if last_work.tzinfo is None:

                last_work = tz.localize(
                    last_work
                )

            remain = (
                last_work + timedelta(hours=1)
            ) - now

            if remain.total_seconds() > 0:

                total = int(
                    remain.total_seconds()
                )

                minute = total // 60
                second = total % 60

                embed = discord.Embed(
                    title="💼 Moon Work",
                    description=(
                        "## 😴 今天已經工作過了\n\n"
                        f"⏰ 剩餘時間\n"
                        f"```{minute} 分 {second} 秒```"
                    ),
                    color=discord.Color.blue()
                )

                embed.set_footer(
                    text="🌙 工作也是需要休息的"
                )

                await interaction.response.send_message(
                    embed=embed
                )

                return

        await interaction.response.defer()

        # ==========================
        # 👑 王宮委託（0.5%）
        # ==========================

        palace = False

        if random.randint(1, 1000) <= 5:

            palace = True

            work_name = "👑 王宮委託"

            work_desc = (
                "國王親自委託你完成一項重要任務。\n"
                "你完美完成了委託，受到王國嘉獎。"
            )

            salary = 5000

        else:

            work = random.choice(WORKS)

            work_name = work["name"]

            work_desc = random.choice(
                work["success"]
            )

            salary = random.randint(
                work["min"],
                work["max"]
            )

        # ==========================
        # ✨ Bonus Event
        # ==========================

        bonus_text = None

        if (not palace) and random.randint(1, 100) <= 10:

            event = random.choice(
                BONUS_EVENTS
            )

            bonus_text = event["name"]

            if "money" in event:

                salary += event["money"]

            elif "multiply" in event:

                salary *= event["multiply"]

        # ==========================
        # 💥 Bad Event
        # ==========================

        bad_text = None

        if (not palace) and random.randint(1, 100) <= 8:

            event = random.choice(
                BAD_EVENTS
            )

            bad_text = event["name"]

            if event["money"] == "zero":

                salary = 0

            else:

                salary += event["money"]

                if salary < 0:

                    salary = 0

        # ==========================
        # 更新努努幣
        # ==========================

        new_money = data["money"] + salary

        c.execute(
            """
            UPDATE users
            SET
                money=?,
                last_work=?
            WHERE user_id=?
            """,
            (
                new_money,
                now.replace(
                    microsecond=0
                ).isoformat(),
                user_id
            )
        )

        conn.commit()

        # ==========================
        # 💼 工作結果
        # ==========================

        if palace:

            color = discord.Color.gold()
            title = "👑 王宮委託完成"

        else:

            color = discord.Color.green()
            title = "💼 今日工作完成"

        embed = discord.Embed(
            title=title,
            color=color
        )

        embed.add_field(
            name="💼 工作",
            value=(
                f"**{work_name}**\n\n"
                f"{work_desc}"
            ),
            inline=False
        )

        if bonus_text:

            embed.add_field(
                name="✨ 額外事件",
                value=bonus_text,
                inline=False
            )

        if bad_text:

            embed.add_field(
                name="💥 意外事件",
                value=bad_text,
                inline=False
            )

        embed.add_field(
            name="💰 今日薪資",
            value=f"<a:emoji40:1510362334026268713> **+{salary:,}**",
            inline=True
        )

        embed.add_field(
            name="🏦 目前資產",
            value=f"<a:emoji40:1510362334026268713> **{new_money:,}**",
            inline=True
        )

        if palace:

            embed.set_footer(
                text="🌙 王國感謝你的付出"
            )

        else:

            embed.set_footer(
                text="🌙 極曜月葵｜努力工作總會有收穫"
            )

        await interaction.followup.send(
            embed=embed
        )

