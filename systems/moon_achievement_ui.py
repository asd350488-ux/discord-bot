# -*- coding: utf-8 -*-
"""🌙 Moon Club｜成就盲盒 UI"""

import datetime
import discord

from .moon_achievements import (
    AchievementStore,
    ACHIEVEMENTS,
    REWARD_VIDEO, REWARD_PHOTO, REWARD_CERTIFICATE, REWARD_BADGE,
    REWARD_NUNU_30000, REWARD_NUNU_40000, REWARD_NUNU_50000,
)

MOMMY_LIST = {
    "🫧 韓馨": 1153640526063607820,
    "☀️ 星弦": 1218542666879598613,
    "🌻 曦兒": 1301905168094335028,
    "🐈 小貓": 806960151578804275,
}

SPECIAL_REWARDS = {
    REWARD_VIDEO, REWARD_PHOTO, REWARD_CERTIFICATE, REWARD_BADGE
}

REWARD_NAMES = {
    REWARD_VIDEO: "🎬 影片合集",
    REWARD_PHOTO: "📷 照片合集",
    REWARD_CERTIFICATE: "💍 結婚證書",
    REWARD_BADGE: "🪪 雙人徽章",
    REWARD_NUNU_30000: "💰 30,000 努努幣",
    REWARD_NUNU_40000: "💰 40,000 努努幣",
    REWARD_NUNU_50000: "💰 50,000 努努幣",
}


