# -*- coding: utf-8 -*-
# ==========================================================
# 🌙 Moon Club｜男模會館
# V14｜三選一隨機新人招募正式版
# 已保留成人男模養成核心，並正式加入三選一隨機新人招募。
# 招募候選人的普通／優秀／稀有度完全隱藏。
# ==========================================================

import json
import random
from datetime import datetime, timezone

import discord
from discord import app_commands

try:
    from database import conn, c
except ImportError:
    raise ImportError("❌ Moon Club 無法載入 database.py 的 conn、c")

try:
    from config import BOT_ADMINS
except ImportError:
    BOT_ADMINS = []

MOONCLUB_COLOR = 0xB9A7E8
MOONCLUB_TESTERS = {871398865012666389}

MODEL_ICON = "👤"   # 全系統統一成人男模圖示，不使用 👶／🍼 等寶寶圖示
OWNER_ICON = "👑"

STAT_EMOJIS = {
    "intelligence": "🧠",
    "emotion": "❤️",
    "fitness": "💪",
    "creativity": "🎨",
    "social": "✨",
}

PERSONALITY_EMOJIS = {
    "高冷": "❄️", "傲嬌": "😼", "溫柔": "🥹", "腹黑": "😈",
    "自信": "👑", "勇敢": "💪", "獨立": "🌱", "黏人": "❤️",
}

TRAINING_LIBRARY = {
    "runway": {"name": "👔 台步訓練", "stat": "social", "interest": "台步"},
    "performance": {"name": "🎭 舞台表演", "stat": "creativity", "interest": "表演"},
    "fitness": {"name": "🏋️ 體能訓練", "stat": "fitness", "interest": "健身"},
    "camera": {"name": "📸 鏡頭訓練", "stat": "intelligence", "interest": "鏡頭"},
    "communication": {"name": "💬 社交訓練", "stat": "emotion", "interest": "社交"},
}

POTENTIALS = ["💃 舞台型", "🎤 表演型", "📸 鏡頭型", "💬 社交型", "👔 時尚型"]
BACKGROUNDS = [
    "因朋友推薦而來，希望嘗試新的舞台。",
    "曾接觸過表演活動，但一直沒有正式發展。",
    "看起來很有自信，其實第一次踏進這個圈子。",
    "一直想找到屬於自己的舞台，於是來到 Moon Club。",
    "話不多，但對未來有自己的期待。",
]

RECRUIT_LIMITS = [
    (0, 2, "🌱 默默無名"),
    (100, 3, "🏠 小有名氣"),
    (250, 4, "⭐ 開始受到注意"),
    (500, 6, "🌟 知名會館"),
    (750, 8, "💎 頂尖會館"),
    (1000, 10, "👑 傳奇 Moon Club"),
]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def parse_json(value, default):
    try:
        return json.loads(value) if value else default
    except Exception:
        return default


def dump_json(value):
    return json.dumps(value, ensure_ascii=False)


def clamp(value, low, high):
    return max(low, min(high, int(value)))


def is_moonclub_tester(user_id):
    return int(user_id) in MOONCLUB_TESTERS


# ==========================================================
# 🗃️ 資料庫
# ==========================================================

def init_moonclub_tables():
    c.execute("""
        CREATE TABLE IF NOT EXISTS moonclub_players (
            user_id TEXT PRIMARY KEY,
            owner_name TEXT NOT NULL,
            owner_identity TEXT NOT NULL DEFAULT '會館老闆',
            current_model_id INTEGER,
            reputation INTEGER NOT NULL DEFAULT 0,
            model_capacity INTEGER NOT NULL DEFAULT 2,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS moonclub_modelren (
            model_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            owner_name TEXT NOT NULL,
            owner_identity TEXT NOT NULL DEFAULT '會館老闆',
            name TEXT NOT NULL,
            gender TEXT NOT NULL DEFAULT '男',
            age_year INTEGER NOT NULL DEFAULT 18,
            intelligence INTEGER NOT NULL DEFAULT 5,
            emotion INTEGER NOT NULL DEFAULT 5,
            fitness INTEGER NOT NULL DEFAULT 5,
            creativity INTEGER NOT NULL DEFAULT 5,
            social INTEGER NOT NULL DEFAULT 5,
            relationship INTEGER NOT NULL DEFAULT 0,
            affection INTEGER NOT NULL DEFAULT 0,
            fame INTEGER NOT NULL DEFAULT 0,
            model_stamina INTEGER NOT NULL DEFAULT 100,
            model_stamina_updated_at TEXT,
            personality_scores TEXT NOT NULL DEFAULT '{}',
            personalities TEXT NOT NULL DEFAULT '[]',
            interests TEXT NOT NULL DEFAULT '[]',
            interest_progress TEXT NOT NULL DEFAULT '{}',
            experiences TEXT NOT NULL DEFAULT '{}',
            hidden_rarity TEXT NOT NULL DEFAULT '普通',
            potential_direction TEXT,
            background_story TEXT,
            created_at TEXT
        )
    """)



    c.execute("""
        CREATE TABLE IF NOT EXISTS moonclub_fame_events (
            user_id TEXT NOT NULL,
            model_id INTEGER NOT NULL,
            event_id TEXT NOT NULL,
            completed_at TEXT,
            PRIMARY KEY (user_id, model_id, event_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS moonclub_memories (
            memory_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            model_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS moonclub_model_daily (
            user_id TEXT NOT NULL,
            model_id INTEGER NOT NULL,
            action_date TEXT NOT NULL,
            training_count INTEGER NOT NULL DEFAULT 0,
            interaction_count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, model_id, action_date)
        )
    """)

    # 舊資料庫可直接沿用；只補 V13 需要的新欄位，不再使用舊寶寶欄位。
    model_columns = {row[1] for row in c.execute("PRAGMA table_info(moonclub_modelren)").fetchall()}
    for column, ddl in {
        "affection": "INTEGER NOT NULL DEFAULT 0",
        "fame": "INTEGER NOT NULL DEFAULT 0",
        "model_stamina": "INTEGER NOT NULL DEFAULT 100",
        "model_stamina_updated_at": "TEXT",
        "hidden_rarity": "TEXT NOT NULL DEFAULT '普通'",
        "potential_direction": "TEXT",
        "background_story": "TEXT",
    }.items():
        if column not in model_columns:
            c.execute(f"ALTER TABLE moonclub_modelren ADD COLUMN {column} {ddl}")

    player_columns = {row[1] for row in c.execute("PRAGMA table_info(moonclub_players)").fetchall()}
    if "reputation" not in player_columns:
        c.execute("ALTER TABLE moonclub_players ADD COLUMN reputation INTEGER NOT NULL DEFAULT 0")
    if "model_capacity" not in player_columns:
        c.execute("ALTER TABLE moonclub_players ADD COLUMN model_capacity INTEGER NOT NULL DEFAULT 2")

    conn.commit()


# ==========================================================
# 📦 資料讀寫
# ==========================================================

MODEL_FIELDS = [
    "model_id", "user_id", "owner_name", "owner_identity", "name", "gender",
    "age_year", "intelligence", "emotion", "fitness", "creativity", "social",
    "relationship", "model_stamina", "model_stamina_updated_at",
    "personality_scores", "personalities", "interests", "interest_progress",
    "experiences", "hidden_rarity", "potential_direction", "background_story",
    "created_at",
]


def get_player(user_id):
    # 明確指定欄位順序，避免舊版資料表欄位順序不同造成讀錯資料。
    c.execute("""
        SELECT user_id, owner_name, owner_identity, current_model_id,
               reputation, model_capacity, created_at
        FROM moonclub_players
        WHERE user_id=?
    """, (str(user_id),))
    return c.fetchone()


def get_models(user_id):
    c.execute("SELECT * FROM moonclub_modelren WHERE user_id=? ORDER BY model_id", (str(user_id),))
    return c.fetchall()


def get_model(user_id, model_id=None):
    user_id = str(user_id)
    if model_id is None:
        player = get_player(user_id)
        if player and player[3]:
            c.execute("SELECT * FROM moonclub_modelren WHERE user_id=? AND model_id=?", (user_id, player[3]))
            row = c.fetchone()
            if row:
                return row
        c.execute("SELECT * FROM moonclub_modelren WHERE user_id=? ORDER BY model_id LIMIT 1", (user_id,))
    else:
        c.execute("SELECT * FROM moonclub_modelren WHERE user_id=? AND model_id=?", (user_id, int(model_id)))
    return c.fetchone()


def model_dict(row):
    if not row:
        return None
    columns = [x[1] for x in c.execute("PRAGMA table_info(moonclub_modelren)").fetchall()]
    return dict(zip(columns, row))


def set_current_model(user_id, model_id):
    c.execute("UPDATE moonclub_players SET current_model_id=? WHERE user_id=?", (int(model_id), str(user_id)))
    conn.commit()


def change_model(model_id, **changes):
    allowed = {
        "name", "age_year", "intelligence", "emotion", "fitness", "creativity",
        "social", "relationship", "affection", "fame", "model_stamina", "model_stamina_updated_at",
        "personality_scores", "personalities", "interests", "interest_progress",
        "experiences", "hidden_rarity", "potential_direction", "background_story",
    }
    changes = {k: v for k, v in changes.items() if k in allowed}
    if not changes:
        return
    sql = ", ".join(f"{k}=?" for k in changes)
    c.execute(f"UPDATE moonclub_modelren SET {sql} WHERE model_id=?", (*changes.values(), int(model_id)))
    conn.commit()


def add_memory(user_id, model_id, title, content):
    c.execute(
        "INSERT INTO moonclub_memories (user_id,model_id,title,content,created_at) VALUES (?,?,?,?,?)",
        (str(user_id), int(model_id), title, content, now_iso()),
    )
    conn.commit()


def club_reputation(user_id):
    player = get_player(user_id)
    return int(player[4] or 0) if player and len(player) > 4 else 0


def recruit_capacity(reputation):
    capacity, stage = 2, "🌱 默默無名"
    for need, limit, title in RECRUIT_LIMITS:
        if reputation >= need:
            capacity, stage = limit, title
    return capacity, stage


def sync_capacity(user_id):
    rep = club_reputation(user_id)
    capacity, _ = recruit_capacity(rep)
    c.execute("UPDATE moonclub_players SET model_capacity=? WHERE user_id=?", (capacity, str(user_id)))
    conn.commit()
    return capacity


def model_count(user_id):
    c.execute("SELECT COUNT(*) FROM moonclub_modelren WHERE user_id=?", (str(user_id),))
    return int(c.fetchone()[0])


def add_reputation(user_id, amount):
    before = club_reputation(user_id)
    after = clamp(before + amount, 0, 1000)
    old_cap, _ = recruit_capacity(before)
    new_cap, stage = recruit_capacity(after)
    c.execute("UPDATE moonclub_players SET reputation=?, model_capacity=? WHERE user_id=?", (after, new_cap, str(user_id)))
    conn.commit()
    return before, after, old_cap, new_cap, stage


# ==========================================================
# 🌙 初始建立
# ==========================================================

class MoonClubSetupModal(discord.ui.Modal, title="🌙 建立 Moon Club"):
    owner_name = discord.ui.TextInput(label="會館老闆名字", max_length=30)
    model1_name = discord.ui.TextInput(label="第一位新人男模名字", max_length=30)
    model2_name = discord.ui.TextInput(label="第二位新人男模名字", max_length=30)

    async def on_submit(self, interaction):
        user_id = str(interaction.user.id)
        owner = self.owner_name.value.strip()
        names = [self.model1_name.value.strip(), self.model2_name.value.strip()]

        if not owner or not all(names):
            await interaction.response.send_message("❌ 請完整填寫所有名字。", ephemeral=True)
            return
        if names[0] == names[1]:
            await interaction.response.send_message("❌ 兩位新人男模的名字不能相同。", ephemeral=True)
            return

        c.execute("DELETE FROM moonclub_memories WHERE user_id=?", (user_id,))
        c.execute("DELETE FROM moonclub_model_daily WHERE user_id=?", (user_id,))
        c.execute("DELETE FROM moonclub_modelren WHERE user_id=?", (user_id,))

        ids = []
        # 初始兩位也是成人新人：從基礎開始養成，並各自保有隱藏潛力。
        for name in names:
            candidate = generate_candidate()
            scores = {p: random.randint(0, 8) for p in PERSONALITY_EMOJIS}
            scores[candidate["personality"]] += 8
            stats = candidate["stats"]
            c.execute("""
                INSERT INTO moonclub_modelren
                (user_id,owner_name,owner_identity,name,gender,age_year,
                 intelligence,emotion,fitness,creativity,social,relationship,affection,
                 model_stamina,personality_scores,personalities,interests,
                 interest_progress,experiences,hidden_rarity,potential_direction,
                 background_story,created_at)
                VALUES (?,?,?,?, '男',?,?,?,?,?,?,0,0,100,?,'[]','[]','{}','{}',?,?,?,?)
            """, (
                user_id, owner, "會館老闆", name, candidate["age"],
                stats["intelligence"], stats["emotion"], stats["fitness"],
                stats["creativity"], stats["social"], dump_json(scores),
                candidate["rarity"], candidate["potential"], candidate["background"], now_iso(),
            ))
            model_id = c.lastrowid
            ids.append(model_id)
            add_memory(user_id, model_id, "✨ 加入 Moon Club", f"{name} 成為 Moon Club 的首批簽約男模，從新人階段開始培養。")

        c.execute("""
            INSERT INTO moonclub_players
            (user_id,owner_name,owner_identity,current_model_id,reputation,model_capacity,created_at)
            VALUES (?,?,'會館老闆',?,0,2,?)
            ON CONFLICT(user_id) DO UPDATE SET
                owner_name=excluded.owner_name,
                owner_identity='會館老闆',
                current_model_id=excluded.current_model_id,
                reputation=0,
                model_capacity=2
        """, (user_id, owner, ids[0], now_iso()))
        conn.commit()

        embed = discord.Embed(
            title="🎉 Moon Club 正式開幕！",
            description=(
                f"{OWNER_ICON} 會館老闆：**{owner}**\n"
                f"👥 初始簽約：**2 / 2**\n\n"
                f"① {MODEL_ICON} **{names[0]}**｜🌱 新人\n"
                f"② {MODEL_ICON} **{names[1]}**｜🌱 新人"
            ),
            color=MOONCLUB_COLOR,
        )
        await interaction.response.send_message(embed=embed, view=MoonClubHomeView(), ephemeral=True)


class StartMoonClubView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="🌙 建立 Moon Club", style=discord.ButtonStyle.success)
    async def start(self, interaction, button):
        await interaction.response.send_modal(MoonClubSetupModal())


# ==========================================================
# 🏠 主畫面
# ==========================================================

def relationship_name(value):
    if value >= 850:
        return "💕 無可取代"
    if value >= 600:
        return "❤️ 深厚信任"
    if value >= 350:
        return "😊 親近"
    if value >= 100:
        return "🌱 熟悉"
    return "🤍 剛認識"

def affection_name(value):
    if value >= 1000:
        return "💎 專屬關係"
    if value >= 800:
        return "🔥 深度親密"
    if value >= 600:
        return "💕 親密"
    if value >= 400:
        return "💗 曖昧"
    if value >= 200:
        return "😊 熟悉"
    return "🤍 認識中"


async def build_home_embed(user_id):
    player = get_player(user_id)
    model = model_dict(get_model(user_id))
    if not player or not model:
        return None

    rep = club_reputation(user_id)
    cap, stage = recruit_capacity(rep)
    count = model_count(user_id)
    personalities = parse_json(model.get("personalities"), [])
    interests = parse_json(model.get("interests"), [])

    embed = discord.Embed(
        title="🌙 Moon Club｜男模會館",
        description=(
            f"{OWNER_ICON} 會館老闆：**{player[1]}**\n"
            f"{MODEL_ICON} 目前培養：**{model['name']}**（{model['age_year']} 歲）\n\n"
            f"🏛️ 知名度：**{rep} / 1000**｜{stage}\n"
            f"👥 簽約名額：**{count} / {cap}**\n"
            f"⚡ 個人體力：**{model.get('model_stamina', 100)} / 100**\n"
            f"💕 默契：**{model['relationship']} / 1000**（{relationship_name(model['relationship'])}）\n"
            f"❤️ 好感度：**{model.get('affection', 0)} / 1000**（{affection_name(model.get('affection', 0))}）\n\n"
            f"😈 個性：{'、'.join(personalities) if personalities else '🌱 還在形成'}\n"
            f"🎭 專長：{'、'.join(interests) if interests else '🌱 尚未正式形成'}"
        ),
        color=MOONCLUB_COLOR,
    )
    return embed



# ==========================================================
# 🌟 知名度系統｜0～1000｜FAME_01～16
# ==========================================================

def fame_name(value):
    value = int(value or 0)
    if value >= 1000: return "💎 頂級知名"
    if value >= 800: return "👑 當紅人氣"
    if value >= 600: return "🔥 人氣上升"
    if value >= 400: return "🌟 嶄露頭角"
    if value >= 200: return "✨ 小有名氣"
    return "🌱 默默無名"

FAME_EVENTS = [
    ("FAME_01",0, "📸 第一次被注意到", "完成公開工作後，有人因為記得他的表現，第一次主動詢問能不能合照。這不是爆紅，只是努力第一次被陌生人看見。", 20),
    ("FAME_02",30, "💬 有人記得他的名字", "再次公開活動時，有陌生人主動叫出他的名字，證明上一次的曝光沒有消失。", 25),
    ("FAME_03",100, "🎭 小型公開機會", "因為累積的工作表現，他收到規模更大的小型公開活動邀請。", 35),
    ("FAME_04",200, "📱 開始有人討論", "活動結束後，零星討論開始出現：有人詢問他的名字，也有人說這位新人表現不錯。", 30),
    ("FAME_05",250, "📸 非工作場合被認出", "只是普通外出，卻有人猶豫後認出他。知名度開始離開單一活動現場。", 25),
    ("FAME_06",250, "🤝 第一個正式合作", "因為能力與累積經歷，他收到第一個正式合作邀請。合作方向會與個人特質有關。", 50),
    ("FAME_07",400, "📰 第一次正式介紹", "他第一次以『值得注意的新面孔』被正式介紹，名字開始進入更大的視野。", 60),
    ("FAME_08",450, "🌟 特別工作邀請", "這次不是單純因為人氣，而是有人真正看中了他的能力與個人特色。", 70),
    ("FAME_09",500, "💬 固定支持者", "活動裡開始出現熟悉的面孔。有人記得他的行程，也有人持續關注他的發展。", 50),
    ("FAME_10",600, "🔥 重要活動的關注", "這次活動中，他明顯發現有不少人是專門為他而來。人氣是前面一次次曝光累積的結果。", 70),
    ("FAME_11",650, "🌟 培養能力受到注意", "外界開始注意到他的成長，也開始有人討論 Moon Club 是如何把新人一步步培養起來的。", 0),
    ("FAME_12",800, "📸 明顯的現場人氣", "活動開始前就有人等待。這一次，他清楚感覺到真的有人是為了自己而來。", 50),
    ("FAME_13",800, "👥 新人開始注意 Moon Club", "隨著第一位男模的成長，你的培養方式開始被看見。有人表達想加入 Moon Club 的意願。", 0),
    ("FAME_14",850, "🤝 更大型的合作", "能力、人氣與過去經歷共同累積後，他收到規格更高的合作機會。", 80),
    ("FAME_15",1000, "👑 Moon Life 代表人物", "首次達到知名度 1000。這不是普通事件，而是永久里程碑：他已成為 Moon Life 的代表級人物。", 0),
    ("FAME_16",1000, "🌟 團隊進入新階段", "第一位頂級知名男模的成功，讓 Moon Club 正式進入新的團隊發展階段。", 0),
]

