import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
from datetime import datetime, timedelta
import pytz

# 🌏 台灣時間
tz = pytz.timezone("Asia/Taipei")
last_birthday_check = None

# 🔧 intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# 🤖 建立 bot
bot = commands.Bot(command_prefix="!", intents=intents)

# 💾 資料庫
conn = sqlite3.connect("bot.db")
c = conn.cursor()

# 👤 使用者資料表
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
try:
    c.execute("ALTER TABLE users ADD COLUMN birthday TEXT")
    conn.commit()
except:
    pass
# ⚙️ 設定資料表
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
    await_bot.tree.sync()

birthday_check.start()
# 🐰 簽到
@bot.tree.command(name="簽到", description="每日簽到（00:00重置）")
async def checkin(interaction: discord.Interaction):

    await interaction.response.defer()

    try:
        user_id = str(interaction.user.id)

        now = datetime.now(tz)
        today = now.date()

        # ⏰ 明天 00:00
        tomorrow = datetime.combine(today + timedelta(days=1), datetime.min.time())
        tomorrow = tz.localize(tomorrow)

        c.execute("SELECT last_checkin, checkin_total, checkin_streak, money FROM users WHERE user_id=?", (user_id,))
        data = c.fetchone()

        if data:
            if data[0]:
                try:
                    last_checkin = datetime.strptime(data[0], "%Y-%m-%d").date()
                except:
                    last_checkin = None
            else:
                last_checkin = None

            # ❌ 已簽到
            if last_checkin == today:
                remaining = tomorrow - now
                hours = remaining.seconds // 3600
                minutes = (remaining.seconds % 3600) // 60

                embed = discord.Embed(
                    title="⏳ 今日已簽到",
                    description="你今天已經領過獎勵了",
                    color=discord.Color.red()
                )

                embed.add_field(
                    name="⏰ 下次簽到",
                    value=f"```{hours} 小時 {minutes} 分鐘```",
                    inline=False
                )

                await interaction.followup.send(embed=embed)
                return

            # 🔥 連續簽到
            if last_checkin == today - timedelta(days=1):
                streak = data[2] + 1
            else:
                streak = 1

            total = data[1] + 1
            money = data[3] + 100

            c.execute("""
            UPDATE users 
            SET last_checkin=?, checkin_total=?, checkin_streak=?, money=? 
            WHERE user_id=?
            """, (str(today), total, streak, money, user_id))

        else:
            total = 1
            streak = 1
            money = 100

            c.execute("""
            INSERT INTO users (user_id, money, checkin_total, checkin_streak, last_checkin)
            VALUES (?, ?, ?, ?, ?)
            """, (user_id, money, total, streak, str(today)))

        conn.commit()

        # 🎨 簽到成功 UI
        embed = discord.Embed(
            title="🌙 每日簽到成功",
            description="✨ 今天也有好好出現呢",
            color=discord.Color.from_rgb(88, 101, 242)
        )

        embed.set_author(
            name=f"{interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url
        )

        embed.add_field(name="📅 總簽到", value=f"```{total} 天```", inline=True)
        embed.add_field(name="🔥 連續簽到", value=f"```{streak} 天```", inline=True)
        embed.add_field(name="💰 獲得獎勵", value="```+100 金幣```", inline=False)

        embed.set_footer(text="每天 00:00 重置簽到")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        print("錯誤：", e)
        await interaction.followup.send("❌ 發生錯誤，請聯絡管理員")


# 💰 錢包
@bot.tree.command(name="錢包", description="查看你的金幣")
async def wallet(interaction: discord.Interaction, member: discord.Member = None):

    await interaction.response.defer()

    try:
        target = member if member else interaction.user
        user_id = str(target.id)

        c.execute("SELECT money, checkin_total, checkin_streak FROM users WHERE user_id=?", (user_id,))
        data = c.fetchone()

        if data:
            money, total, streak = data
        else:
            money, total, streak = 0, 0, 0

        embed = discord.Embed(
            title="💰 錢包資訊",
            description="你的財富狀況 ✨",
            color=discord.Color.gold()
        )

        embed.set_author(
            name=f"{target.display_name}",
            icon_url=target.display_avatar.url
        )

        embed.add_field(name="💵 金幣", value=f"```{money}```", inline=True)
        embed.add_field(name="📅 總簽到", value=f"```{total} 天```", inline=True)
        embed.add_field(name="🔥 連續簽到", value=f"```{streak} 天```", inline=True)

        embed.set_footer(text="努力累積財富吧 💸")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        print("錯誤：", e)
        await interaction.followup.send("❌ 發生錯誤，請聯絡管理員")

#  生日

