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
import random
import asyncio

tz = pytz.timezone("Asia/Taipei")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 💾 DB
conn = sqlite3.connect("bot.db", check_same_thread=False)
c = conn.cursor()

# 👤 使用者資料表
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    money INTEGER DEFAULT 0,
    checkin_total INTEGER DEFAULT 0,
    checkin_streak INTEGER DEFAULT 0,
    last_checkin TEXT,
    birthday TEXT,
    birth_year INTEGER,
    show_age INTEGER DEFAULT 0,
    exp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS shop (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    price INTEGER,
    stock INTEGER,
    description TEXT,
    image TEXT
)
""")
conn.commit()

class ShopView(discord.ui.View):
    def __init__(self, items, page=0):
        super().__init__(timeout=60)
        self.items = items
        self.page = page
        self.per_page = 3

    def get_page_items(self):
        start = self.page * self.per_page
        end = start + self.per_page
        return self.items[start:end]

    async def update(self, interaction):

        self.clear_items()

        embed = discord.Embed(
            title="🛒 商店",
            color=discord.Color.gold()
        )

        page_items = self.get_page_items()

        for item_id, name, price, stock, desc, img in page_items:

            embed.add_field(
                name=f"🆔 {item_id}｜{name}",
                value=f"{desc}\n<a:emoji40:1510362334026268713> {price}｜庫存:{stock}",
                inline=False
            )

            self.add_item(BuyButton(item_id, price, name))

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="⬅ 上一頁", style=discord.ButtonStyle.gray)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        await self.update(interaction)

    @discord.ui.button(label="➡ 下一頁", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if (self.page + 1) * self.per_page < len(self.items):
            self.page += 1
        await self.update(interaction)

c.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    user_id TEXT,
    item_id INTEGER,
    amount INTEGER
)
""")
conn.commit()

class BuyButton(discord.ui.Button):
    def __init__(self, item_id, price, name):
        super().__init__(
            label=f"購買 {name}",
            style=discord.ButtonStyle.green
        )
        self.item_id = item_id
        self.price = price
        self.name = name

    async def callback(self, interaction: discord.Interaction):

        user_id = str(interaction.user.id)

        # 💰 查錢
        c.execute("SELECT money FROM users WHERE user_id=?", (user_id,))
        data = c.fetchone()

        if not data or data[0] < self.price:
            await interaction.response.send_message("❌ 努努幣不足", ephemeral=True)
            return

        # 📦 查庫存
        c.execute("SELECT stock FROM shop WHERE item_id=?", (self.item_id,))
        stock = c.fetchone()

        if not stock or stock[0] <= 0:
            await interaction.response.send_message("❌ 商品已售完", ephemeral=True)
            return

        # 💰 扣錢
        c.execute("UPDATE users SET money = money - ? WHERE user_id=?", (self.price, user_id))

        # 📦 扣庫存
        c.execute("UPDATE shop SET stock = stock - 1 WHERE item_id=?", (self.item_id,))

        # 🎒 加入背包
        c.execute("SELECT amount FROM inventory WHERE user_id=? AND item_id=?", (user_id, self.item_id))
        inv = c.fetchone()

        if inv:
            c.execute("UPDATE inventory SET amount = amount + 1 WHERE user_id=? AND item_id=?", (user_id, self.item_id))
        else:
            c.execute("INSERT INTO inventory (user_id, item_id, amount) VALUES (?, ?, 1)", (user_id, self.item_id))

        conn.commit()

        await interaction.response.send_message(
            f"🛍️ 購買成功！**{self.name}**\n<a:emoji40:1510362334026268713> -{self.price}"
        )

