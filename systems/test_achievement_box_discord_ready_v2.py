# -*- coding: utf-8 -*-
"""
🧪 Moon Life｜成就盲盒 Discord 測試器
只供曦兒開發測試使用。
"""

import sqlite3
import discord
from discord.ext import commands
from discord import app_commands

from systems.moon_achievements import (
    AchievementStore,
    ACHIEVEMENTS,
    EASY,
    MEDIUM,
    MEDIUM_HIGH,
    HIGH,
    LOOT_WEIGHTS,
    roll_loot,
)

TESTER_ID = 1301905168094335028


class DifficultySelect(discord.ui.Select):
    def __init__(self, action):
        self.action = action
        options = [
            discord.SelectOption(label="簡單", value="easy", emoji="🟢"),
            discord.SelectOption(label="中", value="medium", emoji="🟡"),
            discord.SelectOption(label="中高", value="medium_high", emoji="🟠"),
            discord.SelectOption(label="高", value="high", emoji="🔴"),
        ]
        super().__init__(placeholder="選擇測試難度", options=options)

    async def callback(self, interaction: discord.Interaction):
        difficulty_map = {
            "easy": EASY,
            "medium": MEDIUM,
            "medium_high": MEDIUM_HIGH,
            "high": HIGH,
        }
        await self.action(interaction, difficulty_map[self.values[0]])


class DifficultyView(discord.ui.View):
    def __init__(self, action):
        super().__init__(timeout=120)
        self.add_item(DifficultySelect(action))


class CountModal(discord.ui.Modal, title="建立測試資格"):
    count = discord.ui.TextInput(
        label="要建立幾次資格？",
        placeholder="例如：10",
        min_length=1,
        max_length=4,
    )

    def __init__(self, cog, difficulty):
        super().__init__()
        self.cog = cog
        self.difficulty = difficulty

    async def on_submit(self, interaction: discord.Interaction):
        try:
            count = int(self.count.value)
            if count <= 0 or count > 100:
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                "❌ 請輸入 1～100 的正整數。",
                ephemeral=True,
            )
            return

        now = __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat()

        for _ in range(count):
            self.cog.store.db.execute(
                """
                INSERT INTO moon_achievement_draws
                (user_id, difficulty, created_at, used)
                VALUES (?, ?, ?, 0)
                """,
                (TESTER_ID, self.difficulty, now),
            )

        self.cog.store.db.commit()

        await interaction.response.send_message(
            f"✅ 已建立 **{count} 次**「{self.difficulty}」測試資格。",
            ephemeral=True,
        )


class AchievementTestView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=600)
        self.cog = cog

    @discord.ui.button(
        label="🎟️ 建立測試資格",
        style=discord.ButtonStyle.primary,
        row=0,
    )
    async def add_qualification(self, interaction, button):
        await interaction.response.send_message(
            "🎟️ 請選擇測試難度：",
            view=DifficultyView(self.cog.open_count_modal),
            ephemeral=True,
        )

    @discord.ui.button(
        label="🎁 開啟盲盒",
        style=discord.ButtonStyle.success,
        row=0,
    )
    async def draw_box(self, interaction, button):
        await self.cog.draw_box(interaction)

    @discord.ui.button(
        label="📊 查看資格",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def status(self, interaction, button):
        count = self.cog.store.get_draw_count(TESTER_ID)
        await interaction.response.send_message(
            f"🎟️ 目前測試盲盒資格：**{count} 次**",
            ephemeral=True,
        )

    @discord.ui.button(
        label="🎲 查看機率",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def probability(self, interaction, button):
        lines = ["🎲 **目前盲盒機率**"]
        for difficulty, weights in LOOT_WEIGHTS.items():
            total = sum(weights.values())
            lines.append(f"\n**{difficulty}**")
            for reward, weight in weights.items():
                lines.append(f"• {reward}：{weight / total * 100:.1f}%")

        await interaction.response.send_message(
            "\n".join(lines),
            ephemeral=True,
        )

    @discord.ui.button(
        label="🗑️ 清除測試資料",
        style=discord.ButtonStyle.danger,
        row=2,
    )
    async def reset(self, interaction, button):
        self.cog.store.db.execute(
            "DELETE FROM moon_achievement_draws WHERE user_id=?",
            (TESTER_ID,),
        )
        self.cog.store.db.execute(
            "DELETE FROM moon_achievements WHERE user_id=?",
            (TESTER_ID,),
        )
        self.cog.store.db.commit()

        await interaction.response.send_message(
            "🗑️ 測試資料已全部清除。",
            ephemeral=True,
        )


class AchievementTestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect(":memory:")
        self.store = AchievementStore(self.db)

    async def cog_check(self, interaction):
        if interaction.user.id != TESTER_ID:
            await interaction.response.send_message(
                "❌ 這是開發測試功能，你沒有使用權限。",
                ephemeral=True,
            )
            return False
        return True

    @app_commands.command(
        name="成就盲盒測試",
        description="開啟成就盲盒開發測試中心",
    )
    async def achievement_box_test(self, interaction):
        embed = discord.Embed(
            title="🧪 成就盲盒測試中心",
            description=(
                "這裡是開發測試功能。\n\n"
                "可以快速建立不同難度的盲盒資格，"
                "不用真的完成成就即可測試抽獎。"
            ),
        )
        embed.set_footer(text="只有曦兒可以使用")

        await interaction.response.send_message(
            embed=embed,
            view=AchievementTestView(self),
            ephemeral=True,
        )

    async def open_count_modal(self, interaction, difficulty):
        await interaction.response.send_modal(
            CountModal(self, difficulty)
        )

    async def draw_box(self, interaction):
        if self.store.get_draw_count(TESTER_ID) <= 0:
            await interaction.response.send_message(
                "❌ 目前沒有測試盲盒資格。",
                ephemeral=True,
            )
            return

        reward, difficulty = self.store.consume_draw_and_get_reward(TESTER_ID)

        if reward is None:
            await interaction.response.send_message(
                "❌ 抽獎失敗。",
                ephemeral=True,
            )
            return

        remaining = self.store.get_draw_count(TESTER_ID)

        embed = discord.Embed(
            title="🎁 成就盲盒開啟！",
            description=f"✨ 獲得：**{reward}**",
        )
        embed.add_field(name="測試難度", value=difficulty)
        embed.add_field(name="剩餘資格", value=str(remaining))

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(AchievementTestCog(bot))