def fame_completed(user_id, model_id, event_id):
    c.execute("SELECT 1 FROM moonclub_fame_events WHERE user_id=? AND model_id=? AND event_id=?",
              (str(user_id), int(model_id), event_id))
    return c.fetchone() is not None

def fame_mark_completed(user_id, model_id, event_id):
    c.execute("""INSERT OR IGNORE INTO moonclub_fame_events (user_id,model_id,event_id,completed_at)
                 VALUES (?,?,?,?)""", (str(user_id), int(model_id), event_id, now_iso()))
    conn.commit()

def next_fame_event(user_id, model):
    fame = int(model.get("fame", 0))
    completed = {row[0] for row in c.execute(
        "SELECT event_id FROM moonclub_fame_events WHERE user_id=? AND model_id=?",
        (str(user_id), int(model["model_id"]))).fetchall()}
    for event in FAME_EVENTS:
        event_id, required, title, story, gain = event
        if event_id in completed:
            continue
        if fame >= required:
            if event_id == "FAME_02" and "FAME_01" not in completed: continue
            if event_id == "FAME_03" and not {"FAME_01","FAME_02"}.issubset(completed): continue
            if event_id == "FAME_11" and "FAME_10" not in completed: continue
            if event_id == "FAME_12" and "FAME_10" not in completed: continue
            if event_id == "FAME_13" and "FAME_11" not in completed: continue
            if event_id == "FAME_15" and fame < 1000: continue
            if event_id == "FAME_16" and "FAME_15" not in completed: continue
            return event
    return None

class FameChoiceView(discord.ui.View):
    def __init__(self, event):
        super().__init__(timeout=180)
        self.event = event
        for label in ["❤️ 接受並把握機會", "🤍 穩定累積", "📚 先做好準備"]:
            button = discord.ui.Button(label=label, style=discord.ButtonStyle.primary if label.startswith("❤️") else discord.ButtonStyle.secondary)
            async def callback(interaction, label=label):
                await self.choose(interaction, label)
            button.callback = callback
            self.add_item(button)

    async def choose(self, interaction, label):
        user_id = str(interaction.user.id)
        model = model_dict(get_model(user_id))
        event_id, required, title, story, gain = self.event
        before = int(model.get("fame", 0))
        if event_id == "FAME_15":
            after = 1000
        else:
            after = clamp(before + gain, 0, 1000)
        change_model(model["model_id"], fame=after)
        fame_mark_completed(user_id, model["model_id"], event_id)
        add_memory(user_id, model["model_id"], title,
                   f"{story}\n選擇：{label}。🌟 知名度 {before} → {after}。")
        await interaction.response.edit_message(
            embed=discord.Embed(title=title,
                description=f"👤 **{model['name']}**\n{story}\n\n✨ 你的選擇：**{label}**\n🌟 知名度：**{before} → {after} / 1000**（{fame_name(after)}）",
                color=MOONCLUB_COLOR),
            view=BackHomeView())

class FameView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(label="🌟 查看下一個事業事件", style=discord.ButtonStyle.success)
    async def open_event(self, interaction, button):
        user_id = str(interaction.user.id)
        model = model_dict(get_model(user_id))
        if not model:
            await interaction.response.send_message("❌ 目前沒有男模。", ephemeral=True); return
        event = next_fame_event(user_id, model)
        if not event:
            await interaction.response.send_message("🌙 目前沒有符合前因後果的知名度事件。先繼續培訓、工作與累積經歷吧。", ephemeral=True); return
        _, required, title, story, _ = event
        await interaction.response.edit_message(
            embed=discord.Embed(title=title, description=f"👤 **{model['name']}**\n🌟 知名度門檻：{required}\n\n{story}\n\n請選擇接下來的態度：", color=MOONCLUB_COLOR),
            view=FameChoiceView(event))

    @discord.ui.button(label="⬅️ 回 Moon Club", style=discord.ButtonStyle.secondary)
    async def back(self, interaction, button):
        await refresh_home(interaction)

class MoonClubHomeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="🏠 會館", style=discord.ButtonStyle.primary, row=0)
    async def home(self, interaction, button):
        await refresh_home(interaction)

    @discord.ui.button(label="👤 男模資料", style=discord.ButtonStyle.secondary, row=0)
    async def model(self, interaction, button):
        model = model_dict(get_model(str(interaction.user.id)))
        if not model:
            await interaction.response.send_message("❌ 目前沒有男模。", ephemeral=True)
            return
        personalities = parse_json(model["personalities"], [])
        interests = parse_json(model["interests"], [])
        embed = discord.Embed(
            title=f"{MODEL_ICON} {model['name']}｜男模資料",
            description=(
                f"🎂 年齡：**{model['age_year']} 歲**\n"
                f"💕 默契：**{model['relationship']} / 1000**\n"
                f"❤️ 好感度：**{model.get('affection', 0)} / 1000**（{affection_name(model.get('affection', 0))}）\n"
                f"🌟 知名度：**{model.get('fame', 0)} / 1000**（{fame_name(model.get('fame', 0))}）\n"
                f"⚡ 體力：**{model.get('model_stamina', 100)} / 100**\n"
                f"🎭 潛力方向：{model.get('potential_direction') or '尚未確認'}\n\n"
                f"🧠 智慧：{model['intelligence']}\n"
                f"❤️ 情感：{model['emotion']}\n"
                f"💪 體能：{model['fitness']}\n"
                f"🎨 創造：{model['creativity']}\n"
                f"✨ 社交：{model['social']}\n\n"
                f"😈 個性：{'、'.join(personalities) if personalities else '正在形成'}\n"
                f"🌟 專長：{'、'.join(interests) if interests else '尚未形成'}"
            ),
            color=MOONCLUB_COLOR,
        )
        await interaction.response.edit_message(embed=embed, view=BackHomeView())

    @discord.ui.button(label="🔄 切換男模", style=discord.ButtonStyle.primary, row=0)
    async def switch_model(self, interaction, button):
        await interaction.response.edit_message(
            embed=discord.Embed(title="👥 選擇要培養的男模", description="請選擇目前要操作的男模。", color=MOONCLUB_COLOR),
            view=ModelSelectView(str(interaction.user.id)),
        )

    @discord.ui.button(label="🏋️ 培訓", style=discord.ButtonStyle.success, row=1)
    async def training(self, interaction, button):
        await interaction.response.edit_message(
            embed=discord.Embed(title="🏋️ 男模培訓", description="選擇一種成人職涯培訓方向。", color=MOONCLUB_COLOR),
            view=TrainingView(),
        )

    @discord.ui.button(label="💬 互動", style=discord.ButtonStyle.secondary, row=1)
    async def interaction(self, interaction, button):
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="💬 日常互動",
                description="和目前培養的男模進行互動，提升默契。",
                color=MOONCLUB_COLOR,
            ),
            view=InteractionView(),
        )

    @discord.ui.button(label="💗 約會", style=discord.ButtonStyle.danger, row=1)
    async def date(self, interaction, button):
        user_id = str(interaction.user.id)
        model = model_dict(get_model(user_id))
        if not model:
            await interaction.response.send_message("❌ 目前沒有可約會的男模。", ephemeral=True)
            return
        affection = model.get("affection", 0)
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="💗 約會",
                description=(
                    f"👤 **{model['name']}**\n"
                    f"❤️ 好感度：**{affection} / 1000**（{affection_name(affection)}）\n\n"
                    "好感度越高，會解鎖更多私人與親密的約會內容。"
                ),
                color=MOONCLUB_COLOR,
            ),
            view=DateView(),
        )

    @discord.ui.button(label="🌟 知名度", style=discord.ButtonStyle.primary, row=2)
    async def fame(self, interaction, button):
        user_id = str(interaction.user.id)
        model = model_dict(get_model(user_id))
        if not model:
            await interaction.response.send_message("❌ 目前沒有男模。", ephemeral=True); return
        await interaction.response.edit_message(
            embed=discord.Embed(title="🌟 知名度", description=f"👤 **{model['name']}**\n🌟 知名度：**{model.get('fame',0)} / 1000**（{fame_name(model.get('fame',0))}）\n\n知名度事件會依照目前數值與過去經歷循序解鎖。", color=MOONCLUB_COLOR),
            view=FameView())

    @discord.ui.button(label="🎴 招募新人", style=discord.ButtonStyle.success, row=2)
    async def recruit(self, interaction, button):
        await start_recruitment(interaction)

    @discord.ui.button(label="📖 職涯紀錄", style=discord.ButtonStyle.secondary, row=2)
    async def memories(self, interaction, button):
        user_id = str(interaction.user.id)
        model = model_dict(get_model(user_id))
        c.execute("""
            SELECT title, content FROM moonclub_memories
            WHERE user_id=? AND model_id=?
            ORDER BY memory_id DESC LIMIT 20
        """, (user_id, model["model_id"]))
        rows = c.fetchall()
        desc = "\n\n".join(f"**{title}**\n{content}" for title, content in rows) or "目前還沒有職涯紀錄。"
        await interaction.response.edit_message(
            embed=discord.Embed(title=f"📖 {model['name']}的職涯紀錄", description=desc[:4000], color=MOONCLUB_COLOR),
            view=BackHomeView(),
        )


class BackHomeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="⬅️ 回 Moon Club", style=discord.ButtonStyle.secondary)
    async def back(self, interaction, button):
        await refresh_home(interaction)


async def refresh_home(interaction):
    embed = await build_home_embed(str(interaction.user.id))
    await interaction.response.edit_message(embed=embed, view=MoonClubHomeView())


class ModelSelectView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = str(user_id)
        models = [model_dict(row) for row in get_models(user_id)]
        options = [
            discord.SelectOption(
                label=model["name"],
                description=f"{model['age_year']}歲｜默契 {model['relationship']}/1000",
                value=str(model["model_id"]),
                emoji="👤",
            )
            for model in models[:25]
        ]
        if options:
            select = discord.ui.Select(placeholder="選擇男模", options=options)
            select.callback = self.select_callback
            self.add_item(select)

    async def select_callback(self, interaction):
        model_id = int(interaction.data["values"][0])
        set_current_model(self.user_id, model_id)
        await refresh_home(interaction)


# ==========================================================
# 🏋️ 成人培訓
# ==========================================================

def daily_row(user_id, model_id):
    today = datetime.now(timezone.utc).date().isoformat()
    c.execute("""
        INSERT INTO moonclub_model_daily (user_id,model_id,action_date,training_count,interaction_count)
        VALUES (?,?,?,0,0)
        ON CONFLICT(user_id,model_id,action_date) DO NOTHING
    """, (str(user_id), int(model_id), today))
    c.execute("SELECT training_count,interaction_count FROM moonclub_model_daily WHERE user_id=? AND model_id=? AND action_date=?",
              (str(user_id), int(model_id), today))
    return c.fetchone()


def update_personality(model):
    scores = parse_json(model["personality_scores"], {})
    ranked = sorted(scores, key=lambda x: scores[x], reverse=True)
    personalities = [x for x in ranked[:2] if scores.get(x, 0) >= 8]
    change_model(model["model_id"], personalities=dump_json(personalities))


def apply_training(user_id, key):
    model = model_dict(get_model(user_id))
    data = TRAINING_LIBRARY[key]
    training_count, _ = daily_row(user_id, model["model_id"])
    if training_count >= 3:
        return None, "❌ 今天已完成 3 次培訓，讓他休息一下吧。"

    stat = data["stat"]
    gain = random.randint(2, 5)
    updates = {
        stat: clamp(model[stat] + gain, 0, 100),
        "model_stamina": clamp(model.get("model_stamina", 100) - 10, 0, 100),
    }

    progress = parse_json(model["interest_progress"], {})
    interest = data["interest"]
    progress[interest] = progress.get(interest, 0) + gain
    interests = parse_json(model["interests"], [])
    if progress[interest] >= 20 and interest not in interests:
        interests.append(interest)

    scores = parse_json(model["personality_scores"], {})
    for personality in scores:
        scores[personality] = scores.get(personality, 0) + random.randint(0, 1)

    updates.update({
        "interest_progress": dump_json(progress),
        "interests": dump_json(interests),
        "personality_scores": dump_json(scores),
    })
    change_model(model["model_id"], **updates)
    update_personality(model_dict(get_model(user_id)))

    c.execute("""
        UPDATE moonclub_model_daily
        SET training_count=training_count+1
        WHERE user_id=? AND model_id=? AND action_date=?
    """, (str(user_id), model["model_id"], datetime.now(timezone.utc).date().isoformat()))

    rep_gain = 2 if random.random() < 0.35 else 0
    if rep_gain:
        add_reputation(user_id, rep_gain)

    add_memory(
        user_id, model["model_id"], data["name"],
        f"{model['name']}完成一次{data['name']}，{STAT_EMOJIS[stat]} {stat} +{gain}。"
    )
    conn.commit()
    return (model, data, stat, gain, rep_gain), None


class TrainingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    async def run(self, interaction, key):
        result, error = apply_training(str(interaction.user.id), key)
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return
        model, data, stat, gain, rep_gain = result
        extra = f"\n🏛️ Moon Club 知名度 +{rep_gain}" if rep_gain else ""
        await interaction.response.edit_message(
            embed=discord.Embed(
                title=data["name"],
                description=f"👤 **{model['name']}** 完成培訓！\n{STAT_EMOJIS[stat]} 能力 +**{gain}**{extra}",
                color=MOONCLUB_COLOR,
            ),
            view=BackHomeView(),
        )

    @discord.ui.button(label="👔 台步", style=discord.ButtonStyle.primary)
    async def runway(self, interaction, button): await self.run(interaction, "runway")

    @discord.ui.button(label="🎭 表演", style=discord.ButtonStyle.primary)
    async def performance(self, interaction, button): await self.run(interaction, "performance")

    @discord.ui.button(label="🏋️ 體能", style=discord.ButtonStyle.success)
    async def fitness(self, interaction, button): await self.run(interaction, "fitness")

    @discord.ui.button(label="📸 鏡頭", style=discord.ButtonStyle.secondary)
    async def camera(self, interaction, button): await self.run(interaction, "camera")

    @discord.ui.button(label="💬 社交", style=discord.ButtonStyle.secondary)
    async def communication(self, interaction, button): await self.run(interaction, "communication")


# ==========================================================
# 💬 成人日常互動
# ==========================================================

INTERACTIONS = [
    ("☕ 一起喝咖啡", "在安靜的時間聊聊最近的想法。"),
    ("🍽️ 一起吃飯", "用一頓飯交換彼此最近的近況。"),
    ("🗣️ 深度聊天", "聊聊未來與目前的壓力。"),
    ("🎬 看一場作品", "一起觀看表演或時尚作品並交流感想。"),
]


class InteractionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    async def run(self, interaction, index):
        user_id = str(interaction.user.id)
        model = model_dict(get_model(user_id))
        _, interaction_count = daily_row(user_id, model["model_id"])
        if interaction_count >= 3:
            await interaction.response.send_message("❌ 今天已經進行很多互動了，明天再繼續吧。", ephemeral=True)
            return
        name, text = INTERACTIONS[index]
        gain = random.randint(15, 35)
        before = model["relationship"]
        after = clamp(before + gain, 0, 1000)
        change_model(model["model_id"], relationship=after)
        c.execute("""
            UPDATE moonclub_model_daily
            SET interaction_count=interaction_count+1
            WHERE user_id=? AND model_id=? AND action_date=?
        """, (user_id, model["model_id"], datetime.now(timezone.utc).date().isoformat()))
        add_memory(user_id, model["model_id"], name, f"{text} 默契 {before} → {after}。")
        await interaction.response.edit_message(
            embed=discord.Embed(
                title=name,
                description=f"👤 **{model['name']}**\n{text}\n\n💕 默契：**{before} → {after} / 1000**",
                color=MOONCLUB_COLOR,
            ),
            view=BackHomeView(),
        )

    @discord.ui.button(label="☕ 咖啡", style=discord.ButtonStyle.primary)
    async def coffee(self, interaction, button): await self.run(interaction, 0)

    @discord.ui.button(label="🍽️ 吃飯", style=discord.ButtonStyle.primary)
    async def meal(self, interaction, button): await self.run(interaction, 1)

    @discord.ui.button(label="🗣️ 聊天", style=discord.ButtonStyle.secondary)
    async def chat(self, interaction, button): await self.run(interaction, 2)

    @discord.ui.button(label="🎬 一起看作品", style=discord.ButtonStyle.secondary)
    async def show(self, interaction, button): await self.run(interaction, 3)


# ==========================================================
# 💗 約會／好感度系統｜0～1000
# ==========================================================

