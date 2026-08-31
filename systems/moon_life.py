# -*- coding: utf-8 -*-
"""
🌙 Moon Life｜V1 獨立系統
放置位置：systems/moon_life.py

載入方式（main.py）：
await bot.load_extension("systems.moon_life")
"""

import random
import sqlite3
from datetime import datetime, timezone, timedelta

import discord
from discord import app_commands
from discord.ext import commands

TW_TZ = timezone(timedelta(hours=8))
DB_PATH = "moon_life.db"

TRAITS = ["活潑", "害羞", "溫柔", "調皮", "好奇", "勇敢", "獨立", "黏人"]
INTERESTS = ["繪畫", "音樂", "運動", "閱讀", "自然", "探索"]


def now_ts():
    return int(datetime.now(TW_TZ).timestamp())


class MoonLife(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect(DB_PATH)
        self.db.row_factory = sqlite3.Row
        self.init_db()

    def init_db(self):
        c = self.db.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS ml_players (
            user_id INTEGER PRIMARY KEY,
            active_child_id INTEGER,
            created_at INTEGER
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS ml_children (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            owner_name TEXT NOT NULL,
            owner_type TEXT NOT NULL,
            name TEXT NOT NULL,
            gender TEXT NOT NULL,
            age_months INTEGER DEFAULT 1,
            growth INTEGER DEFAULT 0,
            energy INTEGER DEFAULT 10,
            last_energy INTEGER,
            hunger INTEGER DEFAULT 100,
            relationship INTEGER DEFAULT 20,
            intelligence INTEGER DEFAULT 0,
            emotion INTEGER DEFAULT 0,
            fitness INTEGER DEFAULT 0,
            creativity INTEGER DEFAULT 0,
            social INTEGER DEFAULT 0,
            trait_scores TEXT DEFAULT '',
            traits TEXT DEFAULT '',
            interest_scores TEXT DEFAULT '',
            interests TEXT DEFAULT '',
            contacts TEXT DEFAULT '',
            memories TEXT DEFAULT '',
            alive_active INTEGER DEFAULT 1,
            adopted_at INTEGER
        )""")
        self.db.commit()

    def active_child(self, user_id):
        r = self.db.execute("""SELECT c.* FROM ml_players p
            JOIN ml_children c ON p.active_child_id=c.id
            WHERE p.user_id=? AND c.alive_active=1""", (user_id,)).fetchone()
        return r

    def recover_energy(self, child):
        elapsed = max(0, (now_ts() - (child["last_energy"] or now_ts())) // 3600)
        if elapsed <= 0 or child["energy"] >= 10:
            return child
        new_energy = min(10, child["energy"] + elapsed)
        self.db.execute("UPDATE ml_children SET energy=?, last_energy=? WHERE id=?",
                        (new_energy, now_ts(), child["id"]))
        self.db.commit()
        return self.db.execute("SELECT * FROM ml_children WHERE id=?", (child["id"],)).fetchone()

    def relation_label(self, n):
        if n < 10: return "🤍 陌生"
        if n < 30: return "🌱 熟悉"
        if n < 55: return "😊 親近"
        if n < 80: return "❤️ 信任"
        return "💕 無可取代"

    def age_text(self, m):
        return f"{m//12}歲{m%12}個月"

    async def adopt_finish(self, interaction, owner_type, owner_name, child_name):
        gender = random.choice(["男孩", "女孩"])
        scores = [random.randint(3, 8) for _ in range(5)]
        trait_scores = {t: random.randint(20, 80) for t in TRAITS}
        interest_scores = {i: 0 for i in INTERESTS}
        c = self.db.cursor()
        old = self.active_child(interaction.user.id)
        if old:
            await interaction.response.send_message("❌ 你目前已有正在成長的孩子，必須等孩子 18 歲成年後才能再次領養。", ephemeral=True)
            return
        c.execute("""INSERT INTO ml_children
        (owner_id,owner_name,owner_type,name,gender,last_energy,intelligence,emotion,fitness,creativity,social,trait_scores,interest_scores,adopted_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (interaction.user.id,owner_name,owner_type,child_name,gender,now_ts(),*scores,
         repr(trait_scores),repr(interest_scores),now_ts()))
        child_id=c.lastrowid
        c.execute("INSERT OR REPLACE INTO ml_players(user_id,active_child_id,created_at) VALUES(?,?,?)",
                  (interaction.user.id,child_id,now_ts()))
        self.db.commit()
        await interaction.response.send_message(
            f"🌙 **領養成功！**\n\n👤 你：{owner_name}（{owner_type}）\n👶 孩子：{child_name}（{gender}）\n🎂 年齡：0歲1個月\n\n從今天開始，好好陪伴 {child_name} 成長吧！🥹",
            ephemeral=True)

    @app_commands.command(name="moonlife", description="進入 Moon Life")
    async def moonlife(self, interaction: discord.Interaction):
        child = self.active_child(interaction.user.id)
        if not child:
            await interaction.response.send_message("🌙 歡迎來到 Moon Life！請使用 `/領養孩子` 開始你的第一段人生。", ephemeral=True)
            return
        child = self.recover_energy(child)
        embed = discord.Embed(title="🌙 Moon Life", description=f"👤 你：{child['owner_name']} {child['owner_type']}\n👶 孩子：{child['name']}（{child['gender']}）")
        embed.add_field(name="🎂 年齡", value=self.age_text(child["age_months"]))
        embed.add_field(name="🌱 成長", value=f"{child['growth']} / 100")
        embed.add_field(name="⚡ 體力", value=f"{child['energy']} / 10")
        embed.add_field(name="❤️ 關係", value=self.relation_label(child["relationship"]))
        await interaction.response.send_message(embed=embed, view=MoonMenu(self, interaction.user.id), ephemeral=True)

    @app_commands.command(name="領養孩子", description="開始領養你的孩子")
    async def adopt(self, interaction: discord.Interaction):
        if self.active_child(interaction.user.id):
            await interaction.response.send_message("❌ 你目前只能同時養育一位未成年孩子。", ephemeral=True)
            return
        await interaction.response.send_modal(AdoptModal(self))

    async def activity(self, interaction, kind):
        child=self.active_child(interaction.user.id)
        if not child: return await interaction.response.send_message("❌ 目前沒有孩子。", ephemeral=True)
        child=self.recover_energy(child)
        if child["energy"]<=0: return await interaction.response.send_message("⚡ 體力不足，休息後再來吧！", ephemeral=True)
        mapping={
            "home":("🏠 在家", random.choice(["今天一起整理了玩具。","一起度過了安靜的家庭時光。"])),
            "outside":("🌳 外出", random.choice(["一起到公園散步。","今天看到了有趣的新事物。"])),
            "play":("🧸 玩耍", random.choice(["孩子玩得非常開心！","你們一起玩了很久。"]))
        }
        title,text=mapping[kind]
        growth=random.randint(8,15)
        hunger=max(0,child["hunger"]-random.randint(4,9))
        relation=min(100,child["relationship"]+random.randint(1,3))
        self.db.execute("UPDATE ml_children SET energy=energy-1,growth=growth+?,hunger=?,relationship=? WHERE id=?",
                        (growth,hunger,relation,child["id"]))
        self.db.commit()
        msg=f"{title}\n{text}\n\n🌱 成長 +{growth}\n⚡ 體力 -1"
        if hunger<35: msg+="\n\n🥺 孩子摸了摸肚子，好像有點餓了。"
        await interaction.response.send_message(msg, ephemeral=True)

    async def show_child(self, interaction):
        c=self.active_child(interaction.user.id)
        if not c: return await interaction.response.send_message("❌ 目前沒有孩子。",ephemeral=True)
        traits=c["traits"] or "❓ 尚未形成"
        interests=c["interests"] or "🌱 尚未發現"
        e=discord.Embed(title=f"👶 {c['name']} 的資料",description=f"🎂 {self.age_text(c['age_months'])}\n❤️ {self.relation_label(c['relationship'])}")
        e.add_field(name="🧠 智慧",value=f"{c['intelligence']} / 100")
        e.add_field(name="❤️ 情感",value=f"{c['emotion']} / 100")
        e.add_field(name="💪 體能",value=f"{c['fitness']} / 100")
        e.add_field(name="🎨 創造",value=f"{c['creativity']} / 100")
        e.add_field(name="✨ 社交",value=f"{c['social']} / 100")
        e.add_field(name="🌟 個性",value=traits,inline=False)
        e.add_field(name="🎯 興趣",value=interests,inline=False)
        await interaction.response.send_message(embed=e,ephemeral=True)


class AdoptModal(discord.ui.Modal, title="🌙 Moon Life｜領養孩子"):
    owner_type=discord.ui.TextInput(label="你想成為什麼？",placeholder="男 / 女 / 貓 / 狗",max_length=2)
    owner_name=discord.ui.TextInput(label="你的名字",max_length=20)
    child_name=discord.ui.TextInput(label="孩子的名字",max_length=20)

    def __init__(self,cog): super().__init__(); self.cog=cog
    async def on_submit(self,interaction):
        t=self.owner_type.value.strip()
        if t not in ["男","女","貓","狗"]:
            return await interaction.response.send_message("❌ 只能選擇：男、女、貓、狗。",ephemeral=True)
        await self.cog.adopt_finish(interaction,t,self.owner_name.value.strip(),self.child_name.value.strip())


class MoonMenu(discord.ui.View):
    def __init__(self,cog,user_id):
        super().__init__(timeout=180)
        self.cog=cog; self.user_id=user_id

    async def check(self,i):
        if i.user.id!=self.user_id:
            await i.response.send_message("這不是你的 Moon Life 面板喔！",ephemeral=True); return False
        return True

    @discord.ui.button(label="🏠 在家",style=discord.ButtonStyle.primary)
    async def home(self,i,b):
        if await self.check(i): await self.cog.activity(i,"home")

    @discord.ui.button(label="🌳 外出",style=discord.ButtonStyle.primary)
    async def outside(self,i,b):
        if await self.check(i): await self.cog.activity(i,"outside")

    @discord.ui.button(label="👶 孩子",style=discord.ButtonStyle.secondary)
    async def child(self,i,b):
        if await self.check(i): await self.cog.show_child(i)

    @discord.ui.button(label="🧸 玩耍",style=discord.ButtonStyle.success)
    async def play(self,i,b):
        if await self.check(i): await self.cog.activity(i,"play")


async def setup(bot):
    await bot.add_cog(MoonLife(bot))
