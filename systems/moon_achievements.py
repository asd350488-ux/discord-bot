# -*- coding: utf-8 -*-
"""
🌙 Moon Club｜成就與成就盲盒系統

正式規則：
- 80 個成就：簡單 5／中 20／中高 25／高 30
- 不使用好感度／默契作為成就條件
- 成就完成後取得 1 次免費「成就盲盒」資格
- 同一成就只能取得一次資格
- 固定盲盒獎池；依成就等級調整機率
- 只有存在未使用資格時，Moon Club 面板才顯示成就盲盒按鈕

注意：
本檔先獨立封裝資料、狀態與抽獎邏輯；與 Moon Club 的實際資料表／View
接線時，必須以 moon_life(3).py 的現有欄位與架構為準。
"""

from __future__ import annotations

import random
import sqlite3
from dataclasses import dataclass
from typing import Callable, Optional, Sequence


# ============================================================
# 🎁 固定盲盒獎池
# ============================================================

REWARD_VIDEO = "影片合集"
REWARD_PHOTO = "照片合集"
REWARD_CERTIFICATE = "結婚證書"
REWARD_BADGE = "雙人徽章"
REWARD_NUNU_30000 = "30,000 努努幣"
REWARD_NUNU_40000 = "40,000 努努幣"
REWARD_NUNU_50000 = "50,000 努努幣"

LOOT_POOL: tuple[str, ...] = (
    REWARD_VIDEO,
    REWARD_PHOTO,
    REWARD_CERTIFICATE,
    REWARD_BADGE,
    REWARD_NUNU_30000,
    REWARD_NUNU_40000,
    REWARD_NUNU_50000,
)


# ============================================================
# 📊 成就等級
# ============================================================

EASY = "簡單"
MEDIUM = "中"
MEDIUM_HIGH = "中高"
HIGH = "高"


@dataclass(frozen=True)
class Achievement:
    achievement_id: str
    name: str
    description: str
    difficulty: str


# ============================================================
# 🏆 80 個正式成就
# ============================================================
#
# 名稱／條件依已鎖定版本建立。
# 條件判定會透過 AchievementEngine 接到 Moon Club 現有資料。
#

