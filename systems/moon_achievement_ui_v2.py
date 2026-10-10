# -*- coding: utf-8 -*-
"""🌙 Moon Club｜成就盲盒 UI 與圖片獎品兌換流程"""

import asyncio
import datetime
import discord
from discord.ext import tasks

try:
    from config import BOT_ADMINS
except ImportError:
    BOT_ADMINS = set()

from .moon_achievements import (
    AchievementStore, ACHIEVEMENTS, LOOT_WEIGHTS,
    REWARD_VIDEO, REWARD_PHOTO, REWARD_POSTER, REWARD_CHIBI_STICKERS,
    REWARD_CERTIFICATE, REWARD_BANNER, REWARD_COUPLE_PHOTOS_2,
    REWARD_COUPLE_PHOTO_1, REWARD_ILLUSTRATION, REWARD_BADGE,
    REWARD_RANDOM_PROFILE_2, REWARD_RANDOM_PROFILE_1,
    REWARD_NUNU_15000, REWARD_NUNU_10000, REWARD_NUNU_5000,
)

MOMMY_LIST = {
    "🫧 韓馨": 1153640526063607820,
    "☀️ 星弦": 1218542666879598613,
    "🌻 曦兒": 1301905168094335028,
}

ADMIN_MAKER_LIST = {
    "🌷 菜菜": 873202145367846942,
    "🩵 小 E": 844778614268100638,
}

# 媽咪製作、需要指定角色名稱的獎品
MOMMY_REWARDS = {
    REWARD_VIDEO, REWARD_PHOTO, REWARD_POSTER, REWARD_CHIBI_STICKERS,
    REWARD_CERTIFICATE, REWARD_BANNER, REWARD_COUPLE_PHOTOS_2,
    REWARD_COUPLE_PHOTO_1, REWARD_ILLUSTRATION, REWARD_BADGE,
}
# 菜菜／小 E 製作，不詢問媽咪或角色名稱
ADMIN_PROFILE_REWARDS = {REWARD_RANDOM_PROFILE_2, REWARD_RANDOM_PROFILE_1}
# 舊版測試器相容名稱；正式流程使用 MOMMY_REWARDS。
SPECIAL_REWARDS = MOMMY_REWARDS
IMAGE_REWARDS = MOMMY_REWARDS | ADMIN_PROFILE_REWARDS

REWARD_NAMES = {
    REWARD_VIDEO: "🎬 影片合集（張數由媽咪決定）",
    REWARD_PHOTO: "📷 照片合集（張數由媽咪決定）",
    REWARD_POSTER: "🖼️ 雙人海報（版面共 3–4 張）",
    REWARD_CHIBI_STICKERS: "🥰 雙人 Q 版貼圖（四宮格）",
    REWARD_CERTIFICATE: "💍 結婚證書",
    REWARD_BANNER: "🌙 雙人橫幅",
    REWARD_COUPLE_PHOTOS_2: "📸 雙人合照 × 2 張",
    REWARD_COUPLE_PHOTO_1: "📸 雙人合照 × 1 張",
    REWARD_ILLUSTRATION: "🎨 雙人插畫",
    REWARD_BADGE: "🪪 雙人徽章",
    REWARD_RANDOM_PROFILE_2: "🎨 隨機風格人設圖 × 2",
    REWARD_RANDOM_PROFILE_1: "🎨 隨機風格人設圖 × 1",
    REWARD_NUNU_15000: "💰 15,000 努努幣",
    REWARD_NUNU_10000: "💰 10,000 努努幣",
    REWARD_NUNU_5000: "💰 5,000 努努幣",
}

UTC = datetime.timezone.utc
SUBMISSION_HOURS = 48
REMINDER_HOURS = 24


