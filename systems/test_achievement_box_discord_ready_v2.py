# -*- coding: utf-8 -*-
"""
🌙 Moon Life｜成就盲盒 Discord 測試器
只供開發測試使用。

測試方式：
1. /成就盲盒測試
2. 按「建立1次測試資格」——自動建立 1 次【高】難度，不再詢問難度或次數。
3. 按「開啟盲盒」。
4. 若抽到 4 種特殊獎品，會直接進入：
   選擇負責媽咪 → 輸入角色名稱 → 確認送出。
"""

import sqlite3
import datetime
import discord
from discord.ext import commands
from discord import app_commands

from systems.moon_achievements import (
    AchievementStore,
    HIGH,
)

from systems.moon_achievement_ui_v2 import (
    SPECIAL_REWARDS,
    REWARD_NAMES,
    MommySelectView,
)


TESTER_ID = 1301905168094335028


class AchievementTestView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=600)
        self.cog = cog

    @discord.ui.button(
        label="🎟️ 建立1次測試資格",
        style=discord.ButtonStyle.primary,
        row=0,
    )
    async def add_qualification(self, interaction, button):
        if interaction.user.id != TESTER_ID:
            await interaction.response.send_message(
                "❌ 這是開發測試功能，你沒有使用權限。",
                ephemeral=True,
            )
            return

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        self.cog.store.db.execute(
            """
            INSERT INTO moon_achievement_draws
            (user_id, difficulty, created_at, used)
            VALUES (?, ?, ?, 0)
            """,
            (TESTER_ID, HIGH, now),
        )
        self.cog.store.db.commit()

        count = self.cog.store.get_draw_count(TESTER_ID)

        await interaction.response.send_message(
            (
                "✅ 已建立 **1 次**測試資格！\n"
                "🎯 測試難度：**高**\n"
                f"🎟️ 目前剩餘資格：**{count} 次**\n\n"
                "現在直接按「🎁 開啟盲盒」即可。"
            ),
            ephemeral=True,
        )

    @discord.ui.button(
        label="🎁 開啟盲盒",
        style=discord.ButtonStyle.success,
        row=0,
    )
    async def draw_box(self, interaction, button):
        if interaction.user.id != TESTER_ID:
            await interaction.response.send_message(
                "❌ 這是開發測試功能，你沒有使用權限。",
                ephemeral=True,
            )
            return

        await self.cog.draw_box(interaction)

    @discord.ui.button(
        label="📊 查看資格",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def status(self, interaction, button):
        if interaction.user.id != TESTER_ID:
            await interaction.response.send_message(
                "❌ 這是開發測試功能，你沒有使用權限。",
                ephemeral=True,
            )
            return

        count = self.cog.store.get_draw_count(TESTER_ID)

        await interaction.response.send_message(
            f"🎟️ 目前測試盲盒資格：**{count} 次**",
            ephemeral=True,
        )

    @discord.ui.button(
        label="🗑️ 清除測試資料",
        style=discord.ButtonStyle.danger,
        row=1,
    )
    async def reset(self, interaction, button):
        if interaction.user.id != TESTER_ID:
            await interaction.response.send_message(
                "❌ 這是開發測試功能，你沒有使用權限。",
                ephemeral=True,
            )
            return

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
            "🗑️ 測試資格已全部清除。",
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
        count = self.store.get_draw_count(TESTER_ID)

        embed = discord.Embed(
            title="🧪 成就盲盒測試中心",
            description=(
                "這裡是開發測試功能。\n\n"
                "🎟️ 每按一次「建立1次測試資格」就會自動建立 **1 次高難度資格**。\n"
                "不再要求你輸入「高／低」或「幾次」。\n\n"
                f"🎟️ 目前測試資格：**{count} 次**\n\n"
                "抽到以下特殊獎品時，會直接進入正式兌換流程：\n"
                "🎬 影片合集\n"
                "📷 照片合集\n"
                "💍 結婚證書\n"
                "🪪 雙人徽章"
            ),
        )
        embed.set_footer(text="只有曦兒可以使用")

        await interaction.response.send_message(
            embed=embed,
            view=AchievementTestView(self),
            ephemeral=True,
        )

    async def draw_box(self, interaction):
        if self.store.get_draw_count(TESTER_ID) <= 0:
            await interaction.response.send_message(
                "❌ 目前沒有測試盲盒資格。\n請先按「🎟️ 建立1次測試資格」。",
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

        # ⭐ 四種特殊獎品：接正式兌換流程
        if reward in SPECIAL_REWARDS:
            embed = discord.Embed(
                title="🎉 恭喜你抽中特殊獎品！",
                description=(
                    f"🎁 **{REWARD_NAMES[reward]}**\n\n"
                    "請選擇負責的媽咪，接著輸入角色名稱。"
                ),
            )
            embed.add_field(
                name="🎯 測試難度",
                value=str(difficulty),
                inline=True,
            )
            embed.add_field(
                name="🎟️ 剩餘資格",
                value=str(remaining),
                inline=True,
            )

            await interaction.response.send_message(
                embed=embed,
                view=MommySelectView(
                    self.store.db,
                    TESTER_ID,
                    reward,
                ),
                ephemeral=True,
            )
            return

        # ⭐ 努努幣：直接顯示結果
        embed = discord.Embed(
            title="🎁 成就盲盒開啟！",
            description=(
                f"✨ 獲得：**{REWARD_NAMES.get(reward, reward)}**\n\n"
                f"🎯 測試難度：**{difficulty}**\n"
                f"🎟️ 剩餘資格：**{remaining} 次**"
            ),
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(AchievementTestCog(bot))
