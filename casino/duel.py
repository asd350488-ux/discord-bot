import asyncio
import random

import discord
from discord import app_commands

from config import *
from database import c, conn


ACTIVE_DUELS = set()


class DuelView(discord.ui.View):

    def __init__(
        self,
        challenger: discord.Member,
        target: discord.Member,
        amount: int
    ):

        super().__init__(timeout=60)

        self.challenger = challenger
        self.target = target
        self.amount = amount

        self.message = None
        self.finished = False

    async def on_timeout(self):

        if self.finished:
            return

        self.finished = True

        ACTIVE_DUELS.discard(
            self.challenger.id
        )

        ACTIVE_DUELS.discard(
            self.target.id
        )

        for item in self.children:

            item.disabled = True

        embed = discord.Embed(
            title="⌛ 對賭已取消",
            description=(
                "對方沒有在 **60 秒** 內回應。\n\n"
                "本次對賭已失效。"
            ),
            color=discord.Color.red()
        )

        if self.message:

            await self.message.edit(
                embed=embed,
                view=self
            )

    # ==========================
    # ✅ 接受
    # ==========================

    @discord.ui.button(
        label="接受",
        emoji="✅",
        style=discord.ButtonStyle.success
    )
    async def accept(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.user.id != self.target.id:

            await interaction.response.send_message(
                "❌ 只有被挑戰者可以接受。",
                ephemeral=True
            )
            return

        self.finished = True

        ACTIVE_DUELS.discard(
            self.challenger.id
        )

        ACTIVE_DUELS.discard(
            self.target.id
        )

        for item in self.children:

            item.disabled = True

        embed = discord.Embed(
            title="⚔️ 對賭開始",
            description=(
                f"{self.target.mention} 已接受挑戰！\n\n"
                "⚔️ 對決即將開始..."
            ),
            color=discord.Color.green()
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

        await self.start_duel(
            interaction
        )

    # ==========================
    # ❌ 拒絕
    # ==========================

    @discord.ui.button(
        label="拒絕",
        emoji="❌",
        style=discord.ButtonStyle.danger
    )
    async def reject(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.user.id != self.target.id:

            await interaction.response.send_message(
                "❌ 只有被挑戰者可以拒絕。",
                ephemeral=True
            )
            return

        self.finished = True

        ACTIVE_DUELS.discard(
            self.challenger.id
        )

        ACTIVE_DUELS.discard(
            self.target.id
        )

        for item in self.children:

            item.disabled = True

        embed = discord.Embed(
            title="❌ 對賭已取消",
            description=(
                f"{self.target.mention} 拒絕了此次挑戰。"
            ),
            color=discord.Color.red()
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

    # ==========================
    # ⚔️ 開始對決
    # ==========================

    async def start_duel(
        self,
        interaction: discord.Interaction
    ):

        embed = discord.Embed(
            title="⚔️ 對決開始",
            color=discord.Color.orange()
        )

        await interaction.edit_original_response(
            embed=embed,
            view=None
        )

        msg = await interaction.original_response()

        frames = [

            (
                f"👤 {self.challenger.display_name}\n\n"
                "　　　　⚔️\n\n"
                f"👤 {self.target.display_name}"
            ),

            (
                f"👤 {self.challenger.display_name}\n\n"
                "　　 ⚡⚔️⚡\n\n"
                f"👤 {self.target.display_name}"
            ),

            (
                f"👤 {self.challenger.display_name}\n\n"
                "　　　　💥\n\n"
                f"👤 {self.target.display_name}"
            )

        ]

        for frame in frames:

            embed.description = frame

            await msg.edit(
                embed=embed
            )

            await asyncio.sleep(0.8)

        user1 = str(self.challenger.id)
        user2 = str(self.target.id)

        c.execute(
            "SELECT money FROM users WHERE user_id=?",
            (user1,)
        )
        money1 = c.fetchone()["money"]

        c.execute(
            "SELECT money FROM users WHERE user_id=?",
            (user2,)
        )
        money2 = c.fetchone()["money"]

        if money1 < self.amount or money2 < self.amount:

            embed = discord.Embed(
                title="❌ 對賭取消",
                description="有玩家努努幣不足。",
                color=discord.Color.red()
            )

            await msg.edit(
                embed=embed
            )

            return

        winner = random.choice([
            self.challenger,
            self.target
        ])

        loser = (
            self.target
            if winner.id == self.challenger.id
            else self.challenger
        )

        prize = self.amount * 2

        c.execute(
            "UPDATE users SET money=money-? WHERE user_id=?",
            (
                self.amount,
                user1
            )
        )

        c.execute(
            "UPDATE users SET money=money-? WHERE user_id=?",
            (
                self.amount,
                user2
            )
        )

        c.execute(
            "UPDATE users SET money=money+? WHERE user_id=?",
            (
                prize,
                str(winner.id)
            )
        )

        conn.commit()

        c.execute(
            "SELECT money FROM users WHERE user_id=?",
            (
                str(winner.id),
            )
        )

        balance = c.fetchone()["money"]

        result = discord.Embed(
            title="🏆 對賭結果",
            color=discord.Color.gold()
        )

        result.add_field(
            name="⚔️ 對戰",
            value=(
                f"{self.challenger.mention}\n"
                "🆚\n"
                f"{self.target.mention}"
            ),
            inline=False
        )

        result.add_field(
            name="👑 勝利者",
            value=winner.mention,
            inline=False
        )

        result.add_field(
            name="💰 獲得努努幣",
            value=f"<a:emoji40:1510362334026268713> **{prize:,}**",
            inline=True
        )

        result.add_field(
            name="🏦 目前資產",
            value=f"<a:emoji40:1510362334026268713> **{balance:,}**",
            inline=True
        )

        result.set_footer(
            text="🌙 極曜月葵｜對賭系統"
        )

        await msg.edit(
            embed=result
        )

def setup(bot):

    @bot.tree.command(
        name="對賭",
        description="向其他玩家發起對賭"
    )
    @app_commands.describe(
        玩家="要挑戰的玩家",
        金額="100~10000"
    )
    async def duel(
        interaction: discord.Interaction,
        玩家: discord.Member,
        金額: int
    ):

        # ==========================
        # 頻道限制
        # ==========================

        if interaction.channel.id != DUEL_CHANNEL:

            await interaction.response.send_message(
                "❌ 請到指定的對賭頻道使用。",
                ephemeral=True
            )
            return

        # ==========================
        # 金額限制
        # ==========================

        if 金額 < 100:

            await interaction.response.send_message(
                "❌ 最低下注為 100。",
                ephemeral=True
            )
            return

        if 金額 > 10000:

            await interaction.response.send_message(
                "❌ 最高下注為 10000。",
                ephemeral=True
            )
            return

        # ==========================
        # 禁止挑戰自己
        # ==========================

        if 玩家.id == interaction.user.id:

            await interaction.response.send_message(
                "❌ 不能挑戰自己。",
                ephemeral=True
            )
            return

        # ==========================
        # 禁止挑戰 Bot
        # ==========================

        if 玩家.bot:

            await interaction.response.send_message(
                "❌ 不能挑戰 Bot。",
                ephemeral=True
            )
            return

        # ==========================
        # 是否已有進行中的對賭
        # ==========================

        if interaction.user.id in ACTIVE_DUELS:

            await interaction.response.send_message(
                "❌ 你目前已有一場對賭。",
                ephemeral=True
            )
            return

        if 玩家.id in ACTIVE_DUELS:

            await interaction.response.send_message(
                "❌ 對方目前正在進行其他對賭。",
                ephemeral=True
            )
            return

        # ==========================
        # 查詢雙方資料
        # ==========================

        c.execute(
            "SELECT money FROM users WHERE user_id=?",
            (str(interaction.user.id),)
        )

        challenger = c.fetchone()

        c.execute(
            "SELECT money FROM users WHERE user_id=?",
            (str(玩家.id),)
        )

        target = c.fetchone()

        if challenger is None:

            await interaction.response.send_message(
                "❌ 請先使用 /簽到。",
                ephemeral=True
            )
            return

        if target is None:

            await interaction.response.send_message(
                "❌ 對方尚未簽到。",
                ephemeral=True
            )
            return

        if challenger["money"] < 金額:

            await interaction.response.send_message(
                "❌ 你的努努幣不足。",
                ephemeral=True
            )
            return

        if target["money"] < 金額:

            await interaction.response.send_message(
                "❌ 對方的努努幣不足。",
                ephemeral=True
            )
            return

        view = DuelView(
            challenger=interaction.user,
            target=玩家,
            amount=金額
        )

        embed = discord.Embed(
            title="⚔️ 對賭邀請",
            description=(
                f"{interaction.user.mention} 向 {玩家.mention} 發起挑戰！\n\n"
                f"💰 下注：<a:emoji40:1510362334026268713> **{金額:,}**\n\n"
                "請在 **60 秒內** 選擇是否接受。"
            ),
            color=discord.Color.orange()
        )

        embed.add_field(
            name="📜 規則",
            value=(
                "• 最低下注：100\n"
                "• 最高下注：10,000\n"
                "• 勝者獲得全部獎池"
            ),
            inline=False
        )

        embed.set_footer(
            text="🌙 極曜月葵｜對賭系統"
        )

        await interaction.response.send_message(
            embed=embed,
            view=view
        )

        view.message = await interaction.original_response()

        ACTIVE_DUELS.add(
            interaction.user.id
        )

        ACTIVE_DUELS.add(
            玩家.id
        )