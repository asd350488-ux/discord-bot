# ==========================
# 🌙 七夕限定盲盒抽獎系統
# ==========================

import discord
import random
from datetime import datetime, timedelta

from discord.ext import commands

from database import conn, c
from config import BOT_ADMINS


# ==========================
# 🌙 七夕限定盲盒設定
# ==========================

QIXI_DATE = "2026-08-19"

# --------------------------
# 🎟️ 每人最多參與次數
# --------------------------

LIMITED_LOTTERY_MAX_TIMES = 2

# --------------------------
# 💰 參與費用
# --------------------------

LIMITED_LOTTERY_FIRST_PRICE = 500

LIMITED_LOTTERY_SECOND_PRICE = 5000

# --------------------------
# 🎁 獎品機率
# --------------------------

LIMITED_LOTTERY_PRIZES = [
    {
        "type": "money",
        "name": "💰 努努幣 5,000",
        "value": 5000,
        "weight": 40,
    },
    {
        "type": "money",
        "name": "💰 努努幣 8,000",
        "value": 8000,
        "weight": 30,
    },
    {
        "type": "sticker",
        "name": "🎨 角色 Q 版貼圖 ×1",
        "value": 1,
        "weight": 20,
    },
    {
        "type": "couple",
        "name": "💕 角色合照 ×1",
        "value": 1,
        "weight": 10,
    },
]


# ==========================
# 🌙 判斷是否為七夕活動日
# ==========================

def is_qixi_day():

    now = datetime.now()

    return now.strftime("%Y-%m-%d") == QIXI_DATE


# ==========================
# 🌙 取得玩家已參與次數
# ==========================

def get_limited_lottery_count(user_id):

    c.execute(
        """
        SELECT COUNT(*)
        FROM limited_lottery_entries
        WHERE user_id = ?
        """,
        (str(user_id),),
    )

    result = c.fetchone()

    return result[0] if result else 0


# ==========================
# 🌙 建立限定盲盒資料表
# ==========================

def init_limited_lottery_database():

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS limited_lottery_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            draw_number INTEGER NOT NULL,
            price INTEGER NOT NULL,
            prize_type TEXT NOT NULL,
            prize_value TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    conn.commit()


# ==========================
# 🌙 啟動限定盲盒系統
# ==========================

def setup_limited_lottery(bot):

    init_limited_lottery_database()

    print("✅ 七夕限定盲盒系統已載入")