class DuelConfirm(discord.ui.View):
    def __init__(self, challenger, opponent, amount):
        super().__init__(timeout=30)
        self.challenger = challenger
        self.opponent = opponent
        self.amount = amount

    # ✅ 同意
    @discord.ui.button(label="✅ 同意", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user != self.opponent:
            await interaction.response.send_message("❌ 這不是你的對賭", ephemeral=True)
            return

        user1 = str(self.challenger.id)
        user2 = str(self.opponent.id)

        # 💰 再檢查一次
        c.execute("SELECT money FROM users WHERE user_id=?", (user1,))
        m1 = c.fetchone()

        c.execute("SELECT money FROM users WHERE user_id=?", (user2,))
        m2 = c.fetchone()

        if m1[0] < self.amount or m2[0] < self.amount:
            await interaction.response.send_message("❌ 有人錢不夠", ephemeral=True)
            return

        # 🎲 決勝
        roll1 = random.randint(1, 100)
        roll2 = random.randint(1, 100)

        if roll1 > roll2:
            winner = user1
            loser = user2
            winner_name = self.challenger.mention
        else:
            winner = user2
            loser = user1
            winner_name = self.opponent.mention

        # 💰 結算
        c.execute("UPDATE users SET money = money + ? WHERE user_id=?", (self.amount, winner))
        c.execute("UPDATE users SET money = money - ? WHERE user_id=?", (self.amount, loser))
        conn.commit()

        embed = discord.Embed(title="⚔️ 對賭結果", color=discord.Color.red())
        embed.add_field(name="🎲 挑戰者", value=f"```{roll1}```")
        embed.add_field(name="🎲 對手", value=f"```{roll2}```")
        embed.add_field(name="🏆 勝者", value=winner_name)
        embed.add_field(
            name="<a:emoji40:1510362334026268713> 金額",
            value=f"```{self.amount}```"
        )

        await interaction.response.edit_message(embed=embed, view=None)

    # ❌ 拒絕
    @discord.ui.button(label="❌ 拒絕", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user != self.opponent:
            await interaction.response.send_message("❌ 這不是你的對賭", ephemeral=True)
            return

        embed = discord.Embed(
            title="❌ 對賭被拒絕",
            description=f"{self.opponent.mention} 拒絕了對賭",
            color=discord.Color.greyple()
        )

        await interaction.response.edit_message(embed=embed, view=None)

    # ⏳ 超時
    async def on_timeout(self):

        # ⚠️ 注意：這裡不能用 interaction
        # 直接修改原訊息
        for item in self.children:
            item.disabled = True

        try:
            await self.message.edit(
                content="⏳ 對賭已超時（30秒無回應）",
                view=self
            )
        except:
            pass
class MoneyConfirm(discord.ui.View):
    def __init__(self, interaction, 金額, 成員, 身分組, 全體):
        super().__init__(timeout=30)
        self.interaction = interaction
        self.amount = 金額
        self.member = 成員
        self.role = 身分組
        self.all = 全體

    @discord.ui.button(label="✅ 確認發送", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user != self.interaction.user:
            await interaction.response.send_message("❌ 這不是你的操作", ephemeral=True)
            return

        count = 0

        # 💰 單人
        if self.member:
            user_id = str(self.member.id)

            c.execute("INSERT INTO users (user_id, money) VALUES (?, 0) ON CONFLICT(user_id) DO NOTHING", (user_id,))
            c.execute("UPDATE users SET money = money + ? WHERE user_id=?", (self.amount, user_id))

            # 📜 紀錄
            c.execute("""
            INSERT INTO money_log (admin_id, target_id, amount, type, time)
            VALUES (?, ?, ?, ?, ?)
            """, (interaction.user.id, user_id, self.amount, "single", datetime.now().isoformat()))

            count = 1

        # 💰 身分組
        elif self.role:
            for member in self.role.members:
                if member.bot:
                    continue

                user_id = str(member.id)

                c.execute("INSERT INTO users (user_id, money) VALUES (?, 0) ON CONFLICT(user_id) DO NOTHING", (user_id,))
                c.execute("UPDATE users SET money = money + ? WHERE user_id=?", (self.amount, user_id))

                c.execute("""
                INSERT INTO money_log (admin_id, target_id, amount, type, time)
                VALUES (?, ?, ?, ?, ?)
                """, (interaction.user.id, user_id, self.amount, "role", datetime.now().isoformat()))

                count += 1

        # 💰 全體
        elif self.all:
            for member in interaction.guild.members:
                if member.bot:
                    continue

                user_id = str(member.id)

                c.execute("INSERT INTO users (user_id, money) VALUES (?, 0) ON CONFLICT(user_id) DO NOTHING", (user_id,))
                c.execute("UPDATE users SET money = money + ? WHERE user_id=?", (self.amount, user_id))

                c.execute("""
                INSERT INTO money_log (admin_id, target_id, amount, type, time)
                VALUES (?, ?, ?, ?, ?)
                """, (interaction.user.id, user_id, self.amount, "all", datetime.now().isoformat()))

                count += 1

        conn.commit()

        embed = discord.Embed(
            title="💰 發錢完成",
            description=f"已發送 {self.amount} 努努幣\n共 {count} 人",
            color=discord.Color.green()
        )

        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="❌ 取消", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user != self.interaction.user:
            await interaction.response.send_message("❌ 這不是你的操作", ephemeral=True)
            return

        await interaction.response.edit_message(
            content="❌ 已取消發送",
            embed=None,
            view=None
        )

try:
    c.execute("ALTER TABLE users ADD COLUMN last_work TEXT")
    conn.commit()
except:
    pass

# 📜 發錢紀錄表
c.execute("""
CREATE TABLE IF NOT EXISTS money_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id TEXT,
    target_id TEXT,
    amount INTEGER,
    type TEXT,
    time TEXT
)
""")
conn.commit()
@bot.tree.command(name="發錢紀錄")
async def money_log_view(interaction: discord.Interaction):

    # 🔒 限制頻道
    if interaction.channel.id != 1510930723924611163:
        await interaction.response.send_message(
            "❌ 請到管理員頻道使用",
            ephemeral=True
        )
        return

    # 🔒 管理員權限
    ALLOWED_ROLES = [1504824446769172602,1504833586807967914,1504863173168074823,1504863370552152124,1504864390388776992,1505616537296310492]

    if not any(role.id in ALLOWED_ROLES for role in interaction.user.roles):
        await interaction.response.send_message(
            "❌ 你沒有權限",
            ephemeral=True
        )
        return

    # 📜 查最近10筆
    c.execute("""
    SELECT admin_id, target_id, amount, type, time
    FROM money_log
    ORDER BY id DESC
    LIMIT 10
    """)
    logs = c.fetchall()

    if not logs:
        await interaction.response.send_message("📭 沒有任何發錢紀錄")
        return

embed = discord.Embed(
    title="📜 發錢紀錄（最近10筆）",
    color=discord.Color.blue()
)

type_map = {
    "single": "👤 單人",
    "role": "👥 身分組",
    "all": "🌍 全體"
}

for i, (admin_id, target_id, amount, log_type, time) in enumerate(logs):
    if i >= 10:
        break

    admin = interaction.guild.get_member(int(admin_id))
    target = interaction.guild.get_member(int(target_id))

    admin_name = admin.mention if admin else admin_id
    target_name = target.mention if target else target_id

    dt = datetime.fromisoformat(time)
    time_str = dt.strftime("%Y-%m-%d %H:%M")

    embed.add_field(
        name=f"💰 {amount} 努努幣",
        value=f"👤 發送者：{admin_name}\n🎯 對象：{target_name}\n📌 類型：{type_map.get(log_type, log_type)}\n🕒 時間：{time_str}",
        inline=False
    )

await interaction.response.send_message(embed=embed)

# 🚀 啟動
@bot.event
async def on_ready():
    print(f"已登入：{bot.user}")
    await bot.tree.sync()
    if not birthday_check.is_running():
        birthday_check.start()

# 🐰 簽到
@bot.tree.command(name="簽到")
async def checkin(interaction: discord.Interaction):

    # 🔒 限制頻道
    if interaction.channel.id != 1516120502127694027:
        await interaction.response.send_message(
            "❌ 請到指定簽到頻道使用此指令",
            ephemeral=True
        )
        return

    await interaction.response.defer()

    user_id = str(interaction.user.id)
    now = datetime.now(tz)
    today = now.date()

    c.execute("SELECT last_checkin, checkin_total, checkin_streak, money FROM users WHERE user_id=?", (user_id,))
    data = c.fetchone()

    # ❗ 已簽到
    if data and data[0] == str(today):

        tomorrow = datetime.combine(today + timedelta(days=1), datetime.min.time())
        tomorrow = tz.localize(tomorrow)

        remaining = tomorrow - now
        total_seconds = int(remaining.total_seconds())

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        embed = discord.Embed(
            title="⏳ 今日已簽到",
            description="你今天已經領過獎勵了",
            color=discord.Color.from_rgb(255, 105, 180)
        )

        embed.add_field(
            name="⏰ 下次簽到",
            value=f"```{hours} 小時 {minutes} 分鐘```",
            inline=False
        )

        embed.set_footer(text="極曜月葵 ✦ 時間流轉中")

        await interaction.followup.send(embed=embed)
        return

    # 🎰 獎勵
    reward = 500 if random.random() < 0.2 else 100
    crit = reward == 500

    if data:
        total = data[1] + 1
        streak = data[2] + 1 if data[0] == str(today - timedelta(days=1)) else 1
        money = data[3] + reward

        c.execute("UPDATE users SET last_checkin=?, checkin_total=?, checkin_streak=?, money=? WHERE user_id=?",
                  (str(today), total, streak, money, user_id))
    else:
        total, streak, money = 1, 1, reward
        c.execute("INSERT INTO users (user_id, money, checkin_total, checkin_streak, last_checkin) VALUES (?, ?, ?, ?, ?)",
                  (user_id, money, total, streak, str(today)))

    conn.commit()

    # 🌙 UI
    embed = discord.Embed(
        title="🌙 𝑴𝒐𝒐𝒏 𝑪𝒉𝒆𝒄𝒌𝒊𝒏",
        description="✨ 你再次踏入了星月之境",
        color=discord.Color.from_rgb(186, 85, 211)
    )

    embed.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.display_avatar.url
    )

    reward_text = f"✨ 暴擊！+{reward}" if crit else f"+{reward}"

    embed.add_field(
        name="<a:emoji40:1510362334026268713> 努努幣",
        value=f"```{money}```\n{reward_text}"
    )

    embed.add_field(name="🔥 連續簽到", value=f"```{streak} 天```")
    embed.add_field(name="📅 總簽到", value=f"```{total} 天```")

    await interaction.followup.send(embed=embed)

# 💰 錢包
@bot.tree.command(name="錢包")
async def wallet(interaction: discord.Interaction):

    user_id = str(interaction.user.id)
    c.execute("SELECT money, checkin_total, checkin_streak FROM users WHERE user_id=?", (user_id,))
    data = c.fetchone()

    money, total, streak = data if data else (0, 0, 0)

    embed = discord.Embed(title="💰 𝑳𝒖𝒏𝒂 𝑾𝒆𝒂𝒍𝒕𝒉", color=discord.Color.gold())

    embed.add_field(name="<a:emoji40:1510362334026268713> 努努幣", value=f"```{money}```")
    embed.add_field(name="📅 總簽到", value=f"```{total} 天```")
    embed.add_field(name="🔥 連續", value=f"```{streak} 天```")

    await interaction.response.send_message(embed=embed)

# 🏆 排行榜
@bot.tree.command(name="排行榜")
async def leaderboard(interaction: discord.Interaction):

    await interaction.response.defer()

    c.execute("SELECT user_id, money FROM users ORDER BY money DESC")
    data = c.fetchall()

    text = ""
    for i, (uid, money) in enumerate(data[:10]):
        user = bot.get_user(int(uid)) or await bot.fetch_user(int(uid))

        if i == 0:
            text += f"👑 {user.display_name} ✦ <a:emoji40:1510362334026268713> {money} ✨\n"
        elif i == 1:
            text += f"🌟 {user.display_name} ✦ <a:emoji40:1510362334026268713> {money}\n"
        elif i == 2:
            text += f"💫 {user.display_name} ✦ <a:emoji40:1510362334026268713> {money}\n"
        else:
            text += f"{i+1}. ✦ {user.display_name} ｜ <a:emoji40:1510362334026268713> {money}\n"

    embed = discord.Embed(title="🏆 𝑳𝒖𝒏𝒂 𝑻𝒉𝒓𝒐𝒏𝒆", description=text)
    await interaction.followup.send(embed=embed)

# 🏆 等級排行榜
@bot.tree.command(name="等級排行榜")
async def level_leaderboard(interaction: discord.Interaction):

    await interaction.response.defer()

    c.execute("SELECT user_id, level, exp FROM users ORDER BY level DESC, exp DESC")
    data = c.fetchall()

    text = ""

    for i, (uid, level, exp) in enumerate(data[:10]):
        user = bot.get_user(int(uid)) or await bot.fetch_user(int(uid))

        if i == 0:
            text += f"👑 {user.display_name} ｜ Lv.{level} ✨\n"
        elif i == 1:
            text += f"🌟 {user.display_name} ｜ Lv.{level}\n"
        elif i == 2:
            text += f"💫 {user.display_name} ｜ Lv.{level}\n"
        else:
            text += f"{i+1}. {user.display_name} ｜ Lv.{level}\n"

    embed = discord.Embed(
        title="🏆 等級排行榜",
        description=text,
        color=discord.Color.from_rgb(186, 85, 211)
    )

    await interaction.followup.send(embed=embed)

# 🎮 等級系統（聊天獲得經驗）
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    allowed_channels = [1504815515795853432]

    if message.channel.id not in allowed_channels:
        await bot.process_commands(message)
        return

    user_id = str(message.author.id)

    # 📊 取得資料
    c.execute("SELECT exp, level FROM users WHERE user_id=?", (user_id,))
    data = c.fetchone()

    # 🆕 新用戶
    if not data:
        c.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        await bot.process_commands(message)
        return

    exp, level = data

    # 🎲 經驗
    gain = random.randint(5, 10)
    exp += gain

    need = level * 100

    if exp >= need:
        exp -= need
        level += 1

        embed = discord.Embed(
            title="🌙 等級提升",
            description=f"✨ {message.author.mention} 已達到 Lv.{level}",
            color=discord.Color.from_rgb(186, 85, 211)
        )

        level_channel = bot.get_channel(1516120288373506068)

        if level_channel:
            await level_channel.send(embed=embed)
        else:
            await message.channel.send(embed=embed)

    # 💾 更新資料（一定要在 if 外）
    c.execute("UPDATE users SET exp=?, level=? WHERE user_id=?", (exp, level, user_id))
    conn.commit()

    await bot.process_commands(message)

# ⚙️ 管理員設定等級
@bot.tree.command(name="設定等級")
@app_commands.checks.has_permissions(administrator=True)
async def set_level(interaction: discord.Interaction, member: discord.Member, level: int):

    c.execute("UPDATE users SET level=?, exp=0 WHERE user_id=?", (level, str(member.id)))
    conn.commit()

    await interaction.response.send_message(f"✅ 已將 {member.mention} 設為 Lv.{level}")

# 📊 等級查詢
@bot.tree.command(name="等級")
async def level(interaction: discord.Interaction, member: discord.Member = None):

    member = member or interaction.user
    user_id = str(member.id)

    c.execute("SELECT exp, level FROM users WHERE user_id=?", (user_id,))
    data = c.fetchone()

    if not data:
        await interaction.response.send_message("❌ 尚未有資料")
        return

    exp, level = data
    need = level * 100

    # 🧠 排名（✅ 正確位置）
    c.execute("SELECT user_id, level, exp FROM users ORDER BY level DESC, exp DESC")
    all_users = c.fetchall()
    rank = next((i+1 for i, u in enumerate(all_users) if u[0] == user_id), "未知")

    embed = discord.Embed(
        title="🌙 等級資訊",
        color=discord.Color.from_rgb(186, 85, 211)
    )

    embed.set_author(
        name=member.display_name,
        icon_url=member.display_avatar.url
    )

    embed.add_field(name="📈 等級", value=f"```Lv.{level}```")
    embed.add_field(name="✨ 經驗", value=f"```{exp} / {need}```")
    embed.add_field(name="🏅 排名", value=f"```#{rank}```")

    await interaction.response.send_message(embed=embed)

# ⚙️ 頻道設定
@bot.tree.command(name="設定生日頻道")
async def set_birthday_channel(interaction: discord.Interaction, channel: discord.TextChannel):

    c.execute("REPLACE INTO settings VALUES ('birthday_channel', ?)", (str(channel.id),))
    conn.commit()

    await interaction.response.send_message(f"✅ 生日通知頻道已設定為 {channel.mention}")

@bot.tree.command(name="設定歡迎頻道")
async def set_welcome_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    c.execute("REPLACE INTO settings VALUES ('welcome_channel', ?)", (str(channel.id),))
    conn.commit()
    await interaction.response.send_message(f"✅ 已設定：{channel.mention}")

@bot.tree.command(name="設定管理員頻道")
async def set_admin_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    c.execute("REPLACE INTO settings VALUES ('admin_channel', ?)", (str(channel.id),))
    conn.commit()
    await interaction.response.send_message(f"✅ 已設定：{channel.mention}")
@bot.tree.command(name="設定升級頻道")
async def set_level_channel(interaction: discord.Interaction, channel: discord.TextChannel):

    c.execute("REPLACE INTO settings VALUES ('level_channel', ?)", (str(channel.id),))
    conn.commit()

    await interaction.response.send_message(f"✅ 升級通知頻道已設定為 {channel.mention}")

# 🎂 生日系統（最終穩定版）
@tasks.loop(minutes=1)
async def birthday_check():

    now = datetime.now(tz)
    today_str = now.strftime("%Y-%m-%d")

    c.execute("SELECT value FROM settings WHERE key='last_birthday'")
    data = c.fetchone()
    if data and data[0] == today_str:
        return

    if now.hour != 8 or now.minute != 0:
        return

    c.execute("REPLACE INTO settings VALUES ('last_birthday', ?)", (today_str,))
    conn.commit()

    today = now.strftime("%m-%d")

    c.execute("SELECT user_id FROM users WHERE birthday=?", (today,))
    users = c.fetchall()

    if not users:
        return

    # 🎂 生日頻道（直接綁定）
    channel = bot.get_channel(1516119757383008479)

    # 🔐 管理員頻道
    c.execute("SELECT value FROM settings WHERE key='admin_channel'")
    admin_data = c.fetchone()
    admin_channel = bot.get_channel(int(admin_data[0])) if admin_data else None

    for (uid,) in users:
        user = bot.get_user(int(uid)) or await bot.fetch_user(int(uid))

        # 🎰 抽卡
        roll = random.random()
        if roll < 0.70:
            reward = 1000
            reward_text = "✨ 星月祝福"
        elif roll < 0.95:
            reward = 2000
            reward_text = "🌟 閃耀祝福"
        else:
            reward = 5000
            reward_text = "💎 極光降臨"

        # 💰 發錢
        c.execute("UPDATE users SET money = money + ? WHERE user_id=?", (reward, uid))
        conn.commit()

        # 🔐 管理員
        if admin_channel:
            c.execute("SELECT birth_year FROM users WHERE user_id=?", (uid,))
            year_data = c.fetchone()

            age_text = "未提供"
            if year_data and year_data[0]:
                age = now.year - year_data[0]
                age_text = f"{age}歲（{year_data[0]}）"

            admin_embed = discord.Embed(
                title="🎂 壽星資料",
                color=discord.Color.orange()
            )

            admin_embed.add_field(name="👤 使用者", value=user.display_name)
            admin_embed.add_field(name="🎁 獎勵", value=f"{reward_text} +{reward}")
            admin_embed.add_field(name="🎂 年齡", value=age_text)

            await admin_channel.send(embed=admin_embed)

        # 🎬 動畫（完整三段）
        if channel:
            msg = await channel.send("🌙 星門正在開啟...")
            await asyncio.sleep(1.2)

            await msg.edit(content="✨ 正在編織誕生日祝福...")
            await asyncio.sleep(1.2)

            await msg.edit(content="🎂 星月祝福降臨")
            await asyncio.sleep(1.2)

            embed = discord.Embed(
                title="🌙 𝑩𝒊𝒓𝒕𝒉𝒅𝒂𝒚 𝑩𝒍𝒆𝒔𝒔𝒊𝒏𝒈",
                description=f"✨ 今天是 {user.mention} 的誕生日 ✨\n\n願星光與月影都為你停留 🌙\n願這一刻，被世界溫柔記住",
                color=discord.Color.from_rgb(186, 85, 211)
            )

            embed.set_author(
                name=f"{user.display_name} ✦ 星月之子",
                icon_url=user.display_avatar.url
            )

            embed.add_field(
                name="🎁 星月贈禮",
                value=f"{reward_text}\n<a:emoji40:1510362334026268713> +{reward}",
                inline=False
            )

            embed.set_thumbnail(url=user.display_avatar.url)

            if reward == 5000:
                embed.add_field(
                    name="💎 極光降臨",
                    value="✨ 罕見祝福降臨，全服見證 ✨",
                    inline=False
                )

            await asyncio.sleep(0.8)
            await msg.edit(content=None, embed=embed)

        # 💖 私訊完整版
        try:
            dm_embed = discord.Embed(
                title="🌙 𝑷𝒓𝒊𝒗𝒂𝒕𝒆 𝑩𝒊𝒓𝒕𝒉𝒅𝒂𝒚",
                description=(
                    "今天，是只屬於你的日子 ✨\n\n"
                    "沒有喧囂、沒有規則\n"
                    "只有這一刻，世界為你停了一瞬\n\n"
                    "願你被溫柔記住\n"
                    "願你走過的每一步，都有人在看著 🌙"
                ),
                color=discord.Color.from_rgb(186, 85, 211)
            )

            dm_embed.add_field(
                name="🎁 專屬贈禮",
                value=f"{reward_text}\n<a:emoji40:1510362334026268713> +{reward}",
                inline=False
            )

            await user.send(embed=dm_embed)

        except:
            pass

    # 🔔 明天提醒
    tomorrow = (now + timedelta(days=1)).strftime("%m-%d")

    c.execute("SELECT user_id FROM users WHERE birthday=?", (tomorrow,))
    tomorrow_users = c.fetchall()

    if tomorrow_users and admin_channel:
        text = ""
        for (uid,) in tomorrow_users:
            user = bot.get_user(int(uid)) or await bot.fetch_user(int(uid))
            text += f"{user.display_name}\n"

        await admin_channel.send(f"⚠️ 明天壽星：\n{text}")

# 🌸 歡迎系統（動畫版）
@bot.event
async def on_member_join(member):

    # 📡 取得頻道
    c.execute("SELECT value FROM settings WHERE key='welcome_channel'")
    data = c.fetchone()

    if not data:
        return

    channel = bot.get_channel(int(data[0]))
    if not channel:
        return

    count = member.guild.member_count

    # 🎬 動畫開始
    msg = await channel.send("🌙 星門正在開啟...")
    await asyncio.sleep(1.2)

    await msg.edit(content="✨ 正在確認身分...")
    await asyncio.sleep(1.2)

    await msg.edit(content="🌸 新成員已抵達")
    await asyncio.sleep(1.2)

    # 📝 抓歡迎訊息
    c.execute("SELECT value FROM settings WHERE key='welcome_message'")
    msg_data = c.fetchone()

    text = msg_data[0] if msg_data else f"歡迎 {member.mention} 加入伺服器 ✨"

    # 💜 最終卡片
    embed = discord.Embed(
        title="🌙 𝑵𝒆𝒘 𝑨𝒓𝒓𝒊𝒗𝒂𝒍",
        description=f"{text}\n你是第 **{count}** 位成員",
        color=discord.Color.from_rgb(186, 85, 211)
    )

    embed.set_author(
        name=member.display_name,
        icon_url=member.display_avatar.url
    )

    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text="極曜月葵 ✦ 歡迎儀式")

    await asyncio.sleep(0.8)
    await msg.edit(content=None, embed=embed)

@bot.tree.command(name="生日登記", description="設定你的生日")
async def set_birthday(interaction: discord.Interaction, month: int, day: int, year: int = None):

    user_id = str(interaction.user.id)

    # 格式：MM-DD
    birthday = f"{month:02d}-{day:02d}"

    c.execute("""
    UPDATE users 
    SET birthday=?, birth_year=? 
    WHERE user_id=?
    """, (birthday, year, user_id))

    conn.commit()

    await interaction.response.send_message(
        f"🎂 已設定生日為 {birthday}" + (f"（{year}）" if year else ""),
        ephemeral=True
    )

@bot.tree.command(name="生日查詢", description="查看你的生日")
async def check_birthday(interaction: discord.Interaction):

    user_id = str(interaction.user.id)

    c.execute("SELECT birthday, birth_year FROM users WHERE user_id=?", (user_id,))
    data = c.fetchone()

    if not data or not data[0]:
        await interaction.response.send_message("❌ 你還沒有設定生日", ephemeral=True)
        return

    birthday, year = data

    text = f"🎂 你的生日：{birthday}"
    if year:
        text += f"\n📅 出生年：{year}"

    await interaction.response.send_message(text, ephemeral=True)

@bot.tree.command(name="本月壽星", description="查看本月壽星")
async def birthday_list(interaction: discord.Interaction):

    now = datetime.now(tz)
    month = now.strftime("%m")

    c.execute("SELECT user_id, birthday FROM users WHERE birthday LIKE ?", (f"{month}-%",))
    users = c.fetchall()

    if not users:
        await interaction.response.send_message("📭 本月沒有壽星", ephemeral=True)
        return

    text = ""

    for uid, bday in users:
        user = await bot.fetch_user(int(uid))
        text += f"{user.display_name} ｜ {bday}\n"

    embed = discord.Embed(
        title="🎂 本月壽星",
        description=text,
        color=discord.Color.pink()
    )

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="生日刪除", description="刪除你的生日資料")
async def delete_birthday(interaction: discord.Interaction):

    user_id = str(interaction.user.id)

    c.execute("UPDATE users SET birthday=NULL, birth_year=NULL WHERE user_id=?", (user_id,))
    conn.commit()

    await interaction.response.send_message("🗑️ 生日資料已刪除", ephemeral=True)