ACHIEVEMENTS: tuple[Achievement, ...] = (
    # 🟢 簡單 × 5
    Achievement("ACH_001", "🌱 新人站穩腳步", "任一男模完成 FAME_03「小型公開機會」。", EASY),
    Achievement("ACH_002", "📸 第一次留下名字", "任一男模完成 FAME_05「非工作場合被認出」。", EASY),
    Achievement("ACH_003", "🤝 第一份正式合作", "任一男模完成 FAME_06「第一個正式合作」。", EASY),
    Achievement("ACH_004", "🎓 培養出方向", "任一男模完成 specialty_27「專長正式形成」。", EASY),
    Achievement("ACH_005", "🌟 開始被真正看見", "任一男模知名度達 400，並完成 FAME_07「第一次正式介紹」。", EASY),

    # 🟡 中 × 20
    Achievement("ACH_006", "🔥 人氣開始累積", "任一男模知名度達 500。", MEDIUM),
    Achievement("ACH_007", "💬 熟面孔", "任一男模完成 FAME_09「固定支持者」。", MEDIUM),
    Achievement("ACH_008", "🌟 特別邀請", "任一男模完成 FAME_08「特別工作邀請」。", MEDIUM),
    Achievement("ACH_009", "🎤 找到自己的舞台", "完成 specialty_26「小型演出的機會」。", MEDIUM),
    Achievement("ACH_010", "📈 專長能力突破", "完成 specialty_28「專長能力突破」。", MEDIUM),
    Achievement("ACH_011", "🏆 因專長受到肯定", "完成 specialty_29「因專長獲得肯定」。", MEDIUM),
    Achievement("ACH_012", "🎭 第二條路", "任一男模正式擁有 2 個興趣／專長。", MEDIUM),
    Achievement("ACH_013", "🧠 雙項突出", "任一男模有 2 項能力達 70+。", MEDIUM),
    Achievement("ACH_014", "💪 全面成長", "任一男模五項能力平均達 50+。", MEDIUM),
    Achievement("ACH_015", "📖 經歷開始累積", "任一男模累積 15 筆職涯／事件記憶。", MEDIUM),
    Achievement("ACH_016", "🎓 培訓成果受到注意", "完成 training_15「培訓老師的特別評價」。", MEDIUM),
    Achievement("ACH_017", "💥 突破瓶頸", "完成 training_16「突破訓練瓶頸」。", MEDIUM),
    Achievement("ACH_018", "🌟 獲得外部推薦", "完成 training_18「獲得外部推薦」。", MEDIUM),
    Achievement("ACH_019", "✉️ 特別培訓邀請", "完成 training_19「收到特殊培訓邀請」。", MEDIUM),
    Achievement("ACH_020", "🎭 性格逐漸成形", "完成任一正式性格形成事件。", MEDIUM),
    Achievement("ACH_021", "🌙 看見另一面", "完成 personality_38「不願提起的過去」。", MEDIUM),
    Achievement("ACH_022", "📖 職涯起步", "完成 career_42「第一次公開活動」。", MEDIUM),
    Achievement("ACH_023", "📰 開始受到外界注意", "完成 career_44「開始受到外界注意」。", MEDIUM),
    Achievement("ACH_024", "🏛️ Moon Club 開始有名氣", "完成 club_71。", MEDIUM),
    Achievement("ACH_025", "💌 收到合作邀請", "完成 club_72。", MEDIUM),

    # 🟠 中高 × 25
    Achievement("ACH_026", "🔥 重要活動", "完成 FAME_10「重要活動的關注」。", MEDIUM_HIGH),
    Achievement("ACH_027", "🌟 成長受到矚目", "完成 FAME_11「培養能力受到注意」。", MEDIUM_HIGH),
    Achievement("ACH_028", "📸 現場人氣", "完成 FAME_12「明顯的現場人氣」。", MEDIUM_HIGH),
    Achievement("ACH_029", "👥 新人因你而來", "完成 FAME_13「新人開始注意 Moon Club」。", MEDIUM_HIGH),
    Achievement("ACH_030", "🤝 更大型的合作", "完成 FAME_14「更大型的合作」。", MEDIUM_HIGH),
    Achievement("ACH_031", "🌟 一位真正的明星", "任一男模知名度達 800。", MEDIUM_HIGH),
    Achievement("ACH_032", "👑 代表人物", "任一男模知名度達 1000。", MEDIUM_HIGH),
    Achievement("ACH_033", "🧠 全面成熟", "任一男模五項能力平均達 70+。", MEDIUM_HIGH),
    Achievement("ACH_034", "💪 三項專精", "任一男模有 3 項能力達 80+。", MEDIUM_HIGH),
    Achievement("ACH_035", "🔥 雙項巔峰", "任一男模有 2 項能力達 90+。", MEDIUM_HIGH),
    Achievement("ACH_036", "🎭 多元發展", "任一男模擁有 3 個正式專長。", MEDIUM_HIGH),
    Achievement("ACH_037", "📈 專長帶來機會", "完成 specialty_30「專長帶來重大機會」。", MEDIUM_HIGH),
    Achievement("ACH_038", "💥 重大的能力突破", "完成 training_20。", MEDIUM_HIGH),
    Achievement("ACH_039", "👑 第二性格形成", "完成 personality_40。", MEDIUM_HIGH),
    Achievement("ACH_040", "🏆 獲得專業肯定", "完成 career_46。", MEDIUM_HIGH),
    Achievement("ACH_041", "⚖️ 職涯方向", "完成 career_47「職涯方向的選擇」。", MEDIUM_HIGH),
    Achievement("ACH_042", "💎 高級工作", "完成 career_48「高級工作邀請」。", MEDIUM_HIGH),
    Achievement("ACH_043", "👑 職涯重大轉折", "完成 career_50。", MEDIUM_HIGH),
    Achievement("ACH_044", "🎉 第一次大型會館活動", "完成 club_73。", MEDIUM_HIGH),
    Achievement("ACH_045", "🤝 男模開始形成團隊", "完成 club_75「男模之間建立友誼」。", MEDIUM_HIGH),
    Achievement("ACH_046", "🌟 成員突然爆紅", "完成 club_77。", MEDIUM_HIGH),
    Achievement("ACH_047", "🎭 團體合作", "完成 club_78。", MEDIUM_HIGH),
    Achievement("ACH_048", "🏛️ 會館突破", "Moon Club 知名度達 500，並完成 club_73。", MEDIUM_HIGH),
    Achievement("ACH_049", "🌙 經歷豐富", "累計完成 30 個特殊／劇情事件。", MEDIUM_HIGH),
    Achievement("ACH_050", "📖 生涯留下厚度", "同一男模完成至少 3 個不同類型的職涯事件鏈。", MEDIUM_HIGH),

    # 🔴 高 × 30
    Achievement("ACH_051", "💎 頂尖會館", "Moon Club 知名度達 750。", HIGH),
    Achievement("ACH_052", "👑 傳奇會館", "Moon Club 知名度達 1000。", HIGH),
    Achievement("ACH_053", "👥 群星初現", "同時擁有 4 位男模。", HIGH),
    Achievement("ACH_054", "🌟 群星滿堂", "同時擁有 6 位男模，其中至少 3 位知名度 600+。", HIGH),
    Achievement("ACH_055", "👑 八星匯聚", "同時擁有 8 位男模。", HIGH),
    Achievement("ACH_056", "🧠 全能菁英", "任一男模五項能力全部達 80+。", HIGH),
    Achievement("ACH_057", "🔥 五項巔峰", "任一男模五項能力全部達 95+。", HIGH),
    Achievement("ACH_058", "💎 三項巔峰", "任一男模有 3 項能力達 90+。", HIGH),
    Achievement("ACH_059", "🌠 雙子傳奇", "同時培養 2 位男模，兩人的五項能力平均皆達 85+。", HIGH),
    Achievement("ACH_060", "👑 三冠巨星", "同一男模五項能力平均 90+、知名度 800+、正式專長 4 個以上。", HIGH),
    Achievement("ACH_061", "🌟 四星閃耀", "同時擁有 4 位知名度 800+ 男模。", HIGH),
    Achievement("ACH_062", "👑 頂流製造者", "累計培養出 3 位知名度 1000 的男模。", HIGH),
    Achievement("ACH_063", "🎭 百變人生", "完成 5 種不同性格傾向的正式形成／重大性格事件。", HIGH),
    Achievement("ACH_064", "📖 傳奇編年史", "累計完成 50 個特殊／職涯／知名度事件。", HIGH),
    Achievement("ACH_065", "💎 成熟職涯", "完成 career_50，且同一男模知名度 800+。", HIGH),
    Achievement("ACH_066", "🏆 個人代表作", "完成 legend_84。", HIGH),
    Achievement("ACH_067", "💫 被真正記住的名字", "完成 legend_85。", HIGH),
    Achievement("ACH_068", "💎 頂級工作邀請", "完成 legend_86。", HIGH),
    Achievement("ACH_069", "🥇 頂級評價", "完成 legend_88。", HIGH),
    Achievement("ACH_070", "🌟 職涯巔峰", "完成 legend_89。", HIGH),
    Achievement("ACH_071", "👑 頂級男模", "完成 legend_90。", HIGH),
    Achievement("ACH_072", "🌟 Moon Club 成為知名會館", "完成 legend_91。", HIGH),
    Achievement("ACH_073", "🎉 傳奇大型活動", "完成 legend_92。", HIGH),
    Achievement("ACH_074", "💎 頂級合作夥伴", "完成 legend_93。", HIGH),
    Achievement("ACH_075", "🚨 挺過會館危機", "完成 legend_94。", HIGH),
    Achievement("ACH_076", "👑 Moon Club 傳奇里程碑", "完成 legend_95。", HIGH),
    Achievement("ACH_077", "🌌 回到最開始的地方", "完成 legend_96。", HIGH),
    Achievement("ACH_078", "🌠 傳奇的選擇", "完成 legend_98。", HIGH),
    Achievement("ACH_079", "👑 Moon Club 的名字", "完成 legend_99。", HIGH),
    Achievement("ACH_080", "🌙 最終傳奇紀念", "完成 legend_100。", HIGH),
)


