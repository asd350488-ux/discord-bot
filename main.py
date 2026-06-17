import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import View, Button
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
# 🌙 極曜月葵系統設定
NUNU_EMOJI = "<a:emoji40:1516703946012496025>"

# 🎂 生日
BIRTHDAY_DATA_CHANNEL = 1516119757383008479
BIRTHDAY_ANNOUNCE_CHANNEL = 1504815515795853432

# 🎁 抽獎
LOTTERY_CHANNEL = 1516119932230828134

# 📊 查詢
INFO_CHANNEL = 1516493039571308646

# 🛒 商店 / 錢包
SHOP_CHANNEL = 1516120281507434577

# 💼 打工
WORK_CHANNEL = 1516120501704065094

# 🔐 管理員
ADMIN_CHANNEL = 1510930723924611163

# 🌸 歡迎
WELCOME_CHANNEL = 1504805225351876628

# 📢 活動公告
EVENT_CHANNEL = 1504815515795853432

# 📢 公告頻道
WELCOME_CHANNEL = 1504805225351876628
BIRTHDAY_ANNOUNCE_CHANNEL = 1504815515795853432
LEVEL_UP_CHANNEL = 1516120288373506068

# 🛒 系統頻道
SHOP_CHANNEL = 1516120281507434577
WORK_CHANNEL = 1516120501704065094
INFO_CHANNEL = 1516493039571308646

# 🎰 賭場頻道
BIGSMALL_CHANNEL = 1516421134613086370
DUEL_CHANNEL = 1516421134613086370
SLOT_CHANNEL = 1516422545698455593
BOX_CHANNEL = 1516421398548058163
ADVENTURE_CHANNEL = 1516421649732210759
BLACKMARKET_CHANNEL = 1516421863838978248
MOOD_CHANNEL = 1516422869104595036
LAB_CHANNEL = 1516422777995923487
LIFEBET_CHANNEL = 1516422713109909664

# 💰 努努幣
NUNU_EMOJI = "<:nunu:1516703946012496025>"