def ensure_redemption_table(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS moon_achievement_redemptions (
            redemption_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            reward TEXT NOT NULL,
            mommy_name TEXT NOT NULL,
            mommy_id INTEGER NOT NULL,
            character_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'submitted',
            created_at TEXT NOT NULL,
            submitted_at TEXT
        )
    """)
    db.commit()


def get_completed_names(db, user_id):
    rows = db.execute(
        "SELECT achievement_id FROM moon_achievements "
        "WHERE user_id=? AND completed=1 ORDER BY completed_at ASC",
        (int(user_id),)
    ).fetchall()
    ids = {r[0] for r in rows}
    return [a.name for a in ACHIEVEMENTS if a.achievement_id in ids]


def build_achievement_box_embed(db, user_id):
    store = AchievementStore(db)
    names = get_completed_names(db, user_id)
    completed = "\n".join(f"🏆 {x}" for x in names) or "目前還沒有完成的成就。"

    return discord.Embed(
        title="🎁 成就盲盒",
        description=(
            f"🎟️ **目前抽獎次數：{store.get_draw_count(user_id)} 次**\n\n"
            f"🏆 **已完成成就**\n{completed}\n\n"
            "🎁 **獎品內容**\n"
            "💰 30,000 努努幣\n"
            "💰 40,000 努努幣\n"
            "💰 50,000 努努幣\n"
            "🎬 影片合集\n"
            "📷 照片合集\n"
            "💍 結婚證書\n"
            "🪪 雙人徽章"
        )
    )


class MommySelect(discord.ui.Select):
    def __init__(self, db, user_id, reward):
        super().__init__(
            placeholder="👩‍💼 選擇負責媽咪",
            options=[
                discord.SelectOption(label=name, value=str(mid))
                for name, mid in MOMMY_LIST.items()
            ],
        )
        self.db, self.user_id, self.reward = db, int(user_id), reward

    async def callback(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 這不是你的兌換流程。", ephemeral=True)
            return

        mommy_id = int(self.values[0])
        mommy_name = next(k for k, v in MOMMY_LIST.items() if v == mommy_id)
        await interaction.response.send_modal(
            CharacterNameModal(
                self.db, self.user_id, self.reward, mommy_name, mommy_id
            )
        )


class MommySelectView(discord.ui.View):
    def __init__(self, db, user_id, reward):
        super().__init__(timeout=180)
        self.add_item(MommySelect(db, user_id, reward))


class CharacterNameModal(discord.ui.Modal, title="📝 填寫角色名稱"):
    character_name = discord.ui.TextInput(
        label="角色名稱",
        placeholder="請輸入要指定的角色名稱",
        min_length=2,
        max_length=30,
        required=True,
    )

    def __init__(self, db, user_id, reward, mommy_name, mommy_id):
        super().__init__()
        self.db, self.user_id, self.reward = db, int(user_id), reward
        self.mommy_name, self.mommy_id = mommy_name, int(mommy_id)

    async def on_submit(self, interaction):
        name = self.character_name.value.strip()
        await interaction.response.send_message(
            embed=discord.Embed(
                title="📋 確認獎品兌換",
                description=(
                    f"🎁 獎品：**{REWARD_NAMES[self.reward]}**\n"
                    f"👩‍💼 負責媽咪：**{self.mommy_name}**\n"
                    f"🎭 指定角色：**{name}**\n\n"
                    "確認後，機器人會自動通知媽咪。"
                )
            ),
            view=RedemptionConfirmView(
                self.db, self.user_id, self.reward,
                self.mommy_name, self.mommy_id, name
            ),
            ephemeral=True,
        )


class RedemptionConfirmView(discord.ui.View):
    def __init__(self, db, user_id, reward, mommy_name, mommy_id, character_name):
        super().__init__(timeout=120)
        self.db = db
        self.user_id = int(user_id)
        self.reward = reward
        self.mommy_name = mommy_name
        self.mommy_id = int(mommy_id)
        self.character_name = character_name

    @discord.ui.button(label="✅ 確定送出", style=discord.ButtonStyle.success)
    async def confirm(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 這不是你的兌換流程。", ephemeral=True)
            return

        ensure_redemption_table(self.db)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        cur = self.db.execute("""
            INSERT INTO moon_achievement_redemptions
            (user_id, reward, mommy_name, mommy_id, character_name,
             status, created_at, submitted_at)
            VALUES (?, ?, ?, ?, ?, 'submitted', ?, ?)
        """, (
            self.user_id, self.reward, self.mommy_name, self.mommy_id,
            self.character_name, now, now
        ))
        redemption_id = cur.lastrowid
        self.db.commit()

        notify_ok = False
        try:
            mommy = interaction.client.get_user(self.mommy_id)
            if mommy is None:
                mommy = await interaction.client.fetch_user(self.mommy_id)
            await mommy.send(
                "🔔 **成就盲盒獎勵通知**\n\n"
                f"👤 玩家：{interaction.user.mention}\n"
                f"🎁 獎品：{REWARD_NAMES[self.reward]}\n"
                f"🎭 指定角色：{self.character_name}\n"
                f"📌 兌換編號：`#{redemption_id}`\n\n"
                "請協助後續獎勵處理。"
            )
            notify_ok = True
        except Exception:
            pass

        await interaction.response.edit_message(
            embed=discord.Embed(
                title="✅ 兌換已送出",
                description=(
                    f"🎁 **{REWARD_NAMES[self.reward]}**\n"
                    f"👩‍💼 負責媽咪：**{self.mommy_name}**\n"
                    f"🎭 指定角色：**{self.character_name}**\n\n"
                    + ("🔔 已通知媽咪。" if notify_ok
                       else "⚠️ 兌換已記錄，但目前無法發送媽咪通知。")
                )
            ),
            view=None,
        )

    @discord.ui.button(label="❌ 取消", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 這不是你的兌換流程。", ephemeral=True)
            return
        await interaction.response.edit_message(content="已取消這次兌換。", embed=None, view=None)


class AchievementBoxView(discord.ui.View):
    def __init__(self, db, user_id):
        super().__init__(timeout=300)
        self.db, self.user_id = db, int(user_id)

    @discord.ui.button(label="🎁 抽獎", style=discord.ButtonStyle.success)
    async def draw(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 這不是你的成就盲盒。", ephemeral=True)
            return

        store = AchievementStore(self.db)
        reward, _difficulty = store.consume_draw_and_get_reward(self.user_id)

        if reward is None:
            await interaction.response.send_message("❌ 目前沒有抽獎次數。", ephemeral=True)
            return

        if reward in SPECIAL_REWARDS:
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title="🎉 恭喜你抽中特殊獎品！",
                    description=(
                        f"🎁 **{REWARD_NAMES[reward]}**\n\n"
                        "請選擇負責的媽咪，再填寫角色名稱。"
                    )
                ),
                view=MommySelectView(self.db, self.user_id, reward),
            )
            return

        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🎉 成就盲盒開獎！",
                description=(
                    f"恭喜你獲得：\n\n"
                    f"## {REWARD_NAMES[reward]}\n\n"
                    f"🎟️ 剩餘抽獎次數：**{store.get_draw_count(self.user_id)} 次**"
                )
            ),
            view=None,
        )


def make_achievement_box_button(db, user_id):
    if not AchievementStore(db).has_unclaimed_draw(int(user_id)):
        return None

    class AchievementBoxButton(discord.ui.Button):
        def __init__(self):
            super().__init__(
                label="🎁 成就盲盒",
                style=discord.ButtonStyle.success,
                row=2,
            )

        async def callback(self, interaction):
            if interaction.user.id != int(user_id):
                await interaction.response.send_message("❌ 這不是你的成就盲盒。", ephemeral=True)
                return
            await interaction.response.edit_message(
                embed=build_achievement_box_embed(db, int(user_id)),
                view=AchievementBoxView(db, int(user_id)),
            )

    return AchievementBoxButton()
