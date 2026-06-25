# ==========================================
# 🌙 極曜月葵｜Database
# ==========================================

import sqlite3

DB_PATH = "/var/data/bot.db"

conn = sqlite3.connect(
    DB_PATH,
    check_same_thread=False
)

c = conn.cursor()
