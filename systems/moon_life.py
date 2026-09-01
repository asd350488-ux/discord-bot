# -*- coding: utf-8 -*-
# ==========================================================
# 🌙 Moon Life｜完整獨立系統
# 放置位置：systems/moon_life.py
#
# main.py：
# from systems.moon_life import setup_moon_life
# setup_moon_life(bot)
# ==========================================================

import random
from datetime import datetime, timezone

import discord
from discord import app_commands

try:
    from database import conn, c
except ImportError:
    raise ImportError("❌ Moon Life 無法載入 database.py 的 conn、c")

try:
    from config import BOT_ADMINS
except ImportError:
    BOT_ADMINS = []
    print("⚠️ Moon Life 無法載入 config.py 的 BOT_ADMINS，管理員測試無限體力功能已停用。")

# ==========================================================
# ⚙️ 基本設定
# ==========================================================

MOONLIFE_COLOR = 0xB9A7E8

# 🧪 Moon Life 專用測試人員
# 測試期間購買 Moon Life 商店物品／體力時不扣努努幣。
MOONLIFE_TESTERS = {
    871398865012666389,
}

def is_moonlife_tester(user_id):
    return int(user_id) in MOONLIFE_TESTERS

MAX_NATURAL_STAMINA = 10
STAMINA_RECOVER_SECONDS = 3600

GROWTH_PER_MONTH = 100
ADULT_AGE = 18

INTERESTS = ["繪畫", "音樂", "運動", "閱讀", "自然", "探索"]

STAT_EMOJIS = {
    "intelligence": "🧠",
    "emotion": "❤️",
    "fitness": "💪",
    "creativity": "🎨",
    "social": "✨",
}

PERSONALITY_EMOJIS = {
    "活潑": "😄",
    "害羞": "😳",
    "溫柔": "🥹",
    "調皮": "😂",
    "好奇": "🤔",
    "勇敢": "💪",
    "獨立": "🌱",
    "黏人": "❤️",
}

ITEMS = {
    # 🧸 玩具／學習用品：可從背包實際使用
    "玩偶": {"price": 300, "type": "toy", "durability": 20, "desc": "陪伴孩子玩耍的小玩偶。", "relationship": 2, "emotion": 1},
    "球": {"price": 300, "type": "toy", "durability": 30, "desc": "適合跑跳與運動。", "fitness": 2, "interest": "運動", "interest_gain": 8},
    "拼圖": {"price": 400, "type": "toy", "durability": 15, "desc": "動動腦的小遊戲。", "intelligence": 2},
    "畫具": {"price": 500, "type": "toy", "durability": 20, "desc": "開始創作的畫具。", "creativity": 2, "interest": "繪畫", "interest_gain": 8},
    "故事書": {"price": 450, "type": "toy", "durability": 30, "desc": "一起閱讀的故事書。", "intelligence": 2, "interest": "閱讀", "interest_gain": 8},

    # 🍼🍱 食物：依孩子年齡選擇，不能亂餵
    "配方奶": {"price": 80, "type": "food", "hunger": 35, "relationship": 2, "emotion": 1, "min_age": 0, "max_age": 1, "food_stage": "嬰兒", "desc": "👶 0～1歲適用。溫暖的一瓶奶，適合還在喝奶的孩子。"},
    "嬰兒副食品": {"price": 110, "type": "food", "hunger": 28, "emotion": 1, "min_age": 0, "max_age": 1, "food_stage": "嬰兒", "desc": "🥣 0～1歲適用。軟嫩好入口的嬰兒副食品。"},
    "幼兒粥": {"price": 140, "type": "food", "hunger": 32, "relationship": 1, "min_age": 1, "max_age": 3, "food_stage": "幼兒", "desc": "🥣 1～3歲適用。溫暖又容易入口的一餐。"},
    "香蕉": {"price": 90, "type": "food", "hunger": 16, "emotion": 1, "min_age": 1, "max_age": 4, "food_stage": "幼兒", "desc": "🍌 1～4歲適用。簡單方便的小點心。"},
    "水果": {"price": 120, "type": "food", "hunger": 20, "relationship": 1, "emotion": 1, "min_age": 2, "food_stage": "兒童", "desc": "🍎 2歲以上。清爽的水果，恢復一些飢餓並讓心情變好。"},
    "麵包": {"price": 100, "type": "food", "hunger": 15, "min_age": 3, "food_stage": "兒童", "desc": "🥖 3歲以上。簡單又方便的小點心。"},
    "小蛋糕": {"price": 500, "type": "food", "hunger": 25, "emotion": 3, "relationship": 1, "min_age": 3, "food_stage": "兒童", "desc": "🧁 3歲以上。甜甜的親子點心，除了填飽肚子也能帶來好心情。"},
    "便當": {"price": 300, "type": "food", "hunger": 45, "relationship": 1, "min_age": 4, "food_stage": "兒童", "desc": "🍱 4歲以上。好好吃一頓，能大幅緩解飢餓。"},
    "糖果": {"price": 80, "type": "food", "hunger": 8, "emotion": 1, "min_age": 5, "food_stage": "兒童", "desc": "🍬 5歲以上。少量甜食，只能稍微止餓。"},

    # 🎁 特殊物品
    "氣球": {"price": 250, "type": "special", "desc": "可能帶來特別的回憶。"},
    "禮物": {"price": 800, "type": "special", "desc": "送給孩子的小驚喜。"},
    "生日蛋糕": {"price": 1000, "type": "birthday", "hunger": 20, "emotion": 5, "relationship": 3, "desc": "在孩子生日月一起慶祝，留下特別的生日回憶。"},
}


# ==========================================================
# 🗃️ 資料庫
# ==========================================================

def init_moonlife_tables():
    c.execute("""
        CREATE TABLE IF NOT EXISTS moonlife_players (
            user_id TEXT PRIMARY KEY,
            parent_name TEXT NOT NULL,
            parent_identity TEXT NOT NULL,
            stamina INTEGER NOT NULL DEFAULT 10,
            stamina_updated_at TEXT,
            daily_stamina_buys INTEGER NOT NULL DEFAULT 0,
            stamina_buy_date TEXT,
            current_child_id INTEGER,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS moonlife_children (
            child_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            parent_name TEXT NOT NULL,
            parent_identity TEXT NOT NULL,
            name TEXT NOT NULL,
            gender TEXT NOT NULL,
            age_year INTEGER NOT NULL DEFAULT 0,
            age_month INTEGER NOT NULL DEFAULT 1,
            growth INTEGER NOT NULL DEFAULT 0,
            intelligence INTEGER NOT NULL DEFAULT 5,
            emotion INTEGER NOT NULL DEFAULT 5,
            fitness INTEGER NOT NULL DEFAULT 5,
            creativity INTEGER NOT NULL DEFAULT 5,
            social INTEGER NOT NULL DEFAULT 5,
            relationship INTEGER NOT NULL DEFAULT 25,
            hunger INTEGER NOT NULL DEFAULT 20,
            personality_scores TEXT NOT NULL DEFAULT '{}',
            personalities TEXT NOT NULL DEFAULT '[]',
            interests TEXT NOT NULL DEFAULT '[]',
            interest_progress TEXT NOT NULL DEFAULT '{}',
            experiences TEXT NOT NULL DEFAULT '{}',
            is_adult INTEGER NOT NULL DEFAULT 0,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS moonlife_inventory (
            user_id TEXT NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, item_name)
        )
    """)

    # 舊資料庫升級：耐久度欄位不存在時自動補上
    columns = {row[1] for row in c.execute("PRAGMA table_info(moonlife_inventory)").fetchall()}
    if "durability" not in columns:
        c.execute("ALTER TABLE moonlife_inventory ADD COLUMN durability INTEGER")
    if "max_durability" not in columns:
        c.execute("ALTER TABLE moonlife_inventory ADD COLUMN max_durability INTEGER")

    c.execute("""
        CREATE TABLE IF NOT EXISTS moonlife_memories (
            memory_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            child_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS moonlife_daily (
            user_id TEXT PRIMARY KEY,
            game_day INTEGER NOT NULL DEFAULT 1,
            last_day_at TEXT,
            care_done INTEGER NOT NULL DEFAULT 0,
            play_done INTEGER NOT NULL DEFAULT 0,
            outside_done INTEGER NOT NULL DEFAULT 0
        )
    """)

    conn.commit()


# ==========================================================
# 🕒 工具
# ==========================================================

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def clamp(value, low, high):
    return max(low, min(high, value))

def parse_json(text, default):
    import json
    try:
        return json.loads(text) if text else default
    except Exception:
        return default

def dump_json(data):
    import json
    return json.dumps(data, ensure_ascii=False)

def identity_emoji(identity):
    return {"男": "👨", "女": "👩", "貓": "🐱", "狗": "🐶"}.get(identity, "👤")

def gender_emoji(gender):
    return "👦" if gender == "男" else "👧"

def get_player(user_id):
    c.execute("SELECT * FROM moonlife_players WHERE user_id=?", (str(user_id),))
    return c.fetchone()

def get_child(user_id):
    c.execute("""
        SELECT ch.*
        FROM moonlife_players p
        JOIN moonlife_children ch ON p.current_child_id = ch.child_id
        WHERE p.user_id=?
    """, (str(user_id),))
    return c.fetchone()

def child_dict(row):
    if not row:
        return None
    cols = [x[0] for x in c.description]
    return dict(zip(cols, row))

def get_daily(user_id):
    c.execute("SELECT * FROM moonlife_daily WHERE user_id=?", (str(user_id),))
    row = c.fetchone()
    if not row:
        c.execute(
            "INSERT INTO moonlife_daily (user_id, game_day, last_day_at) VALUES (?, 1, ?)",
            (str(user_id), now_iso())
        )
        conn.commit()
        c.execute("SELECT * FROM moonlife_daily WHERE user_id=?", (str(user_id),))
        row = c.fetchone()
    return row

def update_stamina(user_id):
    player = get_player(user_id)
    if not player:
        return None

    c.execute("""
        SELECT stamina, stamina_updated_at
        FROM moonlife_players WHERE user_id=?
    """, (str(user_id),))
    row = c.fetchone()
    if not row:
        return None
    stamina, updated = row
    stamina = int(stamina)

    now = datetime.now(timezone.utc)

    # 購買後超過自然上限時完全停止自然恢復。
    if stamina >= MAX_NATURAL_STAMINA:
        return stamina

    try:
        old = datetime.fromisoformat(updated) if updated else now
    except Exception:
        old = now

    elapsed = max(0, int((now - old).total_seconds()))
    recovered = elapsed // STAMINA_RECOVER_SECONDS
    if recovered > 0:
        stamina = min(MAX_NATURAL_STAMINA, stamina + recovered)
        consumed_seconds = recovered * STAMINA_RECOVER_SECONDS
        new_time = datetime.fromtimestamp(old.timestamp() + consumed_seconds, tz=timezone.utc)
        c.execute(
            "UPDATE moonlife_players SET stamina=?, stamina_updated_at=? WHERE user_id=?",
            (stamina, new_time.isoformat(), str(user_id))
        )
        conn.commit()
    return stamina

def use_stamina(user_id, amount):
    stamina = update_stamina(user_id)
    if stamina is None or stamina < amount:
        return False

    new_stamina = stamina - amount
    # 從 >=10 降到 <10 的瞬間，才重新開始計算自然恢復時間。
    c.execute("SELECT stamina FROM moonlife_players WHERE user_id=?", (str(user_id),))
    old_stamina = int(c.fetchone()[0])
    if old_stamina >= MAX_NATURAL_STAMINA and new_stamina < MAX_NATURAL_STAMINA:
        updated_at = now_iso()
        c.execute(
            "UPDATE moonlife_players SET stamina=?, stamina_updated_at=? WHERE user_id=?",
            (new_stamina, updated_at, str(user_id))
        )
    else:
        c.execute(
            "UPDATE moonlife_players SET stamina=? WHERE user_id=?",
            (new_stamina, str(user_id))
        )
    conn.commit()
    return True

