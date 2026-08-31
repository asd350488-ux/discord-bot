_message(
                "❌ Bot 沒有權限修改身分組。",
                ephemeral=True,
            )
            return

        # -------------------------
        # 更新 Topic
        # -------------------------

        if interaction.channel.topic:
            await interaction.channel.edit(
                topic=interaction.channel.topic.replace(
                    "Status=Pending", "Status=Approved"
                )
            )

        # -------------------------
        # 更新審核 Embed
        # -------------------------

        await update_review_embed(interaction.channel, interaction.user, "🟢 已通過")

        # -------------------------
        # 完成
        # -------------------------

        await interaction.response.defer()

    @discord.ui.button(
        label="⚫ 關閉", style=discord.ButtonStyle.danger, custom_id="review_close"
    )
    async def close_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        if interaction.user.id not in BOT_ADMINS:

            await interaction.response.send_message(
                "❌ 只有管理員可以使用此按鈕。", ephemeral=True
            )
            return

        await interaction.response.send_message(
            "⚠️ 確定要關閉這張 Ticket 嗎？", view=CloseTicketView(), ephemeral=True
        )


# ==========================
# 🌙 關閉 Ticket 確認
# ==========================


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="✅ 確認關閉", style=discord.ButtonStyle.danger)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        if interaction.user.id not in BOT_ADMINS:

            await interaction.response.send_message(
                "❌ 只有管理員可以關閉 Ticket。", ephemeral=True
            )
            return

        await interaction.response.send_message(
            "⚫ Ticket 將於 **5 秒後** 關閉。", ephemeral=True
        )

        await asyncio.sleep(5)

        await interaction.channel.delete(reason=f"{interaction.user} 關閉入群審核")

    @discord.ui.button(label="取消", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.edit_message(content="✅ 已取消關閉。", view=None)


# 🚀 啟動

@bot.event
async def on_ready():

    print(f"已登入：{bot.user}")

    # -------------------------
    # 永久 View（Persistent View）
    # -------------------------

    bot.add_view(ReviewPanelView())
    bot.add_view(ReviewManageView())
    bot.add_view(LotteryView())

    # 🌙 七夕限定盲盒
    setup_limited_lottery(bot)

    # 💌 媽咪專屬身分組
    setup_mommy_roles(bot)

    # 📝 角色考試系統
    setup_character_exam(bot)
    
    # 🎓 角色考試系統
    setup_character_test(bot)

    try:
        synced = await bot.tree.sync()
        print(f"✅ 已同步 {len(synced)} 個 Slash Commands")
    except Exception as e:
        print(f"❌ 指令同步失敗：{e}")

    # 🎂 角色生日系統
    await setup_character_birthday(bot)

    try:
        synced = await bot.tree.sync()
        print(f"✅ 已同步 {len(synced)} 個 Slash Commands")
    except Exception as e:
        print(f"❌ 指令同步失敗：{e}")

    # 🎂 生日系統
    if not birthday_check.is_running():
        birthday_check.start()

    # 🌙 每日簽到提醒
    if not checkin_reminder.is_running():
        checkin_reminder.start()

    # 🎁 抽獎系統
    if not lottery_checker.is_running():
        lottery_checker.start()

    # 🎞️ 人設圖公告系統
    if not photo_event_check.is_running():
        photo_event_check.start()
        print("✅ photo_event_check 已啟動")
        
@bot.tree.command(name="審核面板", description="發送入群審核面板")
async def review_panel(interaction: discord.Interaction):

    # 管理員限制
    if interaction.user.id not in BOT_ADMINS:

        await interaction.response.send_message(
            "❌ 只有管理員可以使用此指令。",
            ephemeral=True,
        )
        return
    embed = discord.Embed(
        title="🌙 極曜月葵｜新成員審核",
        description=(
            "歡迎加入 **極曜月葵 Discord**！\n\n"
            "為了維護社群品質，請先確認符合以下條件後，"
            "再點擊下方按鈕開始申請。\n\n"
            "════════════════════\n\n"
            "📸 **請提供以下四位媽咪其中一位角色的聊天截圖：**\n\n"
            "🌸 星弦媽咪\n"
            "🌸 韓馨媽咪\n"
            "🌸 小貓媽咪\n"
            "🌸 若曦璃媽咪\n\n"
            "════════════════════\n\n"
            "🎮 **角色等級需求**\n\n"
            "✅ C 台角色需達 **15 等**\n"
            "✅ T 台角色需達 **2 等**\n\n"
            "📌 **符合其中一項即可，**\n"
            "請提供符合條件角色的聊天截圖。\n\n"
            "════════════════════\n\n"
            "📱 **追蹤媽咪們的 Instagram（四位都要追蹤哦）請提供已追蹤的截圖**\n\n"
            "<a:emoji_16:1506410360335372299> "
            "[韓馨媽咪的 𝕀𝔾](https://www.instagram.com/hanxin_0410_?igsh=czBnczRwbXdnNmht&utm_source=qr)\n\n"
            "<a:emoji_16:1506410360335372299> "
            "[星弦媽咪的 𝕀𝔾](https://www.instagram.com/xingxian1226?igsh=bTV5NTUzZ3Q0bHFr&utm_source=qr)\n\n"
            "<a:emoji_16:1506410360335372299> "
            "[小小貓媽咪的 𝕀𝔾](https://www.instagram.com/ha.na_999?igsh=bDBvc24zbW82dWF1&utm_source=qr)\n\n"
            "<a:emoji_16:1506410360335372299> "
            "[若曦璃媽咪的 𝕀𝔾](https://www.instagram.com/cixli042?igsh=MTkweDQ5cTgxMWg2MQ%3D%3D&utm_source=qr)\n\n"
            "════════════════════\n\n"
            "⚠️ **為維護審核公平性**\n\n"
            "請勿提供不實資訊或使用他人截圖，\n"
            "經查證屬實將取消審核資格。\n\n"
            "審核通過後，\n"
            "將由管理員協助修改正式身分組。"
        ),
        color=0xC77DFF,
    )

    embed.set_thumbnail(
        url=(
            interaction.guild.icon.url
            if interaction.guild.icon
            else discord.Embed.Empty
        )
    )

    embed.set_footer(text="Moon Bot v2｜入群審核系統")

    await interaction.channel.send(embed=embed, view=ReviewPanelView())

    await interaction.response.send_message(
        "✅ 已成功發送入群審核面板！", ephemeral=True
    )


# 🐰 簽到
@bot.tree.command(name="簽到")
async def checkin(interaction: discord.Interaction):

    # 🔒 限制頻道
    if interaction.channel.id != 1516120502127694027:
        await interaction.response.send_message(
            "❌ 請到指定簽到頻道使用此指令", ephemeral=True
        )
        return

    await interaction.response.defer()

    user_id = str(interaction.user.id)
    now = datetime.now(tz)
    today = now.date()

    c.execute(
        "SELECT last_checkin, checkin_total, checkin_streak, money FROM users WHERE user_id=?",
        (user_id,),
    )
    data = c.fetchone()

    # ❗ 今日已簽到
    if data and data[0] == str(today):

        tomorrow = datetime.combine(today + timedelta(days=1), datetime.min.time())
        tomorrow = tz.localize(tomorrow)

        remaining = tomorrow - now
        total_seconds = int(remaining.total_seconds())

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        embed = discord.Embed(
            title="🌙 𝑴𝒐𝒐𝒏 𝑪𝒉𝒆𝒄𝒌𝒊𝒏", color=discord.Color.from_rgb(186, 85, 211)
        )

        embed.description = (
            "⏳ **今日已完成簽到**\n\n"
            "══════════════════════\n\n"
            "🌙 月神正在等待下一次相遇\n\n"
            f"⏰ **距離下次簽到**\n"
            f"```{hours} 小時 {minutes} 分鐘```\n"
            "══════════════════════"
        )

        embed.set_footer(text="✦ 明天再來接受月神的祝福吧 ✦")

        await interaction.followup.send(embed=embed)
        return

    # 🌸 節日活動
    today_str = str(today)
    event = CHECKIN_EVENTS.get(today_str)

    if event:

        reward = event["reward"]
        rarity = "event"
        blessing = event["message"]

    else:

        roll = random.randint(1, 100)

        if roll == 1:
            reward = 5000
            rarity = "myth"
            blessing = random.choice(MYTH_BLESSINGS)

        elif roll <= 5:
            reward = 2000
            rarity = "epic"
            blessing = random.choice(EPIC_BLESSINGS)

        elif roll <= 20:
            reward = 500
            rarity = "rare"
            blessing = random.choice(RARE_BLESSINGS)

        else:
            reward = 100
            rarity = "normal"
            blessing = random.choice(CHECKIN_BLESSINGS)

    if data:

        total = data[1] + 1

        if data[0] == str(today - timedelta(days=1)):
            streak = data[2] + 1
        else:
            streak = 1

        money = data[3] + reward

        c.execute(
            """
            UPDATE users
            SET last_checkin=?,
                checkin_total=?,
                checkin_streak=?,
                money=?
            WHERE user_id=?
            """,
            (str(today), total, streak, money, user_id),
        )

    else:

        total = 1
        streak = 1
        money = reward

        c.execute(
            """
            INSERT INTO users
            (user_id, money, checkin_total, checkin_streak, last_checkin)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, money, total, streak, str(today)),
        )

    conn.commit()

    # 🌙 Moon Checkin UI
    embed = discord.Embed(
        title="🌙 𝑴𝒐𝒐𝒏 𝑪𝒉𝒆𝒄𝒌𝒊𝒏",
        description=("✨ **星月的祝福再次降臨**\n" "歡迎再次踏入 **星月之境**。"),
        color=discord.Color.from_rgb(186, 85, 211),
    )

    # 🎁 今日獎勵
    if rarity == "event":

        theme = EVENT_THEMES[event["event"]]

        reward_box = (
            f"{theme['emoji']}══════════════{theme['emoji']}\n\n"
            f"## {theme['name']}\n\n"
            f"{blessing}\n\n"
            f" {NUNU_EMOJI} +{reward:,}\n\n"
            f"{theme['emoji']}══════════════{theme['emoji']}"
        )

        footer_text = theme["footer"]

        embed.color = discord.Color(theme["color"])

    elif rarity == "myth":

        reward_box = (
            "👑🌙══════════════🌙👑\n\n"
            f"{blessing}\n\n"
            "🌙 **月神降臨！**\n\n"
            f"{NUNU_EMOJI} +{reward:,}\n\n"
            "👑🌙══════════════🌙👑"
        )

        footer_text = "✦ 月神親自賜予了你祝福 ✦"

    elif rarity == "epic":

        reward_box = (
            "✨🌙══════════════🌙✨\n\n"
            f"{blessing}\n\n"
            "✨ **稀有獎勵！**\n\n"
            f"{NUNU_EMOJI} +{reward:,}\n\n"
            "✨🌙══════════════🌙✨"
        )

        footer_text = "✦ 星與月共同為你送上祝福 ✦"

    elif rarity == "rare":

        reward_box = (
            "🌟✨══════════════✨🌟\n\n"
            f"{blessing}\n\n"
            "🍀 **幸運降臨！**\n\n"
            f"{NUNU_EMOJI} +{reward:,}\n\n"
            "🌟✨══════════════✨🌟"
        )

        footer_text = "✦ 今晚的星空格外閃耀 ✦"

    else:

        reward_box = (
            "✨══════════════✨\n\n"
            f"{blessing}\n\n"
            f"{NUNU_EMOJI} +{reward:,}\n\n"
            "✨══════════════✨"
        )

        footer_text = "✦ 願星月永遠照耀著你 ✦"

    embed.add_field(name="🎁 今日獎勵", value=reward_box, inline=False)

    embed.add_field(name="🔥 連續簽到", value=f"```{streak} 天```", inline=True)

    embed.add_field(name="📅 累積簽到", value=f"```{total} 天```", inline=True)

    embed.set_footer(text=footer_text)

    await interaction.followup.send(embed=embed)


# 💰 錢包
@bot.tree.command(name="錢包")
async def wallet(interaction: discord.Interaction):

    user_id = str(interaction.user.id)

    # 🔒 頻道限制
    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="🛒 星月商會",
            description=("✨ 商會區域限定\n\n" f"請前往 <#{SHOP_CHANNEL}> 使用此指令"),
            color=discord.Color.gold(),
        )

        embed.add_field(
            name="📦 商會功能", value="商店｜購買｜背包｜錢包", inline=False
        )

        embed.set_footer(text="極曜月葵 ✦ 星月商會")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    c.execute(
        "SELECT money, checkin_total, checkin_streak FROM users WHERE user_id=?",
        (user_id,),
    )

    data = c.fetchone()

    if data:
        money, total, streak = data
    else:
        money, total, streak = 0, 0, 0

    embed = discord.Embed(
        title="🌙 𝑳𝒖𝒏𝒂 𝑾𝒂𝒍𝒍𝒆𝒕",
        description="✨ 星月銀行帳戶資訊",
        color=discord.Color.from_rgb(186, 85, 211),
    )

    embed.add_field(name=f"{NUNU_EMOJI} 努努幣", value=f"```{money:,}```", inline=False)

    embed.add_field(name="📅 累積簽到", value=f"```{total:,} 天```", inline=True)

    embed.add_field(name="🔥 連續簽到", value=f"```{streak:,} 天```", inline=True)

    embed.set_footer(text="極曜月葵 ✦ 星月同行")

    await interaction.response.send_message(embed=embed)
    return


# 🏆 富豪排行榜
@bot.tree.command(name="富豪排行榜")
async def leaderboard(interaction: discord.Interaction):

    # 🔒 頻道限制
    if interaction.channel.id != INFO_CHANNEL:

        embed = discord.Embed(
            title="🌙 星月指令限制",
            description=(
                "📊 排行查詢僅能於指定區域使用\n\n" f"請前往 <#{INFO_CHANNEL}>"
            ),
            color=discord.Color.from_rgb(186, 85, 211),
        )

        embed.add_field(
            name="✨ 可使用功能",
            value="等級｜排行榜｜查詢",
            inline=False,
        )

        embed.set_footer(text="極曜月葵 ✦ 星月同行")

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    c.execute("""
        SELECT user_id, money
        FROM users
        ORDER BY money DESC
    """)

    ranking = c.fetchall()

    embed = discord.Embed(
        title="🏆 𝑳𝒖𝒏𝒂 𝑻𝒉𝒓𝒐𝒏𝒆",
        description="✨ 努努幣富豪排行榜 ✨",
        color=discord.Color.gold(),
    )

    medals = {
        1: "👑",
        2: "🥈",
        3: "🥉",
    }

    rank = 1

    for user_id, money in ranking:

        # 🚫 排除指定玩家
        if int(user_id) in EXCLUDED_USERS:
            continue

        member = interaction.guild.get_member(int(user_id))

        if member is None:
            continue

        icon = medals.get(rank, f"#{rank}")

        embed.add_field(
            name=f"{icon} {member.display_name}",
            value=f"{NUNU_EMOJI} `{money:,}`",
            inline=False,
        )

        rank += 1

        if rank > 10:
            break

    embed.set_footer(text="極曜月葵 ✦ 星月同行")

    await interaction.response.send_message(embed=embed)


# 🌟 聊天等級排行榜
@bot.tree.command(name="聊天等級排行榜")
async def level_leaderboard(interaction: discord.Interaction):

    # 🔒 頻道限制
    if interaction.channel.id != INFO_CHANNEL:

        embed = discord.Embed(
            title="🌙 星月指令限制",
            description=(
                "📊 排行查詢僅能於指定區域使用\n\n" f"請前往 <#{INFO_CHANNEL}>"
            ),
            color=discord.Color.from_rgb(186, 85, 211),
        )

        embed.add_field(
            name="✨ 可使用功能",
            value="等級｜排行榜｜查詢",
            inline=False,
        )

        embed.set_footer(text="極曜月葵 ✦ 星月同行")

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    c.execute("""
        SELECT user_id, level, exp
        FROM users
        ORDER BY level DESC, exp DESC
    """)

    ranking = c.fetchall()

    embed = discord.Embed(
        title="🏆 𝑳𝒖𝒏𝒂 𝑹𝒂𝒏𝒌𝒊𝒏𝒈",
        description="✨ 星月聊天等級排行榜 ✨",
        color=discord.Color.from_rgb(186, 85, 211),
    )

    medals = {
        1: "👑",
        2: "🥈",
        3: "🥉",
    }

    rank = 1

    for uid, level, exp in ranking:

        # 🚫 排除指定玩家
        if int(uid) in EXCLUDED_USERS:
            continue

        member = interaction.guild.get_member(int(uid))

        if member is None:
            continue

        icon = medals.get(rank, f"#{rank}")

        embed.add_field(
            name=f"{icon} {member.display_name}",
            value=(f"🌟 **Lv.{level}**\n" f"✨ XP：`{exp:,}`"),
            inline=False,
        )

        rank += 1

        if rank > 10:
            break

    embed.set_footer(text="極曜月葵 ✦ 星月同行")

    await interaction.response.send_message(embed=embed)


# 📈 等級
@bot.tree.command(name="等級")
async def level(interaction: discord.Interaction):

    # 🔒 頻道限制
    if interaction.channel.id != INFO_CHANNEL:

        embed = discord.Embed(
            title="🌙 星月指令限制",
            description=(
                "📊 等級查詢僅能於指定區域使用\n\n" f"請前往 <#{INFO_CHANNEL}>"
            ),
            color=discord.Color.from_rgb(186, 85, 211),
        )

        embed.add_field(name="✨ 可使用功能", value="等級｜排行榜｜查詢", inline=False)

        embed.set_footer(text="極曜月葵 ✦ 星月同行")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    user_id = str(interaction.user.id)

    c.execute(
        """
        SELECT level, exp
        FROM users
        WHERE user_id=?
    """,
        (user_id,),
    )

    result = c.fetchone()

    if not result:
        level = 1
        exp = 0
    else:
        level, exp = result

    next_exp = level * 100

    c.execute(
        """
        SELECT COUNT(*)
        FROM users
        WHERE level > ?
           OR (level = ? AND exp > ?)
    """,
        (level, level, exp),
    )

    rank = c.fetchone()[0] + 1

    percent = min(int((exp / next_exp) * 100), 100)

    bar_length = 10
    filled = int(percent / 10)

    progress_bar = "🟪" * filled + "⬜" * (bar_length - filled)

    embed = discord.Embed(
        title="🌙 𝑳𝒖𝒏𝒂 𝑷𝒓𝒐𝒇𝒊𝒍𝒆",
        description="✨ 星月旅人的成長紀錄",
        color=discord.Color.from_rgb(138, 43, 226),
    )

    embed.add_field(name="📈 等級", value=f"```Lv.{level}```", inline=True)

    embed.add_field(name="🏆 排名", value=f"```#{rank}```", inline=True)

    embed.add_field(
        name="✨ 經驗值",
        value=(f"{progress_bar}\n" f"`{exp:,} / {next_exp:,}`\n" f"完成度：{percent}%"),
        inline=False,
    )

    embed.set_footer(text="極曜月葵 ✦ 星月同行")

    await interaction.response.send_message(embed=embed)
    return


# 📈 個人資料


@bot.tree.command(name="個人資料")
async def profile(interaction: discord.Interaction):

    await interaction.response.defer()

    # 🔒 頻道限制
    if interaction.channel.id != INFO_CHANNEL:

        embed = discord.Embed(
            title="🌙 星月指令限制",
            description=(
                "📊 個人資料僅能於指定區域使用\n\n" f"請前往 <#{INFO_CHANNEL}>"
            ),
            color=discord.Color.from_rgb(186, 85, 211),
        )

        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    user_id = str(interaction.user.id)

    c.execute(
        """
        SELECT level, exp
        FROM users
        WHERE user_id=?
    """,
        (user_id,),
    )

    result = c.fetchone()

    if not result:
        level = 1
        exp = 0
    else:
        level, exp = result

    next_exp = level * 100

    c.execute(
        """
        SELECT COUNT(*)
        FROM users
        WHERE level > ?
           OR (level = ? AND exp > ?)
    """,
        (level, level, exp),
    )

    rank = c.fetchone()[0] + 1

    bg = Image.open("images/rank_bg.jpg").convert("RGBA")

    bg = bg.resize((800, 450))

    # 下載頭像
    async with aiohttp.ClientSession() as session:

        async with session.get(interaction.user.display_avatar.url) as resp:

            avatar_bytes = await resp.read()

    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")

    avatar = avatar.resize((150, 150))

    # 圓形頭像
    mask = Image.new("L", (150, 150), 0)

    draw_mask = ImageDraw.Draw(mask)

    draw_mask.ellipse((0, 0, 150, 150), fill=255)

    avatar.putalpha(mask)

    bg.paste(avatar, (30, 110), avatar)

    # 金色頭像框
    draw_avatar = ImageDraw.Draw(bg)

    draw_avatar.ellipse((25, 105, 185, 265), outline="#FFD700", width=5)

    # 半透明資訊底板
    glass = Image.new("RGBA", bg.size, (0, 0, 0, 0))

    glass_draw = ImageDraw.Draw(glass)

    glass_draw.rounded_rectangle((15, 60, 760, 350), radius=25, fill=(20, 20, 20, 150))

    bg = Image.alpha_composite(bg, glass)

    draw = ImageDraw.Draw(bg)

    # 字型
    font_name = ImageFont.truetype("fonts/NotoSansTC-Regular.ttf", 28)

    font_level = ImageFont.truetype("fonts/NotoSansTC-Regular.ttf", 42)

    font_small = ImageFont.truetype("fonts/NotoSansTC-Regular.ttf", 22)

    # 名稱
    draw.text((210, 90), interaction.user.display_name, fill="white", font=font_name)

    # 等級
    draw.text((210, 145), f"Lv.{level}", fill="#FFD700", font=font_level)

    # 排名徽章底板
    draw.rounded_rectangle((600, 80, 760, 170), radius=20, fill=(40, 40, 40, 180))

    # 排名標題
    draw.text((625, 90), "排名", fill="#FFD700", font=font_small)

    # 排名數字
    draw.text((625, 115), f"#{rank}", fill="white", font=font_level)

    # 經驗值比例
    percent = exp / max(next_exp, 1)

    percent_text = int(percent * 100)

    # 背景條
    draw.rounded_rectangle((210, 250, 720, 285), radius=15, fill=(60, 60, 60))

    # 經驗條
    draw.rounded_rectangle(
        (210, 250, 210 + int(510 * percent), 285), radius=15, fill=(180, 100, 255)
    )

    # XP文字
    draw.text(
        (210, 305),
        f"{exp:,} / {next_exp:,} XP ({percent_text}%)",
        fill="white",
        font=font_small,
    )
    output = io.BytesIO()

    bg.save(output, format="PNG")

    output.seek(0)

    await interaction.followup.send(file=discord.File(output, filename="profile.png"))


# 🎮 聊天經驗系統
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # ==========================
    # 📺 限定聊天頻道升等
    # ==========================

    if message.channel.id != EVENT_CHANNEL:
        await bot.process_commands(message)
        return

    user_id = str(message.author.id)

    c.execute(
        """
        INSERT OR IGNORE INTO users
        (user_id,money,exp,level)
        VALUES (?,0,0,1)
        """,
        (user_id,),
    )

    c.execute("SELECT exp, level FROM users WHERE user_id=?", (user_id,))

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
        (exp, level, user_id),
    )

    conn.commit()

    if level_up:

        channel = bot.get_channel(LEVEL_UP_CHANNEL)

        embed = discord.Embed(
            title="🌙 等級提升",
            description=(f"{message.author.mention}\n\n" f"✨ 已提升至 Lv.{level}"),
            color=discord.Color.from_rgb(186, 85, 211),
        )

        embed.set_footer(text="極曜月葵 ✦ 星月同行")

        if channel:
            await channel.send(embed=embed)

    await bot.process_commands(message)


# ⚙️ 管理員設定等級
@bot.tree.command(name="設定等級")
@app_commands.default_permissions(administrator=True)
@app_commands.rename(member="成員", level="等級")
async def set_level(
    interaction: discord.Interaction, member: discord.Member, level: int
):

    c.execute(
        "UPDATE users SET level=?, exp=0 WHERE user_id=?", (level, str(member.id))
    )
    conn.commit()

    await interaction.response.send_message(f"✅ 已將 {member.mention} 設為 Lv.{level}")


@bot.tree.command(name="設定歡迎頻道")
@app_commands.default_permissions(administrator=True)
@app_commands.rename(channel="頻道")
async def set_welcome_channel(
    interaction: discord.Interaction, channel: discord.TextChannel
):
    c.execute("REPLACE INTO settings VALUES ('welcome_channel', ?)", (str(channel.id),))
    conn.commit()
    await interaction.response.send_message(f"✅ 已設定：{channel.mention}")


@bot.tree.command(name="設定管理員頻道")
@app_commands.default_permissions(administrator=True)
@app_commands.rename(channel="頻道")
async def set_admin_channel(
    interaction: discord.Interaction, channel: discord.TextChannel
):
    c.execute("REPLACE INTO settings VALUES ('admin_channel', ?)", (str(channel.id),))
    conn.commit()
    await interaction.response.send_message(f"✅ 已設定：{channel.mention}")


# ==========================
# 🌙 每日簽到提醒
# ==========================


@tasks.loop(time=time(hour=23, minute=0, tzinfo=tz))
async def checkin_reminder():

    channel = bot.get_channel(EVENT_CHANNEL)

    if channel is None:
        return
    reminder = random.choice(CHECKIN_REMINDERS)

    role = f"<@&{LOTTERY_PING_ROLE}>"

    embed = discord.Embed(
        title="🌙 每日簽到提醒",
        description=(
            f"{reminder}\n\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "⏰ 每日 **00:00** 重置\n"
            "🎁 記得前往每日簽到領取努努幣與祝福！\n\n"
            f"📍 簽到頻道：<#{CHECKIN_CHANNEL}>"
        ),
        color=discord.Color.purple(),
    )

    embed.add_field(
        name="🎁 每日獎勵",
        value=("• 每日努努幣\n" "• 連續簽到獎勵\n" "• 節日限定祝福"),
        inline=False,
    )

    embed.set_footer(text="Moon Bot v2｜每日提醒")

    await channel.send(
        content=role,
        embed=embed,
    )

# ==========================
# 🌸 角色合照活動系統
# ==========================

@tasks.loop(minutes=1)
async def photo_event_check():

    now = datetime.now(tz)

    month = now.month
    day = now.day
    hour = now.hour
    minute = now.minute

    # ==========================
    # 🌸 開放活動
    # ==========================
    
    if (
        day in [2, 16]
        and hour == 0
        and minute == 0
    ):
        today = now.strftime("%Y-%m-%d")

        c.execute(
            "SELECT value FROM settings WHERE key=?",
            ("photo_open",)
        )
        row = c.fetchone()

        if row and row["value"] == today:
            return

        channel = bot.get_channel(1504815515795853432)

        if channel is None:
            return

        await channel.send(
            "<@&1504854895826698392>\n\n"
            "🌸 **角色合照許願活動開始！**\n\n"
            "✨ **活動規則**\n\n"
            "・每月僅 **2 日、16 日** 開放許願。\n"
            "・每人每次僅能許願 **1 隻角色** 的合照。\n"
            "・每位角色皆會提供 **2 張合照**。\n"
            "・請耐心等待製作完成。\n"
            "・其餘許願規則請至活動置頂文章觀看。\n\n"
            "⏰ **本次活動將於隔日 00:00 關閉許願區。**"
        )
        # 開放角色合照許願區
        photo_channel = bot.get_channel(1504820063344267305)
        photo_role = photo_channel.guild.get_role(1504854895826698392)

        if photo_channel and photo_role:

            overwrite = photo_channel.overwrites_for(photo_role)
            overwrite.view_channel = True

            await photo_channel.set_permissions(
                photo_role,
                overwrite=overwrite
            )
            
        c.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            ("photo_open", today)
        )
        conn.commit()
        
    # ==========================
    # 🔒 活動即將結束
    # ==========================

    if (
        day in [2, 16]
        and hour == 23
        and minute == 30
    ):
    
        today = now.strftime("%Y-%m-%d")

        c.execute(
            "SELECT value FROM settings WHERE key=?",
            ("photo_notice",)
        )
        row = c.fetchone()

        if row and row["value"] == today:
            return

        channel = bot.get_channel(1504815515795853432)

        if channel is None:
            return

        await channel.send(
            "⏰ **角色合照許願活動即將結束！**\n\n"
            "<@&1504854895826698392>\n\n"
            "距離本次角色合照許願活動結束還有 **30 分鐘**。\n\n"
            "✨ **尚未許願的成員請把握最後機會！**\n\n"
            "🔒 角色合照許願區將於今日 **00:00** 準時關閉。"
        )
        
        c.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            ("photo_notice", today)
        )
        conn.commit()
        
    # ==========================
    # 🚫 關閉角色合照許願區
    # ==========================

    if (
        day in [3, 17]
        and hour == 0
        and minute == 0
    ):
        today = now.strftime("%Y-%m-%d")

        c.execute(
            "SELECT value FROM settings WHERE key=?",
            ("photo_close",)
        )
        row = c.fetchone()

        if row and row["value"] == today:
            return

        photo_channel = bot.get_channel(1504820063344267305)

        if photo_channel is None:
            return

        photo_role = photo_channel.guild.get_role(1504854895826698392)

        if photo_role is None:
            return

        overwrite = photo_channel.overwrites_for(photo_role)
        overwrite.view_channel = False

        await photo_channel.set_permissions(
            photo_role,
            overwrite=overwrite
        )

        c.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            ("photo_close", today)
        )
        conn.commit()

# ==========================
# 🎂 生日系統（Birthday v2）
# ==========================


@tasks.loop(time=time(hour=8, minute=0, tzinfo=tz))
async def birthday_check():

    now = datetime.now(tz)
    today = now.strftime("%m-%d")
    today_str = now.strftime("%Y-%m-%d")

    # ==========================
    # 🔒 防止重複執行
    # ==========================

    c.execute("""
        SELECT value
        FROM settings
        WHERE key = 'last_birthday'
        """)

    data = c.fetchone()

    if data and data["value"] == today_str:
        return

    c.execute(
        """
        REPLACE INTO settings(key, value)
        VALUES('last_birthday', ?)
        """,
        (today_str,),
    )

    conn.commit()

    # ==========================
    # 🎂 今日壽星
    # ==========================

    c.execute(
        """
        SELECT
            user_id,
            birth_year
        FROM users
        WHERE birthday = ?
        ORDER BY birthday
        """,
        (today,),
    )

    birthday_users = c.fetchall()

    # ==========================
    # 📢 公告頻道
    # ==========================

    birthday_channel = bot.get_channel(BIRTHDAY_CHANNEL)

    # ==========================
    # 👑 管理員頻道
    # ==========================

    admin_channel = bot.get_channel(BIRTHDAY_ADMIN_CHANNEL)

    if birthday_users:

        # ==========================
        # 📋 準備公告資料
        # ==========================

        birthday_members = []

        total_reward = 0
        normal_count = 0
        rare_count = 0
        myth_count = 0

        # ==========================
        # 🎁 發送生日獎勵
        # ==========================

        for row in birthday_users:

            user_id = row["user_id"]
            birth_year = row["birth_year"]

            member = bot.get_user(int(user_id))

            if member is None:
                try:
                    member = await bot.fetch_user(int(user_id))
                except Exception:
                    continue

            # ==========================
            # 🎲 抽取生日獎勵
            # ==========================

            roll = random.random()

            if roll < 0.70:

                reward = 1000
                reward_text = "✨ 星月祝福"
                normal_count += 1

            elif roll < 0.95:

                reward = 2000
                reward_text = "🌟 閃耀祝福"
                rare_count += 1

            else:

                reward = 5000
                reward_text = "💎 極光降臨"
                myth_count += 1

            # ==========================
            # 💰 發放獎勵
            # ==========================

            c.execute(
                """
                UPDATE users
                SET money = money + ?
                WHERE user_id = ?
                """,
                (
                    reward,
                    user_id,
                ),
            )

            total_reward += reward

            # ==========================
            # 🎂 年齡
            # ==========================

            age_text = ""

            if birth_year:

                age = now.year - birth_year
                age_text = f"（{age}歲）"

            # ==========================
            # 📋 公告資料
            # ==========================

            birthday_members.append(
                {
                    "mention": member.mention,
                    "name": member.display_name,
                    "age": age_text,
                    "reward": reward,
                    "reward_text": reward_text,
                }
            )

        conn.commit()
        # ==========================
        # 🎂 今日壽星公告
        # ==========================

        if birthday_channel:

            description = ""

            for member in birthday_members:

                description += f"🎉 {member['mention']} {member['age']}\n"

            birthday_blessing = random.choice(BIRTHDAY_BLESSINGS)

            embed = discord.Embed(
                title="🎂 今日壽星",
                description=(
                    f"{description}" "\n━━━━━━━━━━━━━━━━━━\n\n" f"{birthday_blessing}"
                ),
                color=discord.Color.from_rgb(255, 105, 180),
            )

            gift_text = ""

            if normal_count:
                gift_text += f"✨ 星月祝福 × {normal_count}\n"

            if rare_count:
                gift_text += f"🌟 閃耀祝福 × {rare_count}\n"

            if myth_count:
                gift_text += f"💎 極光降臨 × {myth_count}\n"

            gift_text += f"\n💰 今日共發放 **{total_reward:,} 努努幣**"

            embed.add_field(
                name="🎁 已發送生日禮物",
                value=gift_text,
                inline=False,
            )

            embed.set_footer(text="Moon Bot v2｜Birthday System")

            await birthday_channel.send(embed=embed)
    # ==========================
    # ⏰ 明日壽星提醒
    # ==========================

    tomorrow = (now + timedelta(days=1)).strftime("%m-%d")

    c.execute(
        """
        SELECT
            user_id,
            birth_year
        FROM users
        WHERE birthday = ?
        ORDER BY birthday
        """,
        (tomorrow,),
    )

    tomorrow_users = c.fetchall()

    if admin_channel and tomorrow_users:

        guild = bot.get_guild(GUILD_ID)

        if guild is not None:

            reminder_text = ""
            count = 0

            for row in tomorrow_users:

                member = guild.get_member(int(row["user_id"]))

                if member is None:
                    try:
                        member = await guild.fetch_member(int(row["user_id"]))
                    except Exception:
                        continue

                reminder_text += f"🎂 {member.mention}\n"
                count += 1

            if count:

                reminder = discord.Embed(
                    title="📅 明日壽星提醒",
                    description=(
                        f"{reminder_text}"
                        "\n━━━━━━━━━━━━━━━━━━\n\n"
                        "✨ 請記得提前送上生日祝福！"
                    ),
                    color=discord.Color.gold(),
                )

                reminder.set_footer(text=f"Moon Bot v2｜共 {count} 位壽星")

                await admin_channel.send(embed=reminder)


# ==========================
# 🌙 抽獎背景檢查
# ==========================


async def finish_lottery(message_id):

    c.execute(
        """
        SELECT channel_id, host_id, prize_type, prize_value, message, winner_count, end_time
        FROM lotteries
        WHERE message_id=? AND status='running'
        """,
        (str(message_id),),
    )

    lottery = c.fetchone()

    if not lottery:
        return False

    (channel_id, host_id, prize_type, prize_value, custom_message, winner_count, end_time) = lottery
    end_time = datetime.fromisoformat(end_time)

    c.execute(
        "SELECT user_id FROM lottery_entries WHERE message_id=?",
        (str(message_id),),
    )
    rows = c.fetchall()

    if len(rows) == 0:
        winners = []
    elif len(rows) <= winner_count:
        winners = rows
    else:
        winners = random.sample(rows, winner_count)

    winner_mentions = []

    for (winner_id,) in winners:
        winner_id = str(winner_id)
        winner_mentions.append(f"<@{winner_id}>")

        if prize_type == "money":
            add_money(winner_id, int(prize_value))

        await send_lottery_dm(
            winner_id, host_id, prize_type, prize_value, custom_message
        )

    # 先標記結束，避免背景檢查與手動結束重複開獎
    c.execute(
        "UPDATE lotteries SET status='ended' WHERE message_id=? AND status='running'",
        (str(message_id),),
    )
    conn.commit()

    channel = bot.get_channel(int(channel_id))
    if channel is None:
        return True

    try:
        message = await channel.fetch_message(int(message_id))
    except (discord.NotFound, discord.Forbidden):
        return True

    if prize_type == "money":
        prize_text = f"💰 努努幣 {int(prize_value):,}"
    elif prize_type == "image":
        prize_text = "🎨 隨機風格人設圖"
    elif prize_type == "couple":
        prize_text = "💕 與喜愛角色合照"
    else:
        prize_text = f"📝 {prize_value}"

    timestamp = int(end_time.timestamp())

    embed = discord.Embed(title="🎉 Moon Bot 抽獎", color=0xF1C40F)
    embed.add_field(name="🎁 獎品", value=prize_text, inline=False)
    embed.add_field(name="👥 中獎人數", value=f"{winner_count} 人", inline=True)
    embed.add_field(name="👤 主辦人", value=f"<@{host_id}>", inline=True)
    embed.add_field(name="⏰ 抽獎截止", value=f"<t:{timestamp}:F>", inline=False)
    embed.add_field(
        name="🏆 中獎者",
        value="\n".join(winner_mentions) if winner_mentions else "📭 本次抽獎無人參加",
        inline=False,
    )
    embed.add_field(name="📌 狀態", value="🔴 已結束", inline=False)
    embed.set_footer(text="🎉 本次抽獎已結束，感謝大家參與！")

    ended_view = LotteryView()
    c.execute("SELECT COUNT(*) FROM lottery_entries WHERE message_id=?", (str(message_id),))
    total = c.fetchone()[0]
    ended_view.children[0].label = f"🎉 參加抽獎（{total}）"
    ended_view.children[0].disabled = True
    # 查看名單保留可使用；結束抽獎按鈕鎖定
    for child in ended_view.children:
        if getattr(child, "custom_id", None) == "lottery_manual_end":
            child.disabled = True

    await message.edit(embed=embed, view=ended_view)
    return True


# ==========================
# 🌙 抽獎背景檢查
# ==========================

@tasks.loop(seconds=10)
async def lottery_checker():

    now = datetime.now()

    c.execute(
        "SELECT message_id, end_time FROM lotteries WHERE status='running'"
    )

    lotteries = c.fetchall()

    for message_id, end_time in lotteries:
        if datetime.fromisoformat(end_time) <= now:
            await finish_lottery(str(message_id))


# ==========================
# 🌙 抽獎中獎通知
# ==========================


async def send_lottery_dm(
    user_id,
    host_id,
    prize_type,
    prize_value,
    custom_message=None,
):

    try:

        user = await bot.fetch_user(int(user_id))

        embed = discord.Embed(
            title="🌙 Moon Bot｜抽獎通知",
            description="🎉 恭喜你在本次抽獎中幸運中獎！",
            color=0xF1C40F,
        )

        # -------------------------
        # 💰 努努幣
        # -------------------------

        if prize_type == "money":

            embed.add_field(
                name="🎁 獎品",
                value=f"💰 努努幣 {int(prize_value):,}",
                inline=False,
            )

            embed.description += (
                "\n\n━━━━━━━━━━━━━━━━━━\n\n"
                "Moon Bot 已自動將獎勵發放至你的帳戶。\n\n"
                "可使用 `/錢包` 查看目前餘額。"
            )

        # -------------------------
        # 🎨 人設圖
        # -------------------------

        elif prize_type == "image":

            embed.add_field(
                name="🎁 獎品",
                value="🎨 隨機風格人設圖",
                inline=False,
            )

            embed.add_field(
                name="👤 主辦人",
                value=f"<@{host_id}>",
                inline=False,
            )

            embed.description += (
                "\n\n━━━━━━━━━━━━━━━━━━\n\n"
                "請私訊主辦人，並提供你的人設圖照片。\n\n"
                "主辦人將協助製作本次抽獎獎品。"
            )

        # -------------------------
        # 💕 合照
        # -------------------------

        elif prize_type == "couple":

            embed.add_field(
                name="🎁 獎品",
                value="💕 與喜愛角色合照",
                inline=False,
            )

            embed.add_field(
                name="👤 主辦人",
                value=f"<@{host_id}>",
                inline=False,
            )

            embed.description += (
                "\n\n━━━━━━━━━━━━━━━━━━\n\n"
                "請私訊主辦人，並提供：\n\n"
                "📸 你的人設圖照片\n"
                "💖 想要合照的角色名稱\n\n"
                "💌 溫馨提醒 💌\n"
                "📌 在任何公開平台發布與角色相關的圖片或影片時，請加上浮水印。\n"
                "📌 若需發布影片，請先私訊角色創作者確認內容，經創作者同意後再公開發布。\n"
                "📌 若不知道如何製作浮水印，可請管理員協助處理。"
            )

        # -------------------------
        # 📝 自訂
        # -------------------------

        elif prize_type == "custom":

            embed.add_field(
                name="🎁 獎品",
                value=prize_value,
                inline=False,
            )

            embed.add_field(
                name="👤 主辦人",
                value=f"<@{host_id}>",
                inline=False,
            )

            if custom_message:

                embed.description += (
                    "\n\n━━━━━━━━━━━━━━━━━━\n\n"
                    f"{custom_message}\n\n"
                    "💌 溫馨提醒 💌\n"
                    "📌 在任何公開平台發布與角色相關的圖片或影片時，請加上浮水印。\n"
                    "📌 若需發布影片，請先私訊角色創作者確認內容，經創作者同意後再公開發布。\n"
                    "📌 若不知道如何製作浮水印，可請管理員協助處理。"
                )

            else:

                embed.description += (
                    "\n\n━━━━━━━━━━━━━━━━━━\n\n"
                    "請私訊主辦人領取本次抽獎獎品。\n\n"
                    "💌 溫馨提醒 💌\n"
                    "📌 在任何公開平台發布與角色相關的圖片或影片時，請加上浮水印。\n"
                    "📌 若需發布影片，請先私訊角色創作者確認內容，經創作者同意後再公開發布。\n"
                    "📌 若不知道如何製作浮水印，可請管理員協助處理。"
                )

        embed.set_footer(text="🌙 本訊息由 Moon Bot 自動發送")

        await user.send(embed=embed)

    except discord.Forbidden:
        print(f"⚠️ 無法私訊 {user_id}，對方已關閉私訊。")

    except Exception as e:
        print(f"⚠️ 發送抽獎私訊失敗：{e}")


# ==========================================
# # 🌸 歡迎系統 #
# ==========================================


@bot.event
async def on_member_join(member):

    # ==========================
    # 自動給予新人成員身分組
    # ==========================

    role = member.guild.get_role(1505110931300941844)

    if role is not None:
        await member.add_roles(role, reason="新成員自動加入")

    # 取得歡迎頻道
    c.execute("""
        SELECT value
        FROM settings
        WHERE key='welcome_channel'
    """)

    data = c.fetchone()

    if not data:
        return

    channel = bot.get_channel(int(data[0]))

    if channel is None:
        return

    # ==========================
    # Welcome Card
    # ==========================

    card = await create_welcome_card(member)

    # ==========================
    # 歡迎 Embed
    # ==========================

    embed = discord.Embed(title="🌙 歡迎加入極曜月葵", color=discord.Color.dark_grey())

    embed.description = f"""
歡迎 {member.mention} 寶寶加入我們𖤐⋆₊˚ 𝒳 ⋆ 𝒳 ⋆ 𝒳 ⋆ 𝒳 極 曜 月 葵 ˚₊⋆𖤐

很開心你來到這個小小的粉絲交流空間！<a:emoji_32:1508529055832739911>

<a:emoji_1:1506013957905846372> 請 {member.mention} 寶寶至 <#1506198162724094074>

提供我們需要的截圖。

我們進行審核通過後，
會再修改身分組唷<a:emoji_2:1506043914115879014>
"""

    embed.set_footer(text="極曜月葵 ✦ Welcome")

    # 先送文字（灰底）
    await channel.send(embed=embed)

    # 再送 Welcome Card
    await channel.send(file=card)


# ==========================
# 📅 生日登記
# ==========================


@bot.tree.command(name="生日登記", description="登記你的生日")
@app_commands.rename(month="月份", day="日期", year="出生年")
@app_commands.describe(
    month="生日月份",
    day="生日日期",
    year="出生年（選填）",
)
async def set_birthday(
    interaction: discord.Interaction,
    month: int,
    day: int,
    year: int = None,
):

    user_id = str(interaction.user.id)

    # ==========================
    # 📅 日期驗證
    # ==========================

    try:
        datetime(2000, month, day)
    except ValueError:
        await interaction.response.send_message(
            "❌ 生日日期錯誤，請重新確認。",
            ephemeral=True,
        )
        return

    # ==========================
    # 🔒 是否已登記
    # ==========================

    c.execute(
        """
        SELECT birthday
        FROM users
        WHERE user_id = ?
        """,
        (user_id,),
    )

    data = c.fetchone()

    if data and data["birthday"]:

        await interaction.response.send_message(
            "❌ 你已經完成生日登記。\n\n" "如需修改生日資料，請聯絡管理員協助處理。",
            ephemeral=True,
        )
        return

    # ==========================
    # 🎂 更新生日資料
    # ==========================

    birthday = f"{month:02d}-{day:02d}"

    c.execute(
        """
        UPDATE users
        SET birthday = ?, birth_year = ?
        WHERE user_id = ?
        """,
        (
            birthday,
            year,
            user_id,
        ),
    )

    conn.commit()

    # ==========================
    # 📝 登記紀錄
    # ==========================

    log_channel = bot.get_channel(BIRTHDAY_LOG_CHANNEL)

    if log_channel:

        embed = discord.Embed(
            title="🎂 生日登記",
            color=discord.Color.pink(),
            timestamp=datetime.now(tz),
        )

        embed.add_field(
            name="👤 使用者",
            value=interaction.user.mention,
            inline=False,
        )

        embed.add_field(
            name="📅 生日",
            value=f"{month:02d} / {day:02d}",
            inline=True,
        )

        embed.add_field(
            name="🎈 出生年",
            value=str(year) if year else "未填寫",
            inline=True,
        )

        embed.set_footer(text="Moon Bot v2｜生日系統")

        await log_channel.send(embed=embed)

    # ==========================
    # ✅ 完成
    # ==========================

    await interaction.response.send_message(
        "✅ 生日登記成功！",
        ephemeral=True,
    )


# ==========================
# 📅 生日修改
# ==========================


@bot.tree.command(name="生日修改", description="修改玩家生日")
@app_commands.rename(
    member="玩家",
    month="月份",
    day="日期",
    year="出生年",
)
@app_commands.describe(
    member="要修改生日的玩家",
    month="生日月份",
    day="生日日期",
    year="出生年（選填）",
)
async def edit_birthday(
    interaction: discord.Interaction,
    member: discord.Member,
    month: int,
    day: int,
    year: int = None,
):

    # ==========================
    # 👑 管理員限制
    # ==========================

    if interaction.user.id not in BOT_ADMINS:

        await interaction.response.send_message(
            "❌ 只有管理員可以使用此指令。",
            ephemeral=True,
        )
        return

    # ==========================
    # 📍 頻道限制
    # ==========================

    if interaction.channel.id != BIRTHDAY_ADMIN_CHANNEL:

        await interaction.response.send_message(
            f"❌ 請前往 <#{BIRTHDAY_ADMIN_CHANNEL}> 使用此指令。",
            ephemeral=True,
        )
        return

    # ==========================
    # 📅 日期驗證
    # ==========================

    try:
        datetime(2000, month, day)
    except ValueError:

        await interaction.response.send_message(
            "❌ 日期格式錯誤。",
            ephemeral=True,
        )
        return

    user_id = str(member.id)
    ensure_user(user_id)

    # ==========================
    # 🔍 取得舊資料
    # ==========================

    c.execute(
        """
        SELECT birthday, birth_year
        FROM users
        WHERE user_id = ?
        """,
        (user_id,),
    )

    data = c.fetchone()

    if not data or not data["birthday"]:

        await interaction.response.send_message(
            "❌ 該玩家尚未登記生日。",
            ephemeral=True,
        )
        return

    old_birthday = data["birthday"]
    old_year = data["birth_year"]

    new_birthday = f"{month:02d}-{day:02d}"

    # ==========================
    # 📋 資料相同
    # ==========================

    if old_birthday == new_birthday and old_year == year:

        await interaction.response.send_message(
            "⚠️ 新資料與目前生日資料相同，未進行修改。",
            ephemeral=True,
        )
        return

    # ==========================
    # 💾 更新資料
    # ==========================

    c.execute(
        """
        UPDATE users
        SET birthday = ?, birth_year = ?
        WHERE user_id = ?
        """,
        (
            new_birthday,
            year,
            user_id,
        ),
    )

    conn.commit()

    # ==========================
    # 📝 修改紀錄
    # ==========================

    log_channel = bot.get_channel(BIRTHDAY_LOG_CHANNEL)

    if log_channel:

        embed = discord.Embed(
            title="✏️ 生日資料修改",
            color=discord.Color.orange(),
            timestamp=datetime.now(tz),
        )

        embed.add_field(
            name="👤 玩家",
            value=member.mention,
            inline=False,
        )

        embed.add_field(
            name="👑 管理員",
            value=interaction.user.mention,
            inline=False,
        )

        old_text = old_birthday.replace("-", " / ")
        if old_year:
            old_text += f"\n🎈 {old_year}"

        new_text = new_birthday.replace("-", " / ")
        if year:
            new_text += f"\n🎈 {year}"
        else:
            new_text += "\n🎈 未填寫"
        embed.add_field(
            name="📅 舊資料",
            value=old_text,
            inline=True,
        )

        embed.add_field(
            name="📅 新資料",
            value=new_text,
            inline=True,
        )

        embed.set_footer(text="Moon Bot v2｜生日系統")

        await log_channel.send(embed=embed)

    # ==========================
    # ✅ 完成
    # ==========================

    await interaction.response.send_message(
        f"✅ 已成功修改 **{member.display_name}** 的生日資料。",
        ephemeral=True,
    )


# ==========================
# 📅 生日查詢
# ==========================


@bot.tree.command(name="生日查詢", description="查看所有已登記生日")
async def check_birthday(interaction: discord.Interaction):

    # ==========================
    # 👑 管理員限制
    # ==========================

    if interaction.user.id not in BOT_ADMINS:

        await interaction.response.send_message(
            "❌ 只有管理員可以使用此指令。",
            ephemeral=True,
        )
        return

    # ==========================
    # 📍 頻道限制
    # ==========================

    if interaction.channel.id != BIRTHDAY_ADMIN_CHANNEL:

        await interaction.response.send_message(
            f"❌ 請前往 <#{BIRTHDAY_ADMIN_CHANNEL}> 使用此指令。",
            ephemeral=True,
        )
        return

    # ==========================
    # 📋 查詢生日
    # ==========================

    c.execute("""
        SELECT user_id, birthday, birth_year
        FROM users
        WHERE birthday IS NOT NULL
        ORDER BY birthday
        """)

    users = c.fetchall()

    if not users:

        await interaction.response.send_message(
            "📭 目前沒有任何生日資料。",
            ephemeral=True,
        )
        return

    embed = discord.Embed(
        title="🎂 已登記生日",
        color=discord.Color.pink(),
    )

    text = ""

    for row in users:

        user = interaction.guild.get_member(int(row["user_id"]))

        if user is None:
            continue

        birthday = row["birthday"].replace("-", " / ")

        if row["birth_year"]:

            birthday += f"（{row['birth_year']}）"

        text += f"🌸 {user.display_name}\n📅 {birthday}\n\n"

    embed.description = text

    embed.set_footer(text=f"共 {len(users)} 位玩家")

    await interaction.response.send_message(embed=embed)


# ==========================
# 📅 本月壽星
# ==========================


@bot.tree.command(name="本月壽星", description="查看本月壽星")
async def birthday_list(interaction: discord.Interaction):

    # ==========================
    # 👑 管理員限制
    # ==========================

    if interaction.user.id not in BOT_ADMINS:

        await interaction.response.send_message(
            "❌ 只有管理員可以使用此指令。",
            ephemeral=True,
        )
        return

    # ==========================
    # 📍 頻道限制
    # ==========================

    if interaction.channel.id != BIRTHDAY_ADMIN_CHANNEL:

        await interaction.response.send_message(
            f"❌ 請前往 <#{BIRTHDAY_ADMIN_CHANNEL}> 使用此指令。",
            ephemeral=True,
        )
        return

    now = datetime.now(tz)
    month = now.strftime("%m")

    c.execute(
        """
        SELECT user_id, birthday, birth_year
        FROM users
        WHERE birthday LIKE ?
        ORDER BY birthday
        """,
        (f"{month}-%",),
    )

    users = c.fetchall()

    if not users:

        await interaction.response.send_message(
            "📭 本月沒有壽星。",
            ephemeral=True,
        )
        return

    embed = discord.Embed(
        title=f"🎂 {int(month)} 月壽星",
        color=discord.Color.pink(),
    )

    text = ""

    count = 0

    for row in users:

        member = interaction.guild.get_member(int(row["user_id"]))

        if member is None:
            continue

        birthday = row["birthday"].replace("-", " / ")

        if row["birth_year"]:
            birthday += f"（{row['birth_year']}）"

        text += f"🌸 **{member.display_name}**\n" f"📅 {birthday}\n\n"

        count += 1

    if not text:

        await interaction.response.send_message(
            "📭 本月沒有壽星。",
            ephemeral=True,
        )
        return

    embed.description = text

    embed.set_footer(text=f"本月共 {count} 位壽星｜Moon Bot v2")

    await interaction.response.send_message(embed=embed)


# 💼 打工
@bot.tree.command(name="打工")
async def work(interaction: discord.Interaction):

    # 🔒 頻道限制
    if interaction.channel.id != WORK_CHANNEL:

        embed = discord.Embed(
            title="💼 星月委託中心",
            description=f"請前往 <#{WORK_CHANNEL}> 接取委託任務",
            color=discord.Color.green(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    user_id = str(interaction.user.id)
    ensure_user(user_id)

    # 👤 建立資料
    c.execute(
        """
        INSERT OR IGNORE INTO users
        (user_id,money,exp,level)
        VALUES (?,0,0,1)
        """,
        (user_id,),
    )
    conn.commit()

    # ⏳ 冷卻
    c.execute("SELECT last_work,money FROM users WHERE user_id=?", (user_id,))

    data = c.fetchone()

    last_work = data[0]
    money = data[1]

    if last_work:

        last_time = datetime.fromisoformat(last_work)

        remain = timedelta(hours=1) - (datetime.now(tz) - last_time)

        if remain.total_seconds() > 0:

            minutes = int(remain.total_seconds() // 60)
            seconds = int(remain.total_seconds() % 60)

            embed = discord.Embed(
                title="⏳ 星月委託冷卻中",
                description=f"剩餘時間：{minutes}分 {seconds}秒",
                color=discord.Color.orange(),
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

    # 📜 工作列表
    jobs = [
        ("整理月神圖書館", 120, 250),
        ("護送星月商隊", 180, 320),
        ("照顧月光花園", 100, 220),
        ("清理古代遺跡", 200, 380),
        ("協助魔法研究", 220, 450),
        ("採集月光礦石", 150, 300),
        ("巡邏星空城區", 180, 350),
    ]

    job_name, low, high = random.choice(jobs)

    # 🎲 事件
    roll = random.randint(1, 100)

    if roll <= 5:

        reward = random.randint(low, high) * 3

        title = "🌟 月神眷顧"
        desc = "獲得三倍報酬"
        event_type = "success"

    elif roll <= 75:

        reward = random.randint(low, high)

        title = "✨ 委託成功"
        desc = "順利完成任務"
        event_type = "success"

    elif roll <= 90:

        reward = int(random.randint(low, high) * 0.5)

        title = "⚠️ 工作失誤"
        desc = "只獲得部分報酬"
        event_type = "success"

    elif roll <= 97:

        reward = random.randint(100, 500)

        title = "💸 工作意外"
        desc = "損壞設備需要賠償"
        event_type = "loss"

    else:

        reward = random.randint(500, 1500)

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
        (money, datetime.now(tz).isoformat(), user_id),
    )

    conn.commit()

    # 🌙 Embed
    embed = discord.Embed(
        title="🌙 𝑴𝒐𝒐𝒏 𝑾𝒐𝒓𝒌",
        description=desc,
        color=discord.Color.from_rgb(186, 85, 211),
    )

    embed.add_field(name="📜 委託內容", value=f"```{job_name}```", inline=False)

    embed.add_field(name="✨ 事件結果", value=f"```{title}```", inline=False)

    if event_type == "success":

        embed.add_field(
            name="🎁 本次收入", value=f"{NUNU_EMOJI} `{reward:,}`", inline=True
        )

    else:

        embed.add_field(
            name="💸 本次損失", value=f"{NUNU_EMOJI} `{reward:,}`", inline=True
        )

    embed.add_field(name="💰 錢包餘額", value=f"{NUNU_EMOJI} `{money:,}`", inline=True)

    embed.set_footer(text="極曜月葵 ✦ 星月同行")

    await interaction.response.send_message(embed=embed)


class BuyButton(discord.ui.Button):
    def __init__(self, item_id, price, name):
        super().__init__(label=f"購買 {name}", style=discord.ButtonStyle.green)
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
        c.execute(
            "UPDATE users SET money = money - ? WHERE user_id=?", (self.price, user_id)
        )

        # 📦 扣庫存
        c.execute("UPDATE shop SET stock = stock - 1 WHERE item_id=?", (self.item_id,))

        # 🎒 加入背包
        c.execute(
            "SELECT amount FROM inventory WHERE user_id=? AND item_id=?",
            (user_id, self.item_id),
        )
        inv = c.fetchone()

        if inv:
            c.execute(
                "UPDATE inventory SET amount = amount + 1 WHERE user_id=? AND item_id=?",
                (user_id, self.item_id),
            )
        else:
            c.execute(
                "INSERT INTO inventory (user_id, item_id, amount) VALUES (?, ?, 1)",
                (user_id, self.item_id),
            )

        conn.commit()

        await interaction.response.send_message(
            f"🛍️ 購買成功！**{self.name}**\n<a:emoji40:1510362334026268713> -{self.price}"
        )


# ==========================================
# 🛒 商店 View
# ==========================================
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

        embed = discord.Embed(title="🛒 商店", color=discord.Color.gold())

        page_items = self.get_page_items()

        for item_id, name, price, stock, desc, img in page_items:

            embed.add_field(
                name=f"🆔 {item_id}｜{name}",
                value=f"{desc}\n<a:emoji40:1510362334026268713> {price}｜庫存:{stock}",
                inline=False,
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






# ==========================================
# 🛒 商店
# ==========================================
@bot.tree.command(name="商店")
async def shop(interaction: discord.Interaction):

    # 🔒 頻道限制
    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="🛒 星月商會",
            description=("✨ 商會區域限定\n\n" f"請前往 <#{SHOP_CHANNEL}>"),
            color=discord.Color.gold(),
        )

        embed.add_field(
            name="📦 商會功能", value="商店｜購買｜背包｜錢包", inline=False
        )

        embed.set_footer(text="極曜月葵 ✦ 星月商會")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    c.execute("SELECT item_id, name, price, stock, description, image FROM shop")

    items = c.fetchall()

    if not items:
        await interaction.response.send_message("🛒 商店目前沒有商品")
        return

    view = ShopView(items)

    embed = discord.Embed(
        title="🛒 星月商會",
        description="✨ 點擊按鈕瀏覽商品",
        color=discord.Color.gold(),
    )

    await interaction.response.send_message(embed=embed, view=view)


# 💜 老公商店
@bot.tree.command(name="老公商店")
async def husband_shop(interaction: discord.Interaction):

    # 🔒 頻道限制
    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="💜 星月婚姻介紹所",
            description=(
                "✨ 老公商店僅能於指定區域使用\n\n" f"請前往 <#{SHOP_CHANNEL}>"
            ),
            color=discord.Color.from_rgb(255, 105, 180),
        )

        embed.add_field(name="💍 功能", value="老公商店｜購買老公", inline=False)

        embed.set_footer(text="極曜月葵 ✦ 命定之人")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    c.execute("""
        SELECT name
        FROM husbands
        ORDER BY husband_id
    """)

    husbands = c.fetchall()

    if not husbands:

        await interaction.response.send_message("💔 目前沒有可購買的老公")
        return

    husband_text = ""

    for i, husband in enumerate(husbands, start=1):

        husband_text += f"{i}. {husband[0]}\n"

    embed = discord.Embed(
        title="💜 星月婚姻介紹所",
        description=("歡迎挑選你的命定老公 ✨\n\n" f"{husband_text}"),
        color=discord.Color.from_rgb(255, 105, 180),
    )

    embed.set_footer(text="輸入 /購買老公 名稱")

    await interaction.response.send_message(embed=embed)


# 💜 購買老公
@bot.tree.command(name="購買老公")
async def buy_husband(interaction: discord.Interaction, 名稱: str):

    # 🔒 頻道限制
    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="💜 星月婚姻介紹所",
            description=(
                "✨ 購買老公僅能於指定區域使用\n\n" f"請前往 <#{SHOP_CHANNEL}>"
            ),
            color=discord.Color.from_rgb(255, 105, 180),
        )

        embed.add_field(
            name="💍 功能", value="老公商店｜購買老公｜我的老公", inline=False
        )

        embed.set_footer(text="極曜月葵 ✦ 命定之人")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    user_id = str(interaction.user.id)

    # 查老公是否存在
    c.execute(
        """
        SELECT husband_id
        FROM husbands
        WHERE name=?
    """,
        (名稱,),
    )

    husband = c.fetchone()

    if not husband:

        await interaction.response.send_message("❌ 查無此老公", ephemeral=True)
        return

    husband_id = husband[0]

    # 是否已擁有
    c.execute(
        """
        SELECT *
        FROM user_husbands
        WHERE user_id=?
        AND husband_id=?
    """,
        (user_id, husband_id),
    )

    if c.fetchone():

        await interaction.response.send_message(f"💜 你已經擁有 {名稱}", ephemeral=True)
        return

    # 查錢
    c.execute(
        """
        SELECT money
        FROM users
        WHERE user_id=?
    """,
        (user_id,),
    )

    data = c.fetchone()

    money = data[0] if data else 0

    if money < HUSBAND_PRICE:

        await interaction.response.send_message(
            (f"❌ 努努幣不足\n\n" f"需要：{HUSBAND_PRICE:,}\n" f"目前：{money:,}"),
            ephemeral=True,
        )
        return

    # 扣款
    c.execute(
        """
        UPDATE users
        SET money = money - ?
        WHERE user_id=?
    """,
        (HUSBAND_PRICE, user_id),
    )

    # 收藏
    c.execute(
        """
        INSERT INTO user_husbands
        (user_id, husband_id)
        VALUES (?, ?)
    """,
        (user_id, husband_id),
    )

    conn.commit()

    embed = discord.Embed(
        title="💜 收藏成功",
        description=(f"恭喜獲得\n\n" f"✨ {名稱} ✨"),
        color=discord.Color.from_rgb(255, 105, 180),
    )

    embed.add_field(name="💰 消耗", value=f"{HUSBAND_PRICE:,} 努努幣", inline=False)

    embed.set_footer(text="極曜月葵 ✦ 命定之人")

    await interaction.response.send_message(embed=embed)


# 💜 我的老公
@bot.tree.command(name="我的老公")
async def my_husbands(interaction: discord.Interaction):
    # 🔒 頻道限制
    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="💜 我的老公",
            description=("✨ 此功能僅能於指定區域使用\n\n" f"請前往 <#{SHOP_CHANNEL}>"),
            color=discord.Color.from_rgb(255, 105, 180),
        )

        embed.add_field(
            name="💍 功能", value="老公商店｜購買老公｜我的老公", inline=False
        )

        embed.set_footer(text="極曜月葵 ✦ 命定之人")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    user_id = str(interaction.user.id)

    c.execute(
        """
        SELECT h.name
        FROM user_husbands uh
        JOIN husbands h
        ON uh.husband_id = h.husband_id
        WHERE uh.user_id=?
        ORDER BY h.husband_id
    """,
        (user_id,),
    )

    husbands = c.fetchall()

    if not husbands:

        await interaction.response.send_message("💔 你目前還沒有收藏任何老公")
        return

    husband_text = "\n".join([f"💜 {h[0]}" for h in husbands])

    embed = discord.Embed(
        title="💜 我的老公",
        description=husband_text,
        color=discord.Color.from_rgb(255, 105, 180),
    )

    embed.set_footer(text=f"共收藏 {len(husbands)} 位老公")

    await interaction.response.send_message(embed=embed)


# 🎲 猜大小
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

    # 💰 賭注限制
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

    # 🎲 骰子
    dice = random.randint(1, 6)

    result = "大" if dice >= 4 else "小"

    win = choice == result

    # ⭐ 結果池
    roll = random.randint(1, 100)

    event_name = ""
    change = 0
    # 💸 賭場手續費（10%）
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

    # 💰 扣除本次輸贏
    money += change

    # 💸 扣除賭場手續費
    money -= fee

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

    embed = discord.Embed(
        title="🎲 星月賭場・猜大小", color=discord.Color.from_rgb(186, 85, 211)
    )

    embed.add_field(name="🎯 你的選擇", value=f"```{choice}```", inline=True)

    embed.add_field(name="🎲 骰子結果", value=f"```{dice}```", inline=True)

    embed.add_field(name="✨ 判定", value=f"```{event_name}```", inline=False)

    if change >= 0:

        embed.add_field(
            name="🎉 本次獲得", value=f"{NUNU_EMOJI} `{change:,}`", inline=False
        )

    else:

        embed.add_field(
            name="💸 本次損失",
            value=f"{NUNU_EMOJI} `{abs(change):,}`",
            inline=False,
        )
    embed.add_field(
        name="💸 賭場手續費",
        value=f"{NUNU_EMOJI} `{fee:,}`",
        inline=False,
    )
    embed.add_field(name="💰 錢包餘額", value=f"{NUNU_EMOJI} `{money:,}`", inline=False)

    embed.set_footer(text="極曜月葵 ✦ 星月賭場｜每局收取 10% 手續費")
    await interaction.response.send_message("🎲 擲骰準備中...")

    msg = await interaction.original_response()

    await asyncio.sleep(1)

    await msg.edit(content="🎲 骰子滾動中...")

    await asyncio.sleep(1)

    await msg.edit(content="🎲 🎲 ...")

    await asyncio.sleep(1)

    await msg.edit(content="👀 正在判定大小...")

    await asyncio.sleep(1)

    if result == "大":

        await msg.edit(content=f"🎲 骰子停在 {dice} 點（大）")

    else:

        await msg.edit(content=f"🎲 骰子停在 {dice} 點（小）")

    await asyncio.sleep(1)

    await msg.edit(content=None, embed=embed)


# ⚔️ 對賭
@bot.tree.command(name="對賭")
@app_commands.rename(target="玩家", amount="金額")
@app_commands.describe(target="要挑戰的玩家", amount="下注金額")
async def duel(interaction: discord.Interaction, target: discord.Member, amount: int):

    if interaction.channel.id != DUEL_CHANNEL:

        await interaction.response.send_message(
            f"❌ 請前往 <#{DUEL_CHANNEL}>", ephemeral=True
        )
        return

    if target.bot:

        await interaction.response.send_message("❌ 不能挑戰機器人")
        return

    if target.id == interaction.user.id:

        await interaction.response.send_message("❌ 不能挑戰自己")
        return

    # 💰 賭注限制
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
        embed=embed, view=DuelView(interaction.user, target, amount)
    )

    embed = discord.Embed(title="⚔️ 星月對賭", color=discord.Color.red())

    embed.add_field(name="挑戰者", value=interaction.user.mention, inline=False)

    embed.add_field(name="被挑戰者", value=target.mention, inline=False)

    embed.add_field(name="賭注", value=f"{NUNU_EMOJI} `{amount:,}`", inline=False)

    embed.set_footer(text="60秒內接受挑戰")


# 🎰 老虎機
@bot.tree.command(name="老虎機")
@app_commands.rename(amount="金額")
@app_commands.describe(amount="請輸入下注金額")
async def slot_machine(interaction: discord.Interaction, amount: int):

    if interaction.channel.id != SLOT_CHANNEL:

        embed = discord.Embed(
            title="🎰 星月賭場",
            description=f"請前往 <#{SLOT_CHANNEL}> 使用老虎機",
            color=discord.Color.red(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # 💰 賭注限制
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

    symbols = ["🍒", "🌙", "⭐", "💎"]

    slot = [random.choice(symbols), random.choice(symbols), random.choice(symbols)]

    result_text = " ".join(slot)

    reward = 0
    title = ""

    # ☠️ 爆機事件
    if random.randint(1, 100) <= 10:

        title = "☠️ 爆機"
        reward = -(amount * 2)

        slot = ["💀", "💀", "💀"]

        result_text = " ".join(slot)

    elif slot == ["💎", "💎", "💎"]:

        title = "⭐ 神運 JACKPOT"
        reward = amount * 10

    elif slot[0] == slot[1] == slot[2]:

        title = "✨ 大勝"
        reward = amount * 5

    elif slot[0] == slot[1] or slot[0] == slot[2] or slot[1] == slot[2]:

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
        (money, user_id),
    )

    conn.commit()

    embed = discord.Embed(title="🎰 星月老虎機", color=discord.Color.gold())

    embed.add_field(name="🎰 結果", value=f"```{result_text}```", inline=False)

    embed.add_field(name="✨ 判定", value=f"```{title}```", inline=False)

    if reward >= 0:

        embed.add_field(
            name="🎉 本次獲得", value=f"{NUNU_EMOJI} `{reward:,}`", inline=False
        )

    else:

        embed.add_field(
            name="💸 本次損失", value=f"{NUNU_EMOJI} `{abs(reward):,}`", inline=False
        )

    embed.add_field(name="💰 錢包餘額", value=f"{NUNU_EMOJI} `{money:,}`", inline=False)

    embed.set_footer(text="極曜月葵 ✦ 星月賭場")

    await interaction.response.send_message("🎰 啟動老虎機...")

    msg = await interaction.original_response()

    await asyncio.sleep(1)

    await msg.edit(content="🎰 🍒 ❔ ❔")

    await asyncio.sleep(1)

    await msg.edit(content="🎰 🍒 🌙 ❔")

    await asyncio.sleep(1)

    await msg.edit(content=f"🎰 {result_text}")

    await asyncio.sleep(1)

    await msg.edit(content=None, embed=embed)


# 🎁 驚喜箱


# 🧭 探險
@bot.tree.command(name="探險")
async def adventure(interaction: discord.Interaction):

    if interaction.channel.id != ADVENTURE_CHANNEL:

        embed = discord.Embed(
            title="🧭 星月探險",
            description=f"請前往 <#{ADVENTURE_CHANNEL}> 使用探險",
            color=discord.Color.blurple(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    user_id = str(interaction.user.id)

    c.execute(
        """
        SELECT money,last_adventure
        FROM users
        WHERE user_id=?
        """,
        (user_id,),
    )

    data = c.fetchone()

    if not data:

        await interaction.response.send_message("❌ 找不到帳戶資料", ephemeral=True)
        return

    money, last_adventure = data

    now = datetime.now()

    if last_adventure:

        last_time = datetime.fromisoformat(last_adventure)

        remain = 1800 - int((now - last_time).total_seconds())

        if remain > 0:

            minutes = remain // 60
            seconds = remain % 60

            await interaction.response.send_message(
                f"⏳ 探險冷卻中\n還需 {minutes}分 {seconds}秒", ephemeral=True
            )
            return

    roll = random.randint(1, 100)

    title = ""
    reward = 0

    # 🌌 神級
    if roll <= 5:

        title = random.choice(["🌌 星神降臨", "🌌 月神祝福", "🌌 時空裂縫"])

        reward = random.randint(5000, 20000)

    # 👑 Boss
    elif roll <= 15:

        title = random.choice(["👑 深淵魔狼", "👑 星辰巨龍", "👑 月影騎士"])

        reward = random.randint(1000, 8000)

    # ⚔️ 危險
    elif roll <= 35:

        title = random.choice(["⚔️ 流浪盜賊", "⚔️ 深林陷阱", "⚔️ 魔物襲擊"])

        reward = -random.randint(100, 1000)

    # 🌿 普通
    else:

        title = random.choice(["🌿 補給箱", "🌿 旅行商人", "🌿 遺失財寶"])

        reward = random.randint(100, 1000)

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
        (money, now.isoformat(), user_id),
    )

    conn.commit()

    embed = discord.Embed(title="🧭 星月探險", color=discord.Color.blurple())

    embed.add_field(name="📖 探險結果", value=f"```{title}```", inline=False)

    if reward >= 0:

        embed.add_field(
            name="🎉 獲得", value=f"{NUNU_EMOJI} `{reward:,}`", inline=False
        )

    else:

        embed.add_field(
            name="💸 損失", value=f"{NUNU_EMOJI} `{abs(reward):,}`", inline=False
        )

    embed.add_field(name="💰 錢包餘額", value=f"{NUNU_EMOJI} `{money:,}`", inline=False)

    embed.set_footer(text="極曜月葵 ✦ 星月探險")
    await interaction.response.send_message("🧭 正在離開月葵城...")

    msg = await interaction.original_response()

    await asyncio.sleep(1)

    await msg.edit(content="🌲 穿越迷霧森林...")

    await asyncio.sleep(1)

    await msg.edit(content="👀 搜尋遺跡蹤跡...")

    await asyncio.sleep(1)

    if roll <= 5:

        await msg.edit(content="🌌 神級氣息降臨...")

    elif roll <= 15:

        await msg.edit(content="👑 發現世界Boss...")

    elif roll <= 35:

        await msg.edit(content="⚔️ 遭遇危險事件...")

    else:

        await msg.edit(content="🎁 發現神秘寶箱...")

    await asyncio.sleep(1)

    await msg.edit(content=None, embed=embed)


# 💳 購買
@bot.tree.command(name="購買")
@app_commands.rename(item_id="商品編號")
@app_commands.describe(item_id="商店商品編號")
async def buy(interaction: discord.Interaction, item_id: int):

    # 🔒 頻道限制
    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="🛒 星月商會",
            description=f"請前往 <#{SHOP_CHANNEL}> 使用購買功能",
            color=discord.Color.gold(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    name, price, stock = item

    if stock <= 0:
        await interaction.response.send_message("❌ 商品已售完", ephemeral=True)
        return

    # 💰 查餘額
    c.execute("SELECT money FROM users WHERE user_id=?", (user_id,))

    data = c.fetchone()

    if not data:
        await interaction.response.send_message(
            "❌ 請先簽到或打工建立資料", ephemeral=True
        )
        return

    money = data[0]

    if money < price:
        await interaction.response.send_message("❌ 努努幣不足", ephemeral=True)
        return

    # 💰 扣款
    c.execute("UPDATE users SET money = money - ? WHERE user_id=?", (price, user_id))

    # 📦 扣庫存
    c.execute("UPDATE shop SET stock = stock - 1 WHERE item_id=?", (item_id,))

    # 🎒 加入背包
    c.execute(
        "SELECT amount FROM inventory WHERE user_id=? AND item_id=?", (user_id, item_id)
    )

    inv = c.fetchone()

    if inv:

        c.execute(
            """
            UPDATE inventory
            SET amount = amount + 1
            WHERE user_id=? AND item_id=?
            """,
            (user_id, item_id),
        )

    else:

        c.execute(
            """
            INSERT INTO inventory
            (user_id,item_id,amount)
            VALUES (?,?,1)
            """,
            (user_id, item_id),
        )

    conn.commit()

    embed = discord.Embed(title="🛍️ 購買成功", color=discord.Color.green())

    embed.add_field(name="📦 商品", value=f"```{name}```", inline=False)

    embed.add_field(name="💰 花費", value=f"{NUNU_EMOJI} `{price:,}`", inline=False)

    embed.set_footer(text="極曜月葵 ✦ 星月商會")

    await interaction.response.send_message(embed=embed)


# 🎒 背包
@bot.tree.command(name="背包")
async def inventory_cmd(interaction: discord.Interaction):

    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="🛒 星月商會",
            description=f"請前往 <#{SHOP_CHANNEL}> 使用背包功能",
            color=discord.Color.gold(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    user_id = str(interaction.user.id)

    c.execute(
        """
        SELECT shop.name, inventory.amount
        FROM inventory
        JOIN shop ON inventory.item_id = shop.item_id
        WHERE inventory.user_id=?
    """,
        (user_id,),
    )

    items = c.fetchall()

    if not items:
        await interaction.response.send_message("🎒 你的背包是空的")
        return

    text = ""

    for name, amount in items:
        text += f"🎁 {name} × {amount}\n"

    embed = discord.Embed(
        title="🎒 星月背包", description=text, color=discord.Color.purple()
    )

    embed.set_footer(text="極曜月葵 ✦ 星月商會")

    await interaction.response.send_message(embed=embed)


# 🎁 贈送道具
@bot.tree.command(name="贈送道具")
@app_commands.rename(member="成員", item_name="道具名稱", amount="數量")
@app_commands.describe(
    member="接收道具的玩家", item_name="要贈送的道具", amount="贈送數量"
)
async def give_item(
    interaction: discord.Interaction,
    member: discord.Member,
    item_name: str,
    amount: int,
):

    if interaction.channel.id != SHOP_CHANNEL:

        embed = discord.Embed(
            title="🛒 星月商會",
            description=f"請前往 <#{SHOP_CHANNEL}> 使用贈送功能",
            color=discord.Color.gold(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    sender_id = str(interaction.user.id)
    target_id = str(member.id)

    c.execute("SELECT item_id FROM shop WHERE name=?", (item_name,))

    item = c.fetchone()

    if not item:

        await interaction.response.send_message("❌ 沒有這個商品", ephemeral=True)
        return

    item_id = item[0]

    c.execute(
        """
        SELECT amount
        FROM inventory
        WHERE user_id=? AND item_id=?
        """,
        (sender_id, item_id),
    )

    data = c.fetchone()

    if not data or data[0] < amount:

        await interaction.response.send_message("❌ 道具不足", ephemeral=True)
        return

    # 扣除自己
    c.execute(
        """
        UPDATE inventory
        SET amount = amount - ?
        WHERE user_id=? AND item_id=?
        """,
        (amount, sender_id, item_id),
    )

    # 對方背包
    c.execute(
        """
        SELECT amount
        FROM inventory
        WHERE user_id=? AND item_id=?
        """,
        (target_id, item_id),
    )

    target_data = c.fetchone()

    if target_data:

        c.execute(
            """
            UPDATE inventory
            SET amount = amount + ?
            WHERE user_id=? AND item_id=?
            """,
            (amount, target_id, item_id),
        )

    else:

        c.execute(
            """
            INSERT INTO inventory
            (user_id,item_id,amount)
            VALUES (?,?,?)
            """,
            (target_id, item_id, amount),
        )

    conn.commit()

    embed = discord.Embed(title="🎁 贈送成功", color=discord.Color.green())

    embed.add_field(name="📦 道具", value=f"```{item_name}```", inline=False)

    embed.add_field(name="👤 收件人", value=member.mention, inline=False)

    embed.add_field(name="📦 數量", value=f"`{amount}`", inline=False)

    embed.set_footer(text="極曜月葵 ✦ 星月商會")

    await interaction.response.send_message(embed=embed)


# ⚙️ 增加努努幣

@bot.tree.command(name="發努努幣")
@app_commands.rename(amount="金額", member="成員", role="身分組", everyone="發送全體")
@app_commands.describe(
    amount="發送金額", member="指定成員", role="指定身分組", everyone="是否發送給全體"
)
async def give_money(
    interaction: discord.Interaction,
    amount: int,
    member: discord.Member = None,
    role: discord.Role = None,
    everyone: bool = False,
):

    await interaction.response.defer()

    # 🔒 限制頻道
    if interaction.channel.id != 1510930723924611163:
        await interaction.followup.send("❌ 請到管理員頻道使用", ephemeral=True)
        return

    # 🔒 指定管理員使用者 ID
    ALLOWED_USERS = [
    1153640526063607820,  # 韓馨
    1218542666879598613,  # 星弦
    1301905168094335028,  # 曦兒
    806960151578804275,  # 小貓
    873202145367846942,  # 菜菜
    844778614268100638,  # 小E
]

    if interaction.user.id not in ALLOWED_USERS:
        await interaction.followup.send("❌ 你沒有權限", ephemeral=True)
        return
    
    # 🔒 至少選一個對象
    if not member and not role and not everyone:
        await interaction.followup.send("❌ 請選擇發送對象", ephemeral=True)
        return

    count = 0

    # 👤 單人
    if member:

        add_money(member.id, amount)

        count = 1

    # 👥 身分組
    elif role:

        for m in role.members:

            if m.bot:
                continue

            add_money(m.id, amount)

            count += 1

    # 🌍 全體
    elif everyone:

        for m in interaction.guild.members:

            if m.bot:
                continue

            add_money(m.id, amount)

            count += 1

    embed = discord.Embed(title="💰 發錢完成", color=discord.Color.green())

    embed.add_field(
        name="💵 發送金額", value=f"{NUNU_EMOJI} `{amount:,}`", inline=False
    )

    if member:
        embed.add_field(name="👤 發送對象", value=member.mention, inline=False)

    elif role:
        embed.add_field(name="🎭 發送對象", value=role.mention, inline=False)

    elif everyone:
        embed.add_field(name="🌍 發送對象", value="`全體成員`", inline=False)

    embed.add_field(name="👥 發送人數", value=f"`{count}` 人", inline=False)

    await interaction.followup.send(embed=embed)


# 💣 黑市投資


# 🎯 猜心情




# 🧪 實驗


# 🗡 搶劫


# =========================
# 📋 我的通緝
# =========================




# ==========================
# 🌙 建立抽獎
# ==========================


@bot.tree.command(name="抽獎建立", description="建立一場新的抽獎")
async def lottery_create(interaction: discord.Interaction):

    # -------------------------
    # 頻道限制
    # -------------------------

    if interaction.channel.id != LOTTERY_CHANNEL:

        await interaction.response.send_message(
            "❌ 請至抽獎頻道使用此指令。", ephemeral=True
        )
        return

    # -------------------------
    # 權限限制
    # -------------------------

    if interaction.user.id not in LOTTERY_MANAGERS:

        await interaction.response.send_message(
            "❌ 只有抽獎管理員可以建立抽獎。",
            ephemeral=True,
        )
        return

    # -------------------------
    # 選擇獎品
    # -------------------------

    embed = discord.Embed(
        title="🎁 建立抽獎",
        description=("請選擇本次抽獎的獎品類型。\n\n" "選擇後將會開啟對應的設定視窗。"),
        color=0xF1C40F,
    )

    await interaction.response.send_message(
        embed=embed, view=PrizeSelectView(), ephemeral=True
    )


# ==========================
# 🌙 建立星月盲盒面板
# ==========================


@bot.tree.command(name="建立盲盒面板", description="建立星月盲盒面板")
async def create_blindbox_panel(interaction: discord.Interaction):

    # 只有 BOT 管理員可使用
    if interaction.user.id not in BOT_ADMINS:
        await interaction.response.send_message(
            "❌ 你沒有權限使用此指令！", ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🌙 星月盲盒中心",
        description=(
            "歡迎來到 **星月盲盒中心**！\n\n"
            f"💰 **開啟價格：{BLINDBOX_PRICE:,} 努努幣**"
        ),
        color=discord.Color.purple(),
    )

    embed.add_field(
        name="🎁 可獲得獎勵",
        value=(
            "📹 影片合集\n"
            "📸 照片合集\n"
            "💍 結婚證書\n"
            "🏅 雙人徽章\n\n"
            "💰 努努幣100萬\n"
            "💰 努努幣200萬\n"
            "💰 努努幣300萬\n"
            "💰 努努幣400萬\n"
            "💰 努努幣500萬"
        ),
        inline=False,
    )

    embed.add_field(
        name="📜 抽獎規則",
        value=(
            "① 每次開啟需消耗 500 萬努努幣。\n"
            "② 特殊獎勵將進入第二階段角色抽選。\n"
            "③ 努努幣獎勵將立即發放。\n"
            "④ 抽獎期間不可重複開啟。"
        ),
        inline=False,
    )

    embed.set_footer(text="🌙 Moon Bot v2｜星月盲盒中心")

    await interaction.channel.send(embed=embed, view=BlindBoxPanelView())

    await interaction.response.send_message("✅ 星月盲盒面板建立完成！", ephemeral=True)


# ==========================
# 🌐 Render 保活服務
# ==========================

class ReusableTCPServer(TCPServer):
    allow_reuse_address = True


def run_web():
    port = int(os.environ.get("PORT", 10000))

    with ReusableTCPServer(
        ("0.0.0.0", port),
        SimpleHTTPRequestHandler
    ) as httpd:

        print(f"🌐 Web Server 已啟動，Port：{port}")

        httpd.serve_forever()


threading.Thread(
    target=run_web,
    daemon=True
).start()


# ==========================
# 🌙 簽到條件抽獎系統
# ==========================

setup_streak_lottery(
    bot,
    LOTTERY_CHANNEL,
    LOTTERY_MANAGERS,
    LOTTERY_PING_ROLE,
)


bot.run(os.getenv("TOKEN"))