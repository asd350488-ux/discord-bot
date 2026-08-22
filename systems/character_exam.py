# ==========================
# 🌙 Moon Bot v2｜角色考試系統
# ==========================

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput

import sqlite3
from datetime import datetime, timedelta
import pytz


# ==========================
# 🌙 角色考試系統
# ==========================

def setup_character_exam(bot):

    print("🌙 角色考試系統載入完成")