def add_memory(user_id, child_id, title, content):
    c.execute("""
        INSERT INTO moonlife_memories
        (user_id, child_id, title, content, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (str(user_id), child_id, title, content, now_iso()))
    conn.commit()

def change_child(child_id, **changes):
    allowed = {
        "growth", "intelligence", "emotion", "fitness", "creativity",
        "social", "relationship", "hunger", "age_year", "age_month",
        "personality_scores", "personalities", "interests",
        "interest_progress", "experiences", "is_adult"
    }
    fields = []
    values = []
    for key, value in changes.items():
        if key not in allowed:
            continue
        if key in {"intelligence", "emotion", "fitness", "creativity", "social"}:
            value = clamp(int(value), 0, 100)
        if key == "relationship":
            value = clamp(int(value), 0, 100)
        if key == "hunger":
            value = clamp(int(value), 0, 100)
        fields.append(f"{key}=?")
        values.append(value)

    if fields:
        values.append(child_id)
        c.execute(
            f"UPDATE moonlife_children SET {', '.join(fields)} WHERE child_id=?",
            tuple(values)
        )
        conn.commit()

def get_money(user_id):
    c.execute("SELECT money FROM users WHERE user_id=?", (str(user_id),))
    row = c.fetchone()
    if not row:
        return 0
    return int(row["money"])

def remove_money(user_id, amount):
    amount = int(amount)
    if amount <= 0:
        return False

    # 🧪 Moon Life 測試人員：所有 Moon Life 扣款免費。
    if is_moonlife_tester(user_id):
        return True

    c.execute("""
        UPDATE users
        SET money = money - ?
        WHERE user_id=? AND money >= ?
    """, (amount, str(user_id), amount))
    success = c.rowcount > 0
    conn.commit()
    return success

def is_durable_item(item_name):
    return ITEMS.get(item_name, {}).get("type") == "toy"

def add_inventory(user_id, item_name, amount=1):
    """食物／特殊物品累加數量；玩具用品建立可重複使用的耐久物品。"""
    user_id = str(user_id)
    item = ITEMS.get(item_name, {})
    if is_durable_item(item_name):
        max_durability = int(item.get("durability", 20))
        c.execute("""
            INSERT INTO moonlife_inventory
            (user_id, item_name, quantity, durability, max_durability)
            VALUES (?, ?, 1, ?, ?)
            ON CONFLICT(user_id, item_name)
            DO UPDATE SET
                quantity=1,
                durability=excluded.max_durability,
                max_durability=excluded.max_durability
        """, (user_id, item_name, max_durability, max_durability))
    else:
        c.execute("""
            INSERT INTO moonlife_inventory (user_id, item_name, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, item_name)
            DO UPDATE SET quantity=quantity+excluded.quantity
        """, (user_id, item_name, amount))
    conn.commit()

def remove_inventory(user_id, item_name, amount=1):
    c.execute("""
        SELECT quantity FROM moonlife_inventory
        WHERE user_id=? AND item_name=?
    """, (str(user_id), item_name))
    row = c.fetchone()
    if not row or row[0] < amount:
        return False
    new_qty = row[0] - amount
    if new_qty <= 0:
        c.execute("DELETE FROM moonlife_inventory WHERE user_id=? AND item_name=?", (str(user_id), item_name))
    else:
        c.execute("UPDATE moonlife_inventory SET quantity=? WHERE user_id=? AND item_name=?",
                  (new_qty, str(user_id), item_name))
    conn.commit()
    return True

def use_durability(user_id, item_name):
    c.execute("""
        SELECT durability, max_durability FROM moonlife_inventory
        WHERE user_id=? AND item_name=?
    """, (str(user_id), item_name))
    row = c.fetchone()
    if not row or row[0] is None or int(row[0]) <= 0:
        return False, 0, 0
    durability = int(row[0]) - 1
    max_durability = int(row[1] or ITEMS.get(item_name, {}).get("durability", 20))
    c.execute("""
        UPDATE moonlife_inventory SET durability=?, max_durability=?
        WHERE user_id=? AND item_name=?
    """, (durability, max_durability, str(user_id), item_name))
    conn.commit()
    return True, durability, max_durability


# ==========================================================
# 🌱 成長、個性、興趣
# ==========================================================

def add_growth(user_id, child, amount):
    growth = child["growth"] + amount
    age_year = child["age_year"]
    age_month = child["age_month"]

    months_gained = growth // GROWTH_PER_MONTH
    growth %= GROWTH_PER_MONTH

    if months_gained:
        age_month += months_gained
        while age_month > 12:
            age_month -= 12
            age_year += 1

    adult = 1 if age_year >= ADULT_AGE else 0

    change_child(
        child["child_id"],
        growth=growth,
        age_year=age_year,
        age_month=age_month,
        is_adult=adult
    )

    if adult:
        c.execute("""
            UPDATE moonlife_players
            SET current_child_id=NULL
            WHERE user_id=?
        """, (str(user_id),))
        conn.commit()
        add_memory(
            user_id,
            child["child_id"],
            "🌙 成年了",
            f"{child['name']} 已經 {ADULT_AGE} 歲，正式成年。"
        )
        return True

    return False

def add_personality_progress(child, personality, amount):
    scores = parse_json(child["personality_scores"], {})
    scores[personality] = int(scores.get(personality, 0)) + amount

    personalities = parse_json(child["personalities"], [])
    if child["age_year"] >= 6 and personality not in personalities and len(personalities) < 3:
        if scores[personality] >= 30:
            personalities.append(personality)

    change_child(
        child["child_id"],
        personality_scores=dump_json(scores),
        personalities=dump_json(personalities)
    )

def add_interest_progress(child, interest, amount):
    progress = parse_json(child["interest_progress"], {})
    progress[interest] = int(progress.get(interest, 0)) + amount

    interests = parse_json(child["interests"], [])
    discovered = None

    # 合理規則：至少有相關接觸累積 + 相關素質
    stat_ok = True
    if interest == "繪畫":
        stat_ok = child["creativity"] >= 15
    elif interest == "音樂":
        stat_ok = child["creativity"] >= 15
    elif interest == "運動":
        stat_ok = child["fitness"] >= 15
    elif interest == "閱讀":
        stat_ok = child["intelligence"] >= 15
    elif interest == "自然":
        stat_ok = child["emotion"] >= 10
    elif interest == "探索":
        stat_ok = child["intelligence"] >= 10

    if (
        interest not in interests
        and len(interests) < 3
        and child["age_year"] >= 3
        and progress[interest] >= 25
        and stat_ok
    ):
        interests.append(interest)
        discovered = interest

    change_child(
        child["child_id"],
        interest_progress=dump_json(progress),
        interests=dump_json(interests)
    )
    return discovered

def hunger_text(child):
    hunger = child["hunger"]
    name = child["name"]

    if hunger >= 80:
        return f"😭 {name}看起來非常餓了……"
    if hunger >= 60:
        return f"🥺 {name}摸了摸肚子：「我餓餓……」"
    if hunger >= 40:
        return f"🙂 {name}看起來有點想吃東西。"
    return f"😊 {name}目前看起來精神不錯。"

def relationship_name(value):
    if value >= 90:
        return "💕 無可取代"
    if value >= 65:
        return "❤️ 信任"
    if value >= 40:
        return "😊 親近"
    if value >= 15:
        return "🌱 熟悉"
    return "🤍 陌生"

def stat_level(value):
    if value >= 80:
        return "🌟 非常突出"
    if value >= 50:
        return "⭐ 擅長"
    if value >= 20:
        return "🙂 普通"
    return "🌱 剛開始發展"


# ==========================================================
# 👶 領養流程
# ==========================================================

class AdoptionModal(discord.ui.Modal, title="🌙 Moon Life｜領養孩子"):
    # 第一階段只填家長名字，先抽孩子性別後才取名。
    parent_name = discord.ui.TextInput(
        label="請輸入你在 Moon Life 裡的名字",
        max_length=30
    )

    def __init__(self, identity):
        super().__init__()
        self.identity = identity

    async def on_submit(self, interaction: discord.Interaction):
        parent_name = str(self.parent_name.value).strip()

        if not parent_name:
            await interaction.response.send_message("❌ 請先輸入你的名字。", ephemeral=True)
            return

        # 👶 先由系統抽中孩子性別，再進入命名階段。
        gender = random.choice(["男", "女"])
        gender_text = "男孩 👦" if gender == "男" else "女孩 👧"

        # Modal 提交後不直接再開第二個 Modal。
        # 部分 Discord API 環境會讓「Modal → Modal」回應出現 Invalid Form Body。
        # 改成先顯示抽中的性別，再由按鈕開啟命名視窗。
        await interaction.response.send_message(
            f"🎉 **抽中了！你的孩子是 {gender_text}**\n\n"
            "現在你已經知道孩子的性別，可以幫孩子取名字了 ❤️",
            view=ChildNamingStartView(
                identity=self.identity,
                parent_name=parent_name,
                gender=gender
            ),
            ephemeral=True
        )


class ChildNamingStartView(discord.ui.View):
    """顯示性別後，由新的按鈕互動開啟命名 Modal，避免 Modal→Modal API 問題。"""

    def __init__(self, identity, parent_name, gender):
        super().__init__(timeout=300)
        self.identity = identity
        self.parent_name = parent_name
        self.gender = gender

    @discord.ui.button(label="✏️ 幫孩子取名字", style=discord.ButtonStyle.primary)
    async def name_child(self, interaction, button):
        await interaction.response.send_modal(
            ChildNamingModal(
                identity=self.identity,
                parent_name=self.parent_name,
                gender=self.gender
            )
        )


class ChildNamingModal(discord.ui.Modal, title="🎉 Moon Life｜幫孩子取名字"):
    # 和第一個領養表單使用相同的固定 TextInput 結構，
    # 避免 Modal 元件在部分 Discord API 環境中動態 add_item 出錯。
    child_name = discord.ui.TextInput(
        label="請輸入孩子的名字",
        placeholder="現在知道孩子性別後，再幫孩子取名字吧！",
        max_length=30
    )

    def __init__(self, identity, parent_name, gender):
        super().__init__()
        self.identity = identity
        self.parent_name = parent_name
        self.gender = gender

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        child_name = str(self.child_name.value).strip()

        if not child_name:
            await interaction.response.send_message(
                "❌ 請先幫孩子取一個名字。",
                ephemeral=True
            )
            return

        c.execute("""
            SELECT current_child_id FROM moonlife_players
            WHERE user_id=?
        """, (user_id,))
        old = c.fetchone()

        if old and old[0]:
            c.execute("""
                SELECT is_adult FROM moonlife_children
                WHERE child_id=?
            """, (old[0],))
            row = c.fetchone()
            if row and not row[0]:
                await interaction.response.send_message(
                    "❌ 你目前還有一位未成年的孩子，成年後才能再次領養。",
                    ephemeral=True
                )
                return

        stats = [random.randint(3, 8) for _ in range(5)]

        personality_scores = {
            p: random.randint(0, 8)
            for p in PERSONALITY_EMOJIS
        }

        c.execute("""
            INSERT INTO moonlife_children (
                user_id, parent_name, parent_identity,
                name, gender,
                intelligence, emotion, fitness, creativity, social,
                relationship, hunger,
                personality_scores, personalities,
                interests, interest_progress, experiences,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            self.parent_name,
            self.identity,
            child_name,
            self.gender,
            stats[0], stats[1], stats[2], stats[3], stats[4],
            25,
            20,
            dump_json(personality_scores),
            "[]",
            "[]",
            "{}",
            "{}",
            now_iso()
        ))

        child_id = c.lastrowid

        c.execute("""
            INSERT INTO moonlife_players (
                user_id, parent_name, parent_identity,
                stamina, stamina_updated_at,
                daily_stamina_buys, stamina_buy_date,
                current_child_id, created_at
            )
            VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                parent_name=excluded.parent_name,
                parent_identity=excluded.parent_identity,
                current_child_id=excluded.current_child_id
        """, (
            user_id,
            self.parent_name,
            self.identity,
            10,
            now_iso(),
            datetime.now(timezone.utc).date().isoformat(),
            child_id,
            now_iso()
        ))

        c.execute("""
            INSERT INTO moonlife_daily
            (user_id, game_day, last_day_at, care_done, play_done, outside_done)
            VALUES (?, 1, ?, 0, 0, 0)
            ON CONFLICT(user_id) DO UPDATE SET
                care_done=0, play_done=0, outside_done=0
        """, (user_id, now_iso()))

        conn.commit()

        add_memory(
            user_id,
            child_id,
            "👶 第一次相遇",
            f"{self.parent_name} 領養了 {child_name}。"
        )

        gender_text = "男孩 👦" if self.gender == "男" else "女孩 👧"

        embed = discord.Embed(
            title="🌙 領養成功！",
            description=(
                f"{identity_emoji(self.identity)} 你：**{self.parent_name}**\n"
                f"{gender_emoji(self.gender)} 孩子：**{child_name}**\n"
                f"🎉 性別：**{gender_text}**\n\n"
                f"🎂 **0歲1個月**\n"
                f"🌱 從今天開始，你們要一起慢慢長大。"
            ),
            color=MOONLIFE_COLOR
        )
        await interaction.response.send_message(
            embed=embed,
            view=MoonLifeFullHomeView(),
            ephemeral=True
        )

class AdoptionIdentityView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    async def choose(self, interaction, identity):
        await interaction.response.send_modal(AdoptionModal(identity))

    @discord.ui.button(label="👨 男", style=discord.ButtonStyle.primary)
    async def male(self, interaction, button):
        await self.choose(interaction, "男")

    @discord.ui.button(label="👩 女", style=discord.ButtonStyle.primary)
    async def female(self, interaction, button):
        await self.choose(interaction, "女")

    @discord.ui.button(label="🐱 貓", style=discord.ButtonStyle.secondary)
    async def cat(self, interaction, button):
        await self.choose(interaction, "貓")

    @discord.ui.button(label="🐶 狗", style=discord.ButtonStyle.secondary)
    async def dog(self, interaction, button):
        await self.choose(interaction, "狗")


# ==========================================================
# 🏠 主畫面
# ==========================================================

async def build_home_embed(user_id):
    player = get_player(user_id)
    child_row = get_child(user_id)

    if not player or not child_row:
        return None

    child = child_dict(child_row)
    stamina = update_stamina(user_id)
    daily = get_daily(user_id)

    personalities = parse_json(child["personalities"], [])
    interests = parse_json(child["interests"], [])

    personality_text = "、".join(
        f"{PERSONALITY_EMOJIS.get(x, '🌱')} {x}" for x in personalities
    ) if personalities else "🌱 還在慢慢形成"

    interest_text = "、".join(interests) if interests else "🌱 還在慢慢發現"

    embed = discord.Embed(
        title="🌙 Moon Life",
        description=(
            f"{identity_emoji(player[2])} 你：**{player[1]}**\n"
            f"{gender_emoji(child['gender'])} 孩子：**{child['name']}**\n\n"
            f"🎂 年齡：**{child['age_year']}歲{child['age_month']}個月**\n"
            f"🌱 成長：**{child['growth']} / 100**\n"
            f"⚡ 體力：**{stamina}**"
            f"{' / 10' if stamina <= 10 else ''}\n"
            f"❤️ 關係：**{relationship_name(child['relationship'])}**\n\n"
            f"🌟 個性：{personality_text}\n"
            f"🎨 興趣：{interest_text}\n\n"
            f"📅 遊戲日：第 **{daily[1]}** 天"
        ),
        color=MOONLIFE_COLOR
    )

    embed.add_field(name="🍽️ 狀態", value=hunger_text(child), inline=False)

    return embed


class MoonLifeHomeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    async def refresh(self, interaction):
        embed = await build_home_embed(str(interaction.user.id))
        if embed is None:
            await interaction.response.send_message(
                "❌ 你目前沒有未成年的孩子。",
                ephemeral=True
            )
            return
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🏠 在家", style=discord.ButtonStyle.primary, row=0)
    async def home(self, interaction, button):
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🏠 在家",
                description="選擇今天想和孩子做什麼。",
                color=MOONLIFE_COLOR
            ),
            view=HomeActionsView()
        )

    @discord.ui.button(label="🌳 外出", style=discord.ButtonStyle.success, row=0)
    async def outside(self, interaction, button):
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🌳 外出",
                description="外面的世界正在等著你們。",
                color=MOONLIFE_COLOR
            ),
            view=OutsideView()
        )

    @discord.ui.button(label="👶 孩子", style=discord.ButtonStyle.secondary, row=0)
    async def child(self, interaction, button):
        user_id = str(interaction.user.id)
        row = get_child(user_id)
        if not row:
            await interaction.response.send_message("❌ 找不到孩子資料。", ephemeral=True)
            return

        child = child_dict(row)
        personalities = parse_json(child["personalities"], [])
        interests = parse_json(child["interests"], [])

        embed = discord.Embed(
            title=f"👶 {child['name']} 的資料",
            description=(
                f"{gender_emoji(child['gender'])} {child['gender']}\n"
                f"🎂 {child['age_year']}歲{child['age_month']}個月\n"
                f"❤️ {relationship_name(child['relationship'])}\n\n"
                f"🧠 智慧：{child['intelligence']} / 100\n"
                f"❤️ 情感：{child['emotion']} / 100\n"
                f"💪 體能：{child['fitness']} / 100\n"
                f"🎨 創造：{child['creativity']} / 100\n"
                f"✨ 社交：{child['social']} / 100\n\n"
                f"🌟 個性：{'、'.join(personalities) if personalities else '尚未正式形成'}\n"
                f"🎨 興趣：{'、'.join(interests) if interests else '尚未正式發現'}"
            ),
            color=MOONLIFE_COLOR
        )
        await interaction.response.edit_message(embed=embed, view=BackHomeView())

    @discord.ui.button(label="🍼 餵食", style=discord.ButtonStyle.success, row=0)
    async def feed(self, interaction, button):
        user_id = str(interaction.user.id)
        child = child_dict(get_child(user_id))
        if not child:
            await interaction.response.send_message("❌ 目前沒有正在照顧的孩子。", ephemeral=True)
            return

        c.execute(
            "SELECT item_name, quantity FROM moonlife_inventory "
            "WHERE user_id=? AND quantity>0 ORDER BY item_name",
            (user_id,)
        )
        rows = [
            row for row in c.fetchall()
            if ITEMS.get(row[0], {}).get("type") == "food"
            and is_food_suitable(child, ITEMS.get(row[0], {}))
        ]

        age_label = "🍼 餵奶" if child["age_year"] <= 1 else "🍽️ 餵食"
        if rows:
            description = (
                f"目前 {child['name']}是 **{child['age_year']}歲{child['age_month']}個月**。\n"
                "請從背包中選擇適合年齡的食物。"
            )
        else:
            description = (
                f"目前背包裡沒有適合 **{child['age_year']}歲** 的食物。\n"
                "可以直接到商店購買。"
            )

        await interaction.response.edit_message(
            embed=discord.Embed(title=age_label, description=description, color=MOONLIFE_COLOR),
            view=FeedingView(rows)
        )

    @discord.ui.button(label="🎒 背包", style=discord.ButtonStyle.secondary, row=1)
    async def inventory(self, interaction, button):
        user_id = str(interaction.user.id)
        c.execute("""
            SELECT item_name, quantity FROM moonlife_inventory
            WHERE user_id=? AND quantity>0
            ORDER BY item_name
        """, (user_id,))
        rows = c.fetchall()

        text = "\n".join(f"• {name} × {qty}" for name, qty in rows) if rows else "目前背包是空的。"
        embed = discord.Embed(title="🎒 背包", description=text, color=MOONLIFE_COLOR)
        await interaction.response.edit_message(embed=embed, view=InventoryView(rows))

    @discord.ui.button(label="🛍️ 商店", style=discord.ButtonStyle.secondary, row=1)
    async def shop(self, interaction, button):
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🛍️ Moon Life 商店",
                description="選擇你想購買的類別。",
                color=MOONLIFE_COLOR
            ),
            view=ShopView()
        )

    @discord.ui.button(label="📖 人生回憶", style=discord.ButtonStyle.secondary, row=1)
    async def memories(self, interaction, button):
        user_id = str(interaction.user.id)
        child = child_dict(get_child(user_id))
        c.execute("""
            SELECT title, content FROM moonlife_memories
            WHERE user_id=? AND child_id=?
            ORDER BY memory_id DESC LIMIT 10
        """, (user_id, child["child_id"]))
        rows = c.fetchall()

        description = "\n\n".join(f"**{a}**\n{b}" for a, b in rows) or "還沒有留下回憶。"
        embed = discord.Embed(
            title="📖 人生回憶",
            description=description[:4000],
            color=MOONLIFE_COLOR
        )
        await interaction.response.edit_message(embed=embed, view=BackHomeView())

    @discord.ui.button(label="🌙 結束今天", style=discord.ButtonStyle.danger, row=2)
    async def end_day(self, interaction, button):
        user_id = str(interaction.user.id)
        child = child_dict(get_child(user_id))
        daily = get_daily(user_id)

        if not daily[3]:
            await interaction.response.send_message(
                "❌ 今天還沒有完成基本照顧，先陪陪孩子吧。",
                ephemeral=True
            )
            return

        # 每結束一天，飢餓增加
        change_child(child["child_id"], hunger=child["hunger"] + 18)

        c.execute("""
            UPDATE moonlife_daily
            SET game_day=game_day+1,
                last_day_at=?,
                care_done=0,
                play_done=0,
                outside_done=0
            WHERE user_id=?
        """, (now_iso(), user_id))
        conn.commit()

        child = child_dict(get_child(user_id))
        adult = add_growth(user_id, child, 10)

        if adult:
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title="🌙 孩子成年了",
                    description=f"恭喜！**{child['name']}** 已經 18 歲，正式成年。\n\n你現在可以再次領養新的孩子。",
                    color=MOONLIFE_COLOR
                ),
                view=None
            )
            return

        child = child_dict(get_child(user_id))
        event_text = random.choice([
            f"🌙 {child['name']}今天在你身邊安心地睡著了。",
            f"✨ {child['name']}今天好像又長大了一點。",
            f"🥹 你看著{child['name']}，覺得今天也是很珍貴的一天。",
        ])

        add_memory(user_id, child["child_id"], "🌙 又一天", event_text)

        embed = await build_home_embed(user_id)
        embed.description += f"\n\n{event_text}"
        await interaction.response.edit_message(embed=embed, view=self)


class BackHomeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(label="⬅️ 回到 Moon Life", style=discord.ButtonStyle.primary)
    async def back(self, interaction, button):
        embed = await build_home_embed(str(interaction.user.id))
        await interaction.response.edit_message(embed=embed, view=MoonLifeFullHomeView())


# ==========================================================
# 🏠 在家
# ==========================================================

class HomeActionsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(label="🍽️ 照顧孩子", style=discord.ButtonStyle.success)
    async def care(self, interaction, button):
        user_id = str(interaction.user.id)
        child = child_dict(get_child(user_id))

        if not use_stamina(user_id, 1):
            await interaction.response.send_message("❌ 體力不足。", ephemeral=True)
            return

        change_child(
            child["child_id"],
            relationship=child["relationship"] + random.randint(2, 4),
            hunger=max(0, child["hunger"] - 25),
            emotion=child["emotion"] + random.randint(0, 2)
        )

        c.execute("UPDATE moonlife_daily SET care_done=1 WHERE user_id=?", (user_id,))
        conn.commit()

        add_personality_progress(child, "溫柔", 1)
        add_memory(user_id, child["child_id"], "🍽️ 被好好照顧", f"{child['name']}今天被你好好照顧了。")

        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🍽️ 照顧完成",
                description=f"🥹 {child['name']}看起來安心多了。\n❤️ 親子關係提升\n🍽️ 飢餓狀態改善",
                color=MOONLIFE_COLOR
            ),
            view=BackHomeView()
        )

    @discord.ui.button(label="🧸 一起玩", style=discord.ButtonStyle.primary)
    async def play(self, interaction, button):
        user_id = str(interaction.user.id)
        child = child_dict(get_child(user_id))

        if not use_stamina(user_id, 2):
            await interaction.response.send_message("❌ 體力不足。", ephemeral=True)
            return

        activity = random.choice([
            ("玩積木", "intelligence", "探索"),
            ("畫畫", "creativity", "繪畫"),
            ("玩球", "fitness", "運動"),
            ("看故事", "intelligence", "閱讀"),
        ])

        name, stat, interest = activity
        gain = random.randint(1, 3)

        changes = {
            stat: child[stat] + gain,
            "relationship": child["relationship"] + 2
        }
        change_child(child["child_id"], **changes)
        discovered = add_interest_progress(child, interest, random.randint(5, 9))

        if interest == "探索":
            add_personality_progress(child, "好奇", 2)
        elif interest == "繪畫":
            add_personality_progress(child, "好奇", 1)
        elif interest == "運動":
            add_personality_progress(child, "活潑", 1)

        c.execute("UPDATE moonlife_daily SET play_done=1 WHERE user_id=?", (user_id,))
        conn.commit()

        message = f"🧸 你和{child['name']}一起{name}！\n{STAT_EMOJIS[stat]} +{gain}\n❤️ 關係提升"
        if discovered:
            message += f"\n\n🌟 **發現興趣：{discovered}！**"

        await interaction.response.edit_message(
            embed=discord.Embed(title="🧸 一起玩", description=message, color=MOONLIFE_COLOR),
            view=BackHomeView()
        )


# ==========================================================
# 🌳 外出
# ==========================================================

class OutsideView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    async def go(self, interaction, place):
        user_id = str(interaction.user.id)
        child = child_dict(get_child(user_id))

        if not use_stamina(user_id, 2):
            await interaction.response.send_message("❌ 體力不足。", ephemeral=True)
            return

        if place == "公園":
            stat = "fitness"
            interest = "運動"
            text = f"🌳 {child['name']}在公園跑來跑去，看起來非常開心。"
            personality = "活潑"
        elif place == "圖書館":
            stat = "intelligence"
            interest = "閱讀"
            text = f"📚 {child['name']}安靜地翻著一本故事書。"
            personality = "好奇"
        else:
            stat = "emotion"
            interest = "自然"
            text = f"🌿 {child['name']}停下來觀察周圍的小花與天空。"
            personality = "好奇"

        gain = random.randint(1, 3)
        change_child(
            child["child_id"],
            **{
                stat: child[stat] + gain,
                "relationship": child["relationship"] + 1
            }
        )

        discovered = add_interest_progress(child, interest, random.randint(4, 8))
        add_personality_progress(child, personality, 1)

        c.execute("UPDATE moonlife_daily SET outside_done=1 WHERE user_id=?", (user_id,))
        conn.commit()

        description = f"{text}\n\n{STAT_EMOJIS[stat]} +{gain}"
        if discovered:
            description += f"\n🌟 **發現興趣：{discovered}！**"

        await interaction.response.edit_message(
            embed=discord.Embed(title=f"🌳 外出｜{place}", description=description, color=MOONLIFE_COLOR),
            view=BackHomeView()
        )

    @discord.ui.button(label="🌳 公園", style=discord.ButtonStyle.success)
    async def park(self, interaction, button):
        await self.go(interaction, "公園")

    @discord.ui.button(label="📚 圖書館", style=discord.ButtonStyle.primary)
    async def library(self, interaction, button):
        await self.go(interaction, "圖書館")

    @discord.ui.button(label="🌿 自然散步", style=discord.ButtonStyle.secondary)
    async def nature(self, interaction, button):
        await self.go(interaction, "自然")


# ==========================================================
# 🍼 餵食／年齡適合食物
# ==========================================================

def is_food_suitable(child, item):
    if item.get("type") != "food":
        return False
    age = int(child["age_year"])
    if age < int(item.get("min_age", 0)):
        return False
    max_age = item.get("max_age")
    if max_age is not None and age > int(max_age):
        return False
    return True


def food_age_text(item):
    min_age = item.get("min_age", 0)
    max_age = item.get("max_age")
    if max_age is None:
        return f"{min_age}歲以上"
    return f"{min_age}～{max_age}歲"


async def consume_food(interaction, item_name):
    user_id = str(interaction.user.id)
    item = ITEMS.get(item_name)
    child = child_dict(get_child(user_id))

    if not item or item.get("type") != "food" or not child:
        await interaction.response.send_message("❌ 目前無法使用這個食物。", ephemeral=True)
        return

    if not is_food_suitable(child, item):
        await interaction.response.send_message(
            f"❌ **{item_name}** 適合 {food_age_text(item)} 的孩子，"
            f"{child['name']}目前 {child['age_year']}歲，不能這樣餵喔。",
            ephemeral=True
        )
        return

    if not remove_inventory(user_id, item_name):
        await interaction.response.send_message("❌ 背包裡沒有這個食物了。", ephemeral=True)
        return

    hunger_before = child["hunger"]
    new_hunger = max(0, hunger_before - int(item.get("hunger", 0)))
    updates = {"hunger": new_hunger}
    for stat in ("intelligence", "emotion", "fitness", "creativity", "social", "relationship"):
        if item.get(stat):
            updates[stat] = child[stat] + item[stat]

    change_child(child["child_id"], **updates)

    # 餵食算完成今天的一次基本照顧
    c.execute("UPDATE moonlife_daily SET care_done=1 WHERE user_id=?", (user_id,))
    conn.commit()

    add_memory(
        user_id, child["child_id"], f"🍽️ 餵食｜{item_name}",
        f"今天餵{child['name']}吃了{item_name}，好好照顧了肚子。"
    )

    description = (
        f"使用：**{item_name}**\n"
        f"👶 適用年齡：{food_age_text(item)}\n"
        f"🍽️ 飢餓：{hunger_before} → {new_hunger}\n"
        f"🥰 {child['name']}吃得很安心！"
    )
    if item.get("emotion"):
        description += f"\n❤️ 情緒 +{item['emotion']}"

    await interaction.response.edit_message(
        embed=discord.Embed(title="🍽️ 餵食完成", description=description, color=MOONLIFE_COLOR),
        view=BackHomeView()
    )


class FeedingSelect(discord.ui.Select):
    def __init__(self, rows):
        options = []
        for row in rows[:25]:
            name, qty = row[0], row[1]
            item = ITEMS.get(name, {})
            options.append(discord.SelectOption(
                label=f"{name} × {qty}",
                description=f"適用：{food_age_text(item)}｜飢餓 -{item.get('hunger', 0)}",
                value=name
            ))
        super().__init__(placeholder="選擇要餵給孩子的食物", options=options)

    async def callback(self, interaction):
        await consume_food(interaction, self.values[0])


class FeedingView(discord.ui.View):
    def __init__(self, rows):
        super().__init__(timeout=180)
        if rows:
            self.add_item(FeedingSelect(rows))

    @discord.ui.button(label="🛍️ 去商店買食物", style=discord.ButtonStyle.success)
    async def shop_food(self, interaction, button):
        await show_shop_category(interaction, "food")

    @discord.ui.button(label="⬅️ 回主畫面", style=discord.ButtonStyle.secondary)
    async def back(self, interaction, button):
        embed = await build_home_embed(str(interaction.user.id))
        await interaction.response.edit_message(embed=embed, view=MoonLifeFullHomeView())


# ==========================================================
# 🎒 背包使用
# ==========================================================

class InventoryView(discord.ui.View):
    def __init__(self, rows):
        super().__init__(timeout=180)
        self.rows = rows
        if rows:
            self.add_item(InventorySelect(rows))

    @discord.ui.button(label="⬅️ 回主畫面", style=discord.ButtonStyle.secondary)
    async def back(self, interaction, button):
        embed = await build_home_embed(str(interaction.user.id))
        await interaction.response.edit_message(embed=embed, view=MoonLifeFullHomeView())


