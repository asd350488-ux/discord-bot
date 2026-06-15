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
@bot.tree.command(name="簽到")
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

    embed = discord.Embed(
        title="🌙 𝑴𝒐𝒐𝒏 𝑪𝒉𝒆𝒄𝒌𝒊𝒏",
        description="✨ 你再次踏入了星月之境",
        color=discord.Color.from_rgb(186, 85, 211)
    )

    embed.set_author(
        name=f"{interaction.user.display_name} ✦ 星月契約者",
        icon_url=interaction.user.display_avatar.url
    )

    embed.add_field(name="💰 金幣", value=f"```{money}```", inline=True)
    embed.add_field(name="🔥 連續簽到", value=f"```{streak} 天```", inline=True)
    embed.add_field(name="📅 總簽到", value=f"```{total} 天```", inline=False)

    embed.set_thumbnail(url=interaction.user.display_avatar.url)

    embed.set_image(
        url="https://media.discordapp.net/attachments/1504831006090465320/1515773543286313229/IMG_1765.jpg"
    )

    embed.set_footer(text="極曜月葵 ✦ 每日儀式")

    await interaction.followup.send(embed=embed)

# 💰 錢包
@bot.tree.command(name="錢包")
async def wallet(interaction: discord.Interaction):

    await interaction.response.defer()

    user_id = str(interaction.user.id)
    c.execute("SELECT money, checkin_total, checkin_streak FROM users WHERE user_id=?", (user_id,))
    data = c.fetchone()

    money, total, streak = data if data else (0, 0, 0)

    embed = discord.Embed(
        title="💰 𝑳𝒖𝒏𝒂 𝑾𝒆𝒂𝒍𝒕𝒉",
        description="你的命運與財富交織 ✨",
        color=discord.Color.gold()
    )

    embed.set_author(
        name=f"{interaction.user.display_name} ✦ 星之持有者",
        icon_url=interaction.user.display_avatar.url
    )

    embed.add_field(name="💵 金幣", value=f"```{money}```", inline=True)
    embed.add_field(name="📅 總簽到", value=f"```{total} 天```", inline=True)
    embed.add_field(name="🔥 連續", value=f"```{streak} 天```", inline=True)

    embed.set_thumbnail(url=interaction.user.display_avatar.url)

    embed.set_footer(text="極曜月葵 ✦ 財富系統")

    await interaction.followup.send(embed=embed)

# 🏆 排行榜
@bot.tree.command(name="排行榜")
async def leaderboard(interaction: discord.Interaction):

    await interaction.response.defer()

    c.execute("SELECT user_id, money FROM users ORDER BY money DESC")
    data = c.fetchall()
    top10 = data[:10]

    embed = discord.Embed(
        title="🏆 𝑳𝒖𝒏𝒂 𝑻𝒉𝒓𝒐𝒏𝒆",
        description="誰將登上王座 👑",
        color=discord.Color.gold()
    )

    medals = ["🥇", "🥈", "🥉"]
    text = ""

    for i, (uid, money) in enumerate(top10):
        user = await bot.fetch_user(int(uid))
        medal = medals[i] if i < 3 else f"{i+1}."
        text += f"{medal} ✦ {user.display_name} ｜ 💰 {money}\n"

    embed.add_field(name="🌌 星月排名", value=text, inline=False)

    await interaction.followup.send(embed=embed)

# ⚙️ 設定歡迎頻道
@bot.tree.command(name="設定歡迎頻道", description="設定歡迎訊息頻道")
async def set_welcome_channel(interaction: discord.Interaction, channel: discord.TextChannel):

    c.execute("REPLACE INTO settings (key, value) VALUES ('welcome_channel', ?)", (str(channel.id),))
    conn.commit()

    await interaction.response.send_message(f"✅ 已設定歡迎頻道：{channel.mention}")

# ⚙️ 設定歡迎訊息
@bot.tree.command(name="設定歡迎訊息", description="設定歡迎內容")
async def set_welcome_message(interaction: discord.Interaction, message: str):

    c.execute("REPLACE INTO settings (key, value) VALUES ('welcome_message', ?)", (message,))
    conn.commit()

    await interaction.response.send_message("✅ 歡迎訊息已更新")

# 🎂 設定生日
@bot.tree.command(name="設定生日")
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

# 🎉 生日提醒
@tasks.loop(minutes=1)
async def birthday_check():

    global last_birthday_check

    now = datetime.now(tz)

    if now.hour != 8 or now.minute != 0:
        return

    today = now.strftime("%m-%d")

    c.execute("SELECT user_id FROM users WHERE birthday=?", (today,))
    users = c.fetchall()

    if not users:
        return

    for (uid,) in users:
        user = await bot.fetch_user(int(uid))

        try:
            await user.send("🎂 生日快樂！✨")
        except:
            pass

# 🌸 歡迎系統
@bot.event
async def on_member_join(member):

    import asyncio

    # 📡 取得頻道
    c.execute("SELECT value FROM settings WHERE key='welcome_channel'")
    channel_data = c.fetchone()

    if not channel_data:
        return

    channel = bot.get_channel(int(channel_data[0]))
    if not channel:
        return

    # 📝 取得你設定的歡迎文
    c.execute("SELECT value FROM settings WHERE key='welcome_message'")
    msg_data = c.fetchone()

    if msg_data:
        message = msg_data[0]
    else:
        message = "歡迎 {user} 加入伺服器 ✨"

    count = member.guild.member_count

    # 🔄 替換變數
    message = message.replace("{user}", member.mention)
    message = message.replace("{count}", str(count))

    # 🎬 動畫開始
    msg = await channel.send("🌙 星門正在開啟...")

    await asyncio.sleep(1.2)

    await msg.edit(content="✨ 傳送完成，正在載入星月記錄...")

    await asyncio.sleep(1.2)

    # 🌙 高級卡片（用你的歡迎文）
    embed = discord.Embed(
        title="🌙 𝑵𝒆𝒘 𝑨𝒓𝒓𝒊𝒗𝒂𝒍",
        description=message,
        color=discord.Color.from_rgb(186, 85, 211)
    )

    embed.set_author(
        name=f"{member.display_name} ✦ 星月新生",
        icon_url=member.display_avatar.url
    )

    embed.add_field(
        name="📊 成員編號",
        value=f"第 {count} 位",
        inline=True
    )

    embed.set_thumbnail(url=member.display_avatar.url)

    embed.set_image(
        url="https://media.discordapp.net/attachments/1504831006090465320/1515773543286313229/IMG_1765.jpg"
    )

    embed.set_footer(text="極曜月葵 ✦ 歡迎儀式")

    await asyncio.sleep(0.8)

    await msg.edit(content=None, embed=embed)

# 🌐 Render
def run_web():
    port = int(os.environ.get("PORT", 10000))
    with TCPServer(("", port), SimpleHTTPRequestHandler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_web).start()

bot.run(os.getenv("TOKEN"))