def ensure_redemption_table(db):
    """建立兌換表，並以安全方式為舊表補上新欄位。"""
    db.execute("""
        CREATE TABLE IF NOT EXISTS moon_achievement_redemptions (
            redemption_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            reward TEXT NOT NULL,
            mommy_name TEXT NOT NULL DEFAULT '',
            mommy_id INTEGER NOT NULL DEFAULT 0,
            character_name TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'awaiting_image',
            created_at TEXT NOT NULL,
            submitted_at TEXT,
            expires_at TEXT,
            reminded_at TEXT,
            user_dm_channel_id INTEGER,
            user_image_message_id INTEGER,
            maker_message_id INTEGER,
            maker_channel_id INTEGER,
            completed_at TEXT,
            completed_by INTEGER
        )
    """)
    existing = {row[1] for row in db.execute("PRAGMA table_info(moon_achievement_redemptions)").fetchall()}
    additions = {
        "mommy_name": "TEXT NOT NULL DEFAULT ''",
        "mommy_id": "INTEGER NOT NULL DEFAULT 0",
        "character_name": "TEXT NOT NULL DEFAULT ''",
        "status": "TEXT NOT NULL DEFAULT 'awaiting_image'",
        "submitted_at": "TEXT",
        "expires_at": "TEXT",
        "reminded_at": "TEXT",
        "user_dm_channel_id": "INTEGER",
        "user_image_message_id": "INTEGER",
        "maker_message_id": "INTEGER",
        "maker_channel_id": "INTEGER",
        "completed_at": "TEXT",
        "completed_by": "INTEGER",
    }
    for column, definition in additions.items():
        if column not in existing:
            db.execute(f"ALTER TABLE moon_achievement_redemptions ADD COLUMN {column} {definition}")
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
    rewards = "\n".join(f"• {REWARD_NAMES[r]}（{p:g}%）" for r, p in LOOT_WEIGHTS.items())
    return discord.Embed(
        title="🎁 成就盲盒",
        description=(
            f"🎟️ **目前抽獎次數：{store.get_draw_count(user_id)} 次**\n\n"
            f"🏆 **已完成成就**\n{completed}\n\n"
            f"🎁 **新版獎池（統一機率）**\n{rewards}"
        )
    )


class MommySelect(discord.ui.Select):
    def __init__(self, db, user_id, reward):
        super().__init__(placeholder="👩‍💼 選擇負責媽咪", options=[
            discord.SelectOption(label=name, value=str(mid)) for name, mid in MOMMY_LIST.items()
        ])
        self.db, self.user_id, self.reward = db, int(user_id), reward

    async def callback(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 這不是你的兌換流程。", ephemeral=True)
            return
        mommy_id = int(self.values[0])
        mommy_name = next(k for k, v in MOMMY_LIST.items() if v == mommy_id)
        await interaction.response.send_modal(CharacterNameModal(self.db, self.user_id, self.reward, mommy_name, mommy_id))


class MommySelectView(discord.ui.View):
    def __init__(self, db, user_id, reward):
        super().__init__(timeout=180)
        self.add_item(MommySelect(db, user_id, reward))


class AdminMakerSelect(discord.ui.Select):
    def __init__(self, db, user_id, reward):
        super().__init__(placeholder="🧑‍💼 選擇製作管理員", options=[
            discord.SelectOption(label=name, value=str(mid)) for name, mid in ADMIN_MAKER_LIST.items()
        ])
        self.db, self.user_id, self.reward = db, int(user_id), reward

    async def callback(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 這不是你的兌換流程。", ephemeral=True)
            return
        maker_id = int(self.values[0])
        maker_name = next(k for k, v in ADMIN_MAKER_LIST.items() if v == maker_id)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="📋 確認獎品兌換",
                description=(f"🎁 獎品：**{REWARD_NAMES[self.reward]}**\n"
                             f"🧑‍💼 製作管理員：**{maker_name}**\n\n"
                             "確認後，機器人會私訊你提交一張人設圖。請於 48 小時內提交；逾期視同放棄。")
            ),
            view=AdminMakerConfirmView(self.db, self.user_id, self.reward, maker_name, maker_id),
            ephemeral=True,
        )


class AdminMakerSelectView(discord.ui.View):
    def __init__(self, db, user_id, reward):
        super().__init__(timeout=180)
        self.add_item(AdminMakerSelect(db, user_id, reward))


class CharacterNameModal(discord.ui.Modal, title="📝 填寫角色名稱"):
    character_name = discord.ui.TextInput(label="角色名稱", placeholder="請輸入要指定的角色名稱", min_length=2, max_length=30, required=True)

    def __init__(self, db, user_id, reward, mommy_name, mommy_id):
        super().__init__()
        self.db, self.user_id, self.reward = db, int(user_id), reward
        self.mommy_name, self.mommy_id = mommy_name, int(mommy_id)

    async def on_submit(self, interaction):
        name = self.character_name.value.strip()
        await interaction.response.send_message(
            embed=discord.Embed(title="📋 確認獎品兌換", description=(
                f"🎁 獎品：**{REWARD_NAMES[self.reward]}**\n"
                f"👩‍💼 負責媽咪：**{self.mommy_name}**\n"
                f"🎭 指定角色：**{name}**\n\n"
                "確認後，機器人會私訊你提交一張人設圖。請於 48 小時內提交；逾期視同放棄。"
            )),
            view=RedemptionConfirmView(self.db, self.user_id, self.reward, self.mommy_name, self.mommy_id, name),
            ephemeral=True,
        )


