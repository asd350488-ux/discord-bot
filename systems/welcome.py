# ==========================================
# 🌙 Moon Bot Welcome Card v3
# ==========================================

import io
import aiohttp
import discord

from PIL import (
    Image,
    ImageDraw,
    ImageFont,
)

# ==========================================
# 🖼️ 圖片
# ==========================================

WIDTH = 1400
HEIGHT = 1000

BACKGROUND = "images/welcome_bg.png"
FONT = "fonts/NotoSansTC-Regular.ttf"

# ==========================================
# 📍 座標
# ==========================================

# Logo
TITLE_X = WIDTH // 2
TITLE_Y = 95

WELCOME_X = WIDTH // 2
WELCOME_Y = 170

# Avatar
AVATAR_SIZE = 250

AVATAR_X = WIDTH // 2 - AVATAR_SIZE // 2
AVATAR_Y = 205

# 資訊帶
INFO_LEFT = 40
INFO_TOP = 470

INFO_RIGHT = WIDTH - 40
INFO_BOTTOM = 900

# 文字
TEXT_X = WIDTH // 2

WELCOME_TEXT_Y = 610
MEMBER_Y = 685
QUOTE_Y = 760
BOT_Y = 830

# ==========================================
# 🎨 顏色
# ==========================================

WHITE = (255, 255, 255)

PURPLE = (226, 197, 255)

GLOW = (205, 167, 255)

INFO_COLOR = (18, 18, 24, 150)

OVERLAY = (25, 25, 30, 105)

# ==========================================
# 🔤 字型大小
# ==========================================

TITLE_SIZE = 90

WELCOME_SIZE = 54

NAME_SIZE = 76

MEMBER_SIZE = 46

FOOTER_SIZE = 34

BOT_SIZE = 30

# ==========================================
# 🔤 字型
# ==========================================


def load_font(size):
    return ImageFont.truetype(FONT, size)


# ==========================================
# ✨ Glow 文字
# ==========================================


def draw_glow_text(
    draw,
    position,
    text,
    font,
    fill,
    glow,
    anchor="mm",
):

    x, y = position

    # Glow
    for ox in range(-3, 4):
        for oy in range(-3, 4):

            if ox == 0 and oy == 0:
                continue

            draw.text(
                (x + ox, y + oy),
                text,
                font=font,
                fill=glow,
                anchor=anchor,
            )

    # 正文
    draw.text(
        position,
        text,
        font=font,
        fill=fill,
        anchor=anchor,
    )


# ==========================================
# 🖼️ Discord Avatar
# ==========================================


async def download_avatar(member):

    async with aiohttp.ClientSession() as session:

        async with session.get(member.display_avatar.url) as resp:

            avatar = Image.open(io.BytesIO(await resp.read())).convert("RGBA")

    return avatar


# ==========================================
# 🌙 Welcome Card
# ==========================================


async def create_welcome_card(member):

    # =====================
    # 背景
    # =====================

    bg = Image.open(BACKGROUND).convert("RGBA")
    bg = bg.resize((WIDTH, HEIGHT))

    # =====================
    # 整張淡灰遮罩
    # =====================

    overlay = Image.new(
        "RGBA",
        bg.size,
        OVERLAY,
    )

    bg = Image.alpha_composite(bg, overlay)

    # =====================
    # Discord 頭像
    # =====================

    avatar = await download_avatar(member)

    avatar = avatar.resize((AVATAR_SIZE, AVATAR_SIZE))

    mask = Image.new(
        "L",
        (AVATAR_SIZE, AVATAR_SIZE),
        0,
    )

    mask_draw = ImageDraw.Draw(mask)

    mask_draw.ellipse(
        (
            0,
            0,
            AVATAR_SIZE,
            AVATAR_SIZE,
        ),
        fill=255,
    )

    # =====================
    # 中央資訊帶
    # =====================

    info_layer = Image.new(
        "RGBA",
        bg.size,
        (0, 0, 0, 0),
    )

    info_draw = ImageDraw.Draw(info_layer)

    info_draw.rounded_rectangle(
        (
            INFO_LEFT,
            INFO_TOP,
            INFO_RIGHT,
            INFO_BOTTOM,
        ),
        radius=42,
        fill=INFO_COLOR,
    )

    bg = Image.alpha_composite(
        bg,
        info_layer,
    )

    draw = ImageDraw.Draw(bg)

    # =====================
    # 貼頭像
    # =====================

    bg.paste(
        avatar,
        (AVATAR_X, AVATAR_Y),
        mask,
    )

    # =====================
    # 外框
    # =====================

    draw.ellipse(
        (
            AVATAR_X - 7,
            AVATAR_Y - 7,
            AVATAR_X + AVATAR_SIZE + 7,
            AVATAR_Y + AVATAR_SIZE + 7,
        ),
        outline=PURPLE,
        width=5,
    )

    draw.ellipse(
        (
            AVATAR_X - 13,
            AVATAR_Y - 13,
            AVATAR_X + AVATAR_SIZE + 13,
            AVATAR_Y + AVATAR_SIZE + 13,
        ),
        outline=GLOW,
        width=2,
    )

    # =====================
    # 字型
    # =====================

    title_font = load_font(TITLE_SIZE)
    welcome_font = load_font(WELCOME_SIZE)
    member_font = load_font(MEMBER_SIZE)
    footer_font = load_font(FOOTER_SIZE)
    bot_font = load_font(BOT_SIZE)

    # =====================
    # 名字自動縮放
    # =====================

    name_size = NAME_SIZE

    while True:

        name_font = load_font(name_size)

        bbox = draw.textbbox(
            (0, 0),
            member.display_name,
            font=name_font,
        )

        if (bbox[2] - bbox[0]) <= 900:
            break

        name_size -= 2

        if name_size <= 42:
            break

    # =====================
    # Logo
    # =====================

    draw_glow_text(
        draw,
        (TITLE_X, TITLE_Y),
        "極 曜 月 葵",
        title_font,
        WHITE,
        GLOW,
    )

    draw.text(
        (WELCOME_X, WELCOME_Y),
        "WELCOME",
        fill=PURPLE,
        font=welcome_font,
        anchor="mm",
    )

    # =====================
    # 玩家名稱
    # =====================

    draw_glow_text(
        draw,
        (TEXT_X, WELCOME_TEXT_Y),
        f"歡迎 {member.display_name} 加入我們 ✦ 極曜月葵 ✦",
        name_font,
        WHITE,
        GLOW,
    )

    # =====================
    # Member
    # =====================

    draw.text(
        (TEXT_X, MEMBER_Y),
        f"Member  #{member.guild.member_count:03d}",
        fill=PURPLE,
        font=member_font,
        anchor="mm",
    )

    # =====================
    # 願星光
    # =====================

    draw.text(
        (TEXT_X, QUOTE_Y),
        "✦ 願星光照亮你的旅程。 ✦",
        fill=WHITE,
        font=footer_font,
        anchor="mm",
    )

    # =====================
    # Moon Bot
    # =====================

    draw.text(
        (TEXT_X, BOT_Y),
        "Moon Bot v2",
        fill=PURPLE,
        font=bot_font,
        anchor="mm",
    )

    # =====================
    # 輸出圖片
    # =====================

    output = io.BytesIO()

    bg.save(
        output,
        format="PNG",
    )

    output.seek(0)

    return discord.File(
        fp=output,
        filename="welcome.png",
    )