# ============================================================
# 🎲 成就等級 → 固定獎池機率
# ============================================================

# 每一組總和 = 100。
# 越高階：四種特殊獎勵比例越高；努努幣總比例越低。
# 努努幣內部：30K > 40K > 50K。
LOOT_WEIGHTS = {
    EASY: {
        REWARD_VIDEO: 5,
        REWARD_PHOTO: 5,
        REWARD_CERTIFICATE: 4,
        REWARD_BADGE: 4,
        REWARD_NUNU_30000: 40,
        REWARD_NUNU_40000: 25,
        REWARD_NUNU_50000: 17,
    },
    MEDIUM: {
        REWARD_VIDEO: 8,
        REWARD_PHOTO: 8,
        REWARD_CERTIFICATE: 7,
        REWARD_BADGE: 7,
        REWARD_NUNU_30000: 35,
        REWARD_NUNU_40000: 20,
        REWARD_NUNU_50000: 15,
    },
    MEDIUM_HIGH: {
        REWARD_VIDEO: 12,
        REWARD_PHOTO: 12,
        REWARD_CERTIFICATE: 10,
        REWARD_BADGE: 10,
        REWARD_NUNU_30000: 27,
        REWARD_NUNU_40000: 17,
        REWARD_NUNU_50000: 12,
    },
    HIGH: {
        REWARD_VIDEO: 16,
        REWARD_PHOTO: 16,
        REWARD_CERTIFICATE: 14,
        REWARD_BADGE: 14,
        REWARD_NUNU_30000: 20,
        REWARD_NUNU_40000: 12,
        REWARD_NUNU_50000: 8,
    },
}


def get_achievement(achievement_id: str) -> Optional[Achievement]:
    """依 ID 取得成就。"""
    return next(
        (achievement for achievement in ACHIEVEMENTS
         if achievement.achievement_id == achievement_id),
        None,
    )