DATE_OPTIONS = [
    (0, "☕ 輕鬆見面", "你們找了一個不太吵的地方坐下。從近況聊到彼此的習慣，氣氛比剛認識時自然許多。", (18, 35)),
    (200, "🌆 外出約會", "傍晚的街道比會館安靜。他刻意放慢腳步配合你，偶爾回頭確認你是不是還在身邊。", (25, 45)),
    (400, "💋 親密約會", "氣氛變得比平常更曖昧。靠近時，你們沒有再刻意保持距離；在彼此都願意的情況下，一個吻讓原本的關係明顯跨過了新的界線。", (30, 55)),
    (600, "🌙 私人約會", "他把時間留給了你們兩個人。長時間的擁抱、親吻與貼近，讓原本只存在於玩笑裡的曖昧逐漸變得真實。當氣氛升溫時，他仍停下來確認你的心意。", (35, 60)),
    (800, "🔥 私人時光", "房門關上後，外面的聲音像被隔絕了。他靠近你，低聲說著只有你們聽得見的話。衣著不再像剛出門時那樣整齊，親吻與親密的觸碰讓夜晚變得格外漫長；接下來的私人時光，留給你們自己。🌙", (40, 70)),
    (1000, "💎 專屬約會", "這已經不是普通的約會。你們之間有足夠的信任，也知道彼此真正想要的是什麼。他把你拉進懷裡，長久地吻著你，然後在再次確認彼此心意後，讓這個夜晚只屬於你們兩個人。🌙", (45, 80)),
]

# V17｜DATE_31～60：兩階完整隨機劇情（每次三選一）
DATE_EVENTS = {
400: [
("DATE_31｜🤝 第一次主動牽手","過馬路時他沒有立刻放開你的手。你們都知道理由早已不只是人很多。",[("❤️ 反過來握住他的手",30),("😈 問他打算牽多久",35),("😊 靜靜讓他牽著",32)]),
("DATE_32｜🌃 捨不得結束的夜晚","明明已經說過再見，你們卻都還站在原地。他低聲說：『其實……再走一下也可以。』",[("❤️ 我也還不想回去",35),("😄 問他是不是捨不得",38),("🌙 提議繼續聊天",30)]),
("DATE_33｜💋 差一點吻上的距離","他靠得很近，兩個人同時安靜下來。他沒有越過界線，只等你的反應。",[("❤️ 看著他不躲開",40),("😈 問他想做什麼",38),("😳 主動拉開距離",18)]),
("DATE_34｜🌧️ 同一把傘","雨突然落下，他撐開傘朝你伸手：『過來。』肩膀在狹小的傘下不時碰在一起。",[("🤍 主動靠近他",35),("😄 問他是不是故意靠近",32),("☔ 把傘往他那邊移",30)]),
("DATE_35｜😈 第一次明顯吃醋","你提起另一個人後，他突然安靜了許多。你問怎麼了，他只說『沒什麼。』",[("😈 問他是不是吃醋",42),("❤️ 告訴他不用在意",35),("😄 故意繼續逗他",25)]),
("DATE_36｜🛋️ 第一次到私人空間","約會結束很晚，他在門口猶豫後問：『要不要……進來坐一下？』",[("☕ 進去喝杯東西",35),("❤️ 問他是不是常帶人回來",38),("😊 約好下次再來",30)]),
("DATE_37｜🤍 突然的擁抱","你情緒低落時，他沒有急著說教，只是把你拉進懷裡：『不用每次都假裝沒事。』",[("❤️ 回抱他",42),("😳 問他突然怎麼了",35),("🤍 靜靜待在他懷裡",40)]),
("DATE_38｜🌙 深夜的真心話","夜深後，他忽然問：『你覺得……我們現在算什麼？』",[("❤️ 問他希望是什麼",45),("😄 要他先回答",42),("💬 認真說出感覺",40)]),
("DATE_39｜💋 第一個吻","他停在你面前，先低聲問：『我可以吻你嗎？』",[("❤️ 點頭答應",50),("😈 你覺得呢？",42),("😊 再等等",28)]),
("DATE_40｜🍷 約會後的試探","晚餐後他看著你說：『今天……你看起來很好。』",[("❤️ 稱讚回去",38),("😈 問他是不是故意說這種話",42),("😳 害羞地轉開話題",30)]),
("DATE_41｜🎠 人群中的保護","人潮把你們沖散一點，他立刻拉住你：『跟著我。』一路都沒有放開。",[("❤️ 十指交扣",45),("😄 問他是不是太誇張",32),("🤍 輕輕握住他的手",40)]),
("DATE_42｜🌃 夜景下的靠近","風有點冷，他把外套披到你身上：『別感冒。』",[("❤️ 拉著他一起穿",42),("😈 問他是不是只對你這樣",45),("🤍 靠近他避風",40)]),
("DATE_43｜📸 只有兩人的照片","他說上次的合照還留著，這次又主動站到你身旁：『再拍一張？』",[("❤️ 靠近一起拍",45),("😄 問他是不是要當桌布",48),("📸 幫他拍個人照",35)]),
("DATE_44｜💭 他開始主動想念你","見面前他先傳訊息：『你今天會來吧？』他承認昨天就在想今天。",[("❤️ 我也是",48),("😈 問他是不是想你",45),("😊 說自己很期待",42)]),
("DATE_45｜❤️ 差一點說出口的告白","告別前他說有件事想告訴你，沉默很久又想算了。",[("❤️ 告訴他可以說",55),("😈 直接問是不是喜歡你",58),("🤍 告訴他不用急",45)]),
],
600: [
("DATE_46｜🌙 不想結束的私人約會","他看著時間說今天過得太快了，明顯還不想結束今晚。",[("❤️ 再陪他一下",40),("😈 問他是不是捨不得",45),("🤍 靜靜靠在他身邊",42)]),
("DATE_47｜💋 久別後的見面","忙了一段時間後終於見面，他遠遠看到你就張開雙手。",[("❤️ 主動抱住他",48),("😈 問他有多想",45),("😊 說你也一樣",42)]),
("DATE_48｜🛋️ 窩在一起的午後","電影播到一半，你發現他根本沒在看，因為視線一直停在你身上。",[("😈 問他到底在看什麼",48),("❤️ 靠到他身邊",45),("🎬 拉他回去看電影",40)]),
("DATE_49｜🌃 深夜散步","你們自然牽著手，他捏了捏你的手指：『我喜歡這樣。』",[("❤️ 十指交扣",48),("😄 問他喜歡什麼",45),("🤍 靠近他",42)]),
("DATE_50｜💋 安靜下來後的吻","話題慢慢停下，他靠近前仍先問：『……我可以嗎？』",[("❤️ 主動吻他",55),("💋 點頭",52),("😈 故意不回答",30)]),
("DATE_51｜🌧️ 留在這裡避雨","雨越下越大，他說現在回去不方便，問你要不要再待一會。",[("❤️ 留下來陪他",45),("😈 問他是不是故意的",48),("☕ 一起準備熱飲",42)]),
("DATE_52｜🤍 他在你面前很放鬆","他說只有和你在一起時，不用一直想那麼多。",[("❤️ 讓他一直做自己",52),("🤍 靜靜陪著他",48),("💬 問他平常壓力",55)]),
("DATE_53｜🌙 睡前的電話","他說沒什麼事，只是想聽聽你的聲音。",[("❤️ 陪他聊到想睡",50),("😈 問他是不是每天想你",52),("😊 說你也會想他",48)]),
("DATE_54｜🍳 第一次一起準備早餐","廚房裡忙成一團，他從背後靠近看你的做法。",[("😂 把事情交給他",40),("❤️ 一起完成",48),("😈 叫他不要靠太近",45)]),
("DATE_55｜💗 被朋友問起關係","朋友問你們到底是什麼關係，他先看向你，沒有急著回答。",[("❤️ 要他回答",55),("😈 反問朋友覺得呢",48),("🤍 說正在慢慢了解",50)]),
("DATE_56｜🌃 夜晚的擁抱","告別時他抱著你比平常久，明顯捨不得放手。",[("❤️ 抱得更緊",55),("😈 問他怎麼還不放開",50),("🤍 靜靜待著",48)]),
("DATE_57｜🎁 只有你知道的習慣","你特別準備了他喜歡的東西，他愣住：『你怎麼知道？』",[("❤️ 因為我有記得",55),("😄 問他是不是感動",45),("🎁 說以後也會記得",50)]),
("DATE_58｜💋 親吻後的沉默","親吻結束後距離仍很近，他輕聲問你怎麼突然安靜。",[("❤️ 再靠近他",55),("😳 說不知道該說什麼",50),("😈 問他是不是還想繼續",52)]),
("DATE_59｜🌙 留到很晚的夜晚","原本只見一會，最後聊天看電影吃東西，一轉眼已經很晚。",[("❤️ 說時間過得很快",55),("😈 問他是不是故意拖時間",52),("🌙 說自己也不想離開",50)]),
("DATE_60｜❤️ 真正確認彼此的重要","他說以前習慣一個人，但現在開始習慣有你了。",[("❤️ 告訴他你也一樣",65),("🤍 靜靜握住他的手",58),("😈 問他是不是在告白",62)]),
]
}

# V18｜🔥 DATE_61～75 深度親密期、💎 DATE_76～90 專屬關係
DATE_EVENTS[800] = [
    ('DATE_61｜🔥 門關上之後', '回到私人空間後，他站在你面前，低聲問你知道他今天一直在忍什麼嗎？', [('❤️ 主動靠近他', 65), ('😈 問他在忍什麼', 60), ('🤍 抱住他', 55)]),
    ('DATE_62｜💋 停不下來的吻', '原本只是告別前的一個吻，分開後他又輕聲問：『……再一次？』', [('❤️ 點頭', 68), ('😈 問他不是要走了嗎', 62), ('🤍 靠著他不說話', 50)]),
    ('DATE_63｜🌙 留宿的夜晚', '時間很晚了，他看著你說：『今天……別急著走，好嗎？』', [('❤️ 答應留下', 65), ('😈 問他是不是捨不得', 70), ('🤍 再陪他一會', 55)]),
    ('DATE_64｜👔 曖昧的距離', '剛才的擁抱讓衣服有些凌亂，他替你整理時動作慢了下來，問自己是不是太靠近。', [('❤️ 說沒有', 65), ('😈 問他希望靠多近', 68), ('🤍 幫他整理衣服', 60)]),
    ('DATE_65｜🔥 明顯的佔有欲', '你提到最近有人對你有興趣，他沉默後問：『……那你怎麼回答？』', [('❤️ 說比較在意他', 72), ('😈 問他是不是又吃醋', 65), ('🤍 安撫他', 60)]),
    ('DATE_66｜🌃 深夜不想睡', '夜已經很深，他靠著你說：『我不想睡。』', [('❤️ 再陪他', 65), ('😈 問是不是不想結束今晚', 68), ('🌙 一起安靜休息', 58)]),
    ('DATE_67｜💋 他先停下來', '氣氛升溫時，他忽然停下來確認你的感受：『你確定嗎？』', [('❤️ 明確告訴他可以', 75), ('🤍 說慢一點', 72), ('😊 想先休息一下', 55)]),
    ('DATE_68｜🛋️ 窩在他懷裡', '你已經習慣自然地靠進他懷裡，他笑問：『現在這麼自然？』', [('❤️ 說因為是他', 70), ('😈 問他不喜歡嗎', 62), ('🤍 繼續靠著', 65)]),
    ('DATE_69｜🌧️ 整晚的雨聲', '窗外下著雨，你們安靜靠在一起，他說：『如果每天都能這樣就好了。』', [('❤️ 說那就常常這樣', 68), ('😈 問是不是想把你留下來', 72), ('🤍 握住他的手', 65)]),
    ('DATE_70｜💗 只想看著你', '你發現他一直看著你，問他在看什麼，他直接回答：『你。』', [('😳 問看不膩嗎', 65), ('❤️ 主動靠近他', 70), ('😈 問是不是又在想壞事', 62)]),
    ('DATE_71｜🤍 安靜的清晨', '清晨醒來時，他下意識伸手確認你還在，發現你沒有離開才放鬆。', [('❤️ 主動說早安', 70), ('🤍 再陪他躺一下', 68), ('😈 問是不是怕你跑掉', 72)]),
    ('DATE_72｜🔥 只有兩人的約定', '他認真說：『有些事情，我只想跟你一起經歷。』', [('❤️ 問他是什麼事情', 70), ('🤍 說你也有同樣感覺', 75), ('😈 問是不是在告白', 72)]),
    ('DATE_73｜💋 捨不得放開', '告別時的擁抱持續很久，他低聲說：『再一下。』', [('❤️ 抱緊他', 72), ('😈 問是不是黏人', 75), ('🤍 靜靜陪著', 68)]),
    ('DATE_74｜🌙 想把時間留給彼此', '他開始主動空出行程：『這天不要安排別人，我想留給你。』', [('❤️ 答應他', 72), ('😈 問是不是越來越離不開你', 75), ('🤍 也替他空出時間', 70)]),
    ('DATE_75｜🔥 幾乎說出口的承諾', '夜晚結束前，他拉住你的手，話說到一半又停下，像是在等待最好的時機。', [('❤️ 說會等他說完', 75), ('😈 問是不是想說一輩子', 80), ('🤍 主動握住他的手', 72)]),
]
DATE_EVENTS[1000] = [
    ('DATE_76｜💎 正式確認關係', '他認真說不想再逃避『我們算什麼』，希望你們正式成為彼此的戀人。', [('❤️ 問他希望是什麼', 0), ('🤍 主動握住他的手', 0), ('😈 問是不是在告白', 0)]),
    ('DATE_77｜📱 第一個專屬稱呼', '他忽然用只有你們之間才會用的稱呼叫你，問你喜不喜歡。', [('❤️ 說再叫一次', 0), ('😈 問是不是故意的', 0), ('🤍 幫他取專屬稱呼', 0)]),
    ('DATE_78｜🏠 生活裡開始有彼此', '你發現他的生活裡多了許多和你有關的小習慣與準備。', [('❤️ 問是不是特別準備', 0), ('🤍 說你很開心', 0), ('😈 問是不是早就習慣你', 0)]),
    ('DATE_79｜🎂 第一個重要紀念日', '你們第一次認真慶祝屬於彼此的重要日子，他還準備了小禮物。', [('❤️ 認真收下', 0), ('🎁 準備回禮', 0), ('🤍 說最重要是一起度過', 0)]),
    ('DATE_80｜📸 只屬於彼此的照片', '他主動想留下真正屬於你們的紀念照片，說這張不能弄丟。', [('❤️ 問要不要設桌布', 0), ('🤍 說會好好保存', 0), ('😈 問是不是太誇張', 0)]),
    ('DATE_81｜🌙 只有你知道的脆弱', '只有在你面前，他願意放下平常的防備，讓你看見脆弱的一面。', [('🤍 靜靜陪著他', 0), ('❤️ 說可以依靠你', 0), ('💬 陪他把心事說完', 0)]),
    ('DATE_82｜🌃 為彼此空出時間', '即使很忙，他還是主動調整行程：『這天留給你。』', [('❤️ 也把那天空下來', 0), ('😈 問是不是太黏', 0), ('🤍 問想做什麼', 0)]),
    ('DATE_83｜🎁 他記得所有小事', '你隨口說過的事情，他居然記了很久，還為此準備驚喜。', [('❤️ 說很感動', 0), ('😈 問是不是偷偷觀察', 0), ('🤍 說你也記得他的事', 0)]),
    ('DATE_84｜🛋️ 最舒服的相處', '今天沒有特別安排，只是一起待著，卻發現什麼都不做也不會無聊。', [('❤️ 說喜歡現在這樣', 0), ('🤍 靜靜靠著他', 0), ('😈 問是不是離不開你', 0)]),
    ('DATE_85｜🌙 一起迎接清晨', '聊天不知不覺到天亮，你們一起看著窗外逐漸亮起。', [('❤️ 說下次還要', 0), ('🤍 靠在一起看天亮', 0), ('😈 問是不是根本不想讓你睡', 0)]),
    ('DATE_86｜❤️ 你是第一個想到的人', '他告訴你，現在發生什麼事情時，第一個想到的人總是你。', [('❤️ 說你也是', 0), ('🤍 問為什麼', 0), ('😈 問是不是太依賴你', 0)]),
    ('DATE_87｜🌃 關於未來的對話', '聊天時，他很自然地把你放進自己的未來計畫裡。', [('❤️ 也把他放進你的計畫', 0), ('🤍 認真聽他說', 0), ('😈 問是不是想太遠', 0)]),
    ('DATE_88｜💎 只有彼此知道的秘密', '你們約定了一個只屬於兩人的小秘密，因此變得格外特別。', [('🤍 認真答應保密', 0), ('😈 問會不會說出去', 0), ('❤️ 再告訴他另一個秘密', 0)]),
    ('DATE_89｜🤍 不需要說出口的默契', '相處久了，一個表情或動作就能理解彼此的想法。', [('❤️ 問這樣不好嗎', 0), ('😈 問是不是沒有秘密了', 0), ('🤍 說這是最喜歡的地方', 0)]),
    ('DATE_90｜💎 最後的承諾', '他伸出手說：『以後重要的事情，我都希望有你。』', [('❤️ 把手交給他', 0), ('🤍 主動抱住他', 0), ('😈 問是不是正式求專屬', 0)]),
]

class DateChoiceView(discord.ui.View):
    def __init__(self, event):
        super().__init__(timeout=180)
        self.event = event
        for i, (label, gain) in enumerate(event[2]):
            button = discord.ui.Button(label=label, style=[discord.ButtonStyle.danger, discord.ButtonStyle.primary, discord.ButtonStyle.secondary][i])
            async def callback(interaction, gain=gain, label=label):
                await self.choose(interaction, label, gain)
            button.callback = callback
            self.add_item(button)

    async def choose(self, interaction, label, gain):
        user_id = str(interaction.user.id)
        model = model_dict(get_model(user_id))
        before = model.get("affection", 0)
        after = clamp(before + gain, 0, 1000)
        change_model(model["model_id"], affection=after)
        title, story = self.event[0], self.event[1]
        add_memory(user_id, model["model_id"], title, f"選擇：{label}。{story} 好感度 {before} → {after}。")
        await interaction.response.edit_message(embed=discord.Embed(title=title, description=f"👤 **{model['name']}**\n{story}\n\n✨ 你的選擇：**{label}**\n❤️ 好感度：**{before} → {after} / 1000**（{affection_name(after)}）", color=MOONCLUB_COLOR), view=BackHomeView())