class InventorySelect(discord.ui.Select):
    def __init__(self, rows):
        options = []
        for row in rows[:25]:
            name, qty = row[0], row[1]
            if is_durable_item(name):
                durability = row[2] if len(row) > 2 and row[2] is not None else ITEMS.get(name, {}).get("durability", 20)
                max_durability = row[3] if len(row) > 3 and row[3] is not None else ITEMS.get(name, {}).get("durability", 20)
                label = f"{name}｜耐久 {durability}/{max_durability}"
            else:
                label = f"{name} × {qty}"
            options.append(discord.SelectOption(label=label, value=name))
        super().__init__(placeholder="選擇要使用的物品", options=options)

    async def callback(self, interaction):
        user_id = str(interaction.user.id)
        item_name = self.values[0]
        item = ITEMS.get(item_name)

        if not item:
            await interaction.response.send_message("❌ 找不到這個物品。", ephemeral=True)
            return

        child = child_dict(get_child(user_id))
        if not child:
            await interaction.response.send_message("❌ 目前沒有正在照顧的孩子。", ephemeral=True)
            return

        if item.get("type") == "food":
            if not is_food_suitable(child, item):
                await interaction.response.send_message(
                    f"❌ **{item_name}** 適合 {food_age_text(item)} 的孩子。\n"
                    f"{child['name']}目前 {child['age_year']}歲，請選擇適合年齡的食物。",
                    ephemeral=True
                )
                return
            await consume_food(interaction, item_name)
            return

        # 🎂 生日蛋糕只能在孩子生日月使用
        if item["type"] == "birthday":
            birthday_title = f"🎂 {child['name']} {child['age_year']}歲生日蛋糕"
            if child["age_year"] <= 0 or child["age_month"] != 1:
                await interaction.response.send_message(
                    "🎂 生日蛋糕只能在孩子每滿一歲的生日月使用喔！",
                    ephemeral=True
                )
                return
            if has_memory_title(user_id, child["child_id"], birthday_title):
                await interaction.response.send_message(
                    "🎂 今年已經吃過生日蛋糕慶祝了，明年生日再一起慶祝吧！",
                    ephemeral=True
                )
                return

        if is_durable_item(item_name):
            ok, remaining, maximum = use_durability(user_id, item_name)
            if not ok:
                await interaction.response.send_message(
                    f"❌ **{item_name}** 的耐久度已經歸零，請重新購買新的物品。",
                    ephemeral=True
                )
                return
            durability_text = f"\n🔧 耐久：{remaining}/{maximum}"
        else:
            if not remove_inventory(user_id, item_name):
                await interaction.response.send_message("❌ 物品使用失敗。", ephemeral=True)
                return
            durability_text = ""

        description = f"使用了：**{item_name}**" + durability_text

        updates = {}
        if "hunger" in item:
            updates["hunger"] = max(0, child["hunger"] - item["hunger"])

        for stat in ("intelligence", "emotion", "fitness", "creativity", "social", "relationship"):
            if item.get(stat):
                updates[stat] = child[stat] + item[stat]

        if updates:
            change_child(child["child_id"], **updates)

        discovered = None
        if item.get("interest"):
            discovered = add_interest_progress(
                child,
                item["interest"],
                item.get("interest_gain", 0)
            )

        if item["type"] == "food":
            description += f"\n🍽️ {child['name']}吃得很開心！"
            if item.get("emotion"):
                description += f"\n❤️ 心情 +{item['emotion']}"
        elif item_name == "玩偶":
            description += f"\n🧸 {child['name']}抱著玩偶玩了一會兒。"
        elif item_name == "拼圖":
            description += "\n🧩 一起完成了一次動腦挑戰。"
        elif item["type"] == "special":
            add_memory(
                user_id, child["child_id"], f"🎁 {item_name}",
                f"你和{child['name']}留下了一個特別的小回憶。"
            )
            description += "\n🥹 留下了一段特別的回憶。"
        elif item["type"] == "birthday":
            title = f"🎂 {child['name']} {child['age_year']}歲生日蛋糕"
            memory = (
                f"今天是{child['name']} {child['age_year']}歲的生日月。"
                "你們一起吃了生日蛋糕，留下了一段特別的成長回憶。"
            )
            add_memory(user_id, child["child_id"], title, memory)
            description += f"\n🎉 你們一起慶祝了{child['name']}的生日！"
            description += "\n📖 已加入人生回憶。"

        if discovered:
            description += f"\n🌟 發現興趣：{discovered}"

        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🎒 使用物品",
                description=description,
                color=MOONLIFE_COLOR
            ),
            view=BackHomeView()
        )


# ==========================================================
# 🛍️ 商店
# ==========================================================

class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(label="⚡ 購買體力", style=discord.ButtonStyle.success)
    async def stamina(self, interaction, button):
        user_id = str(interaction.user.id)
        today = datetime.now(timezone.utc).date().isoformat()

        c.execute("""
            SELECT daily_stamina_buys, stamina_buy_date
            FROM moonlife_players WHERE user_id=?
        """, (user_id,))
        buys, buy_date = c.fetchone()

        if buy_date != today:
            buys = 0
            c.execute("""
                UPDATE moonlife_players
                SET daily_stamina_buys=0, stamina_buy_date=?
                WHERE user_id=?
            """, (today, user_id))
            conn.commit()

        # 🔧 Moon Bot 指定管理員測試：不受每日 10 次限制
        # 使用 config.py 的 BOT_ADMINS，不採用 Discord Administrator 權限。
        # 一般玩家仍維持每日最多購買 10 次。
        is_admin = interaction.user.id in BOT_ADMINS

        if not is_admin and buys >= 10:
            await interaction.response.send_message(
                "❌ 今天已經購買 10 次體力。",
                ephemeral=True
            )
            return

        # 第一次 1000，第二次 2000 ... 依購買次數累加
        # 管理員測試帳號可以無限購買，價格規則照常計算。
        price = (buys + 1) * 1000
        money = get_money(user_id)
        is_tester = is_moonlife_tester(interaction.user.id)

        if not is_tester and money < price:
            await interaction.response.send_message(
                f"❌ 努努幣不足。\n需要：{price:,}\n目前：{money:,}",
                ephemeral=True
            )
            return

        remove_money(user_id, price)
        c.execute("""
            UPDATE moonlife_players
            SET stamina=stamina+10,
                stamina_updated_at=?,
                daily_stamina_buys=daily_stamina_buys+1,
                stamina_buy_date=?
            WHERE user_id=?
        """, (now_iso(), today, user_id))
        conn.commit()

        admin_note = "\n🔧 BOT 管理員測試模式：今日購買次數不受限制。" if is_admin else ""
        tester_note = "\n🧪 Moon Life 測試模式：本次免費，不扣努努幣。" if is_tester else ""
        cost_text = "💰 測試免費（0 努努幣）" if is_tester else f"💰 消耗 {price:,} 努努幣"
        await interaction.response.send_message(
            f"⚡ 購買成功！\n體力 +10\n{cost_text}\n\n"
            f"購買體力可以突破自然上限 10。{admin_note}{tester_note}",
            ephemeral=True
        )

    @discord.ui.button(label="🧸 玩具", style=discord.ButtonStyle.primary)
    async def toys(self, interaction, button):
        await show_shop_category(interaction, "toy")

    @discord.ui.button(label="🍼🍎 年齡食物", style=discord.ButtonStyle.primary)
    async def food(self, interaction, button):
        await show_shop_category(interaction, "food")

    @discord.ui.button(label="🎁 特殊物品", style=discord.ButtonStyle.secondary)
    async def special(self, interaction, button):
        await show_shop_category(interaction, "special")

    @discord.ui.button(label="⬅️ 回主畫面", style=discord.ButtonStyle.secondary)
    async def back(self, interaction, button):
        embed = await build_home_embed(str(interaction.user.id))
        await interaction.response.edit_message(embed=embed, view=MoonLifeFullHomeView())


async def show_shop_category(interaction, category):
    options = []
    lines = []

    child = child_dict(get_child(str(interaction.user.id)))

    for name, data in ITEMS.items():
        matches = data["type"] == category
        if category == "food":
            matches = data["type"] == "food" and child and is_food_suitable(child, data)

        if matches:
            extra = f"\n👶 適用：{food_age_text(data)}" if data["type"] == "food" else ""
            lines.append(f"**{name}**｜💰 {data['price']:,}{extra}\n{data['desc']}")
            options.append(discord.SelectOption(
                label=f"{name}｜{data['price']:,} 努努幣",
                value=name
            ))

    view = discord.ui.View(timeout=180)
    view.add_item(ShopSelect(options))
    view.add_item(ShopBackButton())

    embed = discord.Embed(
        title="🛍️ Moon Life 商店",
        description=(
            "📦 **選擇物品後可以輸入購買數量，每次最多 50 個。**\n"
            "🧸 耐久玩具因背包耐久度設計，每次維持購買 1 件。\n\n"
            + "\n\n".join(lines)
        ),
        color=MOONLIFE_COLOR
    )
    await interaction.response.edit_message(embed=embed, view=view)


class ShopQuantityModal(discord.ui.Modal, title="🛍️ Moon Life｜購買數量"):
    """商店數量購買：每次 1～50。"""

    # 使用與目前已正常運作的 AdoptionModal 相同寫法，
    # 避免某些 Discord.py / Discord API 組合對動態 add_item Modal 元件產生 Invalid Form Body。
    quantity = discord.ui.TextInput(
        label="購買數量（1～50）",
        placeholder="例如：10",
        default="1",
        required=True,
        max_length=2
    )

    def __init__(self, item_name):
        super().__init__()
        self.item_name = item_name
        self.item_price = int(ITEMS[item_name]["price"])

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)

        try:
            amount = int(str(self.quantity.value).strip())
        except ValueError:
            await interaction.response.send_message(
                "❌ 購買數量請輸入 1～50 的整數。",
                ephemeral=True
            )
            return

        if not 1 <= amount <= 50:
            await interaction.response.send_message(
                "❌ 每次購買數量必須介於 **1～50**。",
                ephemeral=True
            )
            return

        item = ITEMS.get(self.item_name)
        if not item:
            await interaction.response.send_message("❌ 找不到這個物品。", ephemeral=True)
            return

        if is_durable_item(self.item_name) and amount > 1:
            await interaction.response.send_message(
                "🧸 **耐久玩具目前每次只能購買 1 件。**\n"
                "因為每種玩具在背包中會以單一耐久度物品保存，"
                "避免你買了多件卻只得到一件。",
                ephemeral=True
            )
            return

        total_price = self.item_price * amount
        money = get_money(user_id)
        is_tester = is_moonlife_tester(interaction.user.id)

        if not is_tester and money < total_price:
            await interaction.response.send_message(
                f"❌ 努努幣不足。\n"
                f"單價：{self.item_price:,} 努努幣\n"
                f"數量：{amount}\n"
                f"總價：{total_price:,} 努努幣\n"
                f"目前：{money:,}",
                ephemeral=True
            )
            return

        if not remove_money(user_id, total_price):
            await interaction.response.send_message(
                "❌ 購買失敗，請重新確認努努幣餘額。",
                ephemeral=True
            )
            return

        add_inventory(user_id, self.item_name, amount)

        cost_text = "🧪 測試免費：**0 努努幣**" if is_tester else f"💰 總消耗：**{total_price:,} 努努幣**"
        await interaction.response.send_message(
            f"🛍️ **購買成功！**\n\n"
            f"📦 獲得：**{self.item_name} ×{amount}**\n"
            f"💰 單價：{self.item_price:,} 努努幣\n"
            f"{cost_text}\n"
            f"💳 剩餘：{get_money(user_id):,} 努努幣",
            ephemeral=True
        )

class ShopSelect(discord.ui.Select):
    def __init__(self, options):
        super().__init__(placeholder="選擇要購買的物品", options=options)

    async def callback(self, interaction):
        name = self.values[0]
        item = ITEMS[name]

        # 選擇物品後再讓玩家輸入數量，而不是直接購買 1 個。
        await interaction.response.send_modal(ShopQuantityModal(name))


class ShopBackButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="⬅️ 回商店", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction):
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🛍️ Moon Life 商店",
                description="選擇你想購買的類別。",
                color=MOONLIFE_COLOR
            ),
            view=ShopView()
        )


# ==========================================================
# 🌙 Slash Command
# ==========================================================

# 🌙 Moon Life｜正式完整版擴充
# 以下為完整遊戲循環與條件式事件系統
# ==========================================================

AGE_STAGES = [
    (0, 2, "嬰幼兒期"),
    (3, 5, "幼兒期"),
    (6, 11, "童年期"),
    (12, 17, "青少年期"),
]

