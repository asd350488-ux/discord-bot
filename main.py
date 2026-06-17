
    # ❗ 沒選
    if not 成員 and not 身分組 and not 全體:
        await interaction.followup.send(
            "❌ 請選擇發送對象",
            ephemeral=True
        )
        return

    count = 0

    # 👤 單人
    if 成員:

        user_id = str(成員.id)

        c.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
            (user_id,)
        )

        c.execute(
            "UPDATE users SET money = money + ? WHERE user_id=?",
            (金額, user_id)
        )

        count = 1

    # 👥 身分組
    elif 身分組:

        for member in 身分組.members:

            if member.bot:
                continue

            user_id = str(member.id)

            c.execute(
                "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
                (user_id,)
            )

            c.execute(
                "UPDATE users SET money = money + ? WHERE user_id=?",
                (金額, user_id)
            )

            count += 1

    # 🌍 全體
    elif 全體:

        for member in interaction.guild.members:

            if member.bot:
                continue

            user_id = str(member.id)

            c.execute(
                "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
                (user_id,)
            )

            c.execute(
                "UPDATE users SET money = money + ? WHERE user_id=?",
                (金額, user_id)
            )

            count += 1

    conn.commit()

    embed = discord.Embed(
        title="💰 發錢完成",
        color=discord.Color.green()
    )

    embed.add_field(
        name="💵 發送金額",
        value=f"{NUNU_EMOJI} `{金額:,}`",
        inline=False
    )

    embed.add_field(
        name="👥 發送人數",
        value=f"`{count}` 人",
        inline=False
    )

    await interaction.followup.send(
        embed=embed
    )