# 👑 管理員身分組
ALLOWED_ROLES = [
    1504824446769172602,
    1504833586807967914,
    1504863173168074823,
    1504863370552152124,
    1504864390388776992,
    1505616537296310492
]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 💾 DB
conn = sqlite3.connect("bot.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    money INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    exp INTEGER DEFAULT 0,
    checkin_total INTEGER DEFAULT 0,
    checkin_streak INTEGER DEFAULT 0,
    last_checkin TEXT,
    birthday TEXT,
    birth_year INTEGER,
    last_work TEXT,
    last_adventure TEXT
)
""")

class DuelView(discord.ui.View):

    def __init__(
        self,
        challenger,
        target,
        amount
    ):
        super().__init__(timeout=60)

        self.challenger = challenger
        self.target = target
        self.amount = amount

    @discord.ui.button(
        label="⚔️ 接受對賭",
        style=discord.ButtonStyle.danger
    )
    async def accept(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.user.id != self.target.id:

            await interaction.response.send_message(
                "❌ 這不是你的對賭",
                ephemeral=True
            )
            return

        challenger_id = str(
            self.challenger.id
        )

        target_id = str(
            self.target.id
        )

        # 餘額檢查
        c.execute(
            "SELECT money FROM users WHERE user_id=?",
            (challenger_id,)
        )

        challenger_money = c.fetchone()

        c.execute(
            "SELECT money FROM users WHERE user_id=?",
            (target_id,)
        )

        target_money = c.fetchone()

        if (
            not challenger_money
            or not target_money
        ):
            await interaction.response.send_message(
                "❌ 帳戶不存在"
            )
            return

        challenger_money = challenger_money[0]
        target_money = target_money[0]

        if challenger_money < self.amount:

            await interaction.response.send_message(
                "❌ 挑戰者餘額不足"
            )
            return

        if target_money < self.amount:

            await interaction.response.send_message(
                "❌ 你的餘額不足"
            )
            return

        # 🎲 勝負
        winner = random.choice(
            [
                self.challenger,
                self.target
            ]
        )

        loser = (
            self.target
            if winner == self.challenger
            else self.challenger
        )

        winner_id = str(winner.id)
        loser_id = str(loser.id)

        # 💰 雙方下注
        pot = self.amount * 2

        roll = random.randint(1, 100)

        if roll <= 5:

            title = "⭐ 神運"
            reward = int(pot * 2.5)

        elif roll <= 25:

            title = "✨ 大勝"
            reward = int(pot * 1.5)

        else:

            title = "🎉 小勝"
            reward = pot

        # 💸 雙方先扣下注
        c.execute(
            """
            UPDATE users
            SET money = money - ?
            WHERE user_id=?
            """,
            (
                self.amount,
                challenger_id
            )
        )

        c.execute(
            """
            UPDATE users
            SET money = money - ?
            WHERE user_id=?
            """,
            (
                self.amount,
                target_id
            )
        )

        # 🎁 勝者獲得獎池
        c.execute(
            """
            UPDATE users
            SET money = money + ?
            WHERE user_id=?
            """,
            (
                reward,
                winner_id
            )
        )

        conn.commit()

        embed = discord.Embed(
            title="⚔️ 星月對賭結果",
            color=discord.Color.red()
        )

        embed.add_field(
            name="🏆 勝者",
            value=winner.mention,
            inline=False
        )

        embed.add_field(
            name="✨ 結果",
            value=title,
            inline=False
        )

        embed.add_field(
            name="🏦 獎池",
            value=f"{NUNU_EMOJI} `{pot:,}`",
            inline=False
        )

        embed.add_field(
            name="🎁 最終獎勵",
            value=f"{NUNU_EMOJI} `{reward:,}`",
            inline=False
        )

        embed.add_field(
            name="💀 敗者",
            value=loser.mention,
            inline=False
        )

        await interaction.response.edit_message(
            embed=embed,
            view=None
        )

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

c.execute("""
CREATE TABLE IF NOT EXISTS daily_event (
    date TEXT PRIMARY KEY,
    game TEXT,
    multiplier INTEGER
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
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

# 📜 發錢紀錄表
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

    # 類型顯示
    type_map = {
        "single": "👤 單人",
        "role": "👥 身分組",
        "all": "🌍 全體"
    }

    for admin_id, target_id, amount, log_type, time in logs:

        admin = interaction.guild.get_member(int(admin_id))
        target = interaction.guild.get_member(int(target_id))

        admin_name = admin.mention if admin else admin_id
        target_name = target.mention if target else target_id

        # 🕒 美化時間
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

    # 🔒 頻道限制
    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="🛒 星月商會",
            description=(
                "✨ 商會區域限定\n\n"
                f"請前往 <#{SHOP_CHANNEL}> 使用此指令"
            ),
            color=discord.Color.gold()
        )

        embed.add_field(
            name="📦 商會功能",
            value="商店｜購買｜背包｜錢包",
            inline=False
        )

        embed.set_footer(
            text="極曜月葵 ✦ 星月商會"
        )
        await interaction.response.send_message(
        embed=embed,
        ephemeral=True
         )
        return

    c.execute(
        "SELECT money, checkin_total, checkin_streak FROM users WHERE user_id=?",
        (user_id,)
    )

    data = c.fetchone()

    if data:
        money, total, streak = data
    else:
        money, total, streak = 0, 0, 0

    embed = discord.Embed(
        title="🌙 𝑳𝒖𝒏𝒂 𝑾𝒂𝒍𝒍𝒆𝒕",
        description="✨ 星月銀行帳戶資訊",
        color=discord.Color.from_rgb(186, 85, 211)
    )

    embed.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.display_avatar.url
    )

    embed.add_field(
        name=f"{NUNU_EMOJI} 努努幣",
        value=f"```{money:,}```",
        inline=False
    )

    embed.add_field(
        name="📅 累積簽到",
        value=f"```{total:,} 天```",
        inline=True
    )

    embed.add_field(
        name="🔥 連續簽到",
        value=f"```{streak:,} 天```",
        inline=True
    )

    embed.set_thumbnail(
        url=interaction.user.display_avatar.url
    )

    embed.set_footer(
        text="極曜月葵 ✦ 星月同行"
    )

    await interaction.response.send_message(
        embed=embed
    )
    return
    
# 🏆 排行榜
@bot.tree.command(name="排行榜")
async def leaderboard(interaction: discord.Interaction):

    # 🔒 頻道限制
    if interaction.channel.id != INFO_CHANNEL:

        embed = discord.Embed(
            title="🌙 星月指令限制",
            description=(
                "📊 排行查詢僅能於指定區域使用\n\n"
                f"請前往 <#{INFO_CHANNEL}>"
            ),
            color=discord.Color.from_rgb(186, 85, 211)
        )

        embed.add_field(
            name="✨ 可使用功能",
            value="等級｜排行榜｜查詢",
            inline=False
        )

        embed.set_footer(
            text="極曜月葵 ✦ 星月同行"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )
        return

    c.execute("""
        SELECT user_id, money
        FROM users
        ORDER BY money DESC
        LIMIT 10
    """)

    ranking = c.fetchall()

    embed = discord.Embed(
        title="🏆 𝑳𝒖𝒏𝒂 𝑻𝒉𝒓𝒐𝒏𝒆",
        description="✨ 努努幣富豪排行榜 ✨",
        color=discord.Color.gold()
    )

    medals = {
        1: "👑",
        2: "🥈",
        3: "🥉"
    }

    for index, (user_id, money) in enumerate(ranking, start=1):

        member = interaction.guild.get_member(int(user_id))

        if member:
            name = member.display_name
        else:
            name = f"未知使用者 ({user_id})"

        icon = medals.get(index, f"#{index}")

        embed.add_field(
            name=f"{icon} {name}",
            value=f"{NUNU_EMOJI} `{money:,}`",
            inline=False
        )

    embed.set_footer(
        text="極曜月葵 ✦ 星月同行"
    )

    await interaction.response.send_message(
        embed=embed
    )
    return