ACTIVITY_LIBRARY = {
    "跟孩子說說話": {
        "where": "home", "stamina": 1, "relationship": (1, 3),
        "stats": {"emotion": (1, 2), "social": (0, 1)},
        "personality": [("溫柔", 2), ("黏人", 1)],
        "min_age": 0,
        "memory": "💬 你今天溫柔地和孩子說說話，孩子安靜聽著你的聲音。",
    },
    "抱抱孩子": {
        "where": "home", "stamina": 1, "relationship": (3, 6),
        "stats": {"emotion": (2, 4)},
        "personality": [("溫柔", 2), ("黏人", 1)],
        "min_age": 0,
        "memory": "🤗 今天給了孩子一個暖暖的擁抱。",
    },
    "唱歌給孩子聽": {
        "where": "home", "stamina": 1, "relationship": (2, 4),
        "stats": {"emotion": (1, 3)},
        "interest": ("音樂", (2, 5)),
        "personality": [("好奇", 1)],
        "min_age": 0,
        "memory": "🎵 今天用歌聲陪著孩子，房間裡多了一點溫柔的旋律。",
    },
    "陪玩玩具": {
        "where": "home", "stamina": 1, "relationship": (2, 5),
        "stats": {"emotion": (1, 3), "intelligence": (0, 1)},
        "interest": ("探索", (1, 4)),
        "personality": [("好奇", 2)],
        "min_age": 0,
        "memory": "🧸 今天陪孩子玩了好一會兒玩具。",
    },
    "睡前陪伴": {
        "where": "home", "stamina": 1, "relationship": (2, 5),
        "stats": {"emotion": (2, 4)},
        "personality": [("溫柔", 2)],
        "min_age": 0,
        "memory": "🌙 睡前安靜陪在孩子身邊，直到他安心下來。",
    },
    "看圖畫書": {
        "where": "home", "stamina": 1, "relationship": (1, 4),
        "stats": {"intelligence": (1, 2), "emotion": (1, 2)},
        "interest": ("閱讀", (2, 5)),
        "personality": [("好奇", 2)],
        "min_age": 1,
        "memory": "📖 今天一起翻著圖畫書，孩子對每一頁都很好奇。",
    },
    "拍手遊戲": {
        "where": "home", "stamina": 1, "relationship": (2, 4),
        "stats": {"emotion": (1, 3), "social": (1, 2)},
        "personality": [("活潑", 2)],
        "min_age": 1,
        "memory": "👏 今天一起玩拍手遊戲，笑聲停不下來。",
    },
    "聽音樂跳舞": {
        "where": "home", "stamina": 2, "relationship": (1, 4),
        "stats": {"emotion": (1, 3), "fitness": (0, 2)},
        "interest": ("音樂", (3, 7)),
        "personality": [("活潑", 2), ("好奇", 1)],
        "min_age": 1,
        "memory": "💃 今天跟著音樂搖搖晃晃，跳出了自己的節奏。",
    },
    "拼圖遊戲": {
        "where": "home", "stamina": 2, "relationship": (1, 3),
        "stats": {"intelligence": (2, 4)},
        "interest": ("探索", (3, 7)),
        "personality": [("好奇", 1), ("獨立", 1)],
        "min_age": 2,
        "memory": "🧩 今天一起完成了一幅拼圖。",
    },
    "角色扮演": {
        "where": "home", "stamina": 2, "relationship": (1, 4),
        "stats": {"creativity": (1, 4), "social": (1, 3)},
        "interest": ("表演", (3, 7)),
        "personality": [("活潑", 1), ("好奇", 1)],
        "min_age": 2,
        "memory": "🎭 今天一起玩角色扮演，孩子創造了一個奇妙的小世界。",
    },
    "一起說故事": {
        "where": "home", "stamina": 1, "relationship": (2, 4),
        "stats": {"intelligence": (1, 3), "creativity": (1, 3)},
        "interest": ("閱讀", (3, 7)),
        "personality": [("好奇", 2)],
        "min_age": 3,
        "memory": "📖 今天輪流編故事，最後的結局誰也猜不到。",
    },
    "簡單小實驗": {
        "where": "home", "stamina": 2, "relationship": (1, 3),
        "stats": {"intelligence": (2, 5), "creativity": (1, 2)},
        "interest": ("探索", (4, 8)),
        "personality": [("好奇", 2)],
        "min_age": 4,
        "memory": "🔬 今天一起完成了一個簡單的小實驗，孩子對結果充滿驚喜。",
    },
    "一起做點心": {
        "where": "home", "stamina": 2, "relationship": (2, 4),
        "stats": {"creativity": (1, 3), "intelligence": (0, 2)},
        "interest": ("料理", (3, 7)),
        "personality": [("獨立", 1), ("好奇", 1)],
        "min_age": 4,
        "memory": "🧁 今天一起做了簡單的小點心，過程比成品還要有趣。",
    },
    "整理小房間": {
        "where": "home", "stamina": 1, "relationship": (1, 3),
        "stats": {"emotion": (0, 2)},
        "personality": [("獨立", 2)],
        "min_age": 5,
        "memory": "🏠 今天一起整理房間，孩子也開始學習照顧自己的空間。",
    },
    "桌遊時間": {
        "where": "home", "stamina": 2, "relationship": (2, 4),
        "stats": {"intelligence": (1, 4), "social": (1, 3)},
        "interest": ("策略", (3, 7)),
        "personality": [("好奇", 1), ("活潑", 1)],
        "min_age": 5,
        "memory": "🎲 今天一起玩桌遊，有輸有贏，但笑得很開心。",
    },
    "家庭電影時間": {
        "where": "home", "stamina": 1, "relationship": (2, 5),
        "stats": {"emotion": (1, 3)},
        "interest": ("影視", (2, 5)),
        "personality": [("溫柔", 1)],
        "min_age": 7,
        "memory": "🎬 今天一起看了一部電影，是很平凡卻很溫暖的家庭時光。",
    },
    "一起下廚": {
        "where": "home", "stamina": 2, "relationship": (2, 4),
        "stats": {"creativity": (1, 3), "intelligence": (1, 3)},
        "interest": ("料理", (4, 8)),
        "personality": [("獨立", 2)],
        "min_age": 7,
        "memory": "🍳 今天一起下廚，孩子開始能完成一些屬於自己的小任務。",
    },
    "認真聊聊": {
        "where": "home", "stamina": 1, "relationship": (3, 6),
        "stats": {"emotion": (1, 4), "social": (1, 3)},
        "personality": [("溫柔", 2), ("獨立", 1)],
        "min_age": 8,
        "memory": "💭 今天認真聊了很多心裡話，彼此似乎又更了解了一點。",
    },
    "一起完成小作品": {
        "where": "home", "stamina": 3, "relationship": (2, 4),
        "stats": {"creativity": (2, 5), "intelligence": (1, 3)},
        "interest": ("創作", (4, 8)),
        "personality": [("好奇", 1), ("獨立", 1)],
        "min_age": 8,
        "memory": "🛠️ 今天一起完成了一個小作品，留下了共同努力的成果。",
    },
    "一起閱讀": {
        "where": "home", "stamina": 1, "relationship": (1, 3),
        "stats": {"intelligence": (1, 3), "emotion": (0, 1)},
        "interest": ("閱讀", (4, 8)),
        "personality": [("好奇", 2)],
        "min_age": 2,
        "memory": "📚 今天一起讀了一本故事。",
    },
    "畫畫": {
        "where": "home", "stamina": 2, "relationship": (1, 3),
        "stats": {"creativity": (1, 4)},
        "interest": ("繪畫", (5, 9)),
        "personality": [("好奇", 1), ("獨立", 1)],
        "min_age": 2,
        "memory": "🎨 今天留下了一張小小的作品。",
    },
    "玩積木": {
        "where": "home", "stamina": 2, "relationship": (1, 3),
        "stats": {"intelligence": (1, 3), "creativity": (1, 3)},
        "interest": ("探索", (3, 7)),
        "personality": [("好奇", 2)],
        "min_age": 1,
        "memory": "🧱 今天一起完成了一個積木作品。",
    },
    "嬰兒車散步": {
        "where": "outside", "stamina": 1, "relationship": (2, 4),
        "stats": {"emotion": (1, 2), "social": (0, 1)},
        "interest": ("自然", (2, 4)),
        "personality": [("好奇", 1), ("黏人", 1)],
        "min_age": 0,
        "memory": "🍼 今天推著嬰兒車到外面吹吹風，小小的世界又多了一點新鮮感。",
    },
    "看看外面的世界": {
        "where": "outside", "stamina": 1, "relationship": (1, 3),
        "stats": {"emotion": (1, 3)},
        "personality": [("好奇", 1)],
        "min_age": 0,
        "memory": "🌤️ 今天帶孩子看看天空、樹影與來來往往的人群。",
    },
    "公園玩耍": {
        "where": "outside", "stamina": 2, "relationship": (1, 3),
        "stats": {"fitness": (1, 4), "social": (0, 2)},
        "interest": ("運動", (4, 8)),
        "personality": [("活潑", 2)],
        "min_age": 1,
        "memory": "🌳 今天在公園玩得很開心。",
    },
    "圖書館": {
        "where": "outside", "stamina": 2, "relationship": (1, 2),
        "stats": {"intelligence": (1, 4)},
        "interest": ("閱讀", (5, 9)),
        "personality": [("好奇", 1)],
        "min_age": 3,
        "memory": "📚 今天在圖書館安靜地看了許多書。",
    },
    "自然散步": {
        "where": "outside", "stamina": 2, "relationship": (1, 3),
        "stats": {"emotion": (1, 3), "fitness": (0, 2)},
        "interest": ("自然", (4, 8)),
        "personality": [("好奇", 2)],
        "min_age": 1,
        "memory": "🌿 今天一起觀察了周圍的自然景色。",
    },
    "探索新地方": {
        "where": "outside", "stamina": 3, "relationship": (1, 3),
        "stats": {"intelligence": (1, 3), "social": (0, 3)},
        "interest": ("探索", (5, 10)),
        "personality": [("勇敢", 1), ("好奇", 2)],
        "min_age": 4,
        "memory": "🗺️ 今天一起去了從來沒去過的地方。",
    },
    "一起運動": {
        "where": "outside", "stamina": 3, "relationship": (2, 4),
        "stats": {"fitness": (2, 5), "emotion": (0, 2)},
        "interest": ("運動", (5, 10)),
        "personality": [("活潑", 2), ("勇敢", 1)],
        "min_age": 3,
        "memory": "⚽ 今天一起流了好多汗。",
    },
}

