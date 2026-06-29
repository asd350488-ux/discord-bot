import asyncio
import random

import discord
from discord import app_commands

from config import *
from database import c, conn


def setup(bot):

    @bot.tree.command(
        name="猜大小",
        description="猜三顆骰子的大小"
    )
    @app_commands.describe(
        金額="100~10000",
        選擇="請輸入 大 或 小"
    )
    async def guess(
        interaction: discord.Interaction,
        金額: int,
        選擇: str
    ):

        # =========================
        # 頻道限制
        # =========================

        if interaction.channel.id != BIGSMALL_CHANNEL:

            await interaction.response.send_message(
                "❌ 請到指定的猜大小頻道遊玩。",
                ephemeral=True
            )
            return

        # =========================
        # 玩家輸入
        # =========================

        選擇 = 選擇.strip()

        if 選擇 not in ["大", "小"]:

            await interaction.response.send_message(
                "❌ 請輸入『大』或『小』。",
                ephemeral=True
            )
            return

        # =========================
        # 下注限制
        # =========================

        if 金額 < 100:

            await interaction.response.send_message(
                "❌ 最低下注為 **100** 努努幣。",
                ephemeral=True
            )
            return

        if 金額 > 10000:

            await interaction.response.send_message(
                "❌ 最高下注為 **10000** 努努幣。",
                ephemeral=True
            )
            return

        # =========================
        # 玩家資料
        # =========================

        user_id = str(interaction.user.id)

        c.execute(
            """
            SELECT money
            FROM users
            WHERE user_id=?
            """,
            (user_id,)
        )

        data = c.fetchone()

        if not data:

            await interaction.response.send_message(
                "❌ 請先使用 `/簽到` 建立帳號。",
                ephemeral=True
            )
            return

        money = data["money"]

        if money < 金額:

            await interaction.response.send_message(
                (
                    "❌ 努努幣不足。\n\n"
                    f"目前只有 **{money:,}**。"
                ),
                ephemeral=True
            )
            return

        await interaction.response.defer()

        # =========================
        # 搖骰子動畫
        # =========================

        embed = discord.Embed(
            title="🎲 猜大小",
            description=(
                "## 🎲 正在搖骰子...\n\n"
                "⚪　⚪　⚪"
            ),
            color=discord.Color.gold()
        )

        msg = await interaction.followup.send(
            embed=embed,
            wait=True
        )

        frames = [
            "🎲　⚪　⚪",
            "🎲　🎲　⚪",
            "🎲　🎲　🎲"
        ]

        for frame in frames:

            embed.description = (
                "## 🎲 正在搖骰子...\n\n"
                f"{frame}"
            )

            await msg.edit(
                embed=embed
            )

            await asyncio.sleep(0.45)

        # =========================
        # 🎲 擲三顆骰子
        # =========================

        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        dice3 = random.randint(1, 6)

        total = dice1 + dice2 + dice3

        result = "大" if total >= 11 else "小"

        # =========================
        # 🐆 豹子
        # =========================

        is_leopard = (
            dice1 == dice2 == dice3
        )

        # =========================
        # 🌟 活動倍率
        # =========================

        multiplier = 1
        event_text = None

        c.execute(
            """
            SELECT game, multiplier
            FROM daily_event
            WHERE date=?
            """,
            (
                discord.utils.utcnow().date().isoformat(),
            )
        )

        event = c.fetchone()

        if event and event["game"] == "guess":

            multiplier = event["multiplier"]

            if multiplier == 2:

                event_text = "🌟 今日雙倍區"

            elif multiplier == 3:

                event_text = "👑 今日三倍區"

        # =========================
        # 判定勝負
        # =========================

        win = (選擇 == result)

        reward = 0

        if win:

            reward = 金額 * 2

            reward *= multiplier

            if is_leopard:

                reward *= 2

            new_money = money - 金額 + reward

        else:

            new_money = money - 金額

        # =========================
        # 更新資料
        # =========================

        c.execute(
            """
            UPDATE users
            SET money=?
            WHERE user_id=?
            """,
            (
                new_money,
                user_id
            )
        )

        conn.commit()

        # =========================
        # 結果 Embed
        # =========================

        if win:

            embed = discord.Embed(
                title="🎉 恭喜獲勝！",
                color=discord.Color.green()
            )

        else:

            embed = discord.Embed(
                title="💀 很可惜...",
                color=discord.Color.red()
            )

        # =========================
        # 🌟 活動資訊
        # =========================

        if event_text:

            embed.add_field(
                name=event_text,
                value=f"🎉 本局倍率：x{multiplier}",
                inline=False
            )

        # =========================
        # 🐆 豹子
        # =========================

        if is_leopard:

            embed.add_field(
                name="🐆 豹子！",
                value="三顆骰子相同\n額外獎勵 ×2",
                inline=False
            )

        # =========================
        # 🎲 骰子
        # =========================

        embed.add_field(
            name="🎲 骰子結果",
            value=(
                f"第一顆：**{dice1}**\n"
                f"第二顆：**{dice2}**\n"
                f"第三顆：**{dice3}**"
            ),
            inline=False
        )

        embed.add_field(
            name="📊 總點數",
            value=f"**{total}**",
            inline=True
        )

        embed.add_field(
            name="🎯 開獎結果",
            value=f"**{result}**",
            inline=True
        )

        embed.add_field(
            name="🙋 你的選擇",
            value=f"**{選擇}**",
            inline=True
        )

        # =========================
        # 💰 本局結果
        # =========================

        if win:

            embed.add_field(
                name="💰 本局獲得",
                value=f"<a:emoji40:1510362334026268713> **{reward:,}**",
                inline=False
            )

        else:

            embed.add_field(
                name="💸 本局損失",
                value=f"<a:emoji40:1510362334026268713> **{金額:,}**",
                inline=False
            )

        embed.add_field(
            name="🏦 目前資產",
            value=f"<a:emoji40:1510362334026268713> **{new_money:,}**",
            inline=False
        )

        embed.set_footer(
            text="🌙 極曜月葵｜祝你好運 🍀"
        )

        await msg.edit(
            embed=embed
        )