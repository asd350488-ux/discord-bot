# ==========================
# 🌙 七夕限定盲盒抽獎系統
# ==========================

import discord
import random
import asyncio
from datetime import datetime, timedelta
from discord import app_commands
from discord.ext import commands

from database import conn, c
from config import BOT_ADMINS


# ==========================
# 🌙 七夕限定盲盒設定
# ==========================

QIXI_DATE = "2026-08-19"

# --------------------------
# 🎟️ 每人最多參與次數
# --------------------------

LIMITED_LOTTERY_MAX_TIMES = 2

# --------------------------
# 💰 參與費用
# --------------------------

LIMITED_LOTTERY_FIRST_PRICE = 500

LIMITED_LOTTERY_SECOND_PRICE = 5000

# --------------------------
# 🎁 獎品機率
# --------------------------

LIMITED_LOTTERY_PRIZES = [
    {
        "type": "money",
        "name": "💰 努努幣 5,000",
        "value": 5000,
        "weight": 40,
    },
    {
        "type": "money",
        "name": "💰 努努幣 8,000",
        "value": 8000,
        "weight": 30,
    },
    {
        "type": "sticker",
        "name": "🎨 角色 Q 版貼圖 ×1",
        "value": 1,
        "weight": 20,
    },
    {
        "type": "couple",
        "name": "💕 角色合照 ×1",
        "value": 1,
        "weight": 10,
    },
]

# ==========================
# 🌙 正在開盲盒的玩家
# ==========================

limited_lottery_running = set()

# ==========================
# 🌙 判斷是否為七夕活動日
# ==========================

def is_qixi_day():

    # 🧪 測試期間暫時不限日期
    return True
    
# ==========================
# 🌙 取得玩家正式參與次數
# ==========================

def get_limited_lottery_count(user_id):

    # -------------------------
    # 👑 管理員測試不計入正式次數
    # -------------------------

    if int(user_id) in BOT_ADMINS:
        return 0

    c.execute(
        """
        SELECT COUNT(*)
        FROM limited_lottery_entries
        WHERE user_id = ?
        AND is_test = 0
        """,
        (str(user_id),),
    )

    result = c.fetchone()

    return result[0] if result else 0
    
# ==========================
# 🌙 執行七夕限定盲盒
# ==========================