# 遊樂場比大小

@bot.tree.command(name="猜大小")
async def gamble(interaction: discord.Interaction, 金額: int, 選擇: str):

    # 🔒 限制頻道
    if interaction.channel.id != 1516120600928714752:
        await interaction.response.send_message(
            "❌ 請到指定賭博頻道使用",
            ephemeral=True
        )
        return

    user_id = str(interaction.user.id)

    if 選擇 not in ["大", "小"]:
        await interaction.response.send_message("❌ 請選擇 大 或 小")
        return

    if 金額 <= 0:
        await interaction.response.send_message("❌ 金額必須大於0")
        return

    # 💰 查錢
    c.execute("SELECT money FROM users WHERE user_id=?", (user_id,))
    data = c.fetchone()

    if not data:
        await interaction.response.send_message("❌ 你還沒有帳號資料")
        return

    money = data[0]

    if 金額 > money:
        await interaction.response.send_message("❌ 努努幣不足")
        return

    # 🎲 骰子
    dice = random.randint(1, 12)
    result = "大" if dice >= 7 else "小"

    win = (選擇 == result)

    # 🎰 倍率
    multiplier = 1
    event_text = "普通勝利"

    roll = random.random()

    if roll < 0.05:
        multiplier = 3
        event_text = "💎 超級暴擊 x3"
    elif roll < 0.20:
        multiplier = 2
        event_text = "🔥 暴擊 x2"
    elif roll < 0.50:
        multiplier = 1.5
        event_text = "✨ 小幸運 x1.5"

    if win:
        reward = int(金額 * multiplier)
        money += reward
        result_text = f"{event_text}\n🎉 贏得 {reward} <a:emoji40:1510362334026268713>"
    else:
        money -= 金額
        result_text = f"💔 輸了 {金額} <a:emoji40:1510362334026268713>"

    # 💾 更新
    c.execute("UPDATE users SET money=? WHERE user_id=?", (money, user_id))
    conn.commit()

    embed = discord.Embed(title="🎲 猜大小", color=discord.Color.purple())
    embed.add_field(name="🎲 點數", value=f"```{dice}```")
    embed.add_field(name="📊 結果", value=f"```{result}```")
    embed.add_field(name="💰 結算", value=f"```{result_text}```")
    embed.add_field(
    name="<a:emoji40:1510362334026268713> 努努幣",
    value=f"```{money}```",
    inline=False
)

    await interaction.response.send_message(embed=embed)

