# -*- coding: utf-8 -*-
"""
🌙 Moon Club｜成就與成就盲盒系統

正式規則：
- 80 個成就：簡單 5／中 20／中高 25／高 30
- 不使用好感度／默契作為成就條件
- 成就完成後取得 1 次免費「成就盲盒」資格
- 同一成就只能取得一次資格
- 固定 15 種盲盒獎池；所有成就難度統一機率
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
# 🎁 固定盲盒獎池（所有成就難度統一機率）
# ============================================================

REWARD_VIDEO = "影片合集"
REWARD_PHOTO = "照片合集"
REWARD_POSTER = "雙人海報"
REWARD_CHIBI_STICKERS = "雙人 Q 版貼圖"
REWARD_CERTIFICATE = "結婚證書"
REWARD_BANNER = "雙人橫幅"
REWARD_COUPLE_PHOTOS_2 = "雙人合照 × 2 張"
REWARD_COUPLE_PHOTO_1 = "雙人合照 × 1 張"
REWARD_ILLUSTRATION = "雙人插畫"
REWARD_BADGE = "雙人徽章"
REWARD_RANDOM_PROFILE_2 = "隨機風格人設圖 × 2"
REWARD_RANDOM_PROFILE_1 = "隨機風格人設圖 × 1"
REWARD_NUNU_15000 = "15,000 努努幣"
REWARD_NUNU_10000 = "10,000 努努幣"
REWARD_NUNU_5000 = "5,000 努努幣"

LOOT_WEIGHTS: dict[str, float] = {
    REWARD_VIDEO: 0.2,
    REWARD_PHOTO: 0.5,
    REWARD_POSTER: 1,
    REWARD_CHIBI_STICKERS: 1.5,
    REWARD_CERTIFICATE: 2,
    REWARD_BANNER: 3,
    REWARD_COUPLE_PHOTOS_2: 4,
    REWARD_COUPLE_PHOTO_1: 5,
    REWARD_ILLUSTRATION: 6,
    REWARD_BADGE: 7,
    REWARD_RANDOM_PROFILE_2: 9,
    REWARD_RANDOM_PROFILE_1: 10,
    REWARD_NUNU_15000: 12,
    REWARD_NUNU_10000: 17,
    REWARD_NUNU_5000: 21.8,
}

LOOT_POOL: tuple[str, ...] = tuple(LOOT_WEIGHTS.keys())


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
    Achievement("ACH_001", "🌱 新人站穩腳步", "任一男模完成事件「小型公開機會」。", EASY),
    Achievement("ACH_002", "📸 第一次留下名字", "任一男模完成事件「非工作場合被認出」。", EASY),
    Achievement("ACH_003", "🤝 第一份正式合作", "任一男模完成事件「第一個正式合作」。", EASY),
    Achievement("ACH_004", "🎓 培養出方向", "任一男模完成事件「專長正式形成」。", EASY),
    Achievement("ACH_005", "🌟 開始被真正看見", "任一男模知名度達 400，並完成事件「第一次正式介紹」。", EASY),

    # 🟡 中 × 20
    Achievement("ACH_006", "🔥 人氣開始累積", "任一男模知名度達 500。", MEDIUM),
    Achievement("ACH_007", "💬 熟面孔", "任一男模完成事件「固定支持者」。", MEDIUM),
    Achievement("ACH_008", "🌟 特別邀請", "任一男模完成事件「特別工作邀請」。", MEDIUM),
    Achievement("ACH_009", "🎤 找到自己的舞台", "完成事件「小型演出的機會」。", MEDIUM),
    Achievement("ACH_010", "📈 專長能力突破", "完成事件「專長能力突破」。", MEDIUM),
    Achievement("ACH_011", "🏆 因專長受到肯定", "完成事件「因專長獲得肯定」。", MEDIUM),
    Achievement("ACH_012", "🎭 第二條路", "任一男模正式擁有 2 個興趣／專長。", MEDIUM),
    Achievement("ACH_013", "🧠 雙項突出", "任一男模有 2 項能力達 70+。", MEDIUM),
    Achievement("ACH_014", "💪 全面成長", "任一男模五項能力平均達 50+。", MEDIUM),
    Achievement("ACH_015", "📖 經歷開始累積", "任一男模累積 15 筆職涯／事件記憶。", MEDIUM),
    Achievement("ACH_016", "🎓 培訓成果受到注意", "完成事件「培訓老師的特別評價」。", MEDIUM),
    Achievement("ACH_017", "💥 突破瓶頸", "完成事件「突破訓練瓶頸」。", MEDIUM),
    Achievement("ACH_018", "🌟 獲得外部推薦", "完成事件「獲得外部推薦」。", MEDIUM),
    Achievement("ACH_019", "✉️ 特別培訓邀請", "完成事件「收到特殊培訓邀請」。", MEDIUM),
    Achievement("ACH_020", "🎭 性格逐漸成形", "完成任一正式性格形成事件。", MEDIUM),
    Achievement("ACH_021", "🌙 看見另一面", "完成事件「不願提起的過去」。", MEDIUM),
    Achievement("ACH_022", "📖 職涯起步", "完成事件「第一次公開活動」。", MEDIUM),
    Achievement("ACH_023", "📰 開始受到外界注意", "完成事件「開始受到外界注意」。", MEDIUM),
    Achievement("ACH_024", "🏛️ Moon Club 開始有名氣", "完成會館事件「🏛️ Moon Club 開始有名氣」；需累積多位男模人氣及會館工作紀錄", MEDIUM),
    Achievement("ACH_025", "💌 收到合作邀請", "完成會館事件「💌 收到合作邀請」；需累積會館知名度及工作／活動紀錄", MEDIUM),

    # 🟠 中高 × 25
    Achievement("ACH_026", "🔥 重要活動", "完成事件「重要活動的關注」。", MEDIUM_HIGH),
    Achievement("ACH_027", "🌟 成長受到矚目", "完成事件「培養能力受到注意」。", MEDIUM_HIGH),
    Achievement("ACH_028", "📸 現場人氣", "完成事件「明顯的現場人氣」。", MEDIUM_HIGH),
    Achievement("ACH_029", "👥 新人因你而來", "完成事件「新人開始注意 Moon Club」。", MEDIUM_HIGH),
    Achievement("ACH_030", "🤝 更大型的合作", "完成事件「更大型的合作」。", MEDIUM_HIGH),
    Achievement("ACH_031", "🌟 一位真正的明星", "任一男模知名度達 800。", MEDIUM_HIGH),
    Achievement("ACH_032", "👑 代表人物", "任一男模知名度達 1000。", MEDIUM_HIGH),
    Achievement("ACH_033", "🧠 全面成熟", "任一男模五項能力平均達 70+。", MEDIUM_HIGH),
    Achievement("ACH_034", "💪 三項專精", "任一男模有 3 項能力達 80+。", MEDIUM_HIGH),
    Achievement("ACH_035", "🔥 雙項巔峰", "任一男模有 2 項能力達 90+。", MEDIUM_HIGH),
    Achievement("ACH_036", "🎭 多元發展", "任一男模擁有 3 個正式專長。", MEDIUM_HIGH),
    Achievement("ACH_037", "📈 專長帶來機會", "完成事件「專長帶來重大機會」。", MEDIUM_HIGH),
    Achievement("ACH_038", "💥 重大的能力突破", "完成事件「💥 一次重大的能力突破」", MEDIUM_HIGH),
    Achievement("ACH_039", "👑 第二性格形成", "完成事件「🌟 第二性格形成」", MEDIUM_HIGH),
    Achievement("ACH_040", "🏆 獲得專業肯定", "完成事件「🏆 獲得專業肯定」", MEDIUM_HIGH),
    Achievement("ACH_041", "⚖️ 職涯方向", "完成事件「職涯方向的選擇」。", MEDIUM_HIGH),
    Achievement("ACH_042", "💎 高級工作", "完成事件「高級工作邀請」。", MEDIUM_HIGH),
    Achievement("ACH_043", "👑 職涯重大轉折", "完成事件「👑 職涯第一次重大轉折」", MEDIUM_HIGH),
    Achievement("ACH_044", "🎉 第一次大型會館活動", "完成事件「🎉 第一次大型會館活動」", MEDIUM_HIGH),
    Achievement("ACH_045", "🤝 男模開始形成團隊", "完成事件「男模之間建立友誼」。", MEDIUM_HIGH),
    Achievement("ACH_046", "🌟 成員突然爆紅", "完成事件「🌟 一位成員突然爆紅」", MEDIUM_HIGH),
    Achievement("ACH_047", "🎭 團體合作", "完成事件「🎭 團體合作活動」", MEDIUM_HIGH),
    Achievement("ACH_048", "🏛️ 會館突破", "Moon Club 知名度達 500，並完成會館事件「🎉 第一次大型會館活動」", MEDIUM_HIGH),
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
    Achievement("ACH_065", "💎 成熟職涯", "完成職涯事件「👑 職涯第一次重大轉折」，且同一男模知名度達 800 以上", HIGH),
    Achievement("ACH_066", "🏆 個人代表作", "完成事件「🏆 個人代表作」", HIGH),
    Achievement("ACH_067", "💫 被真正記住的名字", "完成事件「💫 被真正記住的名字」", HIGH),
    Achievement("ACH_068", "💎 頂級工作邀請", "完成事件「💎 頂級工作邀請」", HIGH),
    Achievement("ACH_069", "🥇 頂級評價", "完成事件「🥇 頂級評價」", HIGH),
    Achievement("ACH_070", "🌟 職涯巔峰", "完成事件「🌟 職涯巔峰」", HIGH),
    Achievement("ACH_071", "👑 頂級男模", "完成事件「👑 頂級男模稱號」", HIGH),
    Achievement("ACH_072", "🌟 Moon Club 成為知名會館", "完成事件「🌟 Moon Club 成為知名會館」", HIGH),
    Achievement("ACH_073", "🎉 傳奇大型活動", "完成事件「🎉 傳奇級大型活動」", HIGH),
    Achievement("ACH_074", "💎 頂級合作夥伴", "完成事件「💎 頂級合作夥伴」", HIGH),
    Achievement("ACH_075", "🚨 挺過會館危機", "完成事件「🚨 Moon Club 最大危機」", HIGH),
    Achievement("ACH_076", "👑 Moon Club 傳奇里程碑", "完成事件「👑 Moon Club 傳奇里程碑」", HIGH),
    Achievement("ACH_077", "🌌 回到最開始的地方", "完成事件「🌌 回到最開始的地方」", HIGH),
    Achievement("ACH_078", "🌠 傳奇的選擇", "完成事件「🌠 傳奇的選擇」", HIGH),
    Achievement("ACH_079", "👑 Moon Club 的名字", "完成事件「👑 Moon Club 的名字」", HIGH),
    Achievement("ACH_080", "🌙 最終傳奇紀念", "完成事件「🌙 最終傳奇紀念」", HIGH),
)


# ============================================================
# 🎲 統一獎池機率
# ============================================================

# 所有成就難度共用同一組機率，總和為 100%。


def get_achievement(achievement_id: str) -> Optional[Achievement]:
    """依 ID 取得成就。"""
    return next(
        (achievement for achievement in ACHIEVEMENTS
         if achievement.achievement_id == achievement_id),
        None,
    )


def roll_loot(difficulty: str = "") -> str:
    """所有成就難度共用同一套獎池機率。"""
    return random.choices(
        population=list(LOOT_WEIGHTS.keys()),
        weights=list(LOOT_WEIGHTS.values()),
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
        # 舊版本可能只留下成就完成紀錄，沒有建立對應的盲盒資格。
        # 以「各難度已完成成就數」對照「該難度所有資格紀錄（包含已使用）」補齊差額，
        # 不會重發已存在的資格，也不會重置已使用的資格。
        self._backfill_missing_draws()

    def _backfill_missing_draws(self) -> None:
        import datetime

        difficulty_by_id = {a.achievement_id: a.difficulty for a in ACHIEVEMENTS}
        completed_rows = self.db.execute(
            "SELECT user_id, achievement_id FROM moon_achievements WHERE completed=1"
        ).fetchall()
        completed_counts: dict[tuple[int, str], int] = {}
        for user_id, achievement_id in completed_rows:
            difficulty = difficulty_by_id.get(str(achievement_id))
            if difficulty is None:
                continue
            key = (int(user_id), difficulty)
            completed_counts[key] = completed_counts.get(key, 0) + 1

        draw_rows = self.db.execute(
            "SELECT user_id, difficulty, COUNT(*) FROM moon_achievement_draws "
            "GROUP BY user_id, difficulty"
        ).fetchall()
        draw_counts = {(int(uid), str(diff)): int(count) for uid, diff, count in draw_rows}
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        missing = []
        for key, completed_count in completed_counts.items():
            difference = completed_count - draw_counts.get(key, 0)
            if difference > 0:
                uid, difficulty = key
                missing.extend((uid, difficulty, now) for _ in range(difference))

        if missing:
            self.db.executemany(
                "INSERT INTO moon_achievement_draws (user_id, difficulty, created_at, used) "
                "VALUES (?, ?, ?, 0)",
                missing,
            )
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

    def get_pending_difficulties(self, user_id: int) -> list[str]:
        """取得玩家所有尚未使用的盲盒資格，資格與難度永久保留。"""
        rows = self.db.execute(
            "SELECT difficulty FROM moon_achievement_draws "
            "WHERE user_id=? AND used=0 ORDER BY draw_id ASC",
            (int(user_id),),
        ).fetchall()
        return [str(row[0]) for row in rows]

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
        # 使用 SAVEPOINT，避免共用 SQLite 連線已在交易中時再次 BEGIN 而報錯。
        # 只消耗一張資格；若外層已有交易，不會擅自提交外層交易。
        savepoint = "moon_achievement_draw"
        try:
            self.db.execute(f"SAVEPOINT {savepoint}")
            row = self.db.execute("""
                SELECT draw_id, difficulty
                FROM moon_achievement_draws
                WHERE user_id=? AND used=0
                ORDER BY draw_id ASC
                LIMIT 1
            """, (int(user_id),)).fetchone()

            if not row:
                self.db.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                self.db.execute(f"RELEASE SAVEPOINT {savepoint}")
                return None, None

            draw_id, difficulty = row
            reward = roll_loot()

            import datetime
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()

            cur = self.db.execute("""
                UPDATE moon_achievement_draws
                SET used=1, used_at=?
                WHERE draw_id=? AND user_id=? AND used=0
            """, (now, draw_id, int(user_id)))

            if cur.rowcount != 1:
                self.db.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                self.db.execute(f"RELEASE SAVEPOINT {savepoint}")
                return None, None

            self.db.execute(f"RELEASE SAVEPOINT {savepoint}")
            return reward, difficulty
        except Exception:
            try:
                self.db.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                self.db.execute(f"RELEASE SAVEPOINT {savepoint}")
            except Exception:
                # Savepoint may already have been released; preserve the original exception.
                pass
            raise


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
