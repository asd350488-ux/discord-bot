import os

import discord
from discord.ext import commands

# ===== 設定 =====
from config import *

# ===== Database =====
from database import conn, c

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

@bot.event
async def on_ready():
    print("=" * 50)
    print(f"✅ {bot.user} 已登入")
    print("🌙 Moon Bot v2 啟動成功")
    print("=" * 50)

    try:
        synced = await bot.tree.sync()
        print(f"✅ 已同步 {len(synced)} 個 Slash Commands")
    except Exception as e:
        print(f"❌ 指令同步失敗：{e}")

from systems.checkin import setup as setup_checkin
from systems.work import setup as setup_work
from casino.guess import setup as setup_guess
from casino.duel import setup as setup_duel

setup_work(bot)
setup_guess(bot)
setup_duel(bot)
setup_checkin(bot)


TOKEN = os.getenv("TOKEN")

bot.run(TOKEN)