# 比大小玩家對賭

@bot.tree.command(name="對賭")
async def duel(interaction: discord.Interaction, 對手: discord.Member, 金額: int):

    # 🔒 限制頻道
    if interaction.channel.id != 1510908353122009198:
        await interaction.response.send_message(
            "❌ 請到指定賭博頻道使用",
            ephemeral=True
        )
        return

    user1 = str(interaction.user.id)
    user2 = str(對手.id)

    if 對手.bot:
        await interaction.response.send_message("❌ 不能對機器人賭博")
        return

    if user1 == user2:
        await interaction.response.send_message("❌ 不能跟自己賭")
        return

    if 金額 <= 0:
        await interaction.response.send_message("❌ 金額錯誤")
        return

    # 💰 檢查金額
    c.execute("SELECT money FROM users WHERE user_id=?", (user1,))
    m1 = c.fetchone()

    c.execute("SELECT money FROM users WHERE user_id=?", (user2,))
    m2 = c.fetchone()

    if not m1 or not m2:
        await interaction.response.send_message("❌ 有人還沒資料")
        return

    if m1[0] < 金額 or m2[0] < 金額:
        await interaction.response.send_message("❌ 有人錢不夠")
        return

    view = DuelConfirm(interaction.user, 對手, 金額)

    embed = discord.Embed(
        title="⚔️ 對賭邀請",
        description=f"{對手.mention} 是否接受對賭？\n<a:emoji40:1510362334026268713> 金額：{金額}",
        color=discord.Color.orange()
    )

    msg = await interaction.response.send_message(embed=embed, view=view)
    view.message = await interaction.original_response()

