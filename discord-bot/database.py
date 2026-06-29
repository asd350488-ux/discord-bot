# ==========================================
# 🌙 Moon Bot v2｜Database
# ==========================================

import os
import sqlite3

# Render 使用永久磁碟
if os.path.exists("/var/data"):
    DB_PATH = "/var/data/bot.db"

# 本機開發
else:
    DB_PATH = "bot.db"

conn = sqlite3.connect(
    DB_PATH,
    check_same_thread=False
)

conn.row_factory = sqlite3.Row

c = conn.cursor()