@bot.tree.command(name="設定生日", description="設定你的生日（格式：MM-DD）")
async def set_birthday(interaction: discord.Interaction, date: str):

    await interaction.response.defer()

    try:
        user_id = str(interaction.user.id)

        # 檢查格式
        try:
            datetime.strptime(date, "%m-%d")
        except:
            await interaction.followup.send("❌ 格式錯誤！請用 MM-DD（例如 05-20）")
            return

        c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        if not c.fetchone():
            c.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))

        c.execute("UPDATE users SET birthday=? WHERE user_id=?", (date, user_id))
        conn.commit()

        embed = discord.Embed(
            title="🎂 生日設定成功",
            description=f"你的生日已設定為 **{date}**",
            color=discord.Color.pink()
        )

        await interaction.followup.send(embed=embed)

    except Exception as e:
        print("錯誤：", e)
        await interaction.followup.send("❌ 發生錯誤")


@bot.tree.command(name="我的生日", description="查看你的生日")
async def my_birthday(interaction: discord.Interaction):

    await interaction.response.defer()

    try:
        user_id = str(interaction.user.id)

        c.execute("SELECT birthday FROM users WHERE user_id=?", (user_id,))
        data = c.fetchone()

        if data and data[0]:
            await interaction.followup.send(f"🎂 你的生日是：**{data[0]}**")
        else:
            await interaction.followup.send("❌ 你還沒設定生日！用 /設定生日")

    except Exception as e:
        print("錯誤：", e)
        await interaction.followup.send("❌ 發生錯誤")
@tasks.loop(minutes=1)
async def birthday_check():

    now = datetime.now(tz)

    # 🎯 只在 08:00 觸發
    if now.hour != 8 or now.minute != 0:
        return

    today = now.strftime("%m-%d")

    # 找今天生日的人
    c.execute("SELECT user_id FROM users WHERE birthday=?", (today,))
    users = c.fetchall()

    if not users:
        return

    # 🔍 取得頻道
    c.execute("SELECT value FROM settings WHERE key='welcome_channel'")
    channel_data = c.fetchone()

    if not channel_data:
        return

    channel = bot.get_channel(int(channel_data[0]))
    if not channel:
        return

    for (user_id,) in users:
        user = await bot.fetch_user(int(user_id))
# 💌 私訊祝福
try:
    dm_embed = discord.Embed(
        title="🎂 生日快樂",
        description="今天是屬於你的日子 ✨\n願所有溫柔都降臨在你身上 🌙",
        color=discord.Color.pink()
    )

    dm_embed.set_thumbnail(url=user.display_avatar.url)
    dm_embed.set_footer(text="極曜月葵 ✦ 祝你生日快樂")

    await user.send(embed=dm_embed)

except:
    pass  # 如果對方關私訊就略過


       embed = discord.Embed(
    title="🌙 𝑩𝒊𝒓𝒕𝒉𝒅𝒂𝒚 𝑩𝒍𝒆𝒔𝒔𝒊𝒏𝒈",
    description=f"✨ 今天是 {user.mention} 的誕生日 ✨\n\n願星光與月影都為你停留 🌙",
    color=discord.Color.from_rgb(186, 85, 211)
)

embed.set_author(
    name=f"{user.display_name} ✦ 星月之子",
    icon_url=user.display_avatar.url
)

embed.set_thumbnail(url=user.display_avatar.url)

embed.add_field(
    name="🎂 今日主角",
    value=user.mention,
    inline=True
)

embed.add_field(
    name="🌸 特別日",
    value="生日祝福進行中",
    inline=True
)

embed.add_field(
    name="🎁 願望",
    value="願你被溫柔以待 ✨",
    inline=False
)

# 🌌 背景圖（可以換你自己的）
embed.set_image(
    url="https://media.discordapp.net/attachments/1504831006090465320/1515773543286313229/IMG_1765.jpg"
)

embed.set_footer(text="極曜月葵 ✦ 生日祝福系統")

# 💰 富豪排行榜