# 💼 打工

@bot.tree.command(name="打工", description="賺取遊戲幣")
async def work(interaction: discord.Interaction):

    # 🔒 限制頻道
    if interaction.channel.id != 1516120501704065094:
        await interaction.response.send_message(
            "❌ 請到指定打工頻道使用",
            ephemeral=True
        )
        return
    user_id = str(interaction.user.id)
    now = datetime.now()

    # ⏳ 冷卻檢查（1小時）
    c.execute("SELECT last_work FROM users WHERE user_id=?", (user_id,))
    data = c.fetchone()

    if data and data[0]:
        last_time = datetime.fromisoformat(data[0])
        now_time = datetime.now()

        diff = (now_time - last_time).total_seconds()

        if diff < 3600:
            remaining = int(3600 - diff)
            minutes = remaining // 60
            seconds = remaining % 60

            await interaction.response.send_message(
                f"⏳ 還要 {minutes} 分 {seconds} 秒才能再打工",
                ephemeral=True
            )
            return

    # 🎲 事件
    roll = random.random()

    if roll < 0.6:
        money = random.randint(200, 400)
        text = f"📦 你幫忙搬運貨物\n<a:emoji40:1510362334026268713> +{money}"
    elif roll < 0.85:
        money = random.randint(500, 800)
        text = f"🌟 老闆心情很好\n<a:emoji40:1510362334026268713> +{money}"
    elif roll < 0.95:
        money = -random.randint(100, 300)
        text = f"💥 你打翻東西被扣錢\n<a:emoji40:1510362334026268713> {money}"
    else:
        money = random.randint(1000, 2000)
        text = f"💎 發現隱藏獎勵！\n暴擊 +<a:emoji40:1510362334026268713> +{money}"

    # 💰 更新
    c.execute("SELECT money FROM users WHERE user_id=?", (user_id,))
    data = c.fetchone()

    current = data[0] if data else 0
    new_money = current + money

    c.execute("UPDATE users SET money=? WHERE user_id=?", (new_money, user_id))
    conn.commit()

    embed = discord.Embed(
        title="💼 打工結果",
        description=f"```{text}```",
        color=discord.Color.green()
    )

    embed.add_field(
        name="<a:emoji40:1510362334026268713> 努努幣",
        value=f"```{new_money}```"
    )

    # 🕒 更新打工時間（要在這裡）
    now_time = datetime.now().isoformat()
    c.execute("UPDATE users SET last_work=? WHERE user_id=?", (now_time, user_id))
    conn.commit()

    await interaction.response.send_message(embed=embed)