# 🌟 等級排行榜
@bot.tree.command(name="等級排行榜")
async def level_leaderboard(interaction: discord.Interaction):

    # 🔒 頻道限制
    if interaction.channel.id != INFO_CHANNEL:

        embed = discord.Embed(
            title="🌙 星月指令限制",
            description=(
                "📊 排行查詢僅能於指定區域使用\n\n"
                f"請前往 <#{INFO_CHANNEL}>"
            ),
            color=discord.Color.from_rgb(186, 85, 211)
        )

        embed.add_field(
            name="✨ 可使用功能",
            value="等級｜排行榜｜查詢",
            inline=False
        )

        embed.set_footer(
            text="極曜月葵 ✦ 星月同行"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )
        return

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

    await interaction.response.send_message(
            embed=embed
           )

# 📈 等級
@bot.tree.command(name="等級")
async def level(interaction: discord.Interaction):

    # 🔒 頻道限制
    if interaction.channel.id != INFO_CHANNEL:

        embed = discord.Embed(
            title="🌙 星月指令限制",
            description=(
                "📊 等級查詢僅能於指定區域使用\n\n"
                f"請前往 <#{INFO_CHANNEL}>"
            ),
            color=discord.Color.from_rgb(186, 85, 211)
        )

        embed.add_field(
            name="✨ 可使用功能",
            value="等級｜排行榜｜查詢",
            inline=False
        )

        embed.set_footer(
            text="極曜月葵 ✦ 星月同行"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )
        return

    user_id = str(interaction.user.id)

    c.execute("""
        SELECT level, exp
        FROM users
        WHERE user_id=?
    """, (user_id,))

    result = c.fetchone()

    if not result:
        level = 1
        exp = 0
    else:
        level, exp = result

    next_exp = level * 100

    c.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE level > ?
           OR (level = ? AND exp > ?)
    """, (level, level, exp))

    rank = c.fetchone()[0] + 1

    percent = min(int((exp / next_exp) * 100), 100)

    bar_length = 10
    filled = int(percent / 10)

    progress_bar = (
        "🟪" * filled +
        "⬜" * (bar_length - filled)
    )

    embed = discord.Embed(
        title="🌙 𝑳𝒖𝒏𝒂 𝑷𝒓𝒐𝒇𝒊𝒍𝒆",
        description="✨ 星月旅人的成長紀錄",
        color=discord.Color.from_rgb(138, 43, 226)
    )

    embed.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.display_avatar.url
    )

    embed.set_thumbnail(
        url=interaction.user.display_avatar.url
    )

    embed.add_field(
        name="📈 等級",
        value=f"```Lv.{level}```",
        inline=True
    )

    embed.add_field(
        name="🏆 排名",
        value=f"```#{rank}```",
        inline=True
    )

    embed.add_field(
        name="✨ 經驗值",
        value=(
            f"{progress_bar}\n"
            f"`{exp:,} / {next_exp:,}`\n"
            f"完成度：{percent}%"
        ),
        inline=False
    )

    embed.set_footer(
        text="極曜月葵 ✦ 星月同行"
    )

    await interaction.response.send_message(
        embed=embed
    )
    return

# 🎮 聊天經驗系統
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    user_id = str(message.author.id)

    c.execute(
        """
        INSERT OR IGNORE INTO users
        (user_id,money,exp,level)
        VALUES (?,0,0,1)
        """,
        (user_id,)
    )

    c.execute(
        "SELECT exp, level FROM users WHERE user_id=?",
        (user_id,)
    )

    data = c.fetchone()

    if not data:
        await bot.process_commands(message)
        return

    exp, level = data

    gain = random.randint(5, 10)
    exp += gain

    need_exp = level * 100
    level_up = False

    while exp >= need_exp:

        exp -= need_exp
        level += 1

        need_exp = level * 100
        level_up = True

    c.execute(
        """
        UPDATE users
        SET exp=?, level=?
        WHERE user_id=?
        """,
        (
            exp,
            level,
            user_id
        )
    )

    conn.commit()

    if level_up:

        channel = bot.get_channel(
    1516120288373506068
)

        embed = discord.Embed(
            title="🌙 等級提升",
            description=(
                f"{message.author.mention}\n\n"
                f"✨ 已提升至 Lv.{level}"
            ),
            color=discord.Color.from_rgb(
                186,
                85,
                211
            )
        )

        embed.set_thumbnail(
            url=message.author.display_avatar.url
        )

        embed.set_footer(
            text="極曜月葵 ✦ 星月同行"
        )

        if channel:
            await channel.send(embed=embed)

    await bot.process_commands(message)

# ⚙️ 管理員設定等級
@bot.tree.command(name="設定等級")
@app_commands.checks.has_permissions(administrator=True)
async def set_level(interaction: discord.Interaction, member: discord.Member, level: int):

    c.execute("UPDATE users SET level=?, exp=0 WHERE user_id=?", (level, str(member.id)))
    conn.commit()

    await interaction.response.send_message(f"✅ 已將 {member.mention} 設為 Lv.{level}")

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

# 💼 打工
@bot.tree.command(name="打工")
async def work(interaction: discord.Interaction):

    # 🔒 頻道限制
    if interaction.channel.id != WORK_CHANNEL:

        embed = discord.Embed(
            title="💼 星月委託中心",
            description=f"請前往 <#{WORK_CHANNEL}> 接取委託任務",
            color=discord.Color.green()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )
        return

    user_id = str(interaction.user.id)

    # 👤 建立資料
    c.execute(
        """
        INSERT OR IGNORE INTO users
        (user_id,money,exp,level)
        VALUES (?,0,0,1)
        """,
        (user_id,)
    )
    conn.commit()

    # ⏳ 冷卻
    c.execute(
        "SELECT last_work,money FROM users WHERE user_id=?",
        (user_id,)
    )

    data = c.fetchone()

    last_work = data[0]
    money = data[1]

    if last_work:

        last_time = datetime.fromisoformat(last_work)

        remain = timedelta(hours=1) - (
            datetime.now(tz) - last_time
        )

        if remain.total_seconds() > 0:

            minutes = int(remain.total_seconds() // 60)
            seconds = int(remain.total_seconds() % 60)

            embed = discord.Embed(
                title="⏳ 星月委託冷卻中",
                description=f"剩餘時間：{minutes}分 {seconds}秒",
                color=discord.Color.orange()
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )
            return

    # 📜 工作列表
    jobs = [
        ("整理月神圖書館",120,250),
        ("護送星月商隊",180,320),
        ("照顧月光花園",100,220),
        ("清理古代遺跡",200,380),
        ("協助魔法研究",220,450),
        ("採集月光礦石",150,300),
        ("巡邏星空城區",180,350)
    ]

    job_name, low, high = random.choice(jobs)

    # 🎲 事件
    roll = random.randint(1,100)

    if roll <= 5:

        reward = random.randint(low,high) * 3

        title = "🌟 月神眷顧"
        desc = "獲得三倍報酬"
        event_type = "success"

    elif roll <= 75:

        reward = random.randint(low,high)

        title = "✨ 委託成功"
        desc = "順利完成任務"
        event_type = "success"

    elif roll <= 90:

        reward = int(random.randint(low,high) * 0.5)

        title = "⚠️ 工作失誤"
        desc = "只獲得部分報酬"
        event_type = "success"

    elif roll <= 97:

        reward = random.randint(100,500)

        title = "💸 工作意外"
        desc = "損壞設備需要賠償"
        event_type = "loss"

    else:

        reward = random.randint(500,1500)

        title = "☠️ 災難事件"
        desc = "任務失敗造成重大損失"
        event_type = "loss"

    # 💰 結算
    if event_type == "success":
        money += reward
    else:
        money = max(0, money - reward)

    # 💾 更新
    c.execute(
        """
        UPDATE users
        SET money=?,
            last_work=?
        WHERE user_id=?
        """,
        (
            money,
            datetime.now(tz).isoformat(),
            user_id
        )
    )

    conn.commit()

    # 🌙 Embed
    embed = discord.Embed(
        title="🌙 𝑴𝒐𝒐𝒏 𝑾𝒐𝒓𝒌",
        description=desc,
        color=discord.Color.from_rgb(186,85,211)
    )

    embed.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.display_avatar.url
    )

    embed.add_field(
        name="📜 委託內容",
        value=f"```{job_name}```",
        inline=False
    )

    embed.add_field(
        name="✨ 事件結果",
        value=f"```{title}```",
        inline=False
    )

    if event_type == "success":

        embed.add_field(
            name="🎁 本次收入",
            value=f"{NUNU_EMOJI} `{reward:,}`",
            inline=True
        )

    else:

        embed.add_field(
            name="💸 本次損失",
            value=f"{NUNU_EMOJI} `{reward:,}`",
            inline=True
        )

    embed.add_field(
        name="💰 錢包餘額",
        value=f"{NUNU_EMOJI} `{money:,}`",
        inline=True
    )

    embed.set_footer(
        text="極曜月葵 ✦ 星月同行"
    )

    await interaction.response.send_message(
        embed=embed
    )


# 🛒 商店
@bot.tree.command(name="商店")
async def shop(interaction: discord.Interaction):

    # 🔒 頻道限制
    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="🛒 星月商會",
            description=(
                "✨ 商會區域限定\n\n"
                f"請前往 <#{SHOP_CHANNEL}>"
            ),
            color=discord.Color.gold()
        )

        embed.add_field(
            name="📦 商會功能",
            value="商店｜購買｜背包｜錢包",
            inline=False
        )

        embed.set_footer(
            text="極曜月葵 ✦ 星月商會"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )
        return

    c.execute(
        "SELECT item_id, name, price, stock, description, image FROM shop"
    )

    items = c.fetchall()

    if not items:
        await interaction.response.send_message(
            "🛒 商店目前沒有商品"
        )
        return

    view = ShopView(items)

    embed = discord.Embed(
        title="🛒 星月商會",
        description="✨ 點擊按鈕瀏覽商品",
        color=discord.Color.gold()
    )

    await interaction.response.send_message(
        embed=embed,
        view=view
    )

# 🎲 猜大小
@bot.tree.command(name="猜大小")
@app_commands.describe(
    choice="大 或 小",
    amount="下注金額"
)
async def guess_big_small(
    interaction: discord.Interaction,
    choice: str,
    amount: int
):

    if interaction.channel.id != BIGSMALL_CHANNEL:

        embed = discord.Embed(
            title="🎲 星月賭場",
            description=f"請前往 <#{BIGSMALL_CHANNEL}> 使用猜大小",
            color=discord.Color.red()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )
        return

    choice = choice.strip()

    if choice not in ["大", "小"]:

        await interaction.response.send_message(
            "❌ 請輸入：大 或 小",
            ephemeral=True
        )
        return

    if amount <= 0:

        await interaction.response.send_message(
            "❌ 下注金額必須大於 0",
            ephemeral=True
        )
        return

    user_id = str(interaction.user.id)

    c.execute(
        "SELECT money FROM users WHERE user_id=?",
        (user_id,)
    )

    data = c.fetchone()

    if not data:

        await interaction.response.send_message(
            "❌ 找不到帳戶資料",
            ephemeral=True
        )
        return

    money = data[0]

    if money < amount:

        await interaction.response.send_message(
            "❌ 努努幣不足",
            ephemeral=True
        )
        return

    # 🎲 骰子
    dice = random.randint(1, 6)

    result = "大" if dice >= 4 else "小"

    win = (choice == result)

    # ⭐ 結果池
    roll = random.randint(1, 100)

    event_name = ""
    change = 0

    if win:

        if roll <= 5:

            event_name = "⭐ 神運"
            change = int(amount * 5)

        elif roll <= 25:

            event_name = "✨ 大勝"
            change = int(amount * 2)

        else:

            event_name = "🎉 小勝"
            change = int(amount * 1.5)

    else:

        if roll <= 70:

            event_name = "💀 失敗"
            change = -amount

        else:

            event_name = "☠️ 爆死"
            change = -(amount * 2)

    money += change

    if money < 0:
        money = 0

    c.execute(
        """
        UPDATE users
        SET money=?
        WHERE user_id=?
        """,
        (
            money,
            user_id
        )
    )

    conn.commit()

    embed = discord.Embed(
        title="🎲 星月賭場・猜大小",
        color=discord.Color.from_rgb(
            186,
            85,
            211
        )
    )

    embed.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.display_avatar.url
    )

    embed.add_field(
        name="🎯 你的選擇",
        value=f"```{choice}```",
        inline=True
    )

    embed.add_field(
        name="🎲 骰子結果",
        value=f"```{dice}```",
        inline=True
    )

    embed.add_field(
        name="✨ 判定",
        value=f"```{event_name}```",
        inline=False
    )

    if change >= 0:

        embed.add_field(
            name="🎉 本次獲得",
            value=f"{NUNU_EMOJI} `{change:,}`",
            inline=False
        )

    else:

        embed.add_field(
            name="💸 本次損失",
            value=f"{NUNU_EMOJI} `{abs(change):,}`",
            inline=False
        )

    embed.add_field(
        name="💰 錢包餘額",
        value=f"{NUNU_EMOJI} `{money:,}`",
        inline=False
    )

    embed.set_footer(
        text="極曜月葵 ✦ 星月賭場"
    )

    await interaction.response.send_message(
        embed=embed
    )

# ⚔️ 對賭
@bot.tree.command(name="對賭")
async def duel(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: int
):

    if interaction.channel.id != DUEL_CHANNEL:

        await interaction.response.send_message(
            f"❌ 請前往 <#{DUEL_CHANNEL}>",
            ephemeral=True
        )
        return

    if member.bot:

        await interaction.response.send_message(
            "❌ 不能挑戰機器人"
        )
        return

    if member.id == interaction.user.id:

        await interaction.response.send_message(
            "❌ 不能挑戰自己"
        )
        return

    if amount <= 0:

        await interaction.response.send_message(
            "❌ 下注金額必須大於 0",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="⚔️ 星月對賭",
        color=discord.Color.red()
    )

    embed.add_field(
        name="挑戰者",
        value=interaction.user.mention,
        inline=False
    )

    embed.add_field(
        name="被挑戰者",
        value=member.mention,
        inline=False
    )

    embed.add_field(
        name="賭注",
        value=f"{NUNU_EMOJI} `{amount:,}`",
        inline=False
    )

    embed.set_footer(
        text="60秒內接受挑戰"
    )

    await interaction.response.send_message(
        embed=embed,
        view=DuelView(
            interaction.user,
            member,
            amount
        )
    )

    embed = discord.Embed(
        title="⚔️ 星月對賭",
        color=discord.Color.red()
    )

    embed.add_field(
        name="挑戰者",
        value=interaction.user.mention,
        inline=False
    )

    embed.add_field(
        name="被挑戰者",
        value=member.mention,
        inline=False
    )

    embed.add_field(
        name="賭注",
        value=f"{NUNU_EMOJI} `{amount:,}`",
        inline=False
    )

    embed.set_footer(
        text="60秒內接受挑戰"
    )

# 🎰 老虎機
@bot.tree.command(name="老虎機")
async def slot_machine(
    interaction: discord.Interaction,
    amount: int
):

    if interaction.channel.id != SLOT_CHANNEL:

        embed = discord.Embed(
            title="🎰 星月賭場",
            description=f"請前往 <#{SLOT_CHANNEL}> 使用老虎機",
            color=discord.Color.red()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )
        return

    if amount <= 0:

        await interaction.response.send_message(
            "❌ 下注金額必須大於 0",
            ephemeral=True
        )
        return

    user_id = str(interaction.user.id)

    c.execute(
        "SELECT money FROM users WHERE user_id=?",
        (user_id,)
    )

    data = c.fetchone()

    if not data:

        await interaction.response.send_message(
            "❌ 找不到帳戶資料",
            ephemeral=True
        )
        return

    money = data[0]

    if money < amount:

        await interaction.response.send_message(
            "❌ 努努幣不足",
            ephemeral=True
        )
        return

    symbols = [
        "🍒",
        "🌙",
        "⭐",
        "💎"
    ]

    slot = [
        random.choice(symbols),
        random.choice(symbols),
        random.choice(symbols)
    ]

    result_text = " ".join(slot)

    reward = 0
    title = ""

    # ☠️ 爆機事件
    if random.randint(1, 100) <= 10:

        title = "☠️ 爆機"
        reward = -(amount * 2)

        slot = [
            "💀",
            "💀",
            "💀"
        ]

        result_text = " ".join(slot)

    elif slot == ["💎", "💎", "💎"]:

        title = "⭐ 神運 JACKPOT"
        reward = amount * 10

    elif slot[0] == slot[1] == slot[2]:

        title = "✨ 大勝"
        reward = amount * 5

    elif (
        slot[0] == slot[1]
        or slot[0] == slot[2]
        or slot[1] == slot[2]
    ):

        title = "🎉 小勝"
        reward = amount * 2

    else:

        title = "💀 失敗"
        reward = -amount

    money += reward

    if money < 0:
        money = 0

    c.execute(
        """
        UPDATE users
        SET money=?
        WHERE user_id=?
        """,
        (
            money,
            user_id
        )
    )

    conn.commit()

    embed = discord.Embed(
        title="🎰 星月老虎機",
        color=discord.Color.gold()
    )

    embed.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.display_avatar.url
    )

    embed.add_field(
        name="🎰 結果",
        value=f"```{result_text}```",
        inline=False
    )

    embed.add_field(
        name="✨ 判定",
        value=f"```{title}```",
        inline=False
    )

    if reward >= 0:

        embed.add_field(
            name="🎉 本次獲得",
            value=f"{NUNU_EMOJI} `{reward:,}`",
            inline=False
        )

    else:

        embed.add_field(
            name="💸 本次損失",
            value=f"{NUNU_EMOJI} `{abs(reward):,}`",
            inline=False
        )

    embed.add_field(
        name="💰 錢包餘額",
        value=f"{NUNU_EMOJI} `{money:,}`",
        inline=False
    )

    embed.set_footer(
        text="極曜月葵 ✦ 星月賭場"
    )

    await interaction.response.send_message(
        embed=embed
    )

# 🎁 驚喜箱
@bot.tree.command(name="驚喜箱")
async def surprise_box(
    interaction: discord.Interaction,
    amount: int
):

    if interaction.channel.id != BOX_CHANNEL:

        embed = discord.Embed(
            title="🎁 星月驚喜箱",
            description=f"請前往 <#{BOX_CHANNEL}> 使用驚喜箱",
            color=discord.Color.orange()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )
        return

    if amount <= 0:

        await interaction.response.send_message(
            "❌ 金額必須大於 0",
            ephemeral=True
        )
        return

    user_id = str(interaction.user.id)

    c.execute(
        "SELECT money FROM users WHERE user_id=?",
        (user_id,)
    )

    data = c.fetchone()

    if not data:

        await interaction.response.send_message(
            "❌ 找不到帳戶資料",
            ephemeral=True
        )
        return

    money = data[0]

    if money < amount:

        await interaction.response.send_message(
            "❌ 努努幣不足",
            ephemeral=True
        )
        return

    roll = random.randint(1, 100)

    if roll == 1:

        title = "🌌 星神祝福"
        reward = amount * 20

    elif roll <= 5:

        title = "👑 月神寶藏"
        reward = amount * 10

    elif roll <= 20:

        title = "💎 星光寶箱"
        reward = amount * 5

    elif roll <= 60:

        title = "🎉 意外之喜"
        reward = amount * 2

    elif roll <= 85:

        title = "📦 普通補給"
        reward = amount

    else:

        title = "💀 空箱子"
        reward = 0

    # 扣本金再發獎勵
    money = money - amount + reward

    if money < 0:
        money = 0

    c.execute(
        """
        UPDATE users
        SET money=?
        WHERE user_id=?
        """,
        (
            money,
            user_id
        )
    )

    conn.commit()

    net = reward - amount

    embed = discord.Embed(
        title="🎁 星月驚喜箱",
        color=discord.Color.orange()
    )

    embed.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.display_avatar.url
    )

    embed.add_field(
        name="🎊 開箱結果",
        value=f"```{title}```",
        inline=False
    )

    if net >= 0:

        embed.add_field(
            name="🎉 淨收益",
            value=f"{NUNU_EMOJI} `+{net:,}`",
            inline=False
        )

    else:

        embed.add_field(
            name="💸 淨損失",
            value=f"{NUNU_EMOJI} `-{abs(net):,}`",
            inline=False
        )

    embed.add_field(
        name="💰 錢包餘額",
        value=f"{NUNU_EMOJI} `{money:,}`",
        inline=False
    )

    embed.set_footer(
        text="極曜月葵 ✦ 星月驚喜箱"
    )

    await interaction.response.send_message(
        embed=embed
    )

# 🧭 探險
@bot.tree.command(name="探險")
async def adventure(
    interaction: discord.Interaction
):

    if interaction.channel.id != ADVENTURE_CHANNEL:

        embed = discord.Embed(
            title="🧭 星月探險",
            description=f"請前往 <#{ADVENTURE_CHANNEL}> 使用探險",
            color=discord.Color.blurple()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )
        return

    user_id = str(interaction.user.id)

    c.execute(
        """
        SELECT money,last_adventure
        FROM users
        WHERE user_id=?
        """,
        (user_id,)
    )

    data = c.fetchone()

    if not data:

        await interaction.response.send_message(
            "❌ 找不到帳戶資料",
            ephemeral=True
        )
        return

    money, last_adventure = data

    now = datetime.now()

    if last_adventure:

        last_time = datetime.fromisoformat(
            last_adventure
        )

        remain = 1800 - int(
            (now - last_time).total_seconds()
        )

        if remain > 0:

            minutes = remain // 60
            seconds = remain % 60

            await interaction.response.send_message(
                f"⏳ 探險冷卻中\n還需 {minutes}分 {seconds}秒",
                ephemeral=True
            )
            return

    roll = random.randint(1,100)

    title = ""
    reward = 0

    # 🌌 神級
    if roll <= 5:

        title = random.choice(
            [
                "🌌 星神降臨",
                "🌌 月神祝福",
                "🌌 時空裂縫"
            ]
        )

        reward = random.randint(
            5000,
            20000
        )

    # 👑 Boss
    elif roll <= 15:

        title = random.choice(
            [
                "👑 深淵魔狼",
                "👑 星辰巨龍",
                "👑 月影騎士"
            ]
        )

        reward = random.randint(
            1000,
            8000
        )

    # ⚔️ 危險
    elif roll <= 35:

        title = random.choice(
            [
                "⚔️ 流浪盜賊",
                "⚔️ 深林陷阱",
                "⚔️ 魔物襲擊"
            ]
        )

        reward = -random.randint(
            100,
            1000
        )

    # 🌿 普通
    else:

        title = random.choice(
            [
                "🌿 補給箱",
                "🌿 旅行商人",
                "🌿 遺失財寶"
            ]
        )

        reward = random.randint(
            100,
            1000
        )

    money += reward

    if money < 0:
        money = 0

    c.execute(
        """
        UPDATE users
        SET money=?,
            last_adventure=?
        WHERE user_id=?
        """,
        (
            money,
            now.isoformat(),
            user_id
        )
    )

    conn.commit()

    embed = discord.Embed(
        title="🧭 星月探險",
        color=discord.Color.blurple()
    )

    embed.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.display_avatar.url
    )

    embed.add_field(
        name="📖 探險結果",
        value=f"```{title}```",
        inline=False
    )

    if reward >= 0:

        embed.add_field(
            name="🎉 獲得",
            value=f"{NUNU_EMOJI} `{reward:,}`",
            inline=False
        )

    else:

        embed.add_field(
            name="💸 損失",
            value=f"{NUNU_EMOJI} `{abs(reward):,}`",
            inline=False
        )

    embed.add_field(
        name="💰 錢包餘額",
        value=f"{NUNU_EMOJI} `{money:,}`",
        inline=False
    )

    embed.set_footer(
        text="極曜月葵 ✦ 星月探險"
    )

    await interaction.response.send_message(
        embed=embed
    )

# 💳 購買
@bot.tree.command(name="購買")
async def buy(interaction: discord.Interaction, item_id: int):

    # 🔒 頻道限制
    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="🛒 星月商會",
            description=f"請前往 <#{SHOP_CHANNEL}> 使用購買功能",
            color=discord.Color.gold()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )
        return

    name, price, stock = item

    if stock <= 0:
        await interaction.response.send_message(
            "❌ 商品已售完",
            ephemeral=True
        )
        return

    # 💰 查餘額
    c.execute(
        "SELECT money FROM users WHERE user_id=?",
        (user_id,)
    )

    data = c.fetchone()

    if not data:
        await interaction.response.send_message(
            "❌ 請先簽到或打工建立資料",
            ephemeral=True
        )
        return

    money = data[0]

    if money < price:
        await interaction.response.send_message(
            "❌ 努努幣不足",
            ephemeral=True
        )
        return

    # 💰 扣款
    c.execute(
        "UPDATE users SET money = money - ? WHERE user_id=?",
        (price, user_id)
    )

    # 📦 扣庫存
    c.execute(
        "UPDATE shop SET stock = stock - 1 WHERE item_id=?",
        (item_id,)
    )

    # 🎒 加入背包
    c.execute(
        "SELECT amount FROM inventory WHERE user_id=? AND item_id=?",
        (user_id, item_id)
    )

    inv = c.fetchone()

    if inv:

        c.execute(
            """
            UPDATE inventory
            SET amount = amount + 1
            WHERE user_id=? AND item_id=?
            """,
            (user_id, item_id)
        )

    else:

        c.execute(
            """
            INSERT INTO inventory
            (user_id,item_id,amount)
            VALUES (?,?,1)
            """,
            (user_id, item_id)
        )

    conn.commit()

    embed = discord.Embed(
        title="🛍️ 購買成功",
        color=discord.Color.green()
    )

    embed.add_field(
        name="📦 商品",
        value=f"```{name}```",
        inline=False
    )

    embed.add_field(
        name="💰 花費",
        value=f"{NUNU_EMOJI} `{price:,}`",
        inline=False
    )

    embed.set_footer(
        text="極曜月葵 ✦ 星月商會"
    )

    await interaction.response.send_message(
        embed=embed
    )

# 🎒 背包
@bot.tree.command(name="背包")
async def inventory_cmd(interaction: discord.Interaction):

    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="🛒 星月商會",
            description=f"請前往 <#{SHOP_CHANNEL}> 使用背包功能",
            color=discord.Color.gold()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )
        return

    user_id = str(interaction.user.id)

    c.execute("""
        SELECT shop.name, inventory.amount
        FROM inventory
        JOIN shop ON inventory.item_id = shop.item_id
        WHERE inventory.user_id=?
    """, (user_id,))

    items = c.fetchall()

    if not items:
        await interaction.response.send_message(
            "🎒 你的背包是空的"
        )
        return

    text = ""

    for name, amount in items:
        text += f"🎁 {name} × {amount}\n"

    embed = discord.Embed(
        title="🎒 星月背包",
        description=text,
        color=discord.Color.purple()
    )

    embed.set_footer(
        text="極曜月葵 ✦ 星月商會"
    )

    await interaction.response.send_message(
        embed=embed
    )

# 🎁 贈送道具
@bot.tree.command(name="贈送道具")
async def give_item(
    interaction: discord.Interaction,
    member: discord.Member,
    item_name: str,
    amount: int
):

    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="🛒 星月商會",
            description=f"請前往 <#{SHOP_CHANNEL}> 使用贈送功能",
            color=discord.Color.gold()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )
        return

    sender_id = str(interaction.user.id)
    target_id = str(member.id)

    c.execute(
        "SELECT item_id FROM shop WHERE name=?",
        (item_name,)
    )

    item = c.fetchone()

    if not item:

        await interaction.response.send_message(
            "❌ 沒有這個商品",
            ephemeral=True
        )
        return

    item_id = item[0]

    c.execute(
        """
        SELECT amount
        FROM inventory
        WHERE user_id=? AND item_id=?
        """,
        (sender_id, item_id)
    )

    data = c.fetchone()

    if not data or data[0] < amount:

        await interaction.response.send_message(
            "❌ 道具不足",
            ephemeral=True
        )
        return

    # 扣除自己
    c.execute(
        """
        UPDATE inventory
        SET amount = amount - ?
        WHERE user_id=? AND item_id=?
        """,
        (amount, sender_id, item_id)
    )

    # 對方背包
    c.execute(
        """
        SELECT amount
        FROM inventory
        WHERE user_id=? AND item_id=?
        """,
        (target_id, item_id)
    )

    target_data = c.fetchone()

    if target_data:

        c.execute(
            """
            UPDATE inventory
            SET amount = amount + ?
            WHERE user_id=? AND item_id=?
            """,
            (amount, target_id, item_id)
        )

    else:

        c.execute(
            """
            INSERT INTO inventory
            (user_id,item_id,amount)
            VALUES (?,?,?)
            """,
            (target_id, item_id, amount)
        )

    conn.commit()

    embed = discord.Embed(
        title="🎁 贈送成功",
        color=discord.Color.green()
    )

    embed.add_field(
        name="📦 道具",
        value=f"```{item_name}```",
        inline=False
    )

    embed.add_field(
        name="👤 收件人",
        value=member.mention,
        inline=False
    )

    embed.add_field(
        name="📦 數量",
        value=f"`{amount}`",
        inline=False
    )

    embed.set_footer(
        text="極曜月葵 ✦ 星月商會"
    )

    await interaction.response.send_message(
        embed=embed
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
