import discord
from discord import app_commands
from discord.ext import commands, tasks
import sqlite3
from datetime import datetime, timedelta
import pytz
import os
import threading
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer

# 🌏 台灣時間
tz = pytz.timezone("Asia/Taipei")
last_birthday_check = None

# 🔧 intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 💾 資料庫
conn = sqlite3.connect("bot.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    money INTEGER DEFAULT 0,
    checkin_total INTEGER DEFAULT 0,
    checkin_streak INTEGER DEFAULT 0,
    last_checkin TEXT,
    birthday TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

conn.commit()

# 🚀 啟動
@bot.event
async def on_ready():
    print(f"已登入：{bot.user}")
    await bot.tree.sync()
    birthday_check.start()

# 🐰 簽到
@bot.tree.command(name="簽到", description="每日簽到")
async def checkin(interaction: discord.Interaction):

    await interaction.response.defer()

    user_id = str(interaction.user.id)
    now = datetime.now(tz)
    today = now.date()

    c.execute("SELECT last_checkin, checkin_total, checkin_streak, money FROM users WHERE user_id=?", (user_id,))
    data = c.fetchone()

    if data and data[0] == str(today):
        await interaction.followup.send("❌ 今天已簽到")
        return

    if data:
        total = data[1] + 1
        streak = data[2] + 1 if data[0] == str(today - timedelta(days=1)) else 1
        money = data[3] + 100
        c.execute("UPDATE users SET last_checkin=?, checkin_total=?, checkin_streak=?, money=? WHERE user_id=?",
                  (str(today), total, streak, money, user_id))
    else:
        total, streak, money = 1, 1, 100
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
                  (user_id, money, total, streak, str(today), None))

    conn.commit()

    embed = discord.Embed(title="🌙 簽到成功", color=discord.Color.blurple())
    embed.add_field(name="💰 金幣", value=money)
    embed.add_field(name="🔥 連續", value=streak)
    await interaction.followup.send(embed=embed)

# 💰 錢包
@bot.tree.command(name="錢包", description="查看你的金幣")
async def wallet(interaction: discord.Interaction):

    await interaction.response.defer()

    user_id = str(interaction.user.id)
    c.execute("SELECT money FROM users WHERE user_id=?", (user_id,))
    data = c.fetchone()

    money = data[0] if data else 0

    await interaction.followup.send(f"💰 你有 {money} 金幣")

# 🎂 設定生日
@bot.tree.command(name="設定生日", description="MM-DD")
async def set_birthday(interaction: discord.Interaction, date: str):

    await interaction.response.defer()

    try:
        datetime.strptime(date, "%m-%d")
    except:
        await interaction.followup.send("❌ 格式錯誤")
        return

    user_id = str(interaction.user.id)

    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    c.execute("UPDATE users SET birthday=? WHERE user_id=?", (date, user_id))
    conn.commit()

    await interaction.followup.send(f"🎂 設定成功：{date}")

# 🎉 每日生日檢查
@tasks.loop(minutes=1)
async def birthday_check():

    global last_birthday_check

    now = datetime.now(tz)
    today_str = now.strftime("%Y-%m-%d")

    if last_birthday_check == today_str:
        return

    if now.hour != 8 or now.minute != 0:
        return

    last_birthday_check = today_str

    today = now.strftime("%m-%d")
    c.execute("SELECT user_id FROM users WHERE birthday=?", (today,))
    users = c.fetchall()

    if not users:
        return

    c.execute("SELECT value FROM settings WHERE key='welcome_channel'")
    channel_data = c.fetchone()

    if not channel_data:
        return

    channel = bot.get_channel(int(channel_data[0]))

    for (uid,) in users:
        user = await bot.fetch_user(int(uid))

        # 💌 私訊
        try:
            await user.send("🎂 生日快樂！")
        except:
            pass

        # 🌙 公開卡片
        embed = discord.Embed(
            title="🌙 Birthday Blessing",
            description=f"{user.mention} 今天生日！",
            color=discord.Color.purple()
        )

        await channel.send(embed=embed)

# 🌐 Render 假網站
def run_web():
    port = int(os.environ.get("PORT", 10000))
    with TCPServer(("", port), SimpleHTTPRequestHandler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_web).start()

bot.run(os.getenv("TOKEN"))