# 🛒 商店
@bot.tree.command(name="商店")
async def shop(interaction: discord.Interaction):

    # 🔒 限制頻道
    if interaction.channel.id != 1516120281507434577:
        await interaction.response.send_message(
            "❌ 請到指定商店頻道使用",
            ephemeral=True
        )
        return
    c.execute("SELECT item_id, name, price, stock, description, image FROM shop")
    items = c.fetchall()

    if not items:
        await interaction.response.send_message("🛒 商店目前沒有商品")
        return

    view = ShopView(items)

    embed = discord.Embed(
        title="🛒 商店",
        description="點擊按鈕翻頁",
        color=discord.Color.gold()
    )

    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="新增商品")
async def add_item(interaction: discord.Interaction, name: str, price: int, stock: int, description: str, image: str):

    c.execute(
        "INSERT INTO shop (name, price, stock, description, image) VALUES (?, ?, ?, ?, ?)",
        (name, price, stock, description, image)
    )
    conn.commit()

    await interaction.response.send_message(f"✅ 已新增商品：{name}")

# 💳 購買
@bot.tree.command(name="購買")
async def buy(interaction: discord.Interaction, item_id: int):

    user_id = str(interaction.user.id)

    c.execute("SELECT name, price, stock FROM shop WHERE item_id=?", (item_id,))
    item = c.fetchone()

    if not item:
        await interaction.response.send_message("❌ 商品不存在")
        return

    name, price, stock = item

    if stock <= 0:
        await interaction.response.send_message("❌ 商品已售完")
        return

    c.execute("SELECT money FROM users WHERE user_id=?", (user_id,))
    data = c.fetchone()

    if not data:
        await interaction.response.send_message("❌ 你還沒有帳號資料，請先簽到或打工")
        return

    money = data[0]

    if money < price:
        await interaction.response.send_message("❌ 努努幣不足")
        return

    # 💰 扣錢
    c.execute("UPDATE users SET money = money - ? WHERE user_id=?", (price, user_id))

    # 📦 扣庫存
    c.execute("UPDATE shop SET stock = stock - 1 WHERE item_id=?", (item_id,))

    # 🎒 加入背包
    c.execute("SELECT amount FROM inventory WHERE user_id=? AND item_id=?", (user_id, item_id))
    inv = c.fetchone()

    if inv:
        c.execute("UPDATE inventory SET amount = amount + 1 WHERE user_id=? AND item_id=?", (user_id, item_id))
    else:
        c.execute("INSERT INTO inventory (user_id, item_id, amount) VALUES (?, ?, 1)", (user_id, item_id))

    conn.commit()

    await interaction.response.send_message(
        f"🛍️ 成功購買 **{name}**\n<a:emoji40:1510362334026268713> -{price}"
    )