class DateEventStageView(discord.ui.View):
    def __init__(self): super().__init__(timeout=180)
    async def open_event(self, interaction, required):
        user_id=str(interaction.user.id); model=model_dict(get_model(user_id)); affection=model.get("affection",0)
        if affection < required:
            await interaction.response.send_message(f"🔒 需要 ❤️ 好感度 **{required}** 才能進入這個約會階段。", ephemeral=True); return
        event=random.choice(DATE_EVENTS[required])
        await interaction.response.edit_message(embed=discord.Embed(title=event[0], description=f"👤 **{model['name']}**\n{event[1]}\n\n請選擇你的反應：", color=MOONCLUB_COLOR), view=DateChoiceView(event))
    @discord.ui.button(label="❤️ 曖昧期隨機約會", style=discord.ButtonStyle.danger)
    async def stage400(self, interaction, button): await self.open_event(interaction,400)
    @discord.ui.button(label="💕 親密期隨機約會", style=discord.ButtonStyle.primary)
    async def stage600(self, interaction, button): await self.open_event(interaction,600)
    @discord.ui.button(label="🔥 深度親密期隨機約會", style=discord.ButtonStyle.danger)
    async def stage800(self, interaction, button): await self.open_event(interaction,800)
    @discord.ui.button(label="💎 專屬關係隨機約會", style=discord.ButtonStyle.success)
    async def stage1000(self, interaction, button): await self.open_event(interaction,1000)

class DateView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180); self.add_item(DateSelect())
        self.add_item(discord.ui.Button(label="❤️ DATE_31～45", style=discord.ButtonStyle.danger, custom_id="date_stage_400"))
        self.children[-1].callback=lambda interaction: interaction.response.edit_message(embed=discord.Embed(title="❤️ 曖昧期｜DATE_31～45",description="好感度 400 以上，可隨機體驗 15 個完整劇情。",color=MOONCLUB_COLOR),view=DateEventStageView())
        self.add_item(discord.ui.Button(label="💕 DATE_46～60", style=discord.ButtonStyle.primary, custom_id="date_stage_600"))
        self.children[-1].callback=lambda interaction: interaction.response.edit_message(embed=discord.Embed(title="💕 親密期｜DATE_46～60",description="好感度 600 以上，可隨機體驗 15 個完整劇情。",color=MOONCLUB_COLOR),view=DateEventStageView())
        self.add_item(discord.ui.Button(label="🔥 DATE_61～75", style=discord.ButtonStyle.danger, custom_id="date_stage_800"))
        self.children[-1].callback=lambda interaction: interaction.response.edit_message(embed=discord.Embed(title="🔥 深度親密期｜DATE_61～75",description="好感度 800 以上，可隨機體驗 15 個完整劇情。",color=MOONCLUB_COLOR),view=DateEventStageView())
        self.add_item(discord.ui.Button(label="💎 DATE_76～90", style=discord.ButtonStyle.success, custom_id="date_stage_1000"))
        self.children[-1].callback=lambda interaction: interaction.response.edit_message(embed=discord.Embed(title="💎 專屬關係｜DATE_76～90",description="好感度 1000 時，可隨機體驗 15 個專屬關係劇情。",color=MOONCLUB_COLOR),view=DateEventStageView())

class DateSelect(discord.ui.Select):
    def __init__(self):
        options=[discord.SelectOption(label=title,value=str(i),description=f"❤️ 好感度 {req}+ 解鎖") for i,(req,title,_,_) in enumerate(DATE_OPTIONS)]
        super().__init__(placeholder="選擇基本約會內容…", options=options)
    async def callback(self, interaction):
        user_id=str(interaction.user.id); model=model_dict(get_model(user_id)); idx=int(self.values[0]); required,title,story,gain_range=DATE_OPTIONS[idx]; affection=model.get("affection",0)
        if affection < required:
            await interaction.response.send_message(f"🔒 需要 ❤️ 好感度 **{required}** 才能解鎖這個約會。",ephemeral=True); return
        gain=random.randint(*gain_range); after=clamp(affection+gain,0,1000); change_model(model["model_id"],affection=after); add_memory(user_id,model["model_id"],title,f"{story} 好感度 {affection} → {after}。")
        await interaction.response.edit_message(embed=discord.Embed(title=title,description=f"👤 **{model['name']}**\n{story}\n\n❤️ 好感度：**{affection} → {after} / 1000**（{affection_name(after)}）",color=MOONCLUB_COLOR),view=BackHomeView())

# ==========================================================
# 🎴 V14｜三選一隨機新人招募｜稀有度完全隱藏
# ==========================================================

def generate_candidate():
    # 隱藏稀有度：普通 80%、優秀 17%、稀有 3%。玩家招募前完全看不到。
    roll = random.randint(1, 100)
    rarity = "稀有" if roll <= 3 else "優秀" if roll <= 20 else "普通"

    potential = random.choice(POTENTIALS)
    stats = {key: random.randint(3, 8) for key in STAT_EMOJIS}
    focus_map = {
        "💃 舞台型": "fitness", "🎤 表演型": "creativity", "📸 鏡頭型": "intelligence",
        "💬 社交型": "social", "👔 時尚型": "creativity",
    }
    focus = focus_map[potential]
    # 所有人仍是新人；只有一項初始傾向稍微突出，不會直接變成高能力角色。
    stats[focus] = min(10, stats[focus] + random.randint(1, 3))

    return {
        "age": random.randint(18, 30),
        "personality": random.choice(list(PERSONALITY_EMOJIS)),
        "potential": potential,
        "background": random.choice(BACKGROUNDS),
        "stats": stats,
        "rarity": rarity,  # 僅寫入資料庫，招募畫面與男模資料都不顯示
    }


async def start_recruitment(interaction):
    user_id = str(interaction.user.id)
    current = model_dict(get_model(user_id))
    count = model_count(user_id)
    # 第一位新人招募必須由 FAME_13 合理解鎖；既有多男模資料不受影響。
    if count <= 1 and (not current or not fame_completed(user_id, current["model_id"], "FAME_13")):
        await interaction.response.send_message("🔒 目前尚未解鎖新人招募。請先讓第一位男模累積發展，並完成 🌟 FAME_13。", ephemeral=True)
        return
    rep = club_reputation(user_id)
    capacity, stage = recruit_capacity(rep)

    if count >= capacity:
        next_level = next((x for x in RECRUIT_LIMITS if x[0] > rep), None)
        extra = f"\n下一次解鎖：知名度 {next_level[0]}" if next_level else "\n已達最高招募名額。"
        await interaction.response.send_message(
            f"🔒 目前名額已滿（{count}/{capacity}）。\n🏛️ 知名度：{rep}/1000｜{stage}{extra}",
            ephemeral=True,
        )
        return

    candidates = [generate_candidate() for _ in range(3)]
    lines = [f"🏛️ 知名度：**{rep}/1000**｜{stage}\n👥 名額：**{count}/{capacity}**"]
    for index, candidate in enumerate(candidates, 1):
        st = candidate["stats"]
        lines.append(
            f"**候選人 {index}**\n"
            f"🎂 {candidate['age']} 歲｜😈 {candidate['personality']}｜🎭 {candidate['potential']}\n"
            f"🧠 {st['intelligence']}｜❤️ {st['emotion']}｜💪 {st['fitness']}｜🎨 {st['creativity']}｜✨ {st['social']}\n"
            f"📖 {candidate['background']}"
        )

    await interaction.response.send_message(
        embed=discord.Embed(
            title="🎴 Moon Club｜招募新人",
            description="\n\n".join(lines),
            color=MOONCLUB_COLOR,
        ),
        view=RecruitCandidatesView(candidates, interaction.user.id),
        ephemeral=True,
    )


class RecruitCandidatesView(discord.ui.View):
    def __init__(self, candidates, owner_user_id=None):
        super().__init__(timeout=180)
        self.candidates = candidates
        self.owner_user_id = int(owner_user_id) if owner_user_id else None

    async def pick(self, interaction, index):
        if self.owner_user_id is not None and interaction.user.id != self.owner_user_id:
            await interaction.response.send_message("❌ 這不是你的招募選單。", ephemeral=True)
            return
        await interaction.response.send_modal(RecruitNameModal(self.candidates[index], self.owner_user_id))

    @discord.ui.button(label="選擇候選人 ①", style=discord.ButtonStyle.primary)
    async def first(self, interaction, button): await self.pick(interaction, 0)

    @discord.ui.button(label="選擇候選人 ②", style=discord.ButtonStyle.primary)
    async def second(self, interaction, button): await self.pick(interaction, 1)

    @discord.ui.button(label="選擇候選人 ③", style=discord.ButtonStyle.primary)
    async def third(self, interaction, button): await self.pick(interaction, 2)


class RecruitNameModal(discord.ui.Modal, title="✏️ 替新人取名字"):
    name = discord.ui.TextInput(label="新人男模名字", max_length=30)

    def __init__(self, candidate, owner_user_id=None):
        super().__init__()
        self.candidate = candidate
        self.owner_user_id = int(owner_user_id) if owner_user_id else None

    async def on_submit(self, interaction):
        if self.owner_user_id is not None and interaction.user.id != self.owner_user_id:
            await interaction.response.send_message("❌ 這不是你的招募流程。", ephemeral=True)
            return
        user_id = str(interaction.user.id)
        player = get_player(user_id)
        if not player:
            await interaction.response.send_message("❌ Moon Club 尚未建立。", ephemeral=True)
            return

        capacity = sync_capacity(user_id)
        if model_count(user_id) >= capacity:
            await interaction.response.send_message("❌ 招募名額已滿。", ephemeral=True)
            return

        name = self.name.value.strip()
        if not name:
            await interaction.response.send_message("❌ 請輸入名字。", ephemeral=True)
            return

        c.execute("SELECT 1 FROM moonclub_modelren WHERE user_id=? AND name=?", (user_id, name))
        if c.fetchone():
            await interaction.response.send_message("❌ 已有同名男模，請換一個名字。", ephemeral=True)
            return

        scores = {p: random.randint(0, 8) for p in PERSONALITY_EMOJIS}
        scores[self.candidate["personality"]] += 8
        stats = self.candidate["stats"]

        c.execute("""
            INSERT INTO moonclub_modelren
            (user_id,owner_name,owner_identity,name,gender,age_year,
             intelligence,emotion,fitness,creativity,social,relationship,
             model_stamina,personality_scores,personalities,interests,
             interest_progress,experiences,hidden_rarity,potential_direction,
             background_story,created_at)
            VALUES (?,?,?,?, '男',?,?,?,?,?,?,0,0,100,?,'[]','[]','{}','{}',?,?,?,?)
        """, (
            user_id, player[1], "會館老闆", name, self.candidate["age"],
            stats["intelligence"], stats["emotion"], stats["fitness"],
            stats["creativity"], stats["social"],
            dump_json(scores), self.candidate["rarity"],
            self.candidate["potential"], self.candidate["background"], now_iso(),
        ))
        model_id = c.lastrowid
        add_memory(user_id, model_id, "✨ 新人加入", f"{name} 正式加入 Moon Club。")
        conn.commit()

        await interaction.response.send_message(
            embed=discord.Embed(
                title="🎉 招募成功！",
                description=(
                    f"{MODEL_ICON} **{name}** 正式加入 Moon Club！\n"
                    f"🎂 {self.candidate['age']} 歲\n"
                    f"😈 {self.candidate['personality']}\n"
                    f"🎭 {self.candidate['potential']}\n\n"
                    f"🌱 他將和其他人一樣，從頭開始培養。"
                ),
                color=MOONCLUB_COLOR,
            ),
            ephemeral=True,
        )


# ==========================================================
# 🧹 測試資料清除
# ==========================================================

def clear_moonclub_data(user_id):
    user_id = str(user_id)
    c.execute("DELETE FROM moonclub_memories WHERE user_id=?", (user_id,))
    c.execute("DELETE FROM moonclub_model_daily WHERE user_id=?", (user_id,))
    c.execute("DELETE FROM moonclub_modelren WHERE user_id=?", (user_id,))
    c.execute("DELETE FROM moonclub_players WHERE user_id=?", (user_id,))
    conn.commit()