def roll_loot(difficulty: str) -> str:
    """依成就等級從固定獎池抽出一項獎勵。"""
    weights = LOOT_WEIGHTS[difficulty]
    return random.choices(
        population=list(weights.keys()),
        weights=list(weights.values()),
        k=1,
    )[0]


# ============================================================
# 🗃️ 成就狀態資料表
# ============================================================

CREATE_ACHIEVEMENT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS moon_achievements (
    user_id INTEGER NOT NULL,
    achievement_id TEXT NOT NULL,
    completed INTEGER NOT NULL DEFAULT 0,
    reward_claimed INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT,
    PRIMARY KEY (user_id, achievement_id)
)
"""

CREATE_LOOT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS moon_achievement_loot (
    user_id INTEGER PRIMARY KEY,
    draw_count INTEGER NOT NULL DEFAULT 0
)
"""


class AchievementStore:
    """成就／盲盒資格持久化；每張資格保留來源成就等級。"""

    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self.db.execute(CREATE_ACHIEVEMENT_TABLE_SQL)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS moon_achievement_draws (
                draw_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                difficulty TEXT NOT NULL,
                created_at TEXT NOT NULL,
                used INTEGER NOT NULL DEFAULT 0,
                used_at TEXT
            )
        """)
        self.db.commit()

    def complete_achievement(self, user_id: int, achievement_id: str) -> bool:
        row = self.db.execute(
            "SELECT completed FROM moon_achievements "
            "WHERE user_id=? AND achievement_id=?",
            (user_id, achievement_id),
        ).fetchone()

        if row and row[0]:
            return False

        achievement = get_achievement(achievement_id)
        if achievement is None:
            return False

        import datetime
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        self.db.execute("""
            INSERT INTO moon_achievements
            (user_id, achievement_id, completed, reward_claimed, completed_at)
            VALUES (?, ?, 1, 0, ?)
            ON CONFLICT(user_id, achievement_id)
            DO UPDATE SET completed=1, completed_at=excluded.completed_at
        """, (user_id, achievement_id, now))

        self.db.execute("""
            INSERT INTO moon_achievement_draws
            (user_id, difficulty, created_at)
            VALUES (?, ?, ?)
        """, (user_id, achievement.difficulty, now))

        self.db.commit()
        return True

    def has_unclaimed_draw(self, user_id: int) -> bool:
        return self.db.execute(
            "SELECT 1 FROM moon_achievement_draws "
            "WHERE user_id=? AND used=0 LIMIT 1",
            (int(user_id),),
        ).fetchone() is not None

    def get_draw_count(self, user_id: int) -> int:
        row = self.db.execute(
            "SELECT COUNT(*) FROM moon_achievement_draws "
            "WHERE user_id=? AND used=0",
            (int(user_id),),
        ).fetchone()
        return int(row[0]) if row else 0

    def consume_draw_and_get_reward(self, user_id: int):
        row = self.db.execute("""
            SELECT draw_id, difficulty
            FROM moon_achievement_draws
            WHERE user_id=? AND used=0
            ORDER BY draw_id ASC
            LIMIT 1
        """, (int(user_id),)).fetchone()

        if not row:
            return None, None

        draw_id, difficulty = row
        reward = roll_loot(difficulty)

        import datetime
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        cur = self.db.execute("""
            UPDATE moon_achievement_draws
            SET used=1, used_at=?
            WHERE draw_id=? AND used=0
        """, (now, draw_id))

        if cur.rowcount != 1:
            self.db.rollback()
            return None, None

        self.db.commit()
        return reward, difficulty


# ============================================================
# 🔎 成就判定介面
# ============================================================

class AchievementEngine:
    """
    Moon Club 與成就系統之間的橋樑。

    checkers 由 Moon Club 現有資料提供。
    這裡刻意不假設資料表欄位名稱，避免破壞現有版本。
    """

    def __init__(self, store: AchievementStore):
        self.store = store
        self.checkers: dict[str, Callable[[int], bool]] = {}

    def register_checker(
        self,
        achievement_id: str,
        checker: Callable[[int], bool],
    ) -> None:
        self.checkers[achievement_id] = checker

    def check_one(self, user_id: int, achievement_id: str) -> bool:
        checker = self.checkers.get(achievement_id)
        if checker is None:
            return False

        if not checker(user_id):
            return False

        return self.store.complete_achievement(user_id, achievement_id)

    def check_all(self, user_id: int) -> list[str]:
        newly_completed: list[str] = []

        for achievement in ACHIEVEMENTS:
            if self.check_one(user_id, achievement.achievement_id):
                newly_completed.append(achievement.achievement_id)

        return newly_completed