@bot.tree.command(name="背包")
async def inventory_cmd(interaction: discord.Interaction):

    user_id = str(interaction.user.id)

    c.execute("""
    SELECT shop.name, inventory.amount
    FROM inventory
    JOIN shop ON inventory.item_id = shop.item_id
    WHERE inventory.user_id=?
    """, (user_id,))

    items = c.fetchall()

    if not items:
        await interaction.response.send_message("🎒 你的背包是空的")
        return

    text = ""

    for name, amount in items:
        text += f"🎁 {name} × {amount}\n"

    embed = discord.Embed(
        title="🎒 背包",
        description=text,
        color=discord.Color.purple()
    )

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="贈送道具")
async def give_item(interaction: discord.Interaction, member: discord.Member, item_name: str, amount: int):

    sender_id = str(interaction.user.id)
    target_id = str(member.id)

    # 找商品ID
    c.execute("SELECT item_id FROM shop WHERE name=?", (item_name,))
    item = c.fetchone()

    if not item:
        await interaction.response.send_message("❌ 沒有這個商品")
        return

    item_id = item[0]

    # 檢查背包數量
    c.execute("SELECT amount FROM inventory WHERE user_id=? AND item_id=?", (sender_id, item_id))
    data = c.fetchone()

    if not data or data[0] < amount:
        await interaction.response.send_message("❌ 道具不足")
        return

    # 扣除自己
    c.execute("UPDATE inventory SET amount = amount - ? WHERE user_id=? AND item_id=?", (amount, sender_id, item_id))

    # 加給對方
    c.execute("SELECT amount FROM inventory WHERE user_id=? AND item_id=?", (target_id, item_id))
    target_data = c.fetchone()

    if target_data:
        c.execute("UPDATE inventory SET amount = amount + ? WHERE user_id=? AND item_id=?", (amount, target_id, item_id))
    else:
        c.execute("INSERT INTO inventory (user_id, item_id, amount) VALUES (?, ?, ?)", (target_id, item_id, amount))

    conn.commit()

    await interaction.response.send_message(
        f"🎁 成功送出 {item_name} ×{amount} 給 {member.mention}"
    )

