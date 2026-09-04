# -*- coding: utf-8 -*-
"""
🧪 Moon Life｜成就盲盒 Discord 測試器

用途：
- 讓管理者直接在 Discord 手機上測試成就盲盒
- 可快速建立指定難度的測試資格
- 可直接抽獎、查看資格、清除測試資料
- 使用獨立 :memory: 資料庫，不碰正式玩家資料

⚠️ 這是開發測試 Cog，不是正式玩家功能。
"""

import sqlite3
import discord
from discord.ext import commands
from discord import app_commands

from .moon_achievements import (
    AchievementStore,
    AchievementEngine,
    ACHIEVEMENTS,
    EASY,
    MEDIUM,
    MEDIUM_HIGH,
    HIGH,
    LOOT_WEIGHTS,
    roll_loot,
)

# ============================================================
# 🔒 把這裡改成你的 Discord User ID
# ============================================================
TESTER_ID = 1301905168094335028


class AchievementTestView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog

    @discord.ui.button(label="🎟️ 建立測試資格", style=discord.ButtonStyle.primary, row=0)
    async def add_qualification(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CountModal(self.cog))

    @discord.ui.button(label="🎁 開啟盲盒", style=discord.ButtonStyle.success, row=0)
    async def draw_box(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.draw_menu(interaction)

    @discord.ui.button(label="📊 查看資格", style=discord.ButtonStyle.secondary, row=1)
    async def status(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.show_status(interaction)

    @discord.ui.button(label="🎲 查看機率", style=discord.ButtonStyle.secondary, row=1)
    async def probability(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.show_probability(interaction)

    @discord.ui.button(label="🗑️ 清除測試資料", style=discord.ButtonStyle.danger, row=2)
    async def reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.reset_data(interaction)


class DifficultySelect(discord.ui.Select):
    def __init__(self, cog, action):
        self.cog = cog
        self.action = action
        options = [
            discord.SelectOption(label="簡單", value="easy", emoji="🟢"),
            discord.SelectOption(label="中", value="medium", emoji="🟡"),
            discord.SelectOption(label="中高", value="medium_high", emoji="🟠"),
            discord.SelectOption(label="高", value="high", emoji="🔴"),
        ]
        super().__init__(placeholder="選擇測試難度", options=options)

    async def callback(self, interaction: discord.Interaction):
        mapping = {
            "easy": EASY,
            "medium": MEDIUM,
            "medium_high": MEDIUM_HIGH,
            "high": HIGH,
        }
        difficulty = mapping[self.values[0]]
        await self.action(interaction, difficulty)


class DifficultyView(discord.ui.View):
    def __init__(self, cog, action):
        super().__init__(timeout=120)
        self.add_item(DifficultySelect(cog, action))


class CountModal(discord.ui.Modal, title="建立測試資格"):
    difficulty = discord.ui.TextInput(
        label="測試難度",
        placeholder="請輸入：簡單 / 中 / 中高 / 高",
        min_length=1,
        max_length=3,
        required=True,
    )

    count = discord.ui.TextInput(
        label="要建立幾次資格？",
        placeholder="例如：10",
        min_length=1,
        max_length=4,
        required=True,
    )

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        difficulty_map = {
            "簡單": EASY,
            "中": MEDIUM,
            "中高": MEDIUM_HIGH,
            "高": HIGH,
        }

        difficulty_text = str(self.difficulty.value).strip()
        difficulty = difficulty_map.get(difficulty_text)

        if difficulty is None:
            await interaction.response.send_message(
                "❌ 難度請輸入：簡單 / 中 / 中高 / 高",
                ephemeral=True,
            )
            return

        try:
            count = int(str(self.count.value).strip())
            if count <= 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                "❌ 次數請輸入正整數。",
                ephemeral=True,
            )
            return

        if count > 50:
            await interaction.response.send_message(
                "❌ 單次最多建立 50 次測試資格。",
                ephemeral=True,
            )
            return

        for _ in range(count):
            self.cog.store.add_draw_qualification(
                self.cog.test_user_id,
                difficulty,
            )

        remaining = self.cog.store.get_draw_count(self.cog.test_user_id)

        await interaction.response.send_message(
            f"✅ 已建立 **{count} 次**「{difficulty}」測試盲盒資格。\\n"
            f"🎟️ 目前總資格：**{remaining} 次**",
            ephemeral=True,
        )


class AchievementTestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect(":memory:")
        self.store = AchievementStore(self.db)
        self.engine = AchievementEngine(self.store)
        self.test_user_id = TESTER_ID

    async def cog_check(self, interaction: discord.Interaction):
        if TESTER_ID == 0:
            await interaction.response.send_message(
                "⚠️ 尚未設定 TESTER_ID，請先在測試檔填入你的 Discord User ID。",
                ephemeral=True,
            )
            return False

        if interaction.user.id != TESTER_ID:
            await interaction.response.send_message(
                "❌ 這是開發測試功能，你沒有使用權限。",
                ephemeral=True,
            )
            return False

        return True

    @app_commands.command(name="成就盲盒測試", description="開啟成就盲盒開發測試中心")
    async def achievement_box_test(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🧪 成就盲盒測試中心",
            description=(
                "這裡是開發測試功能。\n\n"
                "可以快速建立不同難度的盲盒資格，"
                "不用真的完成成就即可測試抽獎。"
            ),
        )
        embed.add_field(
            name="🎟️ 測試資格",
            value="可快速建立指定難度、指定次數。",
            inline=False,
        )
        embed.add_field(
            name="🎁 盲盒抽獎",
            value="直接測試實際盲盒獎品與資格扣除。",
            inline=False,
        )
        embed.set_footer(text="只有開發測試者可以使用")
        await interaction.response.send_message(
            embed=embed,
            view=AchievementTestView(self),
            ephemeral=True,
        )

    async def add_qualification_menu(self, interaction):
        await interaction.response.send_message(
            "🎟️ **建立測試盲盒資格**\n請選擇要測試的成就難度：",
            view=DifficultyView(self, self.add_qualification_count),
            ephemeral=True,
        )

    async def add_qualification_count(self, interaction, difficulty):
        await interaction.response.send_modal(CountModal(self, difficulty))

    async def draw_menu(self, interaction):
        count = self.store.get_draw_count(self.test_user_id)
        if count <= 0:
            await interaction.response.send_message(
                "❌ 目前沒有測試盲盒資格。\n請先建立測試資格。",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"🎁 目前有 **{count} 次**測試資格。\n請選擇本次要測試的難度：",
            view=DifficultyView(self, self.do_draw),
            ephemeral=True,
        )

    async def do_draw(self, interaction, difficulty):
        reward = self.store.draw_box(self.test_user_id, difficulty)
        if reward is None:
            await interaction.response.send_message(
                "❌ 抽獎失敗：沒有剩餘資格。",
                ephemeral=True,
            )
            return

        remaining = self.store.get_draw_count(self.test_user_id)
        embed = discord.Embed(
            title="🎁 成就盲盒開啟！",
            description=f"✨ 獲得：**{reward}**",
        )
        embed.add_field(name="剩餘測試資格", value=str(remaining))
        embed.add_field(name="測試難度", value=difficulty, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def show_status(self, interaction):
        count = self.store.get_draw_count(self.test_user_id)
        completed = []

        for a in ACHIEVEMENTS:
            row = self.db.execute(
                """
                SELECT completed
                FROM moon_achievements
                WHERE user_id = ? AND achievement_id = ?
                """,
                (self.test_user_id, a.achievement_id),
            ).fetchone()

            if row and row[0]:
                completed.append(a)

        text = f"🎟️ 測試盲盒資格：**{count} 次**\n"
        text += f"🏆 測試完成成就：**{len(completed)} / {len(ACHIEVEMENTS)}**"

        if completed:
            text += "\n\n已完成：\n"
            text += "\n".join(
                f"• {a.achievement_id}｜{a.name}｜{a.difficulty}"
                for a in completed[:20]
            )

        await interaction.response.send_message(text, ephemeral=True)

    async def show_probability(self, interaction):
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

    async def reset_data(self, interaction):
        self.db.execute(
            "DELETE FROM moon_achievements WHERE user_id = ?",
            (self.test_user_id,),
        )
        self.db.execute(
            "DELETE FROM moon_achievement_loot WHERE user_id = ?",
            (self.test_user_id,),
        )
        self.db.commit()

        await interaction.response.send_message(
            "🗑️ 測試資料已全部清除。",
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(AchievementTestCog(bot))
