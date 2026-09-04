# -*- coding: utf-8 -*-
"""
Moon Life｜成就盲盒 Discord 測試器
只供開發測試使用。
"""

import sqlite3
import discord
from discord.ext import commands
from discord import app_commands

from systems.moon_achievements import (
    AchievementStore,
    EASY,
    MEDIUM,
    MEDIUM_HIGH,
    HIGH,
    LOOT_WEIGHTS,
)

# ============================================================
# 測試者 Discord User ID
# ============================================================
TESTER_ID = 1301905168094335028


# ============================================================
# 建立資格：選難度
# ============================================================

class AddDifficultyView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=120)
        self.cog = cog

    async def choose(self, interaction, difficulty):
        await interaction.response.send_modal(
            CountModal(self.cog, difficulty)
        )

    @discord.ui.button(label="🟢 簡單", style=discord.ButtonStyle.success, row=0)
    async def easy(self, interaction, button):
        await self.choose(interaction, EASY)

    @discord.ui.button(label="🟡 中", style=discord.ButtonStyle.primary, row=0)
    async def medium(self, interaction, button):
        await self.choose(interaction, MEDIUM)

    @discord.ui.button(label="🟠 中高", style=discord.ButtonStyle.primary, row=1)
    async def medium_high(self, interaction, button):
        await self.choose(interaction, MEDIUM_HIGH)

    @discord.ui.button(label="🔴 高", style=discord.ButtonStyle.danger, row=1)
    async def high(self, interaction, button):
        await self.choose(interaction, HIGH)


# ============================================================
# 建立資格：輸入次數 Modal
# ============================================================

class CountModal(discord.ui.Modal, title="建立測試盲盒資格"):
    count = discord.ui.TextInput(
        label="要建立幾次資格？",
        placeholder="請輸入 1～100，例如：10",
        required=True,
        min_length=1,
        max_length=3,
    )

    def __init__(self, cog, difficulty):
        super().__init__()
        self.cog = cog
        self.difficulty = difficulty

    async def on_submit(self, interaction):
        try:
            count = int(self.count.value)
            if count < 1 or count > 100:
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

        remaining = self.cog.store.get_draw_count(TESTER_ID)

        await interaction.response.send_message(
            f"✅ 已建立 **{count} 次**「{self.difficulty}」測試資格。\n"
            f"🎟️ 目前剩餘資格：**{remaining} 次**",
            ephemeral=True,
        )


# ============================================================
# 開啟盲盒：選難度
# ============================================================

class DrawDifficultyView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=120)
        self.cog = cog

    async def choose(self, interaction, difficulty):
        await self.cog.do_draw(interaction, difficulty)

    @discord.ui.button(label="🟢 簡單", style=discord.ButtonStyle.success, row=0)
    async def easy(self, interaction, button):
        await self.choose(interaction, EASY)

    @discord.ui.button(label="🟡 中", style=discord.ButtonStyle.primary, row=0)
    async def medium(self, interaction, button):
        await self.choose(interaction, MEDIUM)

    @discord.ui.button(label="🟠 中高", style=discord.ButtonStyle.primary, row=1)
    async def medium_high(self, interaction, button):
        await self.choose(interaction, MEDIUM_HIGH)

    @discord.ui.button(label="🔴 高", style=discord.ButtonStyle.danger, row=1)
    async def high(self, interaction, button):
        await self.choose(interaction, HIGH)


# ============================================================
# 測試中心主面板
# ============================================================

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
            "🎟️ **建立測試盲盒資格**\n"
            "請點下面按鈕選擇成就難度；選完會立刻跳出輸入次數視窗。",
            view=AddDifficultyView(self.cog),
            ephemeral=True,
        )

    @discord.ui.button(
        label="🎁 開啟盲盒",
        style=discord.ButtonStyle.success,
        row=0,
    )
    async def draw_box(self, interaction, button):
        count = self.cog.store.get_draw_count(TESTER_ID)

        if count <= 0:
            await interaction.response.send_message(
                "❌ 目前沒有測試盲盒資格。\n"
                "請先按「🎟️ 建立測試資格」。",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"🎁 目前有 **{count} 次**測試資格。\n"
            "請選擇本次要測試的盲盒難度：",
            view=DrawDifficultyView(self.cog),
            ephemeral=True,
        )

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
                lines.append(
                    f"• {reward}：{weight / total * 100:.1f}%"
                )

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


# ============================================================
# Discord Cog
# ============================================================

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
                "🎟️ 建立測試資格 → 選難度 → 輸入次數\n"
                "🎁 開啟盲盒 → 選難度 → 直接抽獎"
            ),
        )
        embed.set_footer(text="只有開發測試者可以使用")

        await interaction.response.send_message(
            embed=embed,
            view=AchievementTestView(self),
            ephemeral=True,
        )

    async def do_draw(self, interaction, difficulty):
        count = self.store.get_draw_count(TESTER_ID)

        if count <= 0:
            await interaction.response.send_message(
                "❌ 沒有剩餘測試資格。",
                ephemeral=True,
            )
            return

        # 目前 moon_achievements.py 使用總資格數，
        # 測試模式依你選的難度抽獎。
        reward = self.store.draw_box(TESTER_ID, difficulty)

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
        embed.add_field(
            name="測試難度",
            value=difficulty,
            inline=True,
        )
        embed.add_field(
            name="剩餘資格",
            value=str(remaining),
            inline=True,
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(AchievementTestCog(bot))