# ⚙️ 增加遊戲幣

@bot.tree.command(name="發錢")
async def give_money(
    interaction: discord.Interaction,
    金額: int,
    成員: discord.Member = None,
    身分組: discord.Role = None,
    全體: bool = False
):

    await interaction.response.defer()

    # 🔒 限制頻道
    if interaction.channel.id != 1510930723924611163:
        await interaction.followup.send("❌ 請到管理員頻道使用", ephemeral=True)
        return

    # 🔒 管理員權限
    ALLOWED_ROLES = [1504824446769172602,1504833586807967914,1504863173168074823,1504863370552152124,1504864390388776992,1505616537296310492]

    if not any(role.id in ALLOWED_ROLES for role in interaction.user.roles):
        await interaction.followup.send("❌ 你沒有權限", ephemeral=True)
        return

    if 金額 <= 0:
        await interaction.followup.send("❌ 金額錯誤")
        return

    # ❗ 防止多選
    selected = sum([成員 is not None, 身分組 is not None, 全體])
    if selected > 1:
        await interaction.followup.send("❌ 請只選擇一種發送方式", ephemeral=True)
        return

    # ❗ 沒選
    if not 成員 and not 身分組 and not 全體:
        await interaction.followup.send("❌ 請選擇發送對象", ephemeral=True)
        return

    # ✅ 確認按鈕
    view = MoneyConfirm(interaction, 金額, 成員, 身分組, 全體)

    embed = discord.Embed(
        title="⚠️ 發錢確認",
        description=f"是否確定發送 {金額} 努努幣？",
        color=discord.Color.orange()
    )

    await interaction.followup.send(embed=embed, view=view)

# ⚙️ 設定歡迎訊息
@bot.tree.command(name="設定歡迎訊息")
async def set_welcome_message(interaction: discord.Interaction, message: str):

    c.execute("REPLACE INTO settings VALUES ('welcome_message', ?)", (message,))
    conn.commit()

    await interaction.response.send_message("✅ 歡迎訊息已更新")

# 🌐 保活
def run_web():
    port = int(os.environ.get("PORT", 10000))
    with TCPServer(("", port), SimpleHTTPRequestHandler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_web, daemon=True).start()

bot.run(os.getenv("TOKEN"))
