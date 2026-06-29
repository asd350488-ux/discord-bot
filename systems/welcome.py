# ==========================================
# 🌙 Moon Bot Welcome Card
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
# 🖼️ 圖片設定
# ==========================================

WIDTH = 1400
HEIGHT = 1000

BACKGROUND = "images/welcome_bg.png"
FONT = "fonts/NotoSansTC-Regular.ttf"

# ==========================================
# 📍 座標設定
# ==========================================

TITLE_X = 700
TITLE_Y = 110

WELCOME_X = 700
WELCOME_Y = 195

AVATAR_SIZE = 260

AVATAR_X = 570
AVATAR_Y = 280

NAME_X = 700
NAME_Y = 650

MEMBER_X = 1090
MEMBER_Y = 485

MEMBER_NO_Y = 560

LEFT_X = 300
LEFT_Y = 500

FOOTER_X = 700
FOOTER_Y = 900

MOONBOT_Y = 950

# ==========================================
# 🎨 顏色
# ==========================================

WHITE = (255, 255, 255)

PURPLE = (228, 200, 255)

GLOW = (205, 167, 255)

# ==========================================
# 🔤 字型
# ==========================================

TITLE_SIZE = 90
WELCOME_SIZE = 46
NAME_SIZE = 80
MEMBER_SIZE = 60
FOOTER_SIZE = 40


def load_font(size):

    return ImageFont.truetype(FONT, size)


def draw_glow_text(draw, position, text, font, fill, glow, anchor="mm"):

    x, y = position

    for ox in range(-2, 3):
        for oy in range(-2, 3):

            if ox == 0 and oy == 0:
                continue

            draw.text((x + ox, y + oy), text, font=font, fill=glow, anchor=anchor)

    draw.text(position, text, font=font, fill=fill, anchor=anchor)


async def download_avatar(member):

    async with aiohttp.ClientSession() as session:

        async with session.get(member.display_avatar.url) as resp:

            return Image.open(io.BytesIO(await resp.read())).convert("RGBA")

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
    # Discord 頭像
    # =====================

    avatar = await download_avatar(member)

    avatar = avatar.resize((AVATAR_SIZE, AVATAR_SIZE))

    # =====================
    # 圓形遮罩
    # =====================

    mask = Image.new("L", (AVATAR_SIZE, AVATAR_SIZE), 0)

    mask_draw = ImageDraw.Draw(mask)

    mask_draw.ellipse((0, 0, AVATAR_SIZE, AVATAR_SIZE), fill=255)

    # =====================
    # 貼上頭像
    # =====================

    bg.paste(avatar, (AVATAR_X, AVATAR_Y), mask)

    # =====================
    # 紫色外框
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
    footer_font = load_font(FOOTER_SIZE)

    # =====================
    # 名字自動縮放
    # =====================

    name_size = NAME_SIZE

    while True:

        name_font = load_font(name_size)

        bbox = draw.textbbox((0, 0), member.display_name, font=name_font)

        text_width = bbox[2] - bbox[0]

        if text_width <= 650:
            break

        name_size -= 2

        if name_size <= 40:
            break

    # =====================
    # 標題
    # =====================

    draw_glow_text(draw, (TITLE_X, TITLE_Y), "極 曜 月 葵", title_font, WHITE, GLOW)

    draw.text(
        (WELCOME_X, WELCOME_Y), "WELCOME", fill=PURPLE, font=welcome_font, anchor="mm"
    )

    # =====================
    # 玩家名稱
    # =====================

    draw_glow_text(draw, (NAME_X, NAME_Y), member.display_name, name_font, WHITE, GLOW)

    # =====================
    # MEMBER
    # =====================

    draw.text(
        (MEMBER_X, MEMBER_Y), "MEMBER", fill=PURPLE, font=footer_font, anchor="mm"
    )

    draw_glow_text(
        draw,
        (MEMBER_X, MEMBER_NO_Y),
        f"#{member.guild.member_count:03d}",
        member_font,
        WHITE,
        GLOW,
    )

    # =====================
    # 左側文字
    # =====================

    draw.text((LEFT_X, LEFT_Y), "歡迎加入", fill=PURPLE, font=footer_font, anchor="mm")

    draw.text(
        (LEFT_X, LEFT_Y + 55), "極曜月葵", fill=WHITE, font=footer_font, anchor="mm"
    )

    # =====================
    # Footer
    # =====================

    draw.text(
        (FOOTER_X, FOOTER_Y),
        "✨ 願星光照亮你的旅程。",
        fill=WHITE,
        font=footer_font,
        anchor="mm",
    )

    draw.text(
        (FOOTER_X, MOONBOT_Y), "Moon Bot v2", fill=PURPLE, font=footer_font, anchor="mm"
    )

    # =====================
    # 輸出圖片
    # =====================

    output = io.BytesIO()

    bg.save(output, format="PNG")

    output.seek(0)

    return discord.File(fp=output, filename="welcome.png")