async def run_limited_lottery(
    interaction: discord.Interaction,
    draw_number: int,
    price: int,
):

    user_id = str(interaction.user.id)

    # -------------------------
    # 👑 管理員測試模式
    # -------------------------

    is_test = interaction.user.id in BOT_ADMINS

    # -------------------------
    # 🔒 防止重複抽獎
    # -------------------------

    if interaction.user.id in limited_lottery_running:

        await interaction.response.send_message(
            "🌙 你的七夕盲盒正在開啟中，\n"
            "請稍等一下再操作喔！",
            ephemeral=True,
        )

        return

    limited_lottery_running.add(interaction.user.id)

    try:

        # ==========================
        # 💰 查詢努努幣
        # ==========================

        c.execute(
            """
            SELECT money
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        )

        data = c.fetchone()

        if not data:

            await interaction.response.send_message(
                "❌ 找不到你的努努幣帳戶資料。",
                ephemeral=True,
            )

            return

        money = data["money"]

        # ==========================
        # 💰 檢查餘額
        # ==========================

        if money < price:

            await interaction.response.send_message(
                "❌ 你的努努幣不足！\n\n"
                f"💰 本次需要：**{price:,} 努努幣**\n"
                f"💰 目前餘額：**{money:,} 努努幣**",
                ephemeral=True,
            )

            return

        # ==========================
        # 🎲 抽取獎品
        # ==========================

        prizes = []

        for prize in LIMITED_LOTTERY_PRIZES:

            prizes.extend(
                [prize] * prize["weight"]
            )

        prize = random.choice(prizes)

        prize_type = prize["type"]
        prize_name = prize["name"]
        prize_value = prize["value"]

        # ==========================
        # 💰 扣除參與費
        # ==========================

        money -= price

        # ==========================
        # 💰 努努幣獎品
        # ==========================

        if prize_type == "money":

            money += int(prize_value)

        # ==========================
        # 💾 更新玩家餘額
        # ==========================

        c.execute(
            """
            UPDATE users
            SET money = ?
            WHERE user_id = ?
            """,
            (
                money,
                user_id,
            ),
        )

        # ==========================
        # 💾 記錄抽獎結果
        # ==========================

        c.execute(
            """
            INSERT INTO limited_lottery_entries (
                user_id,
                draw_number,
                price,
                prize_type,
                prize_value,
                is_test,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                draw_number,
                price,
                prize_type,
                str(prize_value),
                1 if is_test else 0,
                datetime.now().isoformat(),
            ),
        )

        conn.commit()

        # ==========================
        # 🌙 開始盲盒動畫
        # ==========================

        await interaction.response.send_message(
            "🌙 **七夕限定盲盒**\n\n"
            "🎁 你的盲盒正在準備中……",
            ephemeral=True,
        )

        # -------------------------
        # ✨ 第一階段
        # -------------------------

        await asyncio.sleep(1)

        await interaction.edit_original_response(
            content=(
                "🌙 **七夕限定盲盒**\n\n"
                "🎁 盲盒正在晃動……\n"
                "✨ 裡面好像有東西！"
            ),
            embed=None,
        )

        # -------------------------
        # ✨ 第二階段
        # -------------------------

        await asyncio.sleep(1)

        await interaction.edit_original_response(
            content=(
                "🌙 **七夕限定盲盒**\n\n"
                "✨✨✨\n"
                "命運正在揭曉……"
            ),
            embed=None,
        )

        # -------------------------
        # ✨ 第三階段
        # -------------------------

        await asyncio.sleep(1)

        await interaction.edit_original_response(
            content=(
                "🌙 **七夕限定盲盒**\n\n"
                "💫 **砰！**\n\n"
                "🎁 盲盒已經打開！"
            ),
            embed=None,
        )

        # -------------------------
        # ✨ 最後揭曉
        # -------------------------

        await asyncio.sleep(1)

        # ==========================
        # 🎁 建立最終結果
        # ==========================

        if prize_type == "money":

            result_description = (
                "🎉 **恭喜你！**\n\n"
                f"## {prize_name}\n\n"
                "💰 獎勵已經自動加入你的錢包！"
            )

        elif prize_type == "sticker":

            result_description = (
                "🎉 **恭喜你！**\n\n"
                f"## {prize_name}\n\n"
                "📌 **領獎方式**\n\n"
                "請務必將本次**抽獎結果截圖保存**，\n"
                "私訊**管理員**並告知角色名稱。\n\n"
                "⚠️ **未提供抽獎結果截圖，將無法領取獎品。**"
            )

        elif prize_type == "couple":

            result_description = (
                "🎉 **恭喜你！**\n\n"
                f"## {prize_name}\n\n"
                "📌 **領獎方式**\n\n"
                "請務必將本次**抽獎結果截圖保存**，\n"
                "私訊**管理員**並告知角色名稱。\n\n"
                "⚠️ **未提供抽獎結果截圖，將無法領取獎品。**"
            )
        else:

            result_description = (
                "🎉 **恭喜你！**\n\n"
                f"## {prize_name}"
            )

        # ==========================
        # 🌙 最終結果 Embed
        # ==========================

        embed = discord.Embed(
            title="🌙 七夕限定盲盒",
            description=result_description,
            color=0xE91E63,
        )

        embed.add_field(
            name="🎟️ 本次抽獎",
            value=f"第 **{draw_number} 次**",
            inline=True,
        )

        embed.add_field(
            name="💸 抽獎費用",
            value=f"{price:,} 努努幣",
            inline=True,
        )

        embed.add_field(
            name="💰 目前餘額",
            value=f"{money:,} 努努幣",
            inline=False,
        )

        # -------------------------
        # 👑 管理員測試提示
        # -------------------------

        if is_test:

            embed.add_field(
                name="🧪 測試模式",
                value=(
                    "👑 管理員測試\n"
                    "本次不計入正式抽獎次數。"
                ),
                inline=False,
            )

        embed.set_footer(
            text="🌙 Moon Bot｜七夕限定盲盒｜2026/8/19"
        )

        # ==========================
        # 🎁 顯示最終結果
        # ==========================

        await interaction.edit_original_response(
            content=None,
            embed=embed,
        )

    finally:

        # ==========================
        # 🔓 解開玩家抽獎鎖
        # ==========================

        limited_lottery_running.discard(
            interaction.user.id
        )