# 合理事件：每個事件都有年齡、數值、經驗、興趣或隱藏狀態條件。
EVENT_LIBRARY = [
    # ==========================================================
    # 🍽️ 基本狀態／生活事件
    # ==========================================================
    {
        "id": "hungry_child",
        "title": "🍽️ 小小的肚子聲",
        "condition": lambda ch, ex: ch["hunger"] >= 65 and ex.get("事件_hungry_child", 0) < 3,
        "text": lambda ch: f"🥺 {ch['name']}看起來有點焦躁，不時扭動身體，像是在告訴你肚子餓了。",
        "effects": {},
    },
    {
        "id": "very_hungry",
        "title": "😭 今天真的好餓",
        "condition": lambda ch, ex: ch["hunger"] >= 85 and ex.get("事件_very_hungry", 0) < 2,
        "text": lambda ch: f"😭 {ch['name']}今天看起來沒什麼精神，連平常喜歡的事情都提不起勁。也許該先好好吃飯。",
        "effects": {"emotion": -1},
    },
    {
        "id": "safe_home",
        "title": "🏠 安心的小窩",
        "condition": lambda ch, ex: ch["relationship"] >= 55 and ch["hunger"] <= 25 and ex.get("活動_照顧孩子", 0) >= 2,
        "text": lambda ch: f"🏠 {ch['name']}今天待在你身邊時顯得很放鬆，好像已經把這裡當成安心的小窩。",
        "effects": {"emotion": 1},
        "personality": ("黏人", 1),
    },
    {
        "id": "first_night",
        "title": "🌙 睡前的小聲音",
        "condition": lambda ch, ex: ch["age_year"] <= 1 and ch["relationship"] >= 35 and ex.get("事件_first_night", 0) < 1,
        "text": lambda ch: f"🌙 睡前，{ch['name']}安靜地靠著你。這段陪伴似乎正在慢慢建立你們之間的信任。",
        "effects": {"relationship": 2, "emotion": 1},
    },

    # ==========================================================
    # ❤️ 親子關係事件
    # ==========================================================
    {
        "id": "trust_moment",
        "title": "❤️ 安心的時刻",
        "condition": lambda ch, ex: ch["relationship"] >= 65 and ex.get("事件_trust_moment", 0) < 3,
        "text": lambda ch: f"🥹 {ch['name']}自然地靠近你，這份信任已經慢慢成為習慣。",
        "effects": {"emotion": 1},
    },
    {
        "id": "asks_for_help",
        "title": "🥹 可以幫我嗎？",
        "condition": lambda ch, ex: ch["relationship"] >= 40 and ch["age_year"] >= 2 and ex.get("活動_照顧孩子", 0) >= 1,
        "text": lambda ch: f"🥹 {ch['name']}遇到不會的事情時，第一個想到的是跑來找你幫忙。",
        "effects": {"relationship": 2},
    },
    {
        "id": "little_hug",
        "title": "🤗 突然的擁抱",
         "condition": lambda ch, ex: ch["age_year"] >= 1 and ch["relationship"] >= 70 and ch["emotion"] >= 15 and ex.get("事件_little_hug", 0) < 3,
        "text": lambda ch: f"🤗 沒有特別的原因，{ch['name']}今天突然給了你一個大大的擁抱。",
        "effects": {"relationship": 2, "emotion": 1},
    },
    {
        "id": "needs_space",
        "title": "🌱 想自己待一下",
        "condition": lambda ch, ex: ch["age_year"] >= 7 and ch["relationship"] >= 45 and ex.get("活動_自然散步", 0) + ex.get("活動_探索", 0) >= 2,
        "text": lambda ch: f"🌱 {ch['name']}今天說想自己安靜做一會兒事情。這不是疏遠，而是開始學習屬於自己的空間。",
        "effects": {"social": 1},
        "personality": ("獨立", 2),
    },

    # ==========================================================
    # 🎨 繪畫／創造
    # ==========================================================
    {
        "id": "likes_drawing",
        "title": "🎨 一張又一張",
        "condition": lambda ch, ex: ex.get("活動_繪畫", 0) >= 2 and int(parse_json(ch["interest_progress"], {}).get("繪畫", 0)) >= 15 and ch["creativity"] >= 12,
        "text": lambda ch: f"🎨 {ch['name']}最近又主動拿起畫具，似乎真的很享受創作。",
        "effects": {"creativity": 1},
    },
    {
        "id": "color_story",
        "title": "🌈 這是我的故事",
        "condition": lambda ch, ex: ex.get("活動_繪畫", 0) >= 4 and ch["creativity"] >= 18 and ex.get("事件_color_story", 0) < 2,
        "text": lambda ch: f"🌈 {ch['name']}指著自己的作品，一點一點告訴你畫裡發生了什麼。原來創作對{ch['name']}來說，也是一種說故事的方法。",
        "effects": {"creativity": 2, "emotion": 1},
        "personality": ("好奇", 1),
    },
    {
        "id": "messy_art",
        "title": "😂 顏料跑得到處都是",
        "condition": lambda ch, ex: ex.get("活動_繪畫", 0) >= 2 and ch["age_year"] <= 6 and ex.get("事件_messy_art", 0) < 2,
        "text": lambda ch: f"😂 {ch['name']}今天創作得太投入，結果桌上、手上甚至臉上都沾到了一點顏料。",
        "effects": {"creativity": 1, "emotion": 1},
        "personality": ("調皮", 1),
    },

    # ==========================================================
    # 📚 閱讀／智慧
    # ==========================================================
    {
        "id": "book_question",
        "title": "📚 為什麼呢？",
        "condition": lambda ch, ex: ch["age_year"] >= 3 and ex.get("活動_閱讀", 0) >= 2 and int(parse_json(ch["interest_progress"], {}).get("閱讀", 0)) >= 10,
        "text": lambda ch: f"📖 {ch['name']}讀完故事後，開始問你書裡發生的事情。",
        "effects": {"intelligence": 1, "emotion": 1},
    },
    {
        "id": "favorite_page",
        "title": "📖 再念一次！",
        "condition": lambda ch, ex: ex.get("活動_閱讀", 0) >= 4 and ch["intelligence"] >= 16 and ex.get("事件_favorite_page", 0) < 3,
        "text": lambda ch: f"📖 {ch['name']}翻到熟悉的頁面，立刻叫你再念一次。看來這個故事已經成為小小的最愛。",
        "effects": {"intelligence": 1, "relationship": 1},
    },
    {
        "id": "deep_question",
        "title": "🤔 一個認真的問題",
        "condition": lambda ch, ex: ch["age_year"] >= 8 and ex.get("活動_閱讀", 0) >= 5 and ch["intelligence"] >= 25,
        "text": lambda ch: f"🤔 {ch['name']}今天問了一個讓你也忍不住思考很久的問題。",
        "effects": {"intelligence": 2},
        "personality": ("好奇", 2),
    },

    # ==========================================================
    # ⚽ 運動／體能
    # ==========================================================
    {
        "id": "sport_energy",
        "title": "⚽ 還想再玩！",
        "condition": lambda ch, ex: ex.get("活動_運動", 0) >= 2 and ch["fitness"] >= 12 and int(parse_json(ch["interest_progress"], {}).get("運動", 0)) >= 10,
        "text": lambda ch: f"⚽ {ch['name']}玩完後還精神滿滿，似乎完全不想回家。",
        "effects": {"fitness": 1},
    },
    {
        "id": "small_race",
        "title": "🏃 比賽！",
        "condition": lambda ch, ex: ch["age_year"] >= 3 and ex.get("活動_運動", 0) >= 4 and ch["fitness"] >= 18,
        "text": lambda ch: f"🏃 {ch['name']}突然拉著你說要比賽跑步，還沒開始就已經興奮得不得了。",
        "effects": {"fitness": 2, "relationship": 1},
        "personality": ("活潑", 2),
    },
    {
        "id": "tired_but_happy",
        "title": "😆 累死了，但很好玩",
        "condition": lambda ch, ex: ex.get("活動_運動", 0) >= 3 and ch["fitness"] >= 15 and ch["hunger"] < 60,
        "text": lambda ch: f"😆 {ch['name']}玩到滿頭大汗，坐下來後卻笑著說今天很好玩。",
        "effects": {"emotion": 1, "fitness": 1},
    },

    # ==========================================================
    # 🌿 自然／探索
    # ==========================================================
    {
        "id": "nature_notice",
        "title": "🌿 小小發現",
        "condition": lambda ch, ex: ex.get("活動_自然", 0) >= 2 and int(parse_json(ch["interest_progress"], {}).get("自然", 0)) >= 10,
        "text": lambda ch: f"🌿 {ch['name']}停下腳步，認真觀察了一片葉子。",
        "effects": {"emotion": 1},
    },
    {
        "id": "tiny_treasure",
        "title": "🍃 小小的寶物",
         "condition": lambda ch, ex: ch["age_year"] >= 1 and ex.get("活動_自然", 0) >= 3 and ex.get("事件_tiny_treasure", 0) < 3,
        "text": lambda ch: f"🍃 {ch['name']}今天撿到了一個覺得非常特別的小東西，認真地說要好好收藏。",
        "effects": {"emotion": 1},
        "personality": ("好奇", 1),
    },
    {
        "id": "lost_in_wonder",
        "title": "🌤️ 為什麼天空會變色？",
        "condition": lambda ch, ex: ch["age_year"] >= 4 and ex.get("活動_自然", 0) >= 4 and ch["intelligence"] >= 14,
        "text": lambda ch: f"🌤️ {ch['name']}抬頭看著天空，開始好奇地問起世界為什麼會是這個樣子。",
        "effects": {"intelligence": 1, "emotion": 1},
        "personality": ("好奇", 2),
    },
    {
        "id": "explorer_route",
        "title": "🗺️ 我們走這邊！",
        "condition": lambda ch, ex: ex.get("活動_探索", 0) >= 3 and ch["age_year"] >= 5,
        "text": lambda ch: f"🗺️ {ch['name']}今天很有主見地指出另一條路，想看看那邊有什麼。",
        "effects": {"social": 1, "intelligence": 1},
        "personality": ("勇敢", 1),
    },

    # ==========================================================
    # 🌟 個性發展
    # ==========================================================
    {
        "id": "curious_question",
        "title": "🤔 十萬個為什麼",
        "condition": lambda ch, ex: ch["intelligence"] >= 15 and ch["age_year"] >= 2 and ex.get("事件_curious_question", 0) < 3,
        "text": lambda ch: f"🤔 {ch['name']}今天對身邊的事情充滿問題。",
        "effects": {"intelligence": 1},
        "personality": ("好奇", 2),
    },
    {
        "id": "growing_independent",
        "title": "🌱 我自己來",
        "condition": lambda ch, ex: ch["age_year"] >= 6 and ch["relationship"] >= 40 and ex.get("事件_growing_independent", 0) < 3,
        "text": lambda ch: f"🌱 {ch['name']}今天說想試著自己完成一件事情。",
        "effects": {"social": 1},
        "personality": ("獨立", 2),
    },
    {
        "id": "shy_hello",
        "title": "😳 躲在你後面",
        "condition": lambda ch, ex: ch["age_year"] >= 2 and ch["relationship"] >= 30 and ch["social"] <= 18,
        "text": lambda ch: f"😳 遇到陌生環境時，{ch['name']}下意識靠近你，悄悄躲在你的身後。",
        "effects": {"relationship": 1},
        "personality": ("害羞", 2),
    },
    {
        "id": "brave_step",
        "title": "💪 我試試看",
        "condition": lambda ch, ex: ch["age_year"] >= 5 and ch["fitness"] >= 18 and ex.get("活動_運動", 0) + ex.get("活動_探索", 0) >= 4,
        "text": lambda ch: f"💪 面對以前可能會猶豫的事情，{ch['name']}今天深呼吸後說：「我想試試看。」",
        "effects": {"emotion": 1},
        "personality": ("勇敢", 2),
    },
    {
        "id": "gentle_choice",
        "title": "🥹 小小的體貼",
        "condition": lambda ch, ex: ch["emotion"] >= 20 and ch["relationship"] >= 55 and ex.get("活動_照顧孩子", 0) >= 3,
        "text": lambda ch: f"🥹 {ch['name']}今天注意到你的狀態，還主動問你是不是累了。",
        "effects": {"emotion": 2},
        "personality": ("溫柔", 2),
    },
    {
        "id": "playful_idea",
        "title": "😂 一個奇怪的主意",
        "condition": lambda ch, ex: ch["creativity"] >= 16 and ch["age_year"] >= 3 and ex.get("活動_繪畫", 0) >= 2,
        "text": lambda ch: f"😂 {ch['name']}今天突然想出一個讓你哭笑不得的玩法，還很認真地邀請你一起加入。",
        "effects": {"creativity": 1, "emotion": 1},
        "personality": ("調皮", 2),
    },

    # ==========================================================
    # 🎂 成長階段事件
    # ==========================================================
    {
        "id": "first_word_like",
        "title": "🗣️ 小小的表達",
        "condition": lambda ch, ex: 1 <= ch["age_year"] <= 2 and ch["social"] >= 10 and ex.get("事件_first_word_like", 0) < 1,
        "text": lambda ch: f"🗣️ {ch['name']}今天比以前更努力地表達自己的想法，你忍不住發現：真的長大了一點。",
        "effects": {"social": 1, "emotion": 1},
    },
    {
        "id": "preschool_friend",
        "title": "👋 第一次主動打招呼",
        "condition": lambda ch, ex: 3 <= ch["age_year"] <= 6 and ch["social"] >= 16 and ex.get("事件_preschool_friend", 0) < 2,
        "text": lambda ch: f"👋 {ch['name']}今天主動向別人打招呼。雖然可能有點緊張，但已經踏出了自己的第一步。",
        "effects": {"social": 2},
    },
    {
        "id": "big_kid_thought",
        "title": "🌙 我已經不是小孩子了",
        "condition": lambda ch, ex: 7 <= ch["age_year"] <= 12 and ch["intelligence"] + ch["social"] >= 45 and ex.get("事件_big_kid_thought", 0) < 2,
        "text": lambda ch: f"🌙 {ch['name']}今天突然認真地說自己已經長大了，讓你有一瞬間不知道該高興還是感傷。",
        "effects": {"emotion": 1, "social": 1},
    },
    {
        "id": "teen_dream",
        "title": "✨ 關於以後",
        "condition": lambda ch, ex: 13 <= ch["age_year"] < 18 and len(parse_json(ch["interests"], [])) >= 1 and ex.get("事件_teen_dream", 0) < 3,
        "text": lambda ch: f"✨ {ch['name']}今天開始和你聊起未來想做的事情。那些曾經的小興趣，似乎正在慢慢變成真正的方向。",
        "effects": {"social": 1, "emotion": 1},
    },
    {
        "id": "almost_adult",
        "title": "🌅 快要長大了",
        "condition": lambda ch, ex: ch["age_year"] >= 16 and ch["relationship"] >= 60 and ex.get("事件_almost_adult", 0) < 2,
        "text": lambda ch: f"🌅 你突然發現，{ch['name']}已經不是以前那個需要你一直牽著手的小孩子了。",
        "effects": {"emotion": 1},
    },
]

def get_age_stage(child):
    age = child["age_year"]
    for low, high, name in AGE_STAGES:
        if low <= age <= high:
            return name
    return "成年"

def has_memory_title(user_id, child_id, title):
    c.execute("""
        SELECT 1 FROM moonlife_memories
        WHERE user_id=? AND child_id=? AND title=?
        LIMIT 1
    """, (str(user_id), child_id, title))
    return c.fetchone() is not None

def add_experience(child_id, key, amount=1):
    c.execute("SELECT experiences FROM moonlife_children WHERE child_id=?", (child_id,))
    row = c.fetchone()
    experiences = parse_json(row[0] if row else "{}", {})
    experiences[key] = int(experiences.get(key, 0)) + amount
    change_child(child_id, experiences=dump_json(experiences))
    return experiences

def apply_stat_changes(child, stats):
    changes = {}
    for stat, value in stats.items():
        current = int(child.get(stat, 0))
        if isinstance(value, tuple):
            gain = random.randint(value[0], value[1])
        else:
            gain = int(value)
        changes[stat] = current + gain
    if changes:
        change_child(child["child_id"], **changes)
    return changes

def eligible_activities(child, where):
    result = []
    for name, data in ACTIVITY_LIBRARY.items():
        if data["where"] == where and child["age_year"] >= data.get("min_age", 0):
            result.append((name, data))
    return result

def roll_monthly_milestone(user_id, child):
    """依月齡逐步解鎖，不直接加年齡，避免等待期間沒有內容。"""
    experiences = parse_json(child["experiences"], {})
    total_months = int(child["age_year"]) * 12 + int(child["age_month"])
    key = f"月齡里程碑_{total_months}"
    if experiences.get(key):
        return None

    milestones = {
        1: ("👀 開始認真看著你", f"{child['name']}似乎開始會認真看著你的臉，對熟悉的聲音也有反應。", {"emotion":1}, ("探索",1)),
        2: ("😊 第一次露出笑容", f"今天{child['name']}對著你露出了一個特別明顯的笑容。", {"emotion":2,"relationship":1}, None),
        3: ("🗣️ 咿咿呀呀", f"{child['name']}開始發出更多咿咿呀呀的聲音，好像很想和你說話。", {"social":1,"emotion":1}, None),
        4: ("🧸 對玩具有反應", f"{child['name']}開始會追著玩具看，也會想伸手碰一碰。", {"intelligence":1}, ("探索",1)),
        5: ("🙌 想抓住東西", f"{child['name']}最近常常伸手想抓住眼前的東西。", {"fitness":1}, ("探索",1)),
        6: ("🥣 開始嘗試新食物", f"{child['name']}對新的味道和食物表現出更多好奇。", {"emotion":1}, None),
        7: ("🪑 嘗試坐穩", f"{child['name']}開始努力讓自己坐得更穩。", {"fitness":2}, None),
        8: ("👀 開始認生", f"{child['name']}遇到不熟悉的人時會先觀察，對熟悉的人則特別安心。", {"relationship":1}, None),
        9: ("🐾 開始努力爬行", f"{child['name']}開始想靠自己的力量到處探索。", {"fitness":2}, ("探索",2)),
        10: ("🧸 能自己玩一下", f"{child['name']}偶爾可以自己專心玩一會兒玩具。", {"emotion":1,"intelligence":1}, None),
        11: ("👣 嘗試扶著站立", f"{child['name']}開始抓著東西努力站起來。", {"fitness":2}, None),
    }
    item = milestones.get(total_months)
    if not item:
        return None

    title, content, effects, interest = item
    changes = {k: child[k] + v for k,v in effects.items()}
    change_child(child["child_id"], **changes)
    fresh = child_dict(get_child(user_id))
    if interest:
        add_interest_progress(fresh, interest[0], interest[1])
    add_memory(user_id, child["child_id"], title, content)
    add_experience(child["child_id"], key, 1)
    return {"title":title,"text":content}


def roll_player_child_encounter(user_id, child, activity_name):
    """外出偶遇真實其他玩家的孩子，並依雙方年齡使用合理互動。"""
    c.execute("""
        SELECT ch.*
        FROM moonlife_children ch
        JOIN moonlife_players p ON p.current_child_id = ch.child_id
        WHERE ch.user_id != ? AND ch.is_adult=0
        ORDER BY RANDOM() LIMIT 1
    """, (str(user_id),))
    row = c.fetchone()
    if not row:
        return None

    other = child_dict(row)
    age = int(child["age_year"])
    other_age = int(other["age_year"])

    # 👶 0歲嬰兒：只會「看到、注視、聽到、微笑」等被動且合理的互動。
    if age == 0:
        if other_age == 0:
            options = [
                ("👶 嬰兒車剛好停在旁邊",
                 f"{child['name']}和「{other['name']}」的嬰兒車剛好停在附近，兩個寶寶安靜地互相張望。",
                 {"emotion": 1}),
                ("😊 看見另一個寶寶",
                 f"{child['name']}注意到另一位寶寶「{other['name']}」，視線停留了一會兒，對這張陌生的小臉很好奇。",
                 {"emotion": 1}),
                ("👀 兩雙好奇的眼睛",
                 f"{child['name']}和「{other['name']}」短暫地看著彼此，兩個小朋友都還太小，只是靜靜感受這次相遇。",
                 {"emotion": 1}),
            ]
        else:
            options = [
                ("👀 看見另一個孩子",
                 f"外出時，{child['name']}注意到不遠處的孩子「{other['name']}」，安靜地看了一會兒。",
                 {"emotion": 1}),
                ("🔊 聽見孩子們的聲音",
                 f"{child['name']}聽見附近孩子們玩耍的聲音，睜大眼睛四處張望。",
                 {"emotion": 1}),
            ]
        title, content, effects = random.choice(options)

    else:
        age_gap = abs(age - other_age)
        if age_gap >= 4:
            title = "👀 遇見另一個孩子"
            content = f"外出時，{child['name']}看見了比自己年紀差很多的孩子「{other['name']}」，兩人短暫地注意到彼此。"
            effects = {"emotion": 1}
        elif age <= 1 and other_age <= 1:
            options = [
                ("👶 兩個小朋友互相張望",
                 f"{child['name']}和「{other['name']}」剛好在附近，兩個小朋友互相張望了好一會兒。",
                 {"emotion": 1}),
                ("😊 對方先笑了",
                 f"另一個孩子「{other['name']}」突然笑了，{child['name']}也一直看著對方。",
                 {"emotion": 1}),
            ]
            title, content, effects = random.choice(options)
        elif child["social"] >= 30:
            options = [
                ("🤝 認識了另一個孩子",
                 f"{child['name']}外出時遇到「{other['name']}」，今天短暫地一起互動了一下。",
                 {"social": 2, "emotion": 1}),
                ("🧸 對彼此很好奇",
                 f"{child['name']}和「{other['name']}」注意到彼此，對這位新朋友都很好奇。",
                 {"social": 1}),
            ]
            title, content, effects = random.choice(options)
        else:
            title = "😳 偷偷觀察另一個孩子"
            content = f"{child['name']}外出時看見「{other['name']}」，沒有馬上靠近，而是在你身邊安靜觀察。"
            effects = {"relationship": 1, "emotion": 1}

    change_child(child["child_id"], **{k: child[k] + v for k, v in effects.items()})
    add_memory(user_id, child["child_id"], title, content)
    add_experience(child["child_id"], f"偶遇玩家孩子_{other['child_id']}", 1)
    return {"title": title, "text": content}


