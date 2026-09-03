# ==========================
# 🎰 Moon Bot v2｜老虎機系統
# ==========================

import random


def setup_slot(
    bot,
    *,
    c,
    conn,
    discord,
    app_commands,
    asyncio,
    MIN_BET,
    MAX_BET,
    CASINO_FEE_RATE,
    NUNU_EMOJI,
    SLOT_CHANNEL,
):
    """
    🎰 老虎機
    - 最低／最高下注由 config.py 控制
    - 每局不論輸贏固定收 10% 手續費
    - 玩家畫面不顯示內部賠率
    """

    # ==========================
    # 🎯 老虎機內部賠率
    # ==========================
    # 注意：這些數值只供程式內部使用，不會顯示給玩家。
    RESULT_TABLE = [
        ("💀 失敗", 40.0),
        ("🎉 小勝", 38.0),
        ("✨ 大勝", 16.0),
        ("☠️ 爆機", 5.5),
        ("⭐ 神運 JACKPOT", 0.5),
    ]

    symbols = ["🍒", "🌙", "⭐", "💎"]

    def roll_result():
        """依照內部機率抽出本次結果。"""
        roll = random.uniform(0, 100)
        current = 0.0

        for title, chance in RESULT_TABLE:
            current += chance
            if roll < current:
                return title

        return RESULT_TABLE[-1][0]

    @bot.tree.command(name="老虎機")
    @app_commands.rename(amount="金額")
    @app_commands.describe(amount="請輸入下注金額")
    async def slot_machine(interaction: discord.Interaction, amount: int):

        # ==========================
        # 📍 頻道限制
        # ==========================
        if interaction.channel.id != SLOT_CHANNEL:
            embed = discord.Embed(
                title="🎰 星月賭場",
                description=f"請前往 <#{SLOT_CHANNEL}> 使用老虎機",
                color=discord.Color.red(),
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return

        # ==========================
        # 💰 賭注限制
        # ==========================
        if amount < MIN_BET or amount > MAX_BET:
            await interaction.response.send_message(
                f"❌ 賭注必須介於 {NUNU_EMOJI} `{MIN_BET:,}` ~ `{MAX_BET:,}`",
                ephemeral=True,
            )
            return

        user_id = str(interaction.user.id)

        c.execute(
            "SELECT money FROM users WHERE user_id=?",
            (user_id,),
        )

        data = c.fetchone()

        if not data:
            await interaction.response.send_message(
                "❌ 找不到帳戶資料",
                ephemeral=True,
            )
            return

        money = data[0]

        # ==========================
        # 💸 手續費
        # ==========================
        fee = int(amount * CASINO_FEE_RATE)
        total_cost = amount + fee

        # 下注本金 + 手續費都必須付得起
        if money < total_cost:
            await interaction.response.send_message(
                f"❌ 努努幣不足\n"
                f"下注：{NUNU_EMOJI} `{amount:,}`\n"
                f"手續費：{NUNU_EMOJI} `{fee:,}`\n"
                f"需要：{NUNU_EMOJI} `{total_cost:,}`",
                ephemeral=True,
            )
            return

        # ==========================
        # 🎰 抽取結果
        # ==========================
        title = roll_result()

        if title == "☠️ 爆機":
            slot = ["💀", "💀", "💀"]
            # 含手續費實際總損失為下注的 2.1 倍
            # 例：下注 10,000 + 手續費 1,000 + 額外扣 10,000 = -21,000
            reward = -amount

        elif title == "⭐ 神運 JACKPOT":
            slot = ["💎", "💎", "💎"]
            # 獎金為下注 3 倍；扣本金與 10% 手續費後實拿 1.9 倍
            # 例：30,000 - 10,000 - 1,000 = +19,000
            reward = amount * 3

        elif title == "✨ 大勝":
            slot = ["⭐", "⭐", "⭐"]
            reward = amount * 2

        elif title == "🎉 小勝":
            # 小勝顯示兩個相同圖案
            pair_symbol = random.choice(symbols)
            other_symbols = [s for s in symbols if s != pair_symbol]
            slot = [
                pair_symbol,
                pair_symbol,
                random.choice(other_symbols),
            ]
            random.shuffle(slot)
            reward = int(amount * 1.5)

        else:
            # 失敗顯示三個不同圖案
            slot = random.sample(symbols, 3)
            # 含手續費實際總損失為下注的 1.6 倍
            # 例：10,000 + 1,000 手續費 + 5,000 額外扣款 = -16,000
            reward = int(-(amount * 0.5))

        result_text = " ".join(slot)

        # ==========================
        # 🎬 老虎機動畫
        # ==========================
        await interaction.response.send_message(
            f"🎰 **星月老虎機啟動中...**"
        )

        message = await interaction.original_response()

        await asyncio.sleep(0.6)
        await message.edit(
            content=f"🎰 {slot[0]} ❔ ❔"
        )

        await asyncio.sleep(0.6)
        await message.edit(
            content=f"🎰 {slot[0]} {slot[1]} ❔"
        )

        await asyncio.sleep(0.7)

        # ==========================
        # 💰 最終結算
        # ==========================
        # 手續費每局都收，不論輸贏。
        # reward 是獎金／額外扣款；實際本局盈虧 = reward - 本金 - 手續費。
        net_change = reward - total_cost
        money = money + net_change

        if money < 0:
            money = 0

        c.execute(
            """
            UPDATE users
            SET money=?
            WHERE user_id=?
            """,
            (money, user_id),
        )

        conn.commit()

        # ==========================
        # 📋 結算訊息
        # ==========================
        # 玩家看到的是完整帳務：
        # 本局贏／輸 → 扣本金 → 扣手續費 → 最終變化
        if reward > 0:
            round_result_name = "💰 本局贏"
            round_result_value = f"{NUNU_EMOJI} `{reward:,}`"
        elif reward < 0:
            round_result_name = "💀 本局輸"
            round_result_value = f"{NUNU_EMOJI} `{abs(reward):,}`"
        else:
            round_result_name = "💰 本局贏"
            round_result_value = f"{NUNU_EMOJI} `0`"

        final_change = (
            f"+{NUNU_EMOJI} `{net_change:,}`"
            if net_change > 0
            else f"-{NUNU_EMOJI} `{abs(net_change):,}`"
            if net_change < 0
            else f"{NUNU_EMOJI} `0`"
        )

        embed = discord.Embed(
            title="🎰 星月老虎機",
            color=discord.Color.gold(),
        )

        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url,
        )

        embed.add_field(
            name="🎰 結果",
            value=f"```{result_text}```",
            inline=False,
        )

        embed.add_field(
            name="📌 判定",
            value=title,
            inline=False,
        )

        embed.add_field(
            name=round_result_name,
            value=round_result_value,
            inline=False,
        )

        embed.add_field(
            name="💵 扣本金",
            value=f"{NUNU_EMOJI} `{amount:,}`",
            inline=True,
        )

        embed.add_field(
            name="💸 扣手續費",
            value=f"{NUNU_EMOJI} `{fee:,}`",
            inline=True,
        )

        embed.add_field(
            name="🪙 最終變化",
            value=final_change,
            inline=False,
        )

        embed.add_field(
            name="👛 餘額",
            value=f"{NUNU_EMOJI} `{money:,}`",
            inline=False,
        )

        embed.set_footer(text="極曜月葵 ✦ 星月賭場")

        await message.edit(
            content=None,
            embed=embed,
        )