@bot.tree.command(name="排行榜", description="查看富豪排行榜")
async def leaderboard(interaction: discord.Interaction):

    await interaction.response.defer()

    try:
        user_id = str(interaction.user.id)

        # 🔥 全部排序（用來算名次）
        c.execute("SELECT user_id, money FROM users ORDER BY money DESC")
        all_data = c.fetchall()

        # 🏆 前10名
        top10 = all_data[:10]

        if not all_data:
            await interaction.followup.send("❌ 還沒有人上榜！")
            return

        embed = discord.Embed(
            title="🏆 富豪排行榜",
            description="誰是最有錢的人呢？💰",
            color=discord.Color.gold()
        )

        rank_text = ""
        medals = ["🥇", "🥈", "🥉"]

        # 🥇 前10顯示
        for i, (uid, money) in enumerate(top10):
            user = await bot.fetch_user(int(uid))

            if i < 3:
                medal = medals[i]
            else:
                medal = f"{i+1}."

            rank_text += f"{medal} {user.display_name} ｜ 💰 {money:,}\n"

        embed.add_field(
            name="排行榜 TOP 10",
            value=rank_text,
            inline=False
        )

        # 🔍 找自己的排名
        my_rank = None
        my_money = 0

        for i, (uid, money) in enumerate(all_data):
            if uid == user_id:
                my_rank = i + 1
                my_money = money
                break

        # 👤 顯示自己的排名
        if my_rank:
            embed.add_field(
                name="📍 你的排名",
                value=f"第 {my_rank} 名 ｜ 💰 {my_money:,}",
                inline=False
            )
        else:
            embed.add_field(
                name="📍 你的排名",
                value="未上榜",
                inline=False
            )

        embed.set_footer(text="努力成為第一名吧 👑")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        print("錯誤：", e)
        await interaction.followup.send("❌ 發生錯誤，請聯絡管理員")
@bot.tree.command(name="設定歡迎頻道", description="設定歡迎訊息發送頻道")
@app_commands.checks.has_permissions(administrator=True)
async def set_welcome_channel(interaction: discord.Interaction, channel: discord.TextChannel):

    c.execute("REPLACE INTO settings (key, value) VALUES ('welcome_channel', ?)", (str(channel.id),))
    conn.commit()

    await interaction.response.send_message(f"✅ 已設定歡迎頻道：{channel.mention}")

@bot.tree.command(name="設定歡迎訊息", description="設定歡迎文字")
@app_commands.checks.has_permissions(administrator=True)
async def set_welcome_message(interaction: discord.Interaction, message: str):

    c.execute("REPLACE INTO settings (key, value) VALUES ('welcome_message', ?)", (message,))
    conn.commit()

    await interaction.response.send_message("✅ 已更新歡迎訊息")

@bot.event
async def on_member_join(member):

    print(f"有人加入：{member}")  

    c.execute("SELECT value FROM settings WHERE key='welcome_channel'")
    channel_data = c.fetchone()

    if not channel_data:
        return

    channel = bot.get_channel(int(channel_data[0]))
    if not channel:
        return

    c.execute("SELECT value FROM settings WHERE key='welcome_message'")
    msg_data = c.fetchone()

    if msg_data:
        message = msg_data[0]
    else:
        message = "歡迎 {user} 來到極曜月葵"

    count = member.guild.member_count

    message = message.replace("{user}", member.mention)
    message = message.replace("{count}", str(count))

    # 🌙 極曜月葵風格卡片
    embed = discord.Embed(
        title="🌙 𝑬𝒄𝒍𝒊𝒑𝒔𝒆 𝑳𝒖𝒏𝒂 𝑮𝒂𝒓𝒅𝒆𝒏",
        description=f"{message}",
        color=discord.Color.from_rgb(186, 85, 211)  # 紫粉色
    )

    # 👤 使用者
    embed.set_author(
        name=f"{member.display_name} ✦ 新月之契",
        icon_url=member.display_avatar.url
    )

    # 📊 資訊
    embed.add_field(
        name="🌙 成員",
        value=member.mention,
        inline=True
    )

    embed.add_field(
        name="✨ 星位編號",
        value=f"第 {count} 位",
        inline=True
    )

    embed.add_field(
        name="🕯 降臨時刻",
        value=f"<t:{int(member.joined_at.timestamp())}:F>",
        inline=False
    )

    # 🌌 圖片
    embed.set_thumbnail(url=member.display_avatar.url)

    embed.set_image(
        url="https://media.discordapp.net/attachments/1504831006090465320/1515773543286313229/IMG_1765.jpg"
    )

    # 🌙 Footer
    embed.set_footer(
        text="極曜月葵 ✦ 請完成入群審核"
    )

    await channel.send(embed=embed)


from discord.ext import tasks
import os

@tasks.loop(minutes=1)
async def birthday_check():

    global last_birthday_check

    now = datetime.now(tz)

    # ❗避免同一天重複
    today_str = now.strftime("%Y-%m-%d")

    if last_birthday_check == today_str:
        return

    if now.hour != 8 or now.minute != 0:
        return

    last_birthday_check = today_str

import threading
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
import os

def run_web():
    port = int(os.environ.get("PORT", 10000))
    with TCPServer(("", port), SimpleHTTPRequestHandler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_web).start()

bot.run(os.getenv("TOKEN"))