def roll_outside_event(user_id, child, activity_name):
    """所有外出活動都有生活事件；0歲嬰兒使用嚴格的嬰兒專屬事件池。"""
    age = int(child["age_year"])
    social = child["social"]
    personalities = parse_json(child["personalities"], [])
    interests = parse_json(child["interests"], [])

    # ==========================================================
    # 👶 0歲嬰兒：只能被動感受世界，不會自己探索、揮手或主動行動
    # ==========================================================
    if age == 0:
        infant_events = [
            {"title": "🍃 聽見風吹樹葉",
             "text": f"微風吹過樹葉，{child['name']}安靜地聽著沙沙聲，眼睛慢慢轉向聲音傳來的方向。",
             "effects": {"emotion": 1}},
            {"title": "👀 好奇地張望",
             "text": f"{child['name']}睜著眼睛看著周圍陌生的光影和景色，對外面的世界似乎充滿好奇。",
             "effects": {"emotion": 1}},
            {"title": "🕊️ 看見飛過的小鳥",
             "text": f"一隻小鳥從眼前飛過，{child['name']}的視線跟著移動了一小段時間。",
             "effects": {"emotion": 1}},
            {"title": "😴 外出後有點累",
             "text": f"外面的聲音和景色看了好多，{child['name']}回程時有點睏，安靜地靠著你休息。",
             "effects": {"relationship": 1}},
            {"title": "☀️ 感受暖暖的陽光",
             "text": f"溫暖的陽光照在身上，{child['name']}看起來很放鬆。",
             "effects": {"emotion": 1}},
            {"title": "🔊 聽見陌生的聲音",
             "text": f"周圍傳來不同的聲音，{child['name']}安靜地聽著，偶爾轉動眼睛尋找聲音的方向。",
             "effects": {"emotion": 1}},
        ]

        activity_events = {
            "嬰兒車散步": [
                {"title": "🍼 嬰兒車上的小旅行",
                 "text": f"你推著{child['name']}慢慢散步，沿路的光影和聲音成了今天的新體驗。",
                 "effects": {"emotion": 1}},
            ],
            "看看外面的世界": [
                {"title": "🌤️ 看著天空",
                 "text": f"{child['name']}安靜地看著明亮的天空和晃動的樹影，今天的世界對他來說又多了一點新鮮感。",
                 "effects": {"emotion": 1}},
            ],
        }
        events = infant_events + activity_events.get(activity_name, [])

    # ==========================================================
    # 🧒 1歲以上：才逐步加入主動觀察與互動
    # ==========================================================
    else:
        events = [
            {"title":"🌤️ 發現不一樣的天空",
             "text":f"今天的天空和以前不太一樣，{child['name']}停下來看了好一會兒。",
             "effects":{"emotion":1},"interest":("自然",1)},
            {"title":"🎵 聽見陌生的聲音",
             "text":f"{child['name']}聽見外面傳來陌生的聲音，忍不住四處尋找聲音的來源。",
             "effects":{"social":1},"interest":("探索",1)},
        ]

        if social >= 25 or "活潑" in personalities:
            events.append(
                {"title":"👋 對陌生人揮手",
                 "text":f"{child['name']}遇到路人時主動揮了揮手，今天似乎比以前更願意接觸外面的世界。",
                 "effects":{"social":2},"personality":("活潑",1)}
            )
        else:
            events.append(
                {"title":"👀 安靜觀察人群",
                 "text":f"{child['name']}沒有急著靠近其他人，而是安靜地待在你身邊觀察。",
                 "effects":{"emotion":1,"relationship":1}}
            )

        activity_events = {
            "自然散步": [
                {"title":"🍂 撿起一片葉子",
                 "text":f"{child['name']}注意到地上的葉子，對它的形狀和顏色很好奇。",
                 "effects":{"intelligence":1},"interest":("自然",2),"personality":("好奇",1)},
            ],
            "圖書館": [
                {"title":"📚 被一本書吸引",
                 "text":f"{child['name']}在書架前停了下來，對其中一本書特別有興趣。",
                 "effects":{"intelligence":1},"interest":("閱讀",2)},
            ],
            "探索新地方": [
                {"title":"🗺️ 發現新角落",
                 "text":f"{child['name']}主動注意到一個以前沒看過的小角落，想再靠近看看。",
                 "effects":{"intelligence":1},"interest":("探索",2),"personality":("好奇",1)},
            ],
            "一起運動": [
                {"title":"💪 不想太快放棄",
                 "text":f"活動累了以後，{child['name']}休息了一下，又想再試一次。",
                 "effects":{"fitness":1},"personality":("勇敢",1)},
            ],
        }
        events += activity_events.get(activity_name, [])

        if "自然" in interests and activity_name in ("嬰兒車散步", "自然散步"):
            events.append(
                {"title":"🌿 又想多看一會兒",
                 "text":f"{child['name']}對周圍的植物特別有興趣，主動停下來多看了一會兒。",
                 "effects":{"emotion":1},"interest":("自然",1)}
            )

    if not events or random.random() > 0.55:
        return None

    event = random.choice(events)
    changes = {k: child[k] + v for k, v in event.get("effects", {}).items()}
    if changes:
        change_child(child["child_id"], **changes)

    fresh = child_dict(get_child(user_id))
    if event.get("interest"):
        interest, amount = event["interest"]
        add_interest_progress(fresh, interest, amount)
        fresh = child_dict(get_child(user_id))

    if event.get("personality"):
        personality, amount = event["personality"]
        add_personality_progress(fresh, personality, amount)

    add_memory(user_id, child["child_id"], event["title"], event["text"])
    add_experience(child["child_id"], f"外出事件_{activity_name}_{event['title']}", 1)
    return event


def roll_park_event(user_id, child):
    """公園限定事件：只有選擇「公園玩耍」後才會觸發。"""
    experiences = parse_json(child["experiences"], {})
    personalities = parse_json(child["personalities"], [])
    interests = parse_json(child["interests"], [])
    age = child["age_year"]
    social = child["social"]
    fitness = child["fitness"]
    relationship = child["relationship"]

    events = []

    if age <= 1:
        events += [
            {"title":"🌳 第一次認真看公園","text":f"{child['name']}坐在一旁好奇地看著樹影和來往的人群，小手不停指著新鮮的東西。","effects":{"emotion":2},"interest":("探索",2),"personality":("好奇",1)},
            {"title":"🫧 被風吹得咯咯笑","text":f"一陣風吹過，{child['name']}開心得笑了起來，似乎很喜歡這種新鮮的感覺。","effects":{"emotion":3},"interest":("自然",1)},
        ]

    if age >= 1:
        events += [
            {"title":"🐕 遇見可愛的小狗","text":f"{child['name']}在公園遇到一隻友善的小狗，站在原地看了很久。","effects":{"emotion":2},"interest":("自然",2),"personality":("好奇",1)},
            {"title":"🐜 發現小昆蟲","text":f"{child['name']}蹲下來觀察地上的小昆蟲，還忍不住問了好多問題。","effects":{"intelligence":1,"emotion":1},"interest":("自然",3),"personality":("好奇",2)},
            {"title":"🛝 想挑戰遊樂設施","text":f"{child['name']}盯著遊樂設施看了一會兒，最後鼓起勇氣去嘗試。","effects":{"fitness":2,"emotion":1},"interest":("運動",2),"personality":("勇敢",1)},
        ]

    if age >= 2:
        events += [
            {"title":"🎈 撿到飄來的氣球","text":f"一顆氣球剛好飄到{child['name']}附近，讓今天的公園時光多了一點驚喜。","effects":{"emotion":2},"personality":("活潑",1)},
            {"title":"🧒 想看看其他孩子在玩什麼","text":f"{child['name']}注意到其他孩子的遊戲，先在旁邊觀察了一會兒。","effects":{"social":1},"interest":("探索",2),"personality":("好奇",1)},
        ]

    if social >= 30 or "活潑" in personalities:
        events += [
            {"title":"🤝 認識了新朋友","text":f"{child['name']}主動加入其他孩子的遊戲，短暫地認識了一位新朋友。","effects":{"social":3,"emotion":1},"personality":("活潑",1)},
        ]
    else:
        events += [
            {"title":"😳 躲在你身後觀察","text":f"其他孩子靠近時，{child['name']}先悄悄躲到你身後觀察，暫時還沒有準備好加入。","effects":{"relationship":2},"personality":("謹慎",1)},
        ]

    if fitness >= 35 or "運動" in interests:
        events += [
            {"title":"⚽ 想加入踢球","text":f"{child['name']}看到有人踢球後越看越有興趣，也想試著踢幾下。","effects":{"fitness":2,"emotion":1},"interest":("運動",3),"personality":("活潑",1)},
        ]

    if relationship >= 70:
        events += [
            {"title":"🤍 拉著你的手","text":f"{child['name']}在公園裡自然地拉著你的手，遇到有趣的東西就第一個想和你分享。","effects":{"relationship":3,"emotion":1}},
        ]

    # 少量重複遊玩後才會出現的成長事件
    park_times = experiences.get("活動_公園玩耍", 0)
    if park_times >= 3:
        events += [
            {"title":"🌳 熟悉的公園","text":f"{child['name']}似乎已經開始熟悉這座公園，走到喜歡的地方時顯得特別自在。","effects":{"emotion":2,"relationship":1}},
        ]

    if not events or random.random() > 0.60:
        return None

    event = random.choice(events)
    changes = {k: child[k] + v for k, v in event.get("effects", {}).items()}
    if changes:
        change_child(child["child_id"], **changes)

    fresh = child_dict(get_child(user_id))
    if event.get("interest"):
        interest, amount = event["interest"]
        add_interest_progress(fresh, interest, amount)
        fresh = child_dict(get_child(user_id))

    if event.get("personality"):
        personality, amount = event["personality"]
        add_personality_progress(fresh, personality, amount)

    add_memory(user_id, child["child_id"], event["title"], event["text"])
    add_experience(child["child_id"], f"公園事件_{event['title']}", 1)
    return event


def run_activity(user_id, activity_name):
    child = child_dict(get_child(user_id))
    if not child:
        return False, "❌ 找不到目前的孩子。", None

    data = ACTIVITY_LIBRARY.get(activity_name)
    if not data:
        return False, "❌ 找不到這個活動。", None

    if child["age_year"] < data.get("min_age", 0):
        return False, f"❌ {child['name']}目前年紀還太小，還不能進行這個活動。", None

    if not use_stamina(user_id, data["stamina"]):
        return False, "❌ 體力不足。", None

    stat_changes = apply_stat_changes(child, data.get("stats", {}))
    # ❤️ 關係成長放慢：日常互動不再一次跳很多。
    relationship_range = data.get("relationship", (0, 0))
    relationship_gain = random.randint(*relationship_range)
    if relationship_gain > 0:
        relationship_gain = max(1, (relationship_gain + 1) // 2)
    # 👶 嬰兒期建立依附需要時間，避免每次活動都快速升滿親近。
    if int(child["age_year"]) == 0 and relationship_gain > 0:
        relationship_gain = 1

    change_child(
        child["child_id"],
        relationship=child["relationship"] + relationship_gain,
        hunger=child["hunger"] + random.randint(3, 8),
    )

    if data.get("interest"):
        interest, amount_range = data["interest"]
        add_experience(child["child_id"], f"活動_{interest}", 1)
        child_after = child_dict(get_child(user_id))
        discovered = add_interest_progress(child_after, interest, random.randint(*amount_range))
    else:
        discovered = None

    for personality, amount in data.get("personality", []):
        child_after = child_dict(get_child(user_id))
        add_personality_progress(child_after, personality, amount)

    add_experience(child["child_id"], f"活動_{activity_name}", 1)
    add_memory(user_id, child["child_id"], f"✨ {activity_name}", data["memory"])

    child_after = child_dict(get_child(user_id))
    milestone = roll_monthly_milestone(user_id, child_after)

    child_after = child_dict(get_child(user_id))
    encounter_event = roll_player_child_encounter(user_id, child_after, activity_name) if data.get("where") == "outside" and random.random() <= 0.35 else None

    child_after = child_dict(get_child(user_id))
    outside_event = roll_outside_event(user_id, child_after, activity_name) if data.get("where") == "outside" else None

    child_after = child_dict(get_child(user_id))
    park_event = roll_park_event(user_id, child_after) if activity_name == "公園玩耍" else None

    child_after = child_dict(get_child(user_id))
    event = roll_reasonable_event(user_id, child_after)

    message = f"{data['memory']}\n"
    if stat_changes:
        message += "\n".join(
            f"{STAT_EMOJIS.get(stat, '✨')} {stat} +{new_value - child[stat]}"
            for stat, new_value in stat_changes.items()
        )
    if discovered:
        message += f"\n\n🌟 **正式發現興趣：{discovered}！**"
        add_memory(user_id, child["child_id"], f"🌟 發現興趣｜{discovered}", f"{child['name']}經過一段時間的接觸與累積，正式發現自己喜歡{discovered}。")

    if milestone:
        message += f"\n\n🌱 **{milestone['title']}**\n{milestone['text']}"

    if encounter_event:
        message += f"\n\n👶 **{encounter_event['title']}**\n{encounter_event['text']}"

    if outside_event:
        message += f"\n\n🎲 **{outside_event['title']}**\n{outside_event['text']}"

    if milestone:
        message += "\n\n✨ 這是孩子目前月齡的新里程碑，已記錄在人生回憶中。"

    if park_event:
        message += f"\n\n🎲 **{park_event['title']}**\n{park_event['text']}"

    if event:
        message += f"\n\n{event['text']}"

    return True, message, outside_event or park_event or event

def roll_reasonable_event(user_id, child):
    experiences = parse_json(child["experiences"], {})
    eligible = [
        event for event in EVENT_LIBRARY
        if event["condition"](child, experiences)
    ]

    # 👶 0歲仍是嬰兒：只能觸發符合發展階段的事件。
    # 避免出現「嬰兒聊天、完整說話、自己撿寶物」等不合理內容。
    if int(child["age_year"]) == 0:
        infant_safe_ids = {
            "hungry_child",
            "very_hungry",
            "safe_home",
            "first_night",
            "trust_moment",
        }
        eligible = [
            event for event in eligible
            if event.get("id") in infant_safe_ids
        ]

    if not eligible:
        return None

    # 不讓每次活動都硬塞事件，維持自然感。
    if random.random() > 0.35:
        return None

    event = random.choice(eligible)
    effects = event.get("effects", {})
    changes = {}
    for key, amount in effects.items():
        if key == "relationship":
            changes[key] = child[key] + amount
        else:
            changes[key] = child[key] + amount
    if changes:
        change_child(child["child_id"], **changes)

    if event.get("personality"):
        fresh = child_dict(get_child(user_id))
        p, amount = event["personality"]
        add_personality_progress(fresh, p, amount)

    text = event["text"](child)
    add_memory(user_id, child["child_id"], event["title"], text)
    add_experience(child["child_id"], f"事件_{event['id']}", 1)
    return {"title": event["title"], "text": text}

def child_status_lines(child):
    lines = []
    if child["hunger"] >= 80:
        lines.append(f"😭 {child['name']}看起來非常餓，最好趕快吃點東西。")
    elif child["hunger"] >= 60:
        lines.append(f"🥺 {child['name']}摸摸肚子：「我有點餓……」")
    elif child["hunger"] >= 40:
        lines.append(f"🙂 {child['name']}偶爾會看看食物。")

    if child["relationship"] < 20:
        lines.append(f"🤍 {child['name']}還需要更多時間認識你。")
    elif child["relationship"] >= 80:
        lines.append(f"❤️ {child['name']}在你身邊看起來非常安心。")

    personalities = parse_json(child["personalities"], [])
    if personalities:
        lines.append("🌟 目前個性：" + "、".join(personalities))

    interests = parse_json(child["interests"], [])
    if interests:
        lines.append("🎨 已發現興趣：" + "、".join(interests))

    return lines or [f"😊 {child['name']}今天看起來精神不錯。"]

# ==========================================================
# 👨‍👩‍👧 家庭紀錄與成年保存
# ==========================================================

def get_child_history(user_id):
    c.execute("""
        SELECT name, gender, age_year, age_month, relationship,
               personalities, interests, is_adult, created_at
        FROM moonlife_children
        WHERE user_id=?
        ORDER BY child_id ASC
    """, (str(user_id),))
    return c.fetchall()

class ActivitySelect(discord.ui.Select):
    def __init__(self, where, child):
        options = []
        for name, data in eligible_activities(child, where)[:25]:
            options.append(discord.SelectOption(
                label=name,
                description=f"⚡ 體力 {data['stamina']}｜{data['where']}"
            ))
        super().__init__(placeholder="選擇今天的活動", options=options)
        self.where = where

    async def callback(self, interaction):
        ok, message, event = run_activity(str(interaction.user.id), self.values[0])
        if not ok:
            await interaction.response.send_message(message, ephemeral=True)
            return
        await interaction.response.edit_message(
            embed=discord.Embed(
                title=f"🌙 {self.values[0]}",
                description=message[:4000],
                color=MOONLIFE_COLOR
            ),
            view=BackHomeView()
        )

class FullActivityView(discord.ui.View):
    def __init__(self, where, child):
        super().__init__(timeout=180)
        acts = eligible_activities(child, where)
        self.has_activities = bool(acts)
        if acts:
            self.add_item(ActivitySelect(where, child))
        else:
            self.add_item(BackHomeButton())

class BackHomeButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="⬅️ 回主畫面", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction):
        embed = await build_home_embed(str(interaction.user.id))
        await interaction.response.edit_message(
            embed=embed,
            view=MoonLifeFullHomeView()
        )

class FamilyHistoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(label="⬅️ 回主畫面", style=discord.ButtonStyle.secondary)
    async def back(self, interaction, button):
        embed = await build_home_embed(str(interaction.user.id))
        if embed:
            await interaction.response.edit_message(embed=embed, view=MoonLifeFullHomeView())
        else:
            await interaction.response.edit_message(
                embed=discord.Embed(title="🌙 Moon Life", description="你目前沒有正在照顧的未成年孩子。", color=MOONLIFE_COLOR),
                view=None
            )

# ==========================================================
# 🧩 正式完整版 UI 擴充
# ==========================================================

class MoonLifeFullHomeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="🏠 在家", style=discord.ButtonStyle.primary, row=0)
    async def home(self, interaction, button):
        child = child_dict(get_child(str(interaction.user.id)))
        await interaction.response.edit_message(
            embed=discord.Embed(title="🏠 在家", description="選擇一個適合孩子目前年齡的活動。", color=MOONLIFE_COLOR),
            view=FullActivityView("home", child)
        )

    @discord.ui.button(label="🌳 外出", style=discord.ButtonStyle.success, row=0)
    async def outside(self, interaction, button):
        child = child_dict(get_child(str(interaction.user.id)))
        view = FullActivityView("outside", child)
        description = "每一次外出都會留下不同的人生經驗。"
        if not view.has_activities:
            description += "\n\n目前孩子的年齡還沒有適合的外出活動。"
        await interaction.response.edit_message(
            embed=discord.Embed(title="🌳 外出", description=description, color=MOONLIFE_COLOR),
            view=view
        )

    @discord.ui.button(label="👶 孩子狀態", style=discord.ButtonStyle.secondary, row=0)
    async def child(self, interaction, button):
        child = child_dict(get_child(str(interaction.user.id)))
        if not child:
            await interaction.response.send_message("❌ 目前沒有未成年的孩子。", ephemeral=True)
            return
        lines = child_status_lines(child)
        interests = parse_json(child["interests"], [])
        personalities = parse_json(child["personalities"], [])
        embed = discord.Embed(
            title=f"👶 {child['name']}｜{get_age_stage(child)}",
            description=(
                f"{gender_emoji(child['gender'])} 性別：{child['gender']}\n"
                f"🎂 年齡：{child['age_year']}歲{child['age_month']}個月\n"
                f"🌱 成長：{child['growth']}/100\n"
                f"❤️ 關係：{relationship_name(child['relationship'])}\n\n"
                f"🧠 智慧：{child['intelligence']}/100\n"
                f"❤️ 情感：{child['emotion']}/100\n"
                f"💪 體能：{child['fitness']}/100\n"
                f"🎨 創造：{child['creativity']}/100\n"
                f"✨ 社交：{child['social']}/100\n\n"
                f"🌟 個性：{'、'.join(personalities) if personalities else '正在形成'}\n"
                f"🎨 興趣：{'、'.join(interests) if interests else '正在慢慢發現'}\n\n"
                + "\n".join(lines)
            ),
            color=MOONLIFE_COLOR
        )
        await interaction.response.edit_message(embed=embed, view=BackHomeView())

    @discord.ui.button(label="🎒 背包", style=discord.ButtonStyle.secondary, row=1)
    async def inventory(self, interaction, button):
        user_id = str(interaction.user.id)
        c.execute("SELECT item_name, quantity, durability, max_durability FROM moonlife_inventory WHERE user_id=? AND quantity>0 ORDER BY item_name", (user_id,))
        rows = c.fetchall()
        lines = []
        for name, qty, durability, max_durability in rows:
            if is_durable_item(name):
                current = int(durability if durability is not None else ITEMS.get(name, {}).get("durability", 20))
                maximum = int(max_durability if max_durability is not None else ITEMS.get(name, {}).get("durability", 20))
                lines.append(f"• {name}【耐久 {current}/{maximum}】")
            else:
                lines.append(f"• {name} × {qty}")
        desc = "\n".join(lines) if lines else "目前背包是空的。"
        await interaction.response.edit_message(
            embed=discord.Embed(title="🎒 背包", description=desc, color=MOONLIFE_COLOR),
            view=InventoryView(rows)
        )

    @discord.ui.button(label="🛍️ 商店", style=discord.ButtonStyle.secondary, row=1)
    async def shop(self, interaction, button):
        await interaction.response.edit_message(
            embed=discord.Embed(title="🛍️ Moon Life 商店", description="玩具、食物與特殊物品都會慢慢影響孩子的生活經驗。", color=MOONLIFE_COLOR),
            view=ShopView()
        )

    @discord.ui.button(label="📖 人生回憶", style=discord.ButtonStyle.secondary, row=1)
    async def memories(self, interaction, button):
        user_id = str(interaction.user.id)
        child = child_dict(get_child(user_id))
        c.execute("""
            SELECT title, content FROM moonlife_memories
            WHERE user_id=? AND child_id=?
            ORDER BY memory_id DESC LIMIT 15
        """, (user_id, child["child_id"]))
        rows = c.fetchall()
        text = "\n\n".join(f"**{title}**\n{content}" for title, content in rows) or "還沒有留下回憶。"
        await interaction.response.edit_message(
            embed=discord.Embed(title=f"📖 {child['name']}的人生回憶", description=text[:4000], color=MOONLIFE_COLOR),
            view=BackHomeView()
        )

    @discord.ui.button(label="👨‍👩‍👧 家庭紀錄", style=discord.ButtonStyle.secondary, row=2)
    async def family(self, interaction, button):
        rows = get_child_history(str(interaction.user.id))
        if not rows:
            desc = "目前還沒有家庭紀錄。"
        else:
            lines = []
            for name, gender, age_y, age_m, rel, p_json, i_json, adult, created in rows:
                status = "🌙 已成年" if adult else "👶 目前照顧中"
                lines.append(
                    f"**{name}**｜{gender_emoji(gender)} {gender}｜{status}\n"
                    f"最後年齡：{age_y}歲{age_m}個月｜關係：{relationship_name(rel)}"
                )
            desc = "\n\n".join(lines)
        await interaction.response.edit_message(
            embed=discord.Embed(title="👨‍👩‍👧 家庭紀錄", description=desc[:4000], color=MOONLIFE_COLOR),
            view=FamilyHistoryView()
        )

    @discord.ui.button(label="🌙 結束今天", style=discord.ButtonStyle.danger, row=2)
    async def end_day(self, interaction, button):
        user_id = str(interaction.user.id)
        child = child_dict(get_child(user_id))
        if not child:
            await interaction.response.send_message("❌ 目前沒有孩子。", ephemeral=True)
            return

        daily = get_daily(user_id)
        if not daily[3]:
            await interaction.response.send_message(
                "❌ 今天還沒有完成基本照顧，先好好照顧孩子吧。",
                ephemeral=True
            )
            return

        change_child(
            child["child_id"],
            hunger=min(100, child["hunger"] + random.randint(10, 18))
        )
        child = child_dict(get_child(user_id))
        adult = add_growth(user_id, child, random.randint(8, 15))

        c.execute("""
            UPDATE moonlife_daily
            SET game_day=game_day+1, last_day_at=?, care_done=0, play_done=0, outside_done=0
            WHERE user_id=?
        """, (now_iso(), user_id))
        conn.commit()

        if adult:
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title="🌙 18歲｜正式成年",
                    description=(
                        f"🥹 **{child['name']}成年了。**\n\n"
                        "從第一次相遇開始，到今天為止留下的所有回憶都會保存在家庭紀錄中。\n"
                        "你現在可以再次領養新的孩子，並且再次選擇自己的男／女／貓／狗身份與名字。"
                    ),
                    color=MOONLIFE_COLOR
                ),
                view=None
            )
            return

        child = child_dict(get_child(user_id))

        # 🎂 每滿一歲：同一個孩子、同一歲只會慶祝一次
        birthday_text = ""
        if child["age_month"] == 1 and child["age_year"] > 0:
            birthday_title = f"🎂 {child['name']} {child['age_year']}歲生日"
            if not has_memory_title(user_id, child["child_id"], birthday_title):
                birthday_text = (
                    f"🎂 今天是{child['name']} {child['age_year']}歲的生日月！"
                    "又陪伴孩子走過了一個成長階段。"
                )
                add_memory(user_id, child["child_id"], birthday_title, birthday_text)

        # 🏆 成長里程碑：首次達成時留下回憶
        milestone_rules = [
            ("🌱 第一次發現興趣", len(parse_json(child["interests"], [])) >= 1),
            ("❤️ 非常親密", child["relationship"] >= 80),
            ("🧠 智慧小達人", child["intelligence"] >= 50),
            ("🎨 創意小達人", child["creativity"] >= 50),
            ("💪 體能小達人", child["fitness"] >= 50),
        ]
        experiences = parse_json(child["experiences"], {})
        for milestone_title, reached in milestone_rules:
            key = f"里程碑_{milestone_title}"
            if reached and experiences.get(key, 0) < 1:
                add_memory(
                    user_id,
                    child["child_id"],
                    f"🏆 {milestone_title}",
                    f"{child['name']}達成了新的成長里程碑：{milestone_title}！"
                )
                add_experience(child["child_id"], key, 1)

        event = roll_reasonable_event(user_id, child)
        text = f"🌙 今天結束了，{child['name']}又慢慢長大了一點。\n🎂 現在：{child['age_year']}歲{child['age_month']}個月"
        if event:
            text += f"\n\n{event['text']}"
        add_memory(user_id, child["child_id"], "🌙 又過了一天", text)

        embed = await build_home_embed(user_id)
        embed.description += "\n\n" + text
        await interaction.response.edit_message(embed=embed, view=MoonLifeFullHomeView())


# ==========================================================
# 🔧 完整版啟動函式覆寫
# ==========================================================

# 🌙 正式對外入口
# main.py 請使用：
# from systems.moon_life import setup_moon_life
# setup_moon_life(bot)
# ==========================================================

def setup_moon_life(bot):
    init_moonlife_tables()

    # 防止 on_ready 因重新連線再次執行時重複註冊指令
    if getattr(bot, "_moon_life_loaded", False):
        return
    bot._moon_life_loaded = True

    @bot.tree.command(name="moonlife", description="進入 Moon Life")
    async def moonlife(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        player = get_player(user_id)
        child = get_child(user_id)

        if not player or not child:
            embed = discord.Embed(
                title="🌙 Moon Life｜人生養成",
                description=(
                    "這是一段陪伴孩子從小慢慢長大的旅程。\n\n"
                    "每次領養時，你都可以重新選擇自己：\n"
                    "👨 男　👩 女　🐱 貓　🐶 狗\n\n"
                    "✏️ 你可以取自己的名字，也可以替孩子取名字。\n"
                    "👶 孩子的性別由系統隨機決定。\n"
                    "🌱 孩子會透過生活、活動、素質與經驗慢慢形成個性與興趣。\n"
                    "📖 所有重要經歷都會留下人生回憶。"
                ),
                color=MOONLIFE_COLOR
            )
            await interaction.response.send_message(embed=embed, view=AdoptionIdentityView(), ephemeral=True)
            return

        embed = await build_home_embed(user_id)
        await interaction.response.send_message(embed=embed, view=MoonLifeFullHomeView(), ephemeral=True)

    print("🌙 Moon Life 正式完整版已載入")
