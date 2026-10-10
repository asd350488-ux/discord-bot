# -*- coding: utf-8 -*-
"""
🧪 Moon Life｜成就盲盒 Discord 測試器
只供曦兒開發測試使用。
"""

import sqlite3
import discord
from discord.ext import commands
from discord import app_commands

from systems.moon_achievement_ui_v2 import (
    AchievementBoxView,
    setup_achievement_redemption,
)

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


class TestRewardRouteView(discord.ui.View):
    """測試抽獎已完成後，讓測試者進入正式兌獎的下一步，不再重抽。"""
    def __init__(self, cog, reward):
        super().__init__(timeout=300)
        self.cog = cog
        self.reward = reward

    @discord.ui.button(label="➡️ 進入獎品兌換流程", style=discord.ButtonStyle.success)
    async def continue_redemption(self, interaction, button):
        if interaction.user.id != TESTER_ID:
            await interaction.response.send_message("❌ 這是開發測試功能，你沒有使用權限。", ephemeral=True)
            return
        # 正式 AchievementBoxView 會自己抽一次，因此不能直接使用它，否則會重抽。
        # 使用與正式流程相同的後續元件，按獎品類型分流。
        from systems.moon_achievement_ui_v2 import (
            MOMMY_REWARDS, ADMIN_PROFILE_REWARDS, REWARD_NAMES,
            MommySelectView, AdminMakerSelectView,
        )
        if self.reward in MOMMY_REWARDS:
            await interaction.response.edit_message(
                embed=discord.Embed(title="🎉 測試中獎｜選擇媽咪", description=f"🎁 **{REWARD_NAMES[self.reward]}**\n\n請選擇負責媽咪，再填寫角色名稱。"),
                view=MommySelectView(self.cog.db, TESTER_ID, self.reward),
            )
        elif self.reward in ADMIN_PROFILE_REWARDS:
            await interaction.response.edit_message(
                embed=discord.Embed(title="🎉 測試中獎｜選擇製作者", description=f"🎁 **{REWARD_NAMES[self.reward]}**\n\n請選擇製作管理員。"),
                view=AdminMakerSelectView(self.cog.db, TESTER_ID, self.reward),
            )
        else:
            # 正式 UI 的努努幣獎項會直接入帳；測試環境只會寫入本 cog 的 :memory: DB。
            amount_map = {
                "15,000 努努幣": 15000,
                "10,000 努努幣": 10000,
                "5,000 努努幣": 5000,
            }
            amount = amount_map.get(self.reward)
            if amount is not None:
                self.cog.db.execute("INSERT OR IGNORE INTO users (user_id, money) VALUES (?, 0)", (str(TESTER_ID),))
                self.cog.db.execute("UPDATE users SET money=COALESCE(money, 0)+? WHERE user_id=?", (amount, str(TESTER_ID)))
                self.cog.db.commit()
            await interaction.response.edit_message(
                embed=discord.Embed(title="🎉 測試盲盒開獎", description=f"獲得：**{self.reward}**\n\n測試獎勵已記錄在獨立測試資料庫，不會影響正式努努幣。"),
                view=None,
            )


class AchievementTestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        # 測試用獨立帳本：測試盲盒的努努幣只寫入記憶體，不會改動正式玩家資產。
        self.db.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, money INTEGER DEFAULT 0)")
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

        # 不只顯示抽獎結果：把已抽中的獎品交給正式兌獎 UI，
        # 讓測試者可實際走完選媽咪／選製作者／確認／私訊交圖流程。
        # 先把抽獎結果放回一筆已消耗資格的視覺回報，再以正式 UI 直接處理獎品，
        # 因此這裡不自行 consume 第二次。下面使用專用測試結果 View。
        embed = discord.Embed(
            title="🎁 成就盲盒測試結果",
            description=f"✨ 抽中：**{reward}**\n\n接下來會進入正式獎品兌換流程。",
        )
        embed.add_field(name="測試難度", value=difficulty)
        embed.add_field(name="剩餘資格", value=str(remaining))
        await interaction.response.send_message(embed=embed, view=TestRewardRouteView(self, reward), ephemeral=True)


async def setup(bot):
    cog = AchievementTestCog(bot)
    # 使用測試專屬記憶體資料庫啟動正式圖片兌換 listener；不碰正式資料庫。
    await setup_achievement_redemption(bot, cog.db)
    await bot.add_cog(cog)
