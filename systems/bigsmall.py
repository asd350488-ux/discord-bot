# -*- coding: utf-8 -*-
# 🎲 Moon Bot｜猜大小系統

def setup_bigsmall(bot, *, get_money, add_money, remove_money, c, conn, discord, app_commands, random, asyncio, datetime, timedelta, MIN_BET, MAX_BET, CASINO_FEE_RATE, NUNU_EMOJI, BIGSMALL_CHANNEL):

    @bot.tree.command(name="猜大小")
    @app_commands.rename(choice="選擇", amount="金額")
    @app_commands.describe(choice="選擇大小", amount="下注金額")
    @app_commands.choices(
        choice=[
            app_commands.Choice(name="🔺 大", value="大"),
            app_commands.Choice(name="🔻 小", value="小"),
        ]
    )
    async def guess_big_small(interaction: discord.Interaction, choice: str, amount: int):
        if interaction.channel.id != BIGSMALL_CHANNEL:
            embed = discord.Embed(
                title="🎲 星月賭場",
                description=f"請前往 <#{BIGSMALL_CHANNEL}> 使用猜大小",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        choice = choice.strip()
        if choice not in ["大", "小"]:
            await interaction.response.send_message("❌ 請輸入：大 或 小", ephemeral=True)
            return

        if amount < MIN_BET or amount > MAX_BET:
            await interaction.response.send_message(
                f"❌ 賭注必須介於 {NUNU_EMOJI} `{MIN_BET:,}` ~ `{MAX_BET:,}`",
                ephemeral=True,
            )
            return

        user_id = str(interaction.user.id)
        c.execute("SELECT money FROM users WHERE user_id=?", (user_id,))
        data = c.fetchone()
        if not data:
            await interaction.response.send_message("❌ 找不到帳戶資料", ephemeral=True)
            return

        money = data[0]
        if money < amount:
            await interaction.response.send_message("❌ 努努幣不足", ephemeral=True)
            return

        dice = random.randint(1, 6)
        result = "大" if dice >= 4 else "小"
        win = choice == result
        roll = random.randint(1, 100)
        fee = int(amount * CASINO_FEE_RATE)

        if win:
            if roll <= 3:
                event_name = "⭐ 神運"
                change = int(amount * 4)
            elif roll <= 20:
                event_name = "✨ 大勝"
                change = int(amount * 2)
            else:
                event_name = "🎉 小勝"
                change = int(amount * 1.2)
        else:
            if roll <= 80:
                event_name = "💀 失敗"
                change = -amount
            else:
                event_name = "☠️ 爆死"
                change = -(amount * 2)

        money += change
        money -= fee
        if money < 0:
            money = 0

        c.execute("UPDATE users SET money=? WHERE user_id=?", (money, user_id))
        conn.commit()

        embed = discord.Embed(
            title="🎲 星月賭場・猜大小",
            color=discord.Color.from_rgb(186, 85, 211),
        )
        embed.add_field(name="🎯 你的選擇", value=f"```{choice}```", inline=True)
        embed.add_field(name="🎲 骰子結果", value=f"```{dice}```", inline=True)
        embed.add_field(name="✨ 判定", value=f"```{event_name}```", inline=False)
        if change >= 0:
            embed.add_field(name="🎉 本次獲得", value=f"{NUNU_EMOJI} `{change:,}`", inline=False)
        else:
            embed.add_field(name="💸 本次損失", value=f"{NUNU_EMOJI} `{abs(change):,}`", inline=False)
        embed.add_field(name="💸 賭場手續費", value=f"{NUNU_EMOJI} `{fee:,}`", inline=False)
        embed.add_field(name="💰 錢包餘額", value=f"{NUNU_EMOJI} `{money:,}`", inline=False)
        fee_percent = CASINO_FEE_RATE * 100
        embed.set_footer(text=f"極曜月葵 ✦ 星月賭場｜每局收取 {fee_percent:g}% 手續費")

        await interaction.response.send_message("🎲 擲骰準備中...")
        msg = await interaction.original_response()
        await asyncio.sleep(1)
        await msg.edit(content="🎲 骰子滾動中...")
        await asyncio.sleep(1)
        await msg.edit(content="🎲 🎲 ...")
        await asyncio.sleep(1)
        await msg.edit(content="👀 正在判定大小...")
        await asyncio.sleep(1)
        await msg.edit(content=f"🎲 骰子停在 {dice} 點（{result}）")
        await asyncio.sleep(1)
        await msg.edit(content=None, embed=embed)