async def _create_redemption(interaction, db, reward, maker_name, maker_id, character_name=""):
    ensure_redemption_table(db)
    now = datetime.datetime.now(UTC)
    expires = now + datetime.timedelta(hours=SUBMISSION_HOURS)
    cur = db.execute("""
        INSERT INTO moon_achievement_redemptions
        (user_id, reward, mommy_name, mommy_id, character_name, status, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?, 'awaiting_image', ?, ?)
    """, (interaction.user.id, reward, maker_name, int(maker_id), character_name,
          now.isoformat(), expires.isoformat()))
    redemption_id = cur.lastrowid
    db.commit()
    dm_ok = await send_upload_request(interaction.client, db, redemption_id, interaction.user.id)
    return redemption_id, dm_ok


class RedemptionConfirmView(discord.ui.View):
    def __init__(self, db, user_id, reward, mommy_name, mommy_id, character_name):
        super().__init__(timeout=120)
        self.db, self.user_id, self.reward = db, int(user_id), reward
        self.mommy_name, self.mommy_id, self.character_name = mommy_name, int(mommy_id), character_name

    @discord.ui.button(label="✅ 確定兌換", style=discord.ButtonStyle.success)
    async def confirm(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 這不是你的兌換流程。", ephemeral=True)
            return
        await interaction.response.defer()
        redemption_id, dm_ok = await _create_redemption(interaction, self.db, self.reward,
                                                          self.mommy_name, self.mommy_id, self.character_name)
        await interaction.edit_original_response(embed=discord.Embed(
            title="✅ 已建立兌換紀錄",
            description=(f"🎁 **{REWARD_NAMES[self.reward]}**\n"
                         f"👩‍💼 負責媽咪：**{self.mommy_name}**\n"
                         f"🎭 角色名稱：**{self.character_name}**\n"
                         f"📌 請截圖備份本次中獎結果。\n"
                         + ("📩 已私訊你上傳人設圖，請於 48 小時內提交。" if dm_ok else
                            "⚠️ 無法私訊你，請開啟機器人私訊後按下方按鈕重新發送通知。")),
        ), view=RetryUploadView(self.db, self.user_id, redemption_id) if not dm_ok else None)

    @discord.ui.button(label="❌ 取消", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 這不是你的兌換流程。", ephemeral=True)
            return
        await interaction.response.edit_message(content="已取消這次兌換。", embed=None, view=None)


class AdminMakerConfirmView(discord.ui.View):
    def __init__(self, db, user_id, reward, maker_name, maker_id):
        super().__init__(timeout=120)
        self.db, self.user_id, self.reward = db, int(user_id), reward
        self.maker_name, self.maker_id = maker_name, int(maker_id)

    @discord.ui.button(label="✅ 確定兌換", style=discord.ButtonStyle.success)
    async def confirm(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 這不是你的兌換流程。", ephemeral=True)
            return
        await interaction.response.defer()
        redemption_id, dm_ok = await _create_redemption(interaction, self.db, self.reward, self.maker_name, self.maker_id)
        await interaction.edit_original_response(embed=discord.Embed(
            title="✅ 已建立兌換紀錄",
            description=(f"🎁 **{REWARD_NAMES[self.reward]}**\n"
                         f"🧑‍💼 製作管理員：**{self.maker_name}**\n"
                         "📌 請截圖備份本次中獎結果。\n"
                         + ("📩 已私訊你上傳人設圖，請於 48 小時內提交。" if dm_ok else
                            "⚠️ 無法私訊你，請開啟機器人私訊後按下方按鈕重新發送通知。")),
        ), view=RetryUploadView(self.db, self.user_id, redemption_id) if not dm_ok else None)

    @discord.ui.button(label="❌ 取消", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 這不是你的兌換流程。", ephemeral=True)
            return
        await interaction.response.edit_message(content="已取消這次兌換。", embed=None, view=None)


class RetryUploadView(discord.ui.View):
    def __init__(self, db, user_id, redemption_id):
        super().__init__(timeout=None)
        self.db, self.user_id, self.redemption_id = db, int(user_id), int(redemption_id)

    @discord.ui.button(label="🔄 重新發送上傳通知", style=discord.ButtonStyle.primary, custom_id="moon_achievement_retry_upload")
    async def retry(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 這不是你的兌換流程。", ephemeral=True)
            return
        row = self.db.execute("SELECT status, expires_at FROM moon_achievement_redemptions WHERE redemption_id=? AND user_id=?",
                              (self.redemption_id, self.user_id)).fetchone()
        if not row or row[0] != "awaiting_image":
            await interaction.response.send_message("這筆兌換目前無法重新發送。", ephemeral=True)
            return
        if datetime.datetime.fromisoformat(row[1]) <= datetime.datetime.now(UTC):
            self.db.execute("UPDATE moon_achievement_redemptions SET status='expired' WHERE redemption_id=?", (self.redemption_id,))
            self.db.commit()
            await interaction.response.send_message("⏰ 提交期限已過，這次兌換視同放棄。", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        ok = await send_upload_request(interaction.client, self.db, self.redemption_id, self.user_id)
        await interaction.followup.send(
            "📩 已重新發送上傳通知。" if ok else "⚠️ 仍無法私訊你，請先開啟機器人私訊。",
            ephemeral=True,
        )


async def send_upload_request(bot, db, redemption_id, user_id):
    row = db.execute("SELECT reward, mommy_name, character_name, status, expires_at FROM moon_achievement_redemptions WHERE redemption_id=? AND user_id=?",
                     (int(redemption_id), int(user_id))).fetchone()
    if not row or row[3] != "awaiting_image":
        return False
    try:
        user = bot.get_user(int(user_id)) or await bot.fetch_user(int(user_id))
        msg = await user.send(
            f"📩 **Moon Club 成就盲盒｜人設圖提交**\n\n"
            f"🎁 獎品：**{REWARD_NAMES[row[0]]}**\n"
            + (f"👩‍💼 負責媽咪：**{row[1]}**\n🎭 角色名稱：**{row[2]}**\n" if row[1] in MOMMY_LIST else f"🧑‍💼 製作管理員：**{row[1]}**\n")
            + "請直接在這則私訊中附上一張人設圖。每筆兌換限一張，不接受額外製作需求。\n"
            "⏳ 兌換後 24 小時會提醒一次，48 小時內未提交即視同放棄。\n"
            "📌 請自行截圖備份中獎結果。"
        )
        db.execute("UPDATE moon_achievement_redemptions SET user_dm_channel_id=? WHERE redemption_id=?",
                   (msg.channel.id, int(redemption_id)))
        db.commit()
        return True
    except Exception:
        return False


class CompleteRedemptionView(discord.ui.View):
    def __init__(self, db, redemption_id, maker_id, player_id=None):
        super().__init__(timeout=None)
        self.db, self.redemption_id, self.maker_id = db, int(redemption_id), int(maker_id)
        if player_id is not None:
            self.add_item(discord.ui.Button(
                label="查看玩家", style=discord.ButtonStyle.link,
                url=f"https://discord.com/users/{int(player_id)}"
            ))
        self.add_item(discord.ui.Button(label="✅ 已完成", style=discord.ButtonStyle.success,
                                        custom_id=f"moon_achievement_complete:{self.redemption_id}"))
        self.children[-1].callback = self.complete

    async def complete(self, interaction):
        if interaction.user.id != self.maker_id and interaction.user.id not in BOT_ADMINS:
            await interaction.response.send_message("❌ 只有負責此案件的製作者或授權管理員可以標記完成。", ephemeral=True)
            return
        row = self.db.execute("SELECT status, user_dm_channel_id, user_image_message_id FROM moon_achievement_redemptions WHERE redemption_id=?",
                              (self.redemption_id,)).fetchone()
        if not row or row[0] != "forwarded":
            await interaction.response.send_message("這筆案件已處理或目前無法完成。", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        now = datetime.datetime.now(UTC).isoformat()
        cur = self.db.execute(
            "UPDATE moon_achievement_redemptions SET status='completed', completed_at=?, completed_by=? "
            "WHERE redemption_id=? AND status='forwarded'",
            (now, interaction.user.id, self.redemption_id),
        )
        self.db.commit()
        if cur.rowcount != 1:
            await interaction.followup.send("這筆案件已由其他人處理完成。", ephemeral=True)
            return

        # 完成後刪除機器人轉交給製作者的訊息及玩家提交的人設圖訊息。
        try:
            await interaction.message.delete()
        except Exception:
            pass
        try:
            if row[1] and row[2]:
                channel = interaction.client.get_channel(int(row[1])) or await interaction.client.fetch_channel(int(row[1]))
                user_message = await channel.fetch_message(int(row[2]))
                await user_message.delete()
        except Exception:
            pass
        await interaction.followup.send("✅ 已標記完成，機器人端相關人設圖訊息已進行清理。", ephemeral=True)


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
        if reward in MOMMY_REWARDS:
            await interaction.response.edit_message(
                embed=discord.Embed(title="🎉 恭喜你抽中特殊獎品！", description=(
                    f"🎁 **{REWARD_NAMES[reward]}**\n\n請選擇負責的媽咪，再填寫角色名稱。"
                )), view=MommySelectView(self.db, self.user_id, reward))
            return
        if reward in ADMIN_PROFILE_REWARDS:
            await interaction.response.edit_message(
                embed=discord.Embed(title="🎉 恭喜你抽中隨機風格人設圖！", description=(
                    f"🎁 **{REWARD_NAMES[reward]}**\n\n請選擇由菜菜或小 E 製作。你只需要提交一張人設圖，不需要填寫角色名稱。"
                )), view=AdminMakerSelectView(self.db, self.user_id, reward))
            return

        # 努努幣獎項直接存入既有 users.money 欄位。
        money_rewards = {
            REWARD_NUNU_15000: 15000,
            REWARD_NUNU_10000: 10000,
            REWARD_NUNU_5000: 5000,
        }
        money_amount = money_rewards.get(reward)
        if money_amount is not None:
            self.db.execute(
                "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
                (str(self.user_id),)
            )
            self.db.execute(
                "UPDATE users SET money = COALESCE(money, 0) + ? WHERE user_id = ?",
                (money_amount, str(self.user_id))
            )
            self.db.commit()

        money_note = f"\n\n💰 已入帳 **+{money_amount:,} 努努幣**" if money_amount is not None else ""
        await interaction.response.edit_message(embed=discord.Embed(
            title="🎉 成就盲盒開獎！", description=(
                f"恭喜你獲得：\n\n## {REWARD_NAMES[reward]}\n\n"
                f"🎟️ 剩餘抽獎次數：**{store.get_draw_count(self.user_id)} 次**"
                f"{money_note}"
            )), view=None)


def make_achievement_box_button(db, user_id):
    if not AchievementStore(db).has_unclaimed_draw(int(user_id)):
        return None
    class AchievementBoxButton(discord.ui.Button):
        def __init__(self):
            super().__init__(label="🎁 成就盲盒", style=discord.ButtonStyle.success, row=2)
        async def callback(self, interaction):
            if interaction.user.id != int(user_id):
                await interaction.response.send_message("❌ 這不是你的成就盲盒。", ephemeral=True)
                return
            await interaction.response.edit_message(embed=build_achievement_box_embed(db, int(user_id)),
                                                    view=AchievementBoxView(db, int(user_id)))
    return AchievementBoxButton()


async def setup_achievement_redemption(bot, db):
    """在主程式啟動時呼叫一次：setup_achievement_redemption(bot, conn)。"""
    ensure_redemption_table(db)

    # 重新啟動後恢復尚待製作者完成的按鈕。
    for row in db.execute("SELECT redemption_id, mommy_id, maker_message_id FROM moon_achievement_redemptions WHERE status='forwarded' AND maker_message_id IS NOT NULL").fetchall():
        dbrow = db.execute("SELECT mommy_id FROM moon_achievement_redemptions WHERE redemption_id=?", (row[0],)).fetchone()
        bot.add_view(CompleteRedemptionView(db, row[0], dbrow[0]))

    async def on_message(message):
        if message.author.bot or not isinstance(message.channel, discord.DMChannel):
            return
        ensure_redemption_table(db)
        now = datetime.datetime.now(UTC)
        row = db.execute("""
            SELECT redemption_id, reward, mommy_name, mommy_id, character_name, expires_at
            FROM moon_achievement_redemptions
            WHERE user_id=? AND status='awaiting_image'
            ORDER BY redemption_id ASC LIMIT 1
        """, (message.author.id,)).fetchone()
        if not row:
            return
        redemption_id, reward, maker_name, maker_id, character_name, expires_at = row
        if now >= datetime.datetime.fromisoformat(expires_at):
            db.execute("UPDATE moon_achievement_redemptions SET status='expired' WHERE redemption_id=? AND status='awaiting_image'", (redemption_id,))
            db.commit()
            await message.channel.send("⏰ 提交期限已過，這次兌換視同放棄。")
            return
        if len(message.attachments) != 1:
            await message.channel.send("請直接附上一張圖片提交；每筆兌換限一張人設圖。")
            return
        attachment = message.attachments[0]
        is_image = bool(
            (attachment.content_type and attachment.content_type.startswith("image/"))
            or attachment.filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"))
        )
        if not is_image:
            await message.channel.send("請直接附上一張圖片提交；每筆兌換限一張人設圖。")
            return
        db.execute("UPDATE moon_achievement_redemptions SET status='image_received', submitted_at=?, user_dm_channel_id=?, user_image_message_id=? WHERE redemption_id=? AND status='awaiting_image'",
                   (now.isoformat(), message.channel.id, message.id, redemption_id))
        db.commit()
        try:
            maker = bot.get_user(int(maker_id)) or await bot.fetch_user(int(maker_id))
            embed = discord.Embed(title="🔔 Moon Club 圖片獎品案件", description=(
                f"👤 玩家：**{message.author.display_name}**\n"
                f"🎁 獎品：**{REWARD_NAMES[reward]}**\n"
                + (f"🎭 角色名稱：**{character_name}**\n" if character_name else "")
                + f"📌 請製作完成後按下「已完成」。"
            ))
            forwarded = await maker.send(
                embed=embed, file=await attachment.to_file(),
                view=CompleteRedemptionView(db, redemption_id, int(maker_id), message.author.id)
            )
            db.execute("UPDATE moon_achievement_redemptions SET status='forwarded', maker_message_id=?, maker_channel_id=? WHERE redemption_id=? AND status='image_received'",
                       (forwarded.id, forwarded.channel.id, redemption_id))
            db.commit()
            await message.channel.send("✅ 人設圖已成功轉交給負責製作者。製作完成後，對方會直接私訊你成品。")
        except Exception:
            db.execute("UPDATE moon_achievement_redemptions SET status='awaiting_image', submitted_at=NULL, user_image_message_id=NULL WHERE redemption_id=? AND status='image_received'", (redemption_id,))
            db.commit()
            # 轉交失敗時先清除這次提交，避免重傳後舊圖片因未被記錄而殘留。
            try:
                await message.delete()
            except Exception:
                pass
            await message.channel.send("⚠️ 人設圖轉交失敗，這次圖片沒有送達製作者。請稍後重新提交同一張人設圖；原兌換紀錄與期限不變。")

    bot.add_listener(on_message, "on_message")

    async def reminder_worker():
        await bot.wait_until_ready()
        while not bot.is_closed():
            now = datetime.datetime.now(UTC)
            rows = db.execute("SELECT redemption_id, user_id, reward, expires_at FROM moon_achievement_redemptions WHERE status='awaiting_image' AND reminded_at IS NULL").fetchall()
            for redemption_id, user_id, reward, expires_at in rows:
                created_row = db.execute("SELECT created_at FROM moon_achievement_redemptions WHERE redemption_id=?", (redemption_id,)).fetchone()
                created = datetime.datetime.fromisoformat(created_row[0])
                expiry = datetime.datetime.fromisoformat(expires_at)
                if now >= expiry:
                    db.execute("UPDATE moon_achievement_redemptions SET status='expired' WHERE redemption_id=? AND status='awaiting_image'", (redemption_id,))
                    db.commit()
                    continue
                if now >= created + datetime.timedelta(hours=REMINDER_HOURS):
                    try:
                        user = bot.get_user(int(user_id)) or await bot.fetch_user(int(user_id))
                        await user.send(f"⏰ **人設圖提交提醒**\n你抽中的獎品是：{REWARD_NAMES[reward]}。請在 48 小時期限內提交一張人設圖，逾期視同放棄。")
                    except Exception:
                        pass
                    db.execute("UPDATE moon_achievement_redemptions SET reminded_at=? WHERE redemption_id=? AND reminded_at IS NULL",
                               (now.isoformat(), redemption_id))
                    db.commit()
            await asyncio.sleep(300)

    asyncio.create_task(reminder_worker())
