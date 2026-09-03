# -*- coding: utf-8 -*-
# ⚔️ Moon Bot｜對賭系統

def setup_duel(bot, *, get_money, add_money, remove_money, c, conn, discord, app_commands, random, asyncio, datetime, timedelta, MIN_BET, MAX_BET, CASINO_FEE_RATE, NUNU_EMOJI, DUEL_CHANNEL):

    class DuelView(discord.ui.View):
        def __init__(self, challenger, target, amount):
            super().__init__(timeout=60)
            self.challenger = challenger
            self.target = target
            self.amount = amount

        @discord.ui.button(label="⚔️ 接受對賭", style=discord.ButtonStyle.danger)
        async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != self.target.id:
                await interaction.response.send_message("❌ 這不是你的對賭", ephemeral=True)
                return

            challenger_id = str(self.challenger.id)
            target_id = str(self.target.id)
            c.execute("SELECT money FROM users WHERE user_id=?", (challenger_id,))
            challenger_money = c.fetchone()
            c.execute("SELECT money FROM users WHERE user_id=?", (target_id,))
            target_money = c.fetchone()

            if not challenger_money or not target_money:
                await interaction.response.send_message("❌ 帳戶不存在", ephemeral=True)
                return

            challenger_money = challenger_money[0]
            target_money = target_money[0]
            if challenger_money < self.amount:
                await interaction.response.send_message(
                    f"❌ {self.challenger.display_name} 的努努幣不足\n需要：{self.amount:,}\n目前：{challenger_money:,}",
                    ephemeral=True,
                )
                return
            if target_money < self.amount:
                await interaction.response.send_message(
                    f"❌ {self.target.display_name} 的努努幣不足\n需要：{self.amount:,}\n目前：{target_money:,}",
                    ephemeral=True,
                )
                return

            await interaction.response.edit_message(content="⚔️ 決鬥準備中...", view=None)
            await asyncio.sleep(1)
            await interaction.edit_original_response(content="🎲 擲骰中...")
            await asyncio.sleep(1)
            await interaction.edit_original_response(content="💥 勝負判定中...")
            await asyncio.sleep(1)

            winner = random.choice([self.challenger, self.target])
            loser = self.target if winner == self.challenger else self.challenger
            winner_id = str(winner.id)
            pot = self.amount * 2
            roll = random.randint(1, 100)
            if roll <= 5:
                title, reward = "⭐ 神運", int(pot * 2.5)
            elif roll <= 25:
                title, reward = "✨ 大勝", int(pot * 1.5)
            else:
                title, reward = "🎉 小勝", pot

            c.execute("UPDATE users SET money = money - ? WHERE user_id=?", (self.amount, challenger_id))
            c.execute("UPDATE users SET money = money - ? WHERE user_id=?", (self.amount, target_id))
            c.execute("UPDATE users SET money = money + ? WHERE user_id=?", (reward, winner_id))
            conn.commit()

            embed = discord.Embed(title="⚔️ 星月對賭結果", color=discord.Color.red())
            embed.add_field(name="🏆 勝者", value=winner.mention, inline=False)
            embed.add_field(name="✨ 結果", value=title, inline=False)
            embed.add_field(name="🏦 獎池", value=f"{NUNU_EMOJI} `{pot:,}`", inline=False)
            embed.add_field(name="🎁 最終獎勵", value=f"{NUNU_EMOJI} `{reward:,}`", inline=False)
            embed.add_field(name="💀 敗者", value=loser.mention, inline=False)
            await interaction.edit_original_response(content=None, embed=embed, view=None)

        @discord.ui.button(label="❌ 拒絕對賭", style=discord.ButtonStyle.secondary)
        async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != self.target.id:
                await interaction.response.send_message("❌ 這不是你的對賭", ephemeral=True)
                return
            embed = discord.Embed(
                title="❌ 對賭取消",
                description=f"{self.target.display_name} 拒絕了這場對賭",
                color=discord.Color.greyple(),
            )
            await interaction.response.edit_message(embed=embed, view=None)

    @bot.tree.command(name="對賭")
    @app_commands.rename(target="玩家", amount="金額")
    @app_commands.describe(target="要挑戰的玩家", amount="下注金額")
    async def duel(interaction: discord.Interaction, target: discord.Member, amount: int):
        if interaction.channel.id != DUEL_CHANNEL:
            await interaction.response.send_message(f"❌ 請前往 <#{DUEL_CHANNEL}>", ephemeral=True)
            return
        if target.bot:
            await interaction.response.send_message("❌ 不能挑戰機器人", ephemeral=True)
            return
        if target.id == interaction.user.id:
            await interaction.response.send_message("❌ 不能挑戰自己", ephemeral=True)
            return
        if amount < MIN_BET or amount > MAX_BET:
            await interaction.response.send_message(
                f"❌ 賭注必須介於 {NUNU_EMOJI} `{MIN_BET:,}` ~ `{MAX_BET:,}`",
                ephemeral=True,
            )
            return

        embed = discord.Embed(title="⚔️ 星月對賭", color=discord.Color.red())
        embed.add_field(name="挑戰者", value=interaction.user.mention, inline=False)
        embed.add_field(name="被挑戰者", value=target.mention, inline=False)
        embed.add_field(name="賭注", value=f"{NUNU_EMOJI} `{amount:,}`", inline=False)
        embed.set_footer(text="60秒內接受挑戰")
        await interaction.response.send_message(
            embed=embed,
            view=DuelView(interaction.user, target, amount),
        )
