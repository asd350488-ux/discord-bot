# ==========================================
# 🌙 Moon Bot Welcome Card v4
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

# 頭像
AVATAR_SIZE = 250

AVATAR_X = WIDTH // 2 - AVATAR_SIZE // 2
AVATAR_Y = 210

# 資訊帶
INFO_LEFT = 50
INFO_RIGHT = WIDTH - 50

INFO_TOP = 180
INFO_BOTTOM = 850

# 中央文字
CENTER_X = WIDTH // 2

WELCOME_TEXT_Y = 610
MEMBER_Y = 675
QUOTE_Y = 730

# ==========================================
# 🎨 顏色
# ==========================================

WHITE = (255, 255, 255)

PURPLE = (226, 197, 255)

GLOW = (205, 167, 255)

# 玻璃資訊帶
INFO_FILL = (18, 18, 24, 165)

INFO_OUTLINE = (220, 200, 255, 55)

# ==========================================
# 🔤 字型
# ==========================================

TITLE_SIZE = 88

WELCOME_SIZE = 42

WELCOME_TEXT_SIZE = 60

MEMBER_SIZE = 40

QUOTE_SIZE = 30

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

    draw.text(
        position,
        text,
        font=font,
        fill=fill,
        anchor=anchor,
    )


# ==========================================
# 📥 Discord Avatar
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

    draw = ImageDraw.Draw(bg)

    # =====================
    # Discord Avatar
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
    # 中央玻璃資訊帶
    # =====================

    glass = Image.new(
        "RGBA",
        bg.size,
        (0, 0, 0, 0),
    )

    glass_draw = ImageDraw.Draw(glass)

    glass_draw.rounded_rectangle(
        (
            INFO_LEFT,
            INFO_TOP,
            INFO_RIGHT,
            INFO_BOTTOM,
        ),
        radius=38,
        fill=INFO_FILL,
        outline=INFO_OUTLINE,
        width=2,
    )

    bg = Image.alpha_composite(
        bg,
        glass,
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
    # 頭像外框
    # =====================

    draw.ellipse(
        (
            AVATAR_X - 6,
            AVATAR_Y - 6,
            AVATAR_X + AVATAR_SIZE + 6,
            AVATAR_Y + AVATAR_SIZE + 6,
        ),
        outline=PURPLE,
        width=5,
    )

    draw.ellipse(
        (
            AVATAR_X - 12,
            AVATAR_Y - 12,
            AVATAR_X + AVATAR_SIZE + 12,
            AVATAR_Y + AVATAR_SIZE + 12,
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
    quote_font = load_font(QUOTE_SIZE)

    # =====================
    # 歡迎文字字型（自動縮放）
    # =====================

    text_size = WELCOME_TEXT_SIZE

    while True:

        text_font = load_font(text_size)

        text = f"歡迎 {member.display_name} 加入極曜月葵"

        bbox = draw.textbbox(
            (0, 0),
            text,
            font=text_font,
        )

        width = bbox[2] - bbox[0]

        if width <= 1000:
            break

        text_size -= 2

        if text_size <= 42:
            break

    # =====================
    # 歡迎文字
    # =====================

    draw_glow_text(
        draw,
        (CENTER_X, WELCOME_TEXT_Y),
        text,
        text_font,
        WHITE,
        GLOW,
    )

    # =====================
    # Member
    # =====================

    draw.text(
        (CENTER_X, MEMBER_Y),
        f"Member #{member.guild.member_count:03d}",
        fill=PURPLE,
        font=member_font,
        anchor="mm",
    )

    # =====================
    # 願星光照亮你的旅程
    # =====================

    draw.text(
        (CENTER_X, QUOTE_Y),
        "願星光照亮你的旅程。",
        fill=WHITE,
        font=quote_font,
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