class MoonClubClearConfirmView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = str(user_id)

    @discord.ui.button(label="🗑️ 確定清空", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction, button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ 這不是你的確認視窗。", ephemeral=True)
            return
        clear_moonclub_data(self.user_id)
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            content="🧹 **Moon Club 測試紀錄已清空！**\n現在可以重新使用 `/moonclub` 開始。",
            view=self,
        )

    @discord.ui.button(label="取消", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ 這不是你的確認視窗。", ephemeral=True)
            return
        await interaction.response.edit_message(content="👉 已取消清除 Moon Club 紀錄。", view=None)


# ==========================================================
# 🚀 指令註冊
# ==========================================================

def setup_moon_club(bot):
    init_moonclub_tables()

    if getattr(bot, "_moon_club_loaded", False):
        return
    bot._moon_club_loaded = True

    @bot.tree.command(name="moonclub清空紀錄", description="清空自己的 Moon Club 測試紀錄")
    async def moonclub_clear_record(interaction: discord.Interaction):
        if interaction.user.id not in BOT_ADMINS and not is_moonclub_tester(interaction.user.id):
            await interaction.response.send_message("❌ 此功能目前只開放 Moon Club 測試人員與管理員。", ephemeral=True)
            return
        await interaction.response.send_message(
            "⚠️ **確定要清空自己的 Moon Club 測試紀錄嗎？**\n\n"
            "這會刪除 Moon Club 的會館資料、所有男模與職涯紀錄，不影響其他系統。",
            view=MoonClubClearConfirmView(interaction.user.id),
            ephemeral=True,
        )

    @bot.tree.command(name="moonclub", description="進入 Moon Club｜男模會館")
    async def moonclub(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if not get_player(user_id) or not get_models(user_id):
            embed = discord.Embed(
                title="🌙 Moon Club｜男模會館",
                description=(
                    "你接手了一間剛起步的小型男模會館。\n\n"
                    f"{OWNER_ICON} 你是會館老闆\n"
                    "👥 一開始可以培養兩位新人男模\n"
                    "🏋️ 培訓五大能力與專長\n"
                    "💕 建立最高 1000 點默契\n"
                    "🏛️ 提升 Moon Club 知名度\n"
                    "🎴 知名度達標後解鎖新人招募\n\n"
                    "✨ 現在，讓 Moon Club 正式開幕吧！"
                ),
                color=MOONCLUB_COLOR,
            )
            await interaction.response.send_message(embed=embed, view=StartMoonClubView(), ephemeral=True)
            return

        embed = await build_home_embed(user_id)
        await interaction.response.send_message(embed=embed, view=MoonClubHomeView(), ephemeral=True)

    print("🌙 Moon Club V14｜三選一隨機新人招募正式版已載入")


# ==========================================================
# 📖 Moon Club｜既有特殊事件資料（保留目前 V12 的事件清單）
# ==========================================================

MOONCLUB_BOND_EVENTS = [
    {"id": "bond_01", "name": "💬 第一次真正的聊天", "bond": 50, "requires": ["chat_once"], "once": True},
    {"id": "bond_02", "name": "☕ 主動邀請喝咖啡", "bond": 150, "requires": ["bond_01", "meal_twice"], "once": True},
    {"id": "bond_03", "name": "📱 第一次私人訊息", "bond": 250, "requires": ["bond_02", "recent_interaction"], "once": True},
    {"id": "bond_04", "name": "🌧️ 情緒低落時找你", "bond": 350, "requires": ["recent_training_or_work", "low_stamina_or_setback"], "once": True},
    {"id": "bond_05", "name": "🌙 深夜談心", "bond": 450, "requires": ["bond_04", "chat_today"], "once": True},
    {"id": "bond_06", "name": "🤍 分享自己的秘密", "bond": 550, "requires": ["bond_05", "multiple_chats"], "once": True},
    {"id": "bond_07", "name": "🥹 主動尋求你的意見", "bond": 650, "requires": ["bond_05", "training_done", "work_done"], "once": True},
    {"id": "bond_08", "name": "🎁 意外準備的小禮物", "bond": 750, "requires": ["gift_received", "multiple_interactions"], "once": True},
    {"id": "bond_09", "name": "❤️ 關鍵時刻的信任", "bond": 850, "requires": ["bond_events_6", "important_career_event"], "once": True},
    {"id": "bond_10", "name": "👑 靈魂搭檔", "bond": 1000, "requires": ["bond_milestones", "career_experience"], "once": True},
]

# 先建立事件資料與判斷入口；詳細 Discord 劇情／選項會隨各行動 UI 完成後接入。
def get_moonclub_bond_event_candidates(model_data, flags=None):
    """依默契與已完成條件篩選可觸發事件，避免純隨機突兀劇情。"""
    flags = flags or set()
    bond = 0
    if model_data:
        try:
            bond = int(model_data.get("bond", model_data.get("affection", 0)))
        except AttributeError:
            try:
                bond = int(model_data["bond"])
            except Exception:
                bond = 0
    result = []
    for event in MOONCLUB_BOND_EVENTS:
        if bond < event["bond"]:
            continue
        if event["id"] in flags:
            continue
        if all(req in flags for req in event["requires"]):
            result.append(event)
    return result

# ==========================================================
# 🎲 Moon Club｜特殊事件系統 v2
# 🏋️ 第二批：培訓事件 11～20
# 規則：必須有實際培訓累積、能力或前置事件，不能無條件跳出。
# ==========================================================

MOONCLUB_TRAINING_EVENTS = [
    {"id": "training_11", "name": "💇 意外成功的形象改造", "requires": ["image_training_multiple", "high_looks", "last_training_image"], "once": True},
    {"id": "training_12", "name": "📸 攝影師注意到他", "requires": ["image_training_or_promo", "high_looks"], "once": True},
    {"id": "training_13", "name": "🗣️ 克服舞台緊張", "requires": ["speech_training_multiple", "recent_speech_training"], "once": True},
    {"id": "training_14", "name": "🎭 發現新的潛力", "requires": ["same_training_multiple", "related_stat_growth", "no_formal_specialty"], "once": True},
    {"id": "training_15", "name": "🎓 培訓老師的特別評價", "requires": ["training_count_threshold", "two_stats_grown", "recent_training"], "once": True},
    {"id": "training_16", "name": "💪 突破訓練瓶頸", "requires": ["stat_plateau", "continued_related_training"], "once": True},
    {"id": "training_17", "name": "😮 遇到培訓挫折", "requires": ["continuous_training", "low_stamina_or_poor_result"], "once": True},
    {"id": "training_18", "name": "🌟 獲得外部推薦", "requires": ["training_multiple", "high_related_stat", "positive_teacher_review"], "once": True},
    {"id": "training_19", "name": "✉️ 收到特殊培訓邀請", "requires": ["continuous_stat_growth", "high_specialty_exposure", "training_events_progress"], "once": True},
    {"id": "training_20", "name": "💥 一次重大的能力突破", "requires": ["high_stat_threshold", "long_term_related_training", "breakthrough_or_special_training"], "once": True},
]


def get_moonclub_training_event_candidates(flags=None):
    """依實際培訓經歷與前置條件篩選培訓特殊事件。"""
    flags = flags or set()
    result = []
    for event in MOONCLUB_TRAINING_EVENTS:
        if event["id"] in flags:
            continue
        if all(req in flags for req in event["requires"]):
            result.append(event)
    return result


# ==========================================================
# 🎲 Moon Club｜特殊事件系統 v3
# 🎭 第三批：專長發展事件 21～30
# 規則：必須有相關接觸、能力、培訓或前置事件，
#       不會沒有基礎就突然形成專長。
# ==========================================================

MOONCLUB_SPECIALTY_EVENTS = [
    {"id": "specialty_21", "name": "🎤 第一次被稱讚歌聲",
     "requires": ["talent_training_multiple", "singing_exposure", "talent_threshold"]},

    {"id": "specialty_22", "name": "💃 舞蹈訓練的邀請",
     "requires": ["dance_exposure", "talent_training_multiple", "talent_threshold"]},

    {"id": "specialty_23", "name": "🏋️ 健身成果受到注意",
     "requires": ["fitness_training_multiple", "appearance_or_charm_threshold"]},

    {"id": "specialty_24", "name": "🗣️ 意外成為氣氛中心",
     "requires": ["speech_training_multiple", "speech_threshold", "social_interaction_history"]},

    {"id": "specialty_25", "name": "🎹 接觸新的樂器",
     "requires": ["talent_training_multiple", "talent_threshold", "specialty_slots_available"]},

    {"id": "specialty_26", "name": "🎭 小型演出的機會",
     "requires": ["talent_threshold", "related_specialty_exposure", "related_training_event"]},

    {"id": "specialty_27", "name": "🌟 專長正式形成",
     "requires": ["specialty_progress_threshold", "related_stat_threshold",
                  "related_event_completed", "specialty_slots_available"]},

    {"id": "specialty_28", "name": "📈 專長能力突破",
     "requires": ["official_specialty", "related_activity_history", "related_stat_growth"]},

    {"id": "specialty_29", "name": "🏆 因專長獲得肯定",
     "requires": ["official_specialty", "high_related_stat", "related_work_history"]},

    {"id": "specialty_30", "name": "👑 專長帶來重大機會",
     "requires": ["mature_specialty", "high_related_stat", "specialty_29_completed",
                  "work_or_activity_experience"]},
]

MOONCLUB_SPECIALTY_EVENT_DETAILS = {
    "specialty_21": {
        "story": "一次練習結束後，老師請他再唱一次剛才的片段，並第一次明確稱讚他的聲音特色。",
        "result": "歌唱接觸度提升、才藝小幅提升，解鎖後續歌唱事件。"
    },
    "specialty_22": {
        "story": "培訓老師邀請他參加一堂舞蹈課，看看是否適合往新的方向發展。",
        "choices": ["💃 鼓勵他參加", "🏛️ 先以目前培訓為主"],
        "result": "不同選擇影響舞蹈接觸度與後續發展。"
    },
    "specialty_23": {
        "story": "長期訓練的成果開始被其他人注意，有人主動詢問他的訓練方式。",
        "result": "健身接觸度提升、魅力與人氣小幅提升。"
    },
    "specialty_24": {
        "story": "一次普通聚會中，大家的注意力不知不覺集中到他身上，他成了帶動氣氛的人。",
        "result": "社交接觸度提升、人氣提升，解鎖社交相關事件。"
    },
    "specialty_25": {
        "story": "課程結束後，他停在一件樂器前，主動詢問是否能試試看。",
        "choices": ["🎹 鼓勵他試試", "📚 建議先專注原本方向"],
        "result": "選擇會影響樂器接觸度或原有專長方向的進度。"
    },
    "specialty_26": {
        "story": "Moon Club 收到小型活動邀請，希望他參與演出，可能是第一次真正站上舞台。",
        "choices": ["🌟 接受演出", "🏋️ 先繼續培訓"],
        "result": "可獲得演出經驗、人氣與相關專長進度。"
    },
    "specialty_27": {
        "story": "長時間累積後，大家開始明白這不只是興趣，而是他真正擅長的事情。",
        "result": "正式形成專長並寫入職涯紀錄。"
    },
    "specialty_28": {
        "story": "曾經需要刻意思考的技巧開始變得自然，他明顯感覺自己進入新的階段。",
        "result": "對應能力額外提升、專長發展進度增加。"
    },
    "specialty_29": {
        "story": "這次不只是老師稱讚，而是外界開始真正注意到他的能力。",
        "result": "人氣提升、寫入職涯紀錄，解鎖更高階機會。"
    },
    "specialty_30": {
        "story": "一個重要機會主動找上門，對方不再只是詢問要不要試試，而是希望由他來。",
        "choices": ["👑 接受重大挑戰", "🏛️ 穩定發展"],
        "result": "選擇影響未來職涯風險、人氣與重大機會。"
    },
}


def moonclub_all_special_events():
    """集中取得目前已建立的特殊事件。"""
    events = []
    for event_name in (
        "MOONCLUB_BOND_EVENTS",
        "MOONCLUB_TRAINING_EVENTS",
        "MOONCLUB_SPECIALTY_EVENTS",
    ):
        value = globals().get(event_name, [])
        if isinstance(value, list):
            events.extend(value)
    return events



# ==========================================================
# 🎲 Moon Club｜特殊事件系統 v4
# 😈 第四批：性格發展事件 31～40
# 性格不是一開始固定，而是由行動、選擇與經歷逐步形成。
# ==========================================================

MOONCLUB_PERSONALITY_EVENTS = [
    {"id": "personality_31", "name": "❄️ 高冷的距離感",
     "requires": ["cold_tendency_high", "distance_choices_multiple"]},
    {"id": "personality_32", "name": "🐶 忠犬般的陪伴",
     "requires": ["loyal_tendency_high", "bond_threshold"]},
    {"id": "personality_33", "name": "🐱 傲嬌的關心",
     "requires": ["tsundere_tendency_high", "bond_medium"]},
    {"id": "personality_34", "name": "🥹 溫柔的安慰",
     "requires": ["gentle_tendency_high", "interaction_history"]},
    {"id": "personality_35", "name": "🔥 主動的邀請",
     "requires": ["active_tendency_high", "bond_threshold"]},
    {"id": "personality_36", "name": "😈 腹黑的小心思",
     "requires": ["scheming_tendency_high", "interaction_multiple"]},
    {"id": "personality_37", "name": "👑 自信的選擇",
     "requires": ["confidence_tendency_high", "positive_training_or_work"]},
    {"id": "personality_38", "name": "🌙 不願提起的過去",
     "requires": ["mysterious_tendency_high", "bond_high", "late_night_talk_completed"]},
    {"id": "personality_39", "name": "⚖️ 性格的重要選擇",
     "requires": ["two_personality_tendencies_close", "important_recent_event"]},
    {"id": "personality_40", "name": "🌟 第二性格形成",
     "requires": ["primary_personality_formed", "second_tendency_high", "special_event_experience"]},
]

MOONCLUB_PERSONALITY_EVENT_DETAILS = {
    "personality_31": {
        "story": "面對陌生人的熱情搭話，他禮貌地保持距離，但你發現他其實一直默默觀察周圍。",
        "choices": ["🤍 尊重他的方式", "💬 鼓勵他多交流"],
        "result": "影響高冷與社交傾向。"
    },
    "personality_32": {
        "story": "你忙了一整天，準備離開時才發現他還在等待，表示想陪你到工作結束。",
        "result": "默契提升，忠誠／陪伴傾向加深。"
    },
    "personality_33": {
        "story": "他把飲料放到你旁邊，嘴上卻說只是剛好多買，否認自己特地準備。",
        "result": "默契提升，傲嬌傾向加深。"
    },
    "personality_34": {
        "story": "他察覺你心情不好，沒有一直追問，只安靜表示：如果你想說，我可以聽。",
        "result": "默契提升，溫柔傾向加深。"
    },
    "personality_35": {
        "story": "這次不是你安排互動，而是他先主動詢問今天是否有空。",
        "choices": ["🌳 一起出去", "📋 今天不方便"],
        "result": "影響後續互動事件與主動傾向。"
    },
    "personality_36": {
        "story": "他似乎早就知道你會怎麼回答，讓你忍不住懷疑自己是不是被他的小心思帶著走。",
        "result": "腹黑傾向提升，解鎖特殊對話。"
    },
    "personality_37": {
        "story": "面對新的機會，他沒有衝動，也沒有退縮，而是平靜地說自己想試試。",
        "result": "自信傾向提升，可能解鎖高階挑戰。"
    },
    "personality_38": {
        "story": "聊天中某個話題讓他突然沉默，只表示這件事以後再說，建立個人過去劇情線。",
        "result": "解鎖後續個人背景事件。"
    },
    "personality_39": {
        "story": "面對重要決定，他必須在謹慎與挑戰之間選擇。",
        "choices": ["🛡️ 謹慎處理", "🔥 鼓勵挑戰"],
        "result": "真正影響未來正式性格的形成方向。"
    },
    "personality_40": {
        "story": "經歷許多事情後，你發現他並不是只有一種樣子，而是逐漸展現出第二個鮮明面向。",
        "result": "正式形成第二性格。"
    },
}


def moonclub_all_special_events():
    """取得目前已建立的全部特殊事件（01～40）。"""
    events = []
    for event_name in (
        "MOONCLUB_BOND_EVENTS",
        "MOONCLUB_TRAINING_EVENTS",
        "MOONCLUB_SPECIALTY_EVENTS",
        "MOONCLUB_PERSONALITY_EVENTS",
    ):
        value = globals().get(event_name, [])
        if isinstance(value, list):
            events.extend(value)
    return events


# ==========================================================
# 🎲 Moon Club｜特殊事件系統 v5
# ⭐ 41～50 職涯事件｜🌙 51～60 生活／會館事件
# ==========================================================

MOONCLUB_CAREER_EVENTS = [
    {"id":"career_41","name":"📸 第一個正式工作邀約","requires":["training_count_threshold","one_stat_threshold"]},
    {"id":"career_42","name":"🎤 第一次公開活動","requires":["work_history","popularity_basic","related_ability"]},
    {"id":"career_43","name":"🌱 小幅人氣成長","requires":["recent_work_or_activity","not_high_popularity"]},
    {"id":"career_44","name":"📰 開始受到外界注意","requires":["popularity_threshold","work_history_multiple"]},
    {"id":"career_45","name":"😓 工作上的失誤","requires":["work_history_multiple","low_energy_or_insufficient_ability"]},
    {"id":"career_46","name":"🏆 獲得專業肯定","requires":["career_experience","high_stat","positive_career_event"]},
    {"id":"career_47","name":"⚖️ 職涯方向的選擇","requires":["popularity_threshold","official_specialty","work_history_multiple"]},
    {"id":"career_48","name":"💎 高級工作邀請","requires":["high_popularity","high_ability","professional_recognition"]},
    {"id":"career_49","name":"🌪️ 職涯壓力","requires":["recent_work_dense","low_energy"]},
    {"id":"career_50","name":"👑 職涯第一次重大轉折","requires":["career_events_multiple","high_popularity","mature_specialty"]},
]

MOONCLUB_CAREER_EVENT_DETAILS = {
    "career_41":{"story":"Moon Club 收到一個小型正式工作邀約，對方對他很感興趣。","choices":["📸 接受工作","🏋️ 再培養一陣子"],"result":"接受可獲得職涯經驗與人氣；繼續培養則獲得小幅能力成長。"},
    "career_42":{"story":"第一次真正站在公開活動中面對大家。","choices":["🌟 接受挑戰","🛡️ 暫時觀望"],"result":"影響舞台經驗與自信傾向。"},
    "career_43":{"story":"開始有人主動詢問 Moon Club 的新人最近是否有活動。","result":"人氣提升。"},
    "career_44":{"story":"外部開始有人討論他的名字，代表他開始被更多人知道。","result":"人氣提升並解鎖更高階邀約。"},
    "career_45":{"story":"一次工作中出現明顯失誤，需要面對與處理。","choices":["🤍 安慰並檢討","🏋️ 加強訓練"],"result":"影響默契、能力與未來工作表現。"},
    "career_46":{"story":"有人正式肯定他的表現，認為他非常有潛力。","result":"人氣與自信提升，解鎖高級工作。"},
    "career_47":{"story":"開始出現不同類型的發展邀請，需要決定職涯方向。","choices":["🌟 挑戰型發展","🏛️ 穩定型發展"],"result":"影響未來職涯事件池。"},
    "career_48":{"story":"Moon Club 收到規格更高的工作邀請。","choices":["👑 接受挑戰","🏋️ 先準備"],"result":"成功後人氣與收入增加，並留下重要職涯紀錄。"},
    "career_49":{"story":"近期密集行程讓他開始感到壓力與疲憊。","choices":["🛋️ 安排休息","🔥 鼓勵繼續"],"result":"影響體力、未來工作成功率與默契。"},
    "career_50":{"story":"一個重大機會出現在眼前，可能真正改變未來職涯。","choices":["👑 全力挑戰","🏛️ 穩定累積"],"result":"建立後續職涯發展方向。"},
}

MOONCLUB_LIFE_EVENTS = [
    {"id":"life_51","name":"😴 過度疲勞","requires":["low_energy","recent_training_or_work_multiple"]},
    {"id":"life_52","name":"🌙 深夜還留在會館","requires":["night_interaction","bond_medium"]},
    {"id":"life_53","name":"📱 一則奇怪的訊息","requires":["public_activity_history","popularity_growth"]},
    {"id":"life_54","name":"🎉 Moon Club 的慶祝活動","requires":["club_milestone_or_special_day"]},
    {"id":"life_55","name":"✨ 意想不到的訪客","requires":["club_development_threshold","rare_random"]},
    {"id":"life_56","name":"🌧️ 下雨天的偶遇","requires":["outing_or_work_today","rare_random"]},
    {"id":"life_57","name":"🎂 特別的生日","requires":["model_birthday","not_completed"]},
    {"id":"life_58","name":"☕ 偶然的相遇","requires":["outing_history","rare_random"]},
    {"id":"life_59","name":"🎁 突然準備的禮物","requires":["bond_medium_high","interaction_multiple"]},
    {"id":"life_60","name":"🚨 Moon Club 突發事件","requires":["club_development_threshold","random_event"]},
]

MOONCLUB_LIFE_EVENT_DETAILS = {
    "life_51":{"story":"最近的培訓與工作累積讓他明顯疲憊。","choices":["🛋️ 強制休息","💬 詢問他的想法"],"result":"影響體力與默契。"},
    "life_52":{"story":"大家離開後，你發現他還留在安靜的 Moon Club 裡。","choices":["💬 陪他聊天","🏠 提醒他回家"],"result":"可能觸發後續默契事件。"},
    "life_53":{"story":"公開活動後，他收到一則奇怪的合作或邀請訊息。","choices":["🔍 仔細確認","❌ 直接拒絕"],"result":"可能開啟後續事件或避免風險。"},
    "life_54":{"story":"Moon Club 達成里程碑或遇上特殊節日，舉辦小型慶祝活動。","result":"所有成員默契小幅提升，並可能觸發其他生活事件。"},
    "life_55":{"story":"某天，一位意想不到的人來到 Moon Club。","choices":["🤝 親自接待","👀 先觀察"],"result":"可能帶來新機會、新事件或特殊人物劇情。"},
    "life_56":{"story":"下雨天的外出途中發生一場偶遇。","result":"偏生活型事件，增加世界真實感並可能留下後續線索。"},
    "life_57":{"story":"在他的生日，依照目前默契與經歷展開不同規模的慶祝。","result":"特殊紀念、默契提升並留下生日紀錄。"},
    "life_58":{"story":"休息日偶然遇到一位可能影響未來的人。","result":"可能是普通生活事件、新工作線索或特殊劇情。"},
    "life_59":{"story":"他突然準備了一份小禮物，不同性格會有不同反應。","result":"默契提升，可能解鎖專屬紀念物。"},
    "life_60":{"story":"Moon Club 突然遇到活動取消、設備問題或工作安排改變。","choices":["🔧 立刻處理","📋 重新安排"],"result":"影響會館發展、工作安排與後續事件。"},
}

def moonclub_all_special_events():
    """取得目前已建立的全部特殊事件（01～60）。"""
    events = []
    for event_name in (
        "MOONCLUB_BOND_EVENTS",
        "MOONCLUB_TRAINING_EVENTS",
        "MOONCLUB_SPECIALTY_EVENTS",
        "MOONCLUB_PERSONALITY_EVENTS",
        "MOONCLUB_CAREER_EVENTS",
        "MOONCLUB_LIFE_EVENTS",
    ):
        value = globals().get(event_name, [])
        if isinstance(value, list):
            events.extend(value)
    return events


# ==========================================================
# 📖 V15｜1～100 特殊事件完整資料補強
# 所有事件依角色狀態與已完成經歷觸發，不作無條件亂抽。
# ==========================================================

MOONCLUB_RELATION_EVENTS = [{'id': 'relation_61', 'name': '🔐 第一次主動說出秘密', 'requires': ['bond_high', 'deep_talk_history']}, {'id': 'relation_62', 'name': '🌙 深夜的電話', 'requires': ['bond_medium_high', 'life_interaction_history']}, {'id': 'relation_63', 'name': '💭 意見不一致', 'requires': ['bond_threshold', 'important_recent_choice']}, {'id': 'relation_64', 'name': '🥀 一個人安靜的時候', 'requires': ['personal_background_event', 'mysterious_or_introvert_tendency']}, {'id': 'relation_65', 'name': '🤝 第一次真正的信任', 'requires': ['bond_high', 'relation_events_multiple']}, {'id': 'relation_66', 'name': '😤 小小的吃醋', 'requires': ['bond_high', 'loyal_or_tsundere_or_active_tendency']}, {'id': 'relation_67', 'name': '🌧️ 雨天的談心', 'requires': ['rain_event_history', 'bond_medium_high']}, {'id': 'relation_68', 'name': '📖 他第一次主動談起過去', 'requires': ['personality_38_completed', 'relation_61_or_64_completed', 'bond_high']}, {'id': 'relation_69', 'name': '🌱 關係的重要轉變', 'requires': ['relation_events_multiple', 'bond_very_high']}, {'id': 'relation_70', 'name': '💫 專屬紀念日', 'requires': ['bond_very_high', 'important_relation_events']}]

MOONCLUB_CLUB_EVENTS = [{'id': 'club_71', 'name': '🏛️ Moon Club 開始有名氣', 'requires': ['multiple_models_popularity', 'club_work_count', 'reputation_100']}, {'id': 'club_72', 'name': '💌 收到合作邀請', 'requires': ['reputation_250', 'club_work_or_activity_count', 'one_model_popularity']}, {'id': 'club_73', 'name': '🎉 第一次大型會館活動', 'requires': ['club_development_threshold', 'multiple_models', 'reputation_300']}, {'id': 'club_74', 'name': '⚡ 男模之間的小競爭', 'requires': ['at_least_two_models', 'ability_gap_small']}, {'id': 'club_75', 'name': '🤝 男模之間建立友誼', 'requires': ['shared_activity_multiple']}, {'id': 'club_76', 'name': '📉 Moon Club 遇到低潮', 'requires': ['work_reduced_or_popularity_down_or_random']}, {'id': 'club_77', 'name': '🌟 一位成員突然爆紅', 'requires': ['rapid_popularity_growth', 'major_work_completed']}, {'id': 'club_78', 'name': '🎭 團體合作活動', 'requires': ['at_least_two_models', 'member_relationship_threshold']}, {'id': 'club_79', 'name': '🚨 會館的重要危機', 'requires': ['club_development_high', 'rare_random', 'reputation_500']}, {'id': 'club_80', 'name': '👑 Moon Club 的重要里程碑', 'requires': ['reputation_750', 'multiple_models_career_results', 'large_event_completed']}]

MOONCLUB_LEGEND_EVENTS = [{'id': 'legend_81', 'name': '✨ 意外的大型邀請', 'requires': ['very_high_stat', 'official_specialty', 'high_popularity']}, {'id': 'legend_82', 'name': '🌍 外地大型發展機會', 'requires': ['legend_81_completed', 'mature_career', 'high_popularity']}, {'id': 'legend_83', 'name': '🎯 生涯的重要決定', 'requires': ['major_career_events_multiple', 'mature_specialty', 'high_popularity']}, {'id': 'legend_84', 'name': '🏆 個人代表作', 'requires': ['large_work_success_multiple', 'very_high_specialty']}, {'id': 'legend_85', 'name': '💫 被真正記住的名字', 'requires': ['high_popularity', 'representative_work', 'professional_recognition_multiple']}, {'id': 'legend_86', 'name': '💎 頂級工作邀請', 'requires': ['legend_84_or_85_completed', 'high_popularity', 'high_ability']}, {'id': 'legend_87', 'name': '⚡ 巔峰前的壓力', 'requires': ['major_work_dense', 'low_energy']}, {'id': 'legend_88', 'name': '🥇 頂級評價', 'requires': ['top_work_completed', 'work_success', 'very_high_ability']}, {'id': 'legend_89', 'name': '🌟 職涯巔峰', 'requires': ['top_events_multiple', 'extreme_popularity', 'mature_specialty']}, {'id': 'legend_90', 'name': '👑 頂級男模稱號', 'requires': ['career_peak', 'high_popularity', 'club_development_good']}, {'id': 'legend_91', 'name': '🌟 Moon Club 成為知名會館', 'requires': ['club_reputation_high', 'multiple_models_career_results']}, {'id': 'legend_92', 'name': '🎉 傳奇級大型活動', 'requires': ['club_reputation_high', 'large_events_multiple', 'multiple_models']}, {'id': 'legend_93', 'name': '💎 頂級合作夥伴', 'requires': ['cooperation_success_multiple', 'club_reputation_high', 'club_crisis_handled']}, {'id': 'legend_94', 'name': '🚨 Moon Club 最大危機', 'requires': ['club_development_very_high', 'rare_random']}, {'id': 'legend_95', 'name': '👑 Moon Club 傳奇里程碑', 'requires': ['club_reputation_high', 'multiple_models_success', 'legend_92_or_93_completed']}, {'id': 'legend_96', 'name': '🌌 回到最開始的地方', 'requires': ['special_events_many', 'at_least_one_model_high_achievement']}, {'id': 'legend_97', 'name': '💕 最重要的那句話', 'requires': ['bond_extreme', 'relation_events_many']}, {'id': 'legend_98', 'name': '🌠 傳奇的選擇', 'requires': ['club_legend_stage', 'at_least_one_top_model', 'special_events_many']}, {'id': 'legend_99', 'name': '👑 Moon Club 的名字', 'requires': ['legend_98_completed', 'club_reputation_near_max', 'multiple_models_high_achievement']}, {'id': 'legend_100', 'name': '🌙 最終傳奇紀念', 'requires': ['legend_99_completed', 'major_events_many']}]

MOONCLUB_FULL_EVENT_DETAILS = {'bond_01': {'story': '在結束一天的行程後，你注意到他不像平常那樣立刻離開，而是在會館裡停留了一會兒。這件事並不是突如其來的偶然，而是建立在你們先前多次互動與共同經歷之上。當你主動關心時，他終於願意把真正的想法說出來。\n\n「💬 第一次真正的聊天」並不是單獨存在的事件，而是會依照目前的能力、個性、互動紀錄與已完成的重要經歷才有機會出現。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '不同選擇會帶來不同的能力、默契、知名度或後續事件影響；結果不會只改一句文字。', 'requires': ['chat_once'], 'once': True}, 'bond_02': {'story': '在結束一天的行程後，你注意到他不像平常那樣立刻離開，而是在會館裡停留了一會兒。這件事並不是突如其來的偶然，而是建立在你們先前多次互動與共同經歷之上。當你主動關心時，他終於願意把真正的想法說出來。\n\n「☕ 主動邀請喝咖啡」並不是單獨存在的事件，而是會依照目前的能力、個性、互動紀錄與已完成的重要經歷才有機會出現。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '不同選擇會帶來不同的能力、默契、知名度或後續事件影響；結果不會只改一句文字。', 'requires': ['bond_01', 'meal_twice'], 'once': True}, 'bond_03': {'story': '在結束一天的行程後，你注意到他不像平常那樣立刻離開，而是在會館裡停留了一會兒。這件事並不是突如其來的偶然，而是建立在你們先前多次互動與共同經歷之上。當你主動關心時，他終於願意把真正的想法說出來。\n\n「📱 第一次私人訊息」並不是單獨存在的事件，而是會依照目前的能力、個性、互動紀錄與已完成的重要經歷才有機會出現。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '不同選擇會帶來不同的能力、默契、知名度或後續事件影響；結果不會只改一句文字。', 'requires': ['bond_02', 'recent_interaction'], 'once': True}, 'bond_04': {'story': '在結束一天的行程後，你注意到他不像平常那樣立刻離開，而是在會館裡停留了一會兒。這件事並不是突如其來的偶然，而是建立在你們先前多次互動與共同經歷之上。當你主動關心時，他終於願意把真正的想法說出來。\n\n「🌧️ 情緒低落時找你」並不是單獨存在的事件，而是會依照目前的能力、個性、互動紀錄與已完成的重要經歷才有機會出現。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '不同選擇會帶來不同的能力、默契、知名度或後續事件影響；結果不會只改一句文字。', 'requires': ['recent_training_or_work', 'low_stamina_or_setback'], 'once': True}, 'bond_05': {'story': '在結束一天的行程後，你注意到他不像平常那樣立刻離開，而是在會館裡停留了一會兒。這件事並不是突如其來的偶然，而是建立在你們先前多次互動與共同經歷之上。當你主動關心時，他終於願意把真正的想法說出來。\n\n「🌙 深夜談心」並不是單獨存在的事件，而是會依照目前的能力、個性、互動紀錄與已完成的重要經歷才有機會出現。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '不同選擇會帶來不同的能力、默契、知名度或後續事件影響；結果不會只改一句文字。', 'requires': ['bond_04', 'chat_today'], 'once': True}, 'bond_06': {'story': '在結束一天的行程後，你注意到他不像平常那樣立刻離開，而是在會館裡停留了一會兒。這件事並不是突如其來的偶然，而是建立在你們先前多次互動與共同經歷之上。當你主動關心時，他終於願意把真正的想法說出來。\n\n「🤍 分享自己的秘密」並不是單獨存在的事件，而是會依照目前的能力、個性、互動紀錄與已完成的重要經歷才有機會出現。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '不同選擇會帶來不同的能力、默契、知名度或後續事件影響；結果不會只改一句文字。', 'requires': ['bond_05', 'multiple_chats'], 'once': True}, 'bond_07': {'story': '在結束一天的行程後，你注意到他不像平常那樣立刻離開，而是在會館裡停留了一會兒。這件事並不是突如其來的偶然，而是建立在你們先前多次互動與共同經歷之上。當你主動關心時，他終於願意把真正的想法說出來。\n\n「🥹 主動尋求你的意見」並不是單獨存在的事件，而是會依照目前的能力、個性、互動紀錄與已完成的重要經歷才有機會出現。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '不同選擇會帶來不同的能力、默契、知名度或後續事件影響；結果不會只改一句文字。', 'requires': ['bond_05', 'training_done', 'work_done'], 'once': True}, 'bond_08': {'story': '在結束一天的行程後，你注意到他不像平常那樣立刻離開，而是在會館裡停留了一會兒。這件事並不是突如其來的偶然，而是建立在你們先前多次互動與共同經歷之上。當你主動關心時，他終於願意把真正的想法說出來。\n\n「🎁 意外準備的小禮物」並不是單獨存在的事件，而是會依照目前的能力、個性、互動紀錄與已完成的重要經歷才有機會出現。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '不同選擇會帶來不同的能力、默契、知名度或後續事件影響；結果不會只改一句文字。', 'requires': ['gift_received', 'multiple_interactions'], 'once': True}, 'bond_09': {'story': '在結束一天的行程後，你注意到他不像平常那樣立刻離開，而是在會館裡停留了一會兒。這件事並不是突如其來的偶然，而是建立在你們先前多次互動與共同經歷之上。當你主動關心時，他終於願意把真正的想法說出來。\n\n「❤️ 關鍵時刻的信任」並不是單獨存在的事件，而是會依照目前的能力、個性、互動紀錄與已完成的重要經歷才有機會出現。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '不同選擇會帶來不同的能力、默契、知名度或後續事件影響；結果不會只改一句文字。', 'requires': ['bond_events_6', 'important_career_event'], 'once': True}, 'bond_10': {'story': '在結束一天的行程後，你注意到他不像平常那樣立刻離開，而是在會館裡停留了一會兒。這件事並不是突如其來的偶然，而是建立在你們先前多次互動與共同經歷之上。當你主動關心時，他終於願意把真正的想法說出來。\n\n「👑 靈魂搭檔」並不是單獨存在的事件，而是會依照目前的能力、個性、互動紀錄與已完成的重要經歷才有機會出現。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '不同選擇會帶來不同的能力、默契、知名度或後續事件影響；結果不會只改一句文字。', 'requires': ['bond_milestones', 'career_experience'], 'once': True}, 'training_11': {'story': '最近幾次培訓留下了明確的累積。這次機會出現時，他不再只是第一次嘗試的新手，而是必須把之前練習過的內容真正拿來面對結果。你需要決定是穩紮穩打，還是鼓勵他把握這次挑戰。\n\n「💇 意外成功的形象改造」並不是單獨存在的事件，而是會依照目前的能力、個性、互動紀錄與已完成的重要經歷才有機會出現。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '不同選擇會帶來不同的能力、默契、知名度或後續事件影響；結果不會只改一句文字。', 'requires': ['image_training_multiple', 'high_looks', 'last_training_image'], 'once': True}, 'training_12': {'story': '最近幾次培訓留下了明確的累積。這次機會出現時，他不再只是第一次嘗試的新手，而是必須把之前練習過的內容真正拿來面對結果。你需要決定是穩紮穩打，還是鼓勵他把握這次挑戰。\n\n「📸 攝影師注意到他」並不是單獨存在的事件，而是會依照目前的能力、個性、互動紀錄與已完成的重要經歷才有機會出現。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '不同選擇會帶來不同的能力、默契、知名度或後續事件影響；結果不會只改一句文字。', 'requires': ['image_training_or_promo', 'high_looks'], 'once': True}, 'training_13': {'story': '最近幾次培訓留下了明確的累積。這次機會出現時，他不再只是第一次嘗試的新手，而是必須把之前練習過的內容真正拿來面對結果。你需要決定是穩紮穩打，還是鼓勵他把握這次挑戰。\n\n「🗣️ 克服舞台緊張」並不是單獨存在的事件，而是會依照目前的能力、個性、互動紀錄與已完成的重要經歷才有機會出現。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '不同選擇會帶來不同的能力、默契、知名度或後續事件影響；結果不會只改一句文字。', 'requires': ['speech_training_multiple', 'recent_speech_training'], 'once': True}, 'training_14': {'story': '最近幾次培訓留下了明確的累積。這次機會出現時，他不再只是第一次嘗試的新手，而是必須把之前練習過的內容真正拿來面對結果。你需要決定是穩紮穩打，還是鼓勵他把握這次挑戰。\n\n「🎭 發現新的潛力」並不是單獨存在的事件，而是會依照目前的能力、個性、互動紀錄與已完成的重要經歷才有機會出現。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '不同選擇會帶來不同的能力、默契、知名度或後續事件影響；結果不會只改一句文字。', 'requires': ['same_training_multiple', 'related_stat_growth', 'no_formal_specialty'], 'once': True}, 'training_15': {'story': '最近幾次培訓留下了明確的累積。這次機會出現時，他不再只是第一次嘗試的新手，而是必須把之前練習過的內容真正拿來面對結果。你需要決定是穩紮穩打，還是鼓勵他把握這次挑戰。\n\n「🎓 培訓老師的特別評價」並不是單獨存在的事件，而是會依照目前的能力、個性、互動紀錄與已完成的重要經歷才有機會出現。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '不同選擇會帶來不同的能力、默契、知名度或後續事件影響；結果不會只改一句文字。', 'requires': ['training_count_threshold', 'two_stats_grown', 'recent_training'], 'once': True}, 'training_16': {'story': '最近幾次培訓留下了明確的累積。這次機會出現時，他不再只是第一次嘗試的新手，而是必須把之前練習過的內容真正拿來面對結果。你需要決定是穩紮穩打，還是鼓勵他把握這次挑戰。\n\n「💪 突破訓練瓶頸」並不是單獨存在的事件，而是會依照目前的能力、個性、互動紀錄與已完成的重要經歷才有機會出現。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '不同選擇會帶來不同的能力、默契、知名度或後續事件影響；結果不會只改一句文字。', 'requires': ['stat_plateau', 'continued_related_training'], 'once': True}, 'training_17': {'story': '最近幾次培訓留下了明確的累積。這次機會出現時，他不再只是第一次嘗試的新手，而是必須把之前練習過的內容真正拿來面對結果。你需要決定是穩紮穩打，還是鼓勵他把握這次挑戰。\n\n「😮 遇到培訓挫折」並不是單獨存在的事件，而是會依照目前的能力、個性、互動紀錄與已完成的重要經歷才有機會出現。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '不同選擇會帶來不同的能力、默契、知名度或後續事件影響；結果不會只改一句文字。', 'requires': ['continuous_training', 'low_stamina_or_poor_result'], 'once': True}, 'training_18': {'story': '最近幾次培訓留下了明確的累積。這次機會出現時，他不再只是第一次嘗試的新手，而是必須把之前練習過的內容真正拿來面對結果。你需要決定是穩紮穩打，還是鼓勵他把握這次挑戰。\n\n「🌟 獲得外部推薦」並不是單獨存在的事件，而是會依照目前的能力、個性、互動紀錄與已完成的重要經歷才有機會出現。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '不同選擇會帶來不同的能力、默契、知名度或後續事件影響；結果不會只改一句文字。', 'requires': ['training_multiple', 'high_related_stat', 'positive_teacher_review'], 'once': True}, 'training_19': {'story': '最近幾次培訓留下了明確的累積。這次機會出現時，他不再只是第一次嘗試的新手，而是必須把之前練習過的內容真正拿來面對結果。你需要決定是穩紮穩打，還是鼓勵他把握這次挑戰。\n\n「✉️ 收到特殊培訓邀請」並不是單獨存在的事件，而是會依照目前的能力、個性、互動紀錄與已完成的重要經歷才有機會出現。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '不同選擇會帶來不同的能力、默契、知名度或後續事件影響；結果不會只改一句文字。', 'requires': ['continuous_stat_growth', 'high_specialty_exposure', 'training_events_progress'], 'once': True}, 'training_20': {'story': '最近幾次培訓留下了明確的累積。這次機會出現時，他不再只是第一次嘗試的新手，而是必須把之前練習過的內容真正拿來面對結果。你需要決定是穩紮穩打，還是鼓勵他把握這次挑戰。\n\n「💥 一次重大的能力突破」並不是單獨存在的事件，而是會依照目前的能力、個性、互動紀錄與已完成的重要經歷才有機會出現。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '不同選擇會帶來不同的能力、默契、知名度或後續事件影響；結果不會只改一句文字。', 'requires': ['high_stat_threshold', 'long_term_related_training', 'breakthrough_or_special_training'], 'once': True}, 'specialty_21': {'story': '一次練習結束後，老師請他再唱一次剛才的片段，並第一次明確稱讚他的聲音特色。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '歌唱接觸度提升、才藝小幅提升，解鎖後續歌唱事件。', 'requires': ['talent_training_multiple', 'singing_exposure', 'talent_threshold'], 'once': True}, 'specialty_22': {'story': '培訓老師邀請他參加一堂舞蹈課，看看是否適合往新的方向發展。', 'choices': ['💃 鼓勵他參加', '🏛️ 先以目前培訓為主'], 'result': '不同選擇影響舞蹈接觸度與後續發展。', 'requires': ['dance_exposure', 'talent_training_multiple', 'talent_threshold'], 'once': True}, 'specialty_23': {'story': '長期訓練的成果開始被其他人注意，有人主動詢問他的訓練方式。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '健身接觸度提升、魅力與人氣小幅提升。', 'requires': ['fitness_training_multiple', 'appearance_or_charm_threshold'], 'once': True}, 'specialty_24': {'story': '一次普通聚會中，大家的注意力不知不覺集中到他身上，他成了帶動氣氛的人。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '社交接觸度提升、人氣提升，解鎖社交相關事件。', 'requires': ['speech_training_multiple', 'speech_threshold', 'social_interaction_history'], 'once': True}, 'specialty_25': {'story': '課程結束後，他停在一件樂器前，主動詢問是否能試試看。', 'choices': ['🎹 鼓勵他試試', '📚 建議先專注原本方向'], 'result': '選擇會影響樂器接觸度或原有專長方向的進度。', 'requires': ['talent_training_multiple', 'talent_threshold', 'specialty_slots_available'], 'once': True}, 'specialty_26': {'story': 'Moon Club 收到小型活動邀請，希望他參與演出，可能是第一次真正站上舞台。', 'choices': ['🌟 接受演出', '🏋️ 先繼續培訓'], 'result': '可獲得演出經驗、人氣與相關專長進度。', 'requires': ['talent_threshold', 'related_specialty_exposure', 'related_training_event'], 'once': True}, 'specialty_27': {'story': '長時間累積後，大家開始明白這不只是興趣，而是他真正擅長的事情。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '正式形成專長並寫入職涯紀錄。', 'requires': ['specialty_progress_threshold', 'related_stat_threshold', 'related_event_completed', 'specialty_slots_available'], 'once': True}, 'specialty_28': {'story': '曾經需要刻意思考的技巧開始變得自然，他明顯感覺自己進入新的階段。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '對應能力額外提升、專長發展進度增加。', 'requires': ['official_specialty', 'related_activity_history', 'related_stat_growth'], 'once': True}, 'specialty_29': {'story': '這次不只是老師稱讚，而是外界開始真正注意到他的能力。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '人氣提升、寫入職涯紀錄，解鎖更高階機會。', 'requires': ['official_specialty', 'high_related_stat', 'related_work_history'], 'once': True}, 'specialty_30': {'story': '一個重要機會主動找上門，對方不再只是詢問要不要試試，而是希望由他來。', 'choices': ['👑 接受重大挑戰', '🏛️ 穩定發展'], 'result': '選擇影響未來職涯風險、人氣與重大機會。', 'requires': ['mature_specialty', 'high_related_stat', 'specialty_29_completed', 'work_or_activity_experience'], 'once': True}, 'personality_31': {'story': '面對陌生人的熱情搭話，他禮貌地保持距離，但你發現他其實一直默默觀察周圍。', 'choices': ['🤍 尊重他的方式', '💬 鼓勵他多交流'], 'result': '影響高冷與社交傾向。', 'requires': ['cold_tendency_high', 'distance_choices_multiple'], 'once': True}, 'personality_32': {'story': '你忙了一整天，準備離開時才發現他還在等待，表示想陪你到工作結束。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '默契提升，忠誠／陪伴傾向加深。', 'requires': ['loyal_tendency_high', 'bond_threshold'], 'once': True}, 'personality_33': {'story': '他把飲料放到你旁邊，嘴上卻說只是剛好多買，否認自己特地準備。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '默契提升，傲嬌傾向加深。', 'requires': ['tsundere_tendency_high', 'bond_medium'], 'once': True}, 'personality_34': {'story': '他察覺你心情不好，沒有一直追問，只安靜表示：如果你想說，我可以聽。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '默契提升，溫柔傾向加深。', 'requires': ['gentle_tendency_high', 'interaction_history'], 'once': True}, 'personality_35': {'story': '這次不是你安排互動，而是他先主動詢問今天是否有空。', 'choices': ['🌳 一起出去', '📋 今天不方便'], 'result': '影響後續互動事件與主動傾向。', 'requires': ['active_tendency_high', 'bond_threshold'], 'once': True}, 'personality_36': {'story': '他似乎早就知道你會怎麼回答，讓你忍不住懷疑自己是不是被他的小心思帶著走。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '腹黑傾向提升，解鎖特殊對話。', 'requires': ['scheming_tendency_high', 'interaction_multiple'], 'once': True}, 'personality_37': {'story': '面對新的機會，他沒有衝動，也沒有退縮，而是平靜地說自己想試試。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '自信傾向提升，可能解鎖高階挑戰。', 'requires': ['confidence_tendency_high', 'positive_training_or_work'], 'once': True}, 'personality_38': {'story': '聊天中某個話題讓他突然沉默，只表示這件事以後再說，建立個人過去劇情線。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '解鎖後續個人背景事件。', 'requires': ['mysterious_tendency_high', 'bond_high', 'late_night_talk_completed'], 'once': True}, 'personality_39': {'story': '面對重要決定，他必須在謹慎與挑戰之間選擇。', 'choices': ['🛡️ 謹慎處理', '🔥 鼓勵挑戰'], 'result': '真正影響未來正式性格的形成方向。', 'requires': ['two_personality_tendencies_close', 'important_recent_event'], 'once': True}, 'personality_40': {'story': '經歷許多事情後，你發現他並不是只有一種樣子，而是逐漸展現出第二個鮮明面向。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '正式形成第二性格。', 'requires': ['primary_personality_formed', 'second_tendency_high', 'special_event_experience'], 'once': True}, 'career_41': {'story': 'Moon Club 收到一個小型正式工作邀約，對方對他很感興趣。', 'choices': ['📸 接受工作', '🏋️ 再培養一陣子'], 'result': '接受可獲得職涯經驗與人氣；繼續培養則獲得小幅能力成長。', 'requires': ['training_count_threshold', 'one_stat_threshold'], 'once': True}, 'career_42': {'story': '第一次真正站在公開活動中面對大家。', 'choices': ['🌟 接受挑戰', '🛡️ 暫時觀望'], 'result': '影響舞台經驗與自信傾向。', 'requires': ['work_history', 'popularity_basic', 'related_ability'], 'once': True}, 'career_43': {'story': '開始有人主動詢問 Moon Club 的新人最近是否有活動。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '人氣提升。', 'requires': ['recent_work_or_activity', 'not_high_popularity'], 'once': True}, 'career_44': {'story': '外部開始有人討論他的名字，代表他開始被更多人知道。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '人氣提升並解鎖更高階邀約。', 'requires': ['popularity_threshold', 'work_history_multiple'], 'once': True}, 'career_45': {'story': '一次工作中出現明顯失誤，需要面對與處理。', 'choices': ['🤍 安慰並檢討', '🏋️ 加強訓練'], 'result': '影響默契、能力與未來工作表現。', 'requires': ['work_history_multiple', 'low_energy_or_insufficient_ability'], 'once': True}, 'career_46': {'story': '有人正式肯定他的表現，認為他非常有潛力。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '人氣與自信提升，解鎖高級工作。', 'requires': ['career_experience', 'high_stat', 'positive_career_event'], 'once': True}, 'career_47': {'story': '開始出現不同類型的發展邀請，需要決定職涯方向。', 'choices': ['🌟 挑戰型發展', '🏛️ 穩定型發展'], 'result': '影響未來職涯事件池。', 'requires': ['popularity_threshold', 'official_specialty', 'work_history_multiple'], 'once': True}, 'career_48': {'story': 'Moon Club 收到規格更高的工作邀請。', 'choices': ['👑 接受挑戰', '🏋️ 先準備'], 'result': '成功後人氣與收入增加，並留下重要職涯紀錄。', 'requires': ['high_popularity', 'high_ability', 'professional_recognition'], 'once': True}, 'career_49': {'story': '近期密集行程讓他開始感到壓力與疲憊。', 'choices': ['🛋️ 安排休息', '🔥 鼓勵繼續'], 'result': '影響體力、未來工作成功率與默契。', 'requires': ['recent_work_dense', 'low_energy'], 'once': True}, 'career_50': {'story': '一個重大機會出現在眼前，可能真正改變未來職涯。', 'choices': ['👑 全力挑戰', '🏛️ 穩定累積'], 'result': '建立後續職涯發展方向。', 'requires': ['career_events_multiple', 'high_popularity', 'mature_specialty'], 'once': True}, 'life_51': {'story': '最近的培訓與工作累積讓他明顯疲憊。', 'choices': ['🛋️ 強制休息', '💬 詢問他的想法'], 'result': '影響體力與默契。', 'requires': ['low_energy', 'recent_training_or_work_multiple'], 'once': True}, 'life_52': {'story': '大家離開後，你發現他還留在安靜的 Moon Club 裡。', 'choices': ['💬 陪他聊天', '🏠 提醒他回家'], 'result': '可能觸發後續默契事件。', 'requires': ['night_interaction', 'bond_medium'], 'once': True}, 'life_53': {'story': '公開活動後，他收到一則奇怪的合作或邀請訊息。', 'choices': ['🔍 仔細確認', '❌ 直接拒絕'], 'result': '可能開啟後續事件或避免風險。', 'requires': ['public_activity_history', 'popularity_growth'], 'once': True}, 'life_54': {'story': 'Moon Club 達成里程碑或遇上特殊節日，舉辦小型慶祝活動。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '所有成員默契小幅提升，並可能觸發其他生活事件。', 'requires': ['club_milestone_or_special_day'], 'once': True}, 'life_55': {'story': '某天，一位意想不到的人來到 Moon Club。', 'choices': ['🤝 親自接待', '👀 先觀察'], 'result': '可能帶來新機會、新事件或特殊人物劇情。', 'requires': ['club_development_threshold', 'rare_random'], 'once': True}, 'life_56': {'story': '下雨天的外出途中發生一場偶遇。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '偏生活型事件，增加世界真實感並可能留下後續線索。', 'requires': ['outing_or_work_today', 'rare_random'], 'once': True}, 'life_57': {'story': '在他的生日，依照目前默契與經歷展開不同規模的慶祝。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '特殊紀念、默契提升並留下生日紀錄。', 'requires': ['model_birthday', 'not_completed'], 'once': True}, 'life_58': {'story': '休息日偶然遇到一位可能影響未來的人。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '可能是普通生活事件、新工作線索或特殊劇情。', 'requires': ['outing_history', 'rare_random'], 'once': True}, 'life_59': {'story': '他突然準備了一份小禮物，不同性格會有不同反應。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '默契提升，可能解鎖專屬紀念物。', 'requires': ['bond_medium_high', 'interaction_multiple'], 'once': True}, 'life_60': {'story': 'Moon Club 突然遇到活動取消、設備問題或工作安排改變。', 'choices': ['🔧 立刻處理', '📋 重新安排'], 'result': '影響會館發展、工作安排與後續事件。', 'requires': ['club_development_threshold', 'random_event'], 'once': True}, 'relation_61': {'story': '安靜相處時，他第一次主動表示有件事情一直沒有告訴別人。', 'choices': ['🤍 安靜聽他說', '💬 主動追問'], 'result': '影響個人故事線與默契。', 'requires': ['bond_high', 'deep_talk_history'], 'once': True}, 'relation_62': {'story': '深夜突然收到他的電話，他詢問你現在是否方便說話。', 'choices': ['📞 接起來', '💤 晚點再回覆'], 'result': '影響默契與主動／依賴傾向。', 'requires': ['bond_medium_high', 'life_interaction_history'], 'once': True}, 'relation_63': {'story': '他第一次明確不同意你的安排，雙方需要面對意見差異。', 'choices': ['🤝 聽他的想法', '📋 堅持原本安排'], 'result': '影響默契、自信與性格發展。', 'requires': ['bond_threshold', 'important_recent_choice'], 'once': True}, 'relation_64': {'story': '你發現他獨自安靜坐著，和平常完全不同。', 'choices': ['🤍 靜靜陪著', '🚶 給他空間'], 'result': '可能解鎖更深層個人故事。', 'requires': ['personal_background_event', 'mysterious_or_introvert_tendency'], 'once': True}, 'relation_65': {'story': '遇到重要事情時，他第一次主動表示自己相信你。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '大幅增加默契並解鎖高階關係事件。', 'requires': ['bond_high', 'relation_events_multiple'], 'once': True}, 'relation_66': {'story': '看到你明顯花很多時間關心其他男模後，他的反應開始有點不太自然。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '依不同性格產生不同對話與後續反應。', 'requires': ['bond_high', 'loyal_or_tsundere_or_active_tendency'], 'once': True}, 'relation_67': {'story': '下雨天的安靜時光裡，你們有了一次深入談心。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '可能解鎖個人回憶。', 'requires': ['rain_event_history', 'bond_medium_high'], 'once': True}, 'relation_68': {'story': '這一次，他主動提起以前的事情。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '個人背景故事正式開啟。', 'requires': ['personality_38_completed', 'relation_61_or_64_completed', 'bond_high'], 'once': True}, 'relation_69': {'story': '回頭才發現，你們的相處方式已經和剛開始完全不同。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '解鎖高階專屬互動。', 'requires': ['relation_events_multiple', 'bond_very_high'], 'once': True}, 'relation_70': {'story': '系統記錄下一個屬於你們的重要日子。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '留下專屬紀念、特殊紀錄並提升默契。', 'requires': ['bond_very_high', 'important_relation_events'], 'once': True}, 'club_71': {'story': '隨著多位成員累積成果，Moon Club 開始被更多人知道。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '提升或確認會館知名度進入小有名氣階段。', 'requires': ['multiple_models_popularity', 'club_work_count', 'reputation_100'], 'once': True}, 'club_72': {'story': 'Moon Club 收到正式合作訊息，希望邀請會館成員參與活動。', 'choices': ['🤝 接受合作', '🔍 先了解合作內容', '❌ 婉拒合作'], 'result': '影響會館知名度、活動收益、參與成員人氣與後續大型合作事件。', 'requires': ['reputation_250', 'club_work_or_activity_count', 'one_model_popularity'], 'once': True}, 'club_73': {'story': 'Moon Club 舉辦第一次真正的大型會館活動。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '參與成員人氣增加、可能提升成員關係，並留下大型活動紀錄。', 'requires': ['club_development_threshold', 'multiple_models', 'reputation_300'], 'once': True}, 'club_74': {'story': '兩位能力相近的男模開始暗暗比較彼此。', 'choices': ['🏆 舉辦友誼競賽', '🤝 鼓勵互相合作'], 'result': '影響成員關係與能力發展。', 'requires': ['at_least_two_models', 'ability_gap_small'], 'once': True}, 'club_75': {'story': '經過多次共同活動後，成員之間逐漸建立真正的友誼。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '建立或提升成員關係值。', 'requires': ['shared_activity_multiple'], 'once': True}, 'club_76': {'story': '近期工作減少或人氣下降，整個 Moon Club 的氣氛有些低迷。', 'choices': ['🎉 舉辦活動', '🏋️ 加強培訓', '🛋️ 暫時休息調整'], 'result': '影響會館知名度、成員狀態與後續發展。', 'requires': ['work_reduced_or_popularity_down_or_random'], 'once': True}, 'club_77': {'story': '某位成員因重大工作突然受到大量注意。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '會館知名度提升，但可能影響其他成員的心態。', 'requires': ['rapid_popularity_growth', 'major_work_completed'], 'once': True}, 'club_78': {'story': '多位男模共同參與團體合作活動。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '依合作成果提升友誼、人氣，或產生新的競爭線。', 'requires': ['at_least_two_models', 'member_relationship_threshold'], 'once': True}, 'club_79': {'story': 'Moon Club 遇到一個必須慎重處理的重要問題。', 'choices': ['🔧 自己處理', '🤝 尋求協助'], 'result': '影響會館發展與後續重大事件。', 'requires': ['club_development_high', 'rare_random', 'reputation_500'], 'once': True}, 'club_80': {'story': '回頭才發現，Moon Club 已經和最開始完全不同。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '解鎖高階活動、稀有職涯事件與 81～100 重大事件池。', 'requires': ['reputation_750', 'multiple_models_career_results', 'large_event_completed'], 'once': True}, 'legend_81': {'story': 'Moon Club 突然收到一份規格完全不同的重要活動邀請。', 'choices': ['👑 接受邀請', '🔍 先詳細了解', '🛡️ 婉拒'], 'result': '依選擇影響後續重大職涯機會。', 'requires': ['very_high_stat', 'official_specialty', 'high_popularity'], 'once': True}, 'legend_82': {'story': '出現一個需要離開熟悉環境、前往外地發展的大型機會。', 'choices': ['🌍 接受新挑戰', '🏛️ 留在 Moon Club 發展'], 'result': '形成不同職涯分支。', 'requires': ['legend_81_completed', 'mature_career', 'high_popularity'], 'once': True}, 'legend_83': {'story': '經歷許多工作後，他開始真正思考自己接下來想成為什麼樣的人。', 'choices': ['🌟 繼續衝刺', '🏛️ 穩定發展', '🌙 放慢腳步'], 'result': '影響最終職涯方向。', 'requires': ['major_career_events_multiple', 'mature_specialty', 'high_popularity'], 'once': True}, 'legend_84': {'story': '終於出現一個足以成為他代表作的重要工作。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '人氣大幅提升，建立代表作紀錄並解鎖頂級職涯事件。', 'requires': ['large_work_success_multiple', 'very_high_specialty'], 'once': True}, 'legend_85': {'story': '大家談到他時，不再只是稱呼 Moon Club 的男模，而是開始直接記住他的名字。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '個人知名度大幅提升並解鎖傳奇個人事件。', 'requires': ['high_popularity', 'representative_work', 'professional_recognition_multiple'], 'once': True}, 'legend_86': {'story': '收到目前為止規格最高的工作邀請。', 'choices': ['👑 全力接受', '🏋️ 延後準備'], 'result': '依準備與能力影響頂級工作的後續成果。', 'requires': ['legend_84_or_85_completed', 'high_popularity', 'high_ability'], 'once': True}, 'legend_87': {'story': '越接近巔峰，壓力與疲憊反而越來越明顯。', 'choices': ['🛋️ 休息調整', '🔥 繼續衝刺'], 'result': '影響頂級工作表現與後續職涯狀態。', 'requires': ['major_work_dense', 'low_energy'], 'once': True}, 'legend_88': {'story': '頂級工作完成後，獲得目前為止最高層級之一的專業評價。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '人氣大幅增加並建立頂級評價紀錄。', 'requires': ['top_work_completed', 'work_success', 'very_high_ability'], 'once': True}, 'legend_89': {'story': '這一刻，他真正站到了自己目前職涯的最高位置。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '進入職涯巔峰狀態。', 'requires': ['top_events_multiple', 'extreme_popularity', 'mature_specialty'], 'once': True}, 'legend_90': {'story': '長期累積的努力終於被正式認可。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '正式獲得 👑 頂級男模 稱號。', 'requires': ['career_peak', 'high_popularity', 'club_development_good'], 'once': True}, 'legend_91': {'story': '多位成員累積職涯成果後，Moon Club 正式進入高階知名會館階段。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '開啟更高階的會館發展內容。', 'requires': ['club_reputation_high', 'multiple_models_career_results'], 'once': True}, 'legend_92': {'story': 'Moon Club 舉辦一場真正具有代表性的傳奇級大型活動。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '參與成員人氣提升，建立重大活動紀錄，會館發展大幅推進。', 'requires': ['club_reputation_high', 'large_events_multiple', 'multiple_models'], 'once': True}, 'legend_93': {'story': 'Moon Club 收到真正長期合作夥伴的正式邀請。', 'choices': ['🤝 簽訂合作', '🔍 繼續觀察'], 'result': '影響長期合作線與會館發展。', 'requires': ['cooperation_success_multiple', 'club_reputation_high', 'club_crisis_handled'], 'once': True}, 'legend_94': {'story': '一次重大危機真正可能影響 Moon Club 未來。', 'choices': ['👑 全力處理', '🤝 尋求外部協助', '🛡️ 暫時縮小規模'], 'result': '不同選擇形成不同的會館發展結果。', 'requires': ['club_development_very_high', 'rare_random'], 'once': True}, 'legend_95': {'story': 'Moon Club 到達重要傳奇里程碑。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '解鎖最終傳奇事件線。', 'requires': ['club_reputation_high', 'multiple_models_success', 'legend_92_or_93_completed'], 'once': True}, 'legend_96': {'story': '某天回頭看，想起 Moon Club 最開始只是培養兩位新人。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '解鎖重要回憶紀錄。', 'requires': ['special_events_many', 'at_least_one_model_high_achievement'], 'once': True}, 'legend_97': {'story': '在極高默契與長期相處後，他說出一句最重要的話；不同性格會有不同內容。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '解鎖專屬最高階關係紀錄。', 'requires': ['bond_extreme', 'relation_events_many'], 'once': True}, 'legend_98': {'story': 'Moon Club 到達傳奇階段後，出現足以影響未來方向的重要選擇。', 'choices': ['👑 繼續擴張', '🏛️ 維持巔峰', '🌙 回歸最初'], 'result': '決定會館最終發展方向。', 'requires': ['club_legend_stage', 'at_least_one_top_model', 'special_events_many'], 'once': True}, 'legend_99': {'story': '你必須決定希望 Moon Club 最終被大家記住成什麼樣子。', 'choices': ['👑 傳奇會館', '💎 頂尖培養所', '🌙 最初的夢想'], 'result': '依發展方向建立不同最終稱號。', 'requires': ['legend_98_completed', 'club_reputation_near_max', 'multiple_models_high_achievement'], 'once': True}, 'legend_100': {'story': 'Moon Club 已經走過很長的路，而最初培養的兩位新人也早已不再是最開始的樣子。', 'choices': ['🌙 仔細了解後再決定', '💪 鼓勵他勇敢嘗試', '🛡️ 先保留並繼續準備'], 'result': '🌙 Moon Club 傳奇紀念達成；保留自由遊玩並開放後續擴充內容。', 'requires': ['legend_99_completed', 'major_events_many'], 'once': True}}

# 讓既有分區事件詳情與完整資料合併使用
def get_moonclub_event_detail(event_id):
    return MOONCLUB_FULL_EVENT_DETAILS.get(event_id, {})

MOONCLUB_ALL_EVENTS = [{'id': 'bond_01', 'name': '💬 第一次真正的聊天', 'bond': 50, 'requires': ['chat_once'], 'once': True}, {'id': 'bond_02', 'name': '☕ 主動邀請喝咖啡', 'bond': 150, 'requires': ['bond_01', 'meal_twice'], 'once': True}, {'id': 'bond_03', 'name': '📱 第一次私人訊息', 'bond': 250, 'requires': ['bond_02', 'recent_interaction'], 'once': True}, {'id': 'bond_04', 'name': '🌧️ 情緒低落時找你', 'bond': 350, 'requires': ['recent_training_or_work', 'low_stamina_or_setback'], 'once': True}, {'id': 'bond_05', 'name': '🌙 深夜談心', 'bond': 450, 'requires': ['bond_04', 'chat_today'], 'once': True}, {'id': 'bond_06', 'name': '🤍 分享自己的秘密', 'bond': 550, 'requires': ['bond_05', 'multiple_chats'], 'once': True}, {'id': 'bond_07', 'name': '🥹 主動尋求你的意見', 'bond': 650, 'requires': ['bond_05', 'training_done', 'work_done'], 'once': True}, {'id': 'bond_08', 'name': '🎁 意外準備的小禮物', 'bond': 750, 'requires': ['gift_received', 'multiple_interactions'], 'once': True}, {'id': 'bond_09', 'name': '❤️ 關鍵時刻的信任', 'bond': 850, 'requires': ['bond_events_6', 'important_career_event'], 'once': True}, {'id': 'bond_10', 'name': '👑 靈魂搭檔', 'bond': 1000, 'requires': ['bond_milestones', 'career_experience'], 'once': True}, {'id': 'training_11', 'name': '💇 意外成功的形象改造', 'requires': ['image_training_multiple', 'high_looks', 'last_training_image'], 'once': True}, {'id': 'training_12', 'name': '📸 攝影師注意到他', 'requires': ['image_training_or_promo', 'high_looks'], 'once': True}, {'id': 'training_13', 'name': '🗣️ 克服舞台緊張', 'requires': ['speech_training_multiple', 'recent_speech_training'], 'once': True}, {'id': 'training_14', 'name': '🎭 發現新的潛力', 'requires': ['same_training_multiple', 'related_stat_growth', 'no_formal_specialty'], 'once': True}, {'id': 'training_15', 'name': '🎓 培訓老師的特別評價', 'requires': ['training_count_threshold', 'two_stats_grown', 'recent_training'], 'once': True}, {'id': 'training_16', 'name': '💪 突破訓練瓶頸', 'requires': ['stat_plateau', 'continued_related_training'], 'once': True}, {'id': 'training_17', 'name': '😮 遇到培訓挫折', 'requires': ['continuous_training', 'low_stamina_or_poor_result'], 'once': True}, {'id': 'training_18', 'name': '🌟 獲得外部推薦', 'requires': ['training_multiple', 'high_related_stat', 'positive_teacher_review'], 'once': True}, {'id': 'training_19', 'name': '✉️ 收到特殊培訓邀請', 'requires': ['continuous_stat_growth', 'high_specialty_exposure', 'training_events_progress'], 'once': True}, {'id': 'training_20', 'name': '💥 一次重大的能力突破', 'requires': ['high_stat_threshold', 'long_term_related_training', 'breakthrough_or_special_training'], 'once': True}, {'id': 'specialty_21', 'name': '🎤 第一次被稱讚歌聲', 'requires': ['talent_training_multiple', 'singing_exposure', 'talent_threshold']}, {'id': 'specialty_22', 'name': '💃 舞蹈訓練的邀請', 'requires': ['dance_exposure', 'talent_training_multiple', 'talent_threshold']}, {'id': 'specialty_23', 'name': '🏋️ 健身成果受到注意', 'requires': ['fitness_training_multiple', 'appearance_or_charm_threshold']}, {'id': 'specialty_24', 'name': '🗣️ 意外成為氣氛中心', 'requires': ['speech_training_multiple', 'speech_threshold', 'social_interaction_history']}, {'id': 'specialty_25', 'name': '🎹 接觸新的樂器', 'requires': ['talent_training_multiple', 'talent_threshold', 'specialty_slots_available']}, {'id': 'specialty_26', 'name': '🎭 小型演出的機會', 'requires': ['talent_threshold', 'related_specialty_exposure', 'related_training_event']}, {'id': 'specialty_27', 'name': '🌟 專長正式形成', 'requires': ['specialty_progress_threshold', 'related_stat_threshold', 'related_event_completed', 'specialty_slots_available']}, {'id': 'specialty_28', 'name': '📈 專長能力突破', 'requires': ['official_specialty', 'related_activity_history', 'related_stat_growth']}, {'id': 'specialty_29', 'name': '🏆 因專長獲得肯定', 'requires': ['official_specialty', 'high_related_stat', 'related_work_history']}, {'id': 'specialty_30', 'name': '👑 專長帶來重大機會', 'requires': ['mature_specialty', 'high_related_stat', 'specialty_29_completed', 'work_or_activity_experience']}, {'id': 'personality_31', 'name': '❄️ 高冷的距離感', 'requires': ['cold_tendency_high', 'distance_choices_multiple']}, {'id': 'personality_32', 'name': '🐶 忠犬般的陪伴', 'requires': ['loyal_tendency_high', 'bond_threshold']}, {'id': 'personality_33', 'name': '🐱 傲嬌的關心', 'requires': ['tsundere_tendency_high', 'bond_medium']}, {'id': 'personality_34', 'name': '🥹 溫柔的安慰', 'requires': ['gentle_tendency_high', 'interaction_history']}, {'id': 'personality_35', 'name': '🔥 主動的邀請', 'requires': ['active_tendency_high', 'bond_threshold']}, {'id': 'personality_36', 'name': '😈 腹黑的小心思', 'requires': ['scheming_tendency_high', 'interaction_multiple']}, {'id': 'personality_37', 'name': '👑 自信的選擇', 'requires': ['confidence_tendency_high', 'positive_training_or_work']}, {'id': 'personality_38', 'name': '🌙 不願提起的過去', 'requires': ['mysterious_tendency_high', 'bond_high', 'late_night_talk_completed']}, {'id': 'personality_39', 'name': '⚖️ 性格的重要選擇', 'requires': ['two_personality_tendencies_close', 'important_recent_event']}, {'id': 'personality_40', 'name': '🌟 第二性格形成', 'requires': ['primary_personality_formed', 'second_tendency_high', 'special_event_experience']}, {'id': 'career_41', 'name': '📸 第一個正式工作邀約', 'requires': ['training_count_threshold', 'one_stat_threshold']}, {'id': 'career_42', 'name': '🎤 第一次公開活動', 'requires': ['work_history', 'popularity_basic', 'related_ability']}, {'id': 'career_43', 'name': '🌱 小幅人氣成長', 'requires': ['recent_work_or_activity', 'not_high_popularity']}, {'id': 'career_44', 'name': '📰 開始受到外界注意', 'requires': ['popularity_threshold', 'work_history_multiple']}, {'id': 'career_45', 'name': '😓 工作上的失誤', 'requires': ['work_history_multiple', 'low_energy_or_insufficient_ability']}, {'id': 'career_46', 'name': '🏆 獲得專業肯定', 'requires': ['career_experience', 'high_stat', 'positive_career_event']}, {'id': 'career_47', 'name': '⚖️ 職涯方向的選擇', 'requires': ['popularity_threshold', 'official_specialty', 'work_history_multiple']}, {'id': 'career_48', 'name': '💎 高級工作邀請', 'requires': ['high_popularity', 'high_ability', 'professional_recognition']}, {'id': 'career_49', 'name': '🌪️ 職涯壓力', 'requires': ['recent_work_dense', 'low_energy']}, {'id': 'career_50', 'name': '👑 職涯第一次重大轉折', 'requires': ['career_events_multiple', 'high_popularity', 'mature_specialty']}, {'id': 'life_51', 'name': '😴 過度疲勞', 'requires': ['low_energy', 'recent_training_or_work_multiple']}, {'id': 'life_52', 'name': '🌙 深夜還留在會館', 'requires': ['night_interaction', 'bond_medium']}, {'id': 'life_53', 'name': '📱 一則奇怪的訊息', 'requires': ['public_activity_history', 'popularity_growth']}, {'id': 'life_54', 'name': '🎉 Moon Club 的慶祝活動', 'requires': ['club_milestone_or_special_day']}, {'id': 'life_55', 'name': '✨ 意想不到的訪客', 'requires': ['club_development_threshold', 'rare_random']}, {'id': 'life_56', 'name': '🌧️ 下雨天的偶遇', 'requires': ['outing_or_work_today', 'rare_random']}, {'id': 'life_57', 'name': '🎂 特別的生日', 'requires': ['model_birthday', 'not_completed']}, {'id': 'life_58', 'name': '☕ 偶然的相遇', 'requires': ['outing_history', 'rare_random']}, {'id': 'life_59', 'name': '🎁 突然準備的禮物', 'requires': ['bond_medium_high', 'interaction_multiple']}, {'id': 'life_60', 'name': '🚨 Moon Club 突發事件', 'requires': ['club_development_threshold', 'random_event']}, {'id': 'relation_61', 'name': '🔐 第一次主動說出秘密', 'requires': ['bond_high', 'deep_talk_history']}, {'id': 'relation_62', 'name': '🌙 深夜的電話', 'requires': ['bond_medium_high', 'life_interaction_history']}, {'id': 'relation_63', 'name': '💭 意見不一致', 'requires': ['bond_threshold', 'important_recent_choice']}, {'id': 'relation_64', 'name': '🥀 一個人安靜的時候', 'requires': ['personal_background_event', 'mysterious_or_introvert_tendency']}, {'id': 'relation_65', 'name': '🤝 第一次真正的信任', 'requires': ['bond_high', 'relation_events_multiple']}, {'id': 'relation_66', 'name': '😤 小小的吃醋', 'requires': ['bond_high', 'loyal_or_tsundere_or_active_tendency']}, {'id': 'relation_67', 'name': '🌧️ 雨天的談心', 'requires': ['rain_event_history', 'bond_medium_high']}, {'id': 'relation_68', 'name': '📖 他第一次主動談起過去', 'requires': ['personality_38_completed', 'relation_61_or_64_completed', 'bond_high']}, {'id': 'relation_69', 'name': '🌱 關係的重要轉變', 'requires': ['relation_events_multiple', 'bond_very_high']}, {'id': 'relation_70', 'name': '💫 專屬紀念日', 'requires': ['bond_very_high', 'important_relation_events']}, {'id': 'club_71', 'name': '🏛️ Moon Club 開始有名氣', 'requires': ['multiple_models_popularity', 'club_work_count', 'reputation_100']}, {'id': 'club_72', 'name': '💌 收到合作邀請', 'requires': ['reputation_250', 'club_work_or_activity_count', 'one_model_popularity']}, {'id': 'club_73', 'name': '🎉 第一次大型會館活動', 'requires': ['club_development_threshold', 'multiple_models', 'reputation_300']}, {'id': 'club_74', 'name': '⚡ 男模之間的小競爭', 'requires': ['at_least_two_models', 'ability_gap_small']}, {'id': 'club_75', 'name': '🤝 男模之間建立友誼', 'requires': ['shared_activity_multiple']}, {'id': 'club_76', 'name': '📉 Moon Club 遇到低潮', 'requires': ['work_reduced_or_popularity_down_or_random']}, {'id': 'club_77', 'name': '🌟 一位成員突然爆紅', 'requires': ['rapid_popularity_growth', 'major_work_completed']}, {'id': 'club_78', 'name': '🎭 團體合作活動', 'requires': ['at_least_two_models', 'member_relationship_threshold']}, {'id': 'club_79', 'name': '🚨 會館的重要危機', 'requires': ['club_development_high', 'rare_random', 'reputation_500']}, {'id': 'club_80', 'name': '👑 Moon Club 的重要里程碑', 'requires': ['reputation_750', 'multiple_models_career_results', 'large_event_completed']}, {'id': 'legend_81', 'name': '✨ 意外的大型邀請', 'requires': ['very_high_stat', 'official_specialty', 'high_popularity']}, {'id': 'legend_82', 'name': '🌍 外地大型發展機會', 'requires': ['legend_81_completed', 'mature_career', 'high_popularity']}, {'id': 'legend_83', 'name': '🎯 生涯的重要決定', 'requires': ['major_career_events_multiple', 'mature_specialty', 'high_popularity']}, {'id': 'legend_84', 'name': '🏆 個人代表作', 'requires': ['large_work_success_multiple', 'very_high_specialty']}, {'id': 'legend_85', 'name': '💫 被真正記住的名字', 'requires': ['high_popularity', 'representative_work', 'professional_recognition_multiple']}, {'id': 'legend_86', 'name': '💎 頂級工作邀請', 'requires': ['legend_84_or_85_completed', 'high_popularity', 'high_ability']}, {'id': 'legend_87', 'name': '⚡ 巔峰前的壓力', 'requires': ['major_work_dense', 'low_energy']}, {'id': 'legend_88', 'name': '🥇 頂級評價', 'requires': ['top_work_completed', 'work_success', 'very_high_ability']}, {'id': 'legend_89', 'name': '🌟 職涯巔峰', 'requires': ['top_events_multiple', 'extreme_popularity', 'mature_specialty']}, {'id': 'legend_90', 'name': '👑 頂級男模稱號', 'requires': ['career_peak', 'high_popularity', 'club_development_good']}, {'id': 'legend_91', 'name': '🌟 Moon Club 成為知名會館', 'requires': ['club_reputation_high', 'multiple_models_career_results']}, {'id': 'legend_92', 'name': '🎉 傳奇級大型活動', 'requires': ['club_reputation_high', 'large_events_multiple', 'multiple_models']}, {'id': 'legend_93', 'name': '💎 頂級合作夥伴', 'requires': ['cooperation_success_multiple', 'club_reputation_high', 'club_crisis_handled']}, {'id': 'legend_94', 'name': '🚨 Moon Club 最大危機', 'requires': ['club_development_very_high', 'rare_random']}, {'id': 'legend_95', 'name': '👑 Moon Club 傳奇里程碑', 'requires': ['club_reputation_high', 'multiple_models_success', 'legend_92_or_93_completed']}, {'id': 'legend_96', 'name': '🌌 回到最開始的地方', 'requires': ['special_events_many', 'at_least_one_model_high_achievement']}, {'id': 'legend_97', 'name': '💕 最重要的那句話', 'requires': ['bond_extreme', 'relation_events_many']}, {'id': 'legend_98', 'name': '🌠 傳奇的選擇', 'requires': ['club_legend_stage', 'at_least_one_top_model', 'special_events_many']}, {'id': 'legend_99', 'name': '👑 Moon Club 的名字', 'requires': ['legend_98_completed', 'club_reputation_near_max', 'multiple_models_high_achievement']}, {'id': 'legend_100', 'name': '🌙 最終傳奇紀念', 'requires': ['legend_99_completed', 'major_events_many']}]


# ==========================================================
# 🌙 Moon Life 系統相容入口
# main.py 使用此名稱載入 Moon Club 系統
# ==========================================================
def setup_moon_life(bot):
    return setup_moon_club(bot)