# ==========================
# 🌙 建立限定盲盒資料表
# ==========================

def init_limited_lottery_database():

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS limited_lottery_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            draw_number INTEGER NOT NULL,
            price INTEGER NOT NULL,
            prize_type TEXT NOT NULL,
            prize_value TEXT NOT NULL,
            is_test INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )

    # -------------------------
    # 🌙 舊資料表補上測試欄位
    # -------------------------

    try:

        c.execute(
            """
            ALTER TABLE limited_lottery_entries
            ADD COLUMN is_test INTEGER DEFAULT 0
            """
        )

    except Exception:

        pass

    conn.commit()

# ==========================
# 🌙 七夕限定盲盒面板
# ==========================


class LimitedLotteryView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    # ==========================
    # 🎟️ 第一次抽獎
    # ==========================

    @discord.ui.button(
        label="🎁 第一次抽獎｜500 努努幣",
        style=discord.ButtonStyle.primary,
        custom_id="limited_lottery_first",
        row=0,
    )
    async def first_draw(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        # -------------------------
        # 🌙 活動日期檢查
        # -------------------------

        if not is_qixi_day():

            await interaction.response.send_message(
                "🌙 七夕限定盲盒目前沒有開放喔！\n"
                "本活動僅限 **2026/8/19** 當日參與。",
                ephemeral=True,
            )

            return

        # -------------------------
        # 🌙 查詢參與次數
        # -------------------------

        count = get_limited_lottery_count(interaction.user.id)

        if count >= LIMITED_LOTTERY_MAX_TIMES:

            await interaction.response.send_message(
                "❌ 你已經完成本次七夕限定盲盒的 **2 次抽獎**。",
                ephemeral=True,
            )

            return

        # -------------------------
        # 🌙 確認是否為第一次
        # -------------------------

        if count != 0:

            await interaction.response.send_message(
                "⚠️ 你已經使用過第一次抽獎機會了。\n"
                "如果還有剩餘次數，請使用 **第二次抽獎｜5,000 努努幣**。",
                ephemeral=True,
            )

            return

        # -------------------------
        # 🌙 暫時顯示確認訊息
        # -------------------------

        await run_limited_lottery(
            interaction,
            draw_number=1,
            price=LIMITED_LOTTERY_FIRST_PRICE,
        )


    # ==========================
    # 🎟️ 第二次抽獎
    # ==========================

    @discord.ui.button(
        label="🌙 第二次抽獎｜5,000 努努幣",
        style=discord.ButtonStyle.success,
        custom_id="limited_lottery_second",
        row=1,
    )
    async def second_draw(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        # -------------------------
        # 🌙 活動日期檢查
        # -------------------------

        if not is_qixi_day():

            await interaction.response.send_message(
                "🌙 七夕限定盲盒目前沒有開放喔！\n"
                "本活動僅限 **2026/8/19** 當日參與。",
                ephemeral=True,
            )

            return

        # -------------------------
        # 🌙 查詢參與次數
        # -------------------------

        count = get_limited_lottery_count(interaction.user.id)

        # -------------------------
        # 🌙 尚未完成第一次
        # -------------------------

        if count == 0 and interaction.user.id not in BOT_ADMINS:

            await interaction.response.send_message(
                "❌ 你還沒有進行第一次抽獎。\n\n"
                "請先完成 **第一次抽獎｜500 努努幣**，"
                "才能進行第二次抽獎。",
                ephemeral=True,
            )

            return

        # -------------------------
        # 🌙 已經完成兩次
        # -------------------------

        if count >= LIMITED_LOTTERY_MAX_TIMES:

            await interaction.response.send_message(
                "❌ 你已經完成本次七夕限定盲盒的 **2 次抽獎**。",
                ephemeral=True,
            )

            return

        # -------------------------
        # 🌙 暫時顯示確認訊息
        # -------------------------

        await run_limited_lottery(
            interaction,
            draw_number=2,
            price=LIMITED_LOTTERY_SECOND_PRICE,
        )


# ==========================
# 🌙 七夕限定盲盒 Embed
# ==========================


def create_limited_lottery_embed():

    embed = discord.Embed(
        title="🌙 七夕限定盲盒",
        description=(
            "💫 **一年一度的七夕限定活動！**\n\n"
            "8/19 七夕當日限定開放，\n"
            "每位成員最多可以參與 **2 次**。\n\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            
            "🎁 **盲盒獎品**\n\n"
            "💰 努努幣 5,000　｜　40%\n"
            "💰 努努幣 8,000　｜　30%\n"
            "🎨 角色 Q 版貼圖 ×1　｜　20%\n"
            "💕 角色合照 ×1　｜　10%\n\n"
            
            "━━━━━━━━━━━━━━━━━━\n\n"
            
            "📌 **角色獎品領取方式**\n\n"
            "🎨 抽到 **角色 Q 版貼圖**\n"
            "💕 抽到 **角色合照**\n\n"
            "請務必將**抽獎結果截圖保存**，\n"
            "私訊**管理員**並告知角色名稱。\n\n"
            "⚠️ **未提供抽獎結果截圖，將無法領取獎品。**\n\n"
            
            "━━━━━━━━━━━━━━━━━━\n\n"
            
            "🎟️ **抽獎費用**\n\n"
            "第一次　→　💰 **500 努努幣**\n"
            "第二次　→　💰 **5,000 努努幣**\n\n"
            "每人最多 **2 次**，每次皆為獨立抽獎。\n\n"
            "💌 **七夕限定，只有一天！**"
        ),
        color=0xE91E63,
    )

    embed.set_footer(
        text="🌙 Moon Bot｜七夕限定盲盒｜2026/8/19"
    )

    return embed


# ==========================
# 🌙 發送七夕限定盲盒面板
# ==========================


async def send_limited_lottery_panel(channel):

    embed = create_limited_lottery_embed()

    await channel.send(
        embed=embed,
        view=LimitedLotteryView(),
    )
    
# ==========================
# 🧪 七夕限定盲盒｜管理員測試指令
# ==========================

@app_commands.command(
    name="qixi_test",
    description="🌙 發送七夕限定盲盒測試面板",
)
async def limited_lottery_test(
    interaction: discord.Interaction,
):

    # -------------------------
    # 👑 管理員限定
    # -------------------------

    if interaction.user.id not in BOT_ADMINS:

        await interaction.response.send_message(
            "❌ 只有管理員可以使用這個測試指令。",
            ephemeral=True,
        )

        return

    # -------------------------
    # 🌙 發送測試面板
    # -------------------------

    await send_limited_lottery_panel(
        interaction.channel
    )

    await interaction.response.send_message(
        "✅ 七夕限定盲盒測試面板已發送！",
        ephemeral=True,
    )
    
# ==========================
# 🌙 啟動限定盲盒系統
# ==========================

def setup_limited_lottery(bot):

    init_limited_lottery_database()

    # -------------------------
    # 🌙 註冊永久按鈕
    # -------------------------

    bot.add_view(LimitedLotteryView())

    # -------------------------
    # 🧪 註冊管理員測試指令
    # -------------------------

    if bot.tree.get_command("qixi_test") is None:
        bot.tree.add_command(limited_lottery_test)

    print("✅ 七夕限定盲盒系統已載入")