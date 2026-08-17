import discord
from discord import app_commands

from config import BOT_ADMINS


# ==========================
# 💌 媽咪專屬身分組設定
# ==========================

MOMMY_ROLES = {
    "小貓媽咪的小月牙": 1513814405585047622,
    "韓馨媽咪的小極光": 1513815160047796375,
    "星弦媽咪的小太陽": 1513815300594991154,
    "曦璃媽咪的向日葵": 1513815485135720469,
}


# ==========================
# 💌 媽咪身分組按鈕
# ==========================


class MommyRoleButton(discord.ui.Button):

    def __init__(
        self,
        role_name: str,
        role_id: int,
        custom_id: str,
        row: int,
    ):
        self.role_name = role_name
        self.role_id = role_id

        super().__init__(
            label=role_name,
            emoji="📩",
            style=discord.ButtonStyle.primary,
            custom_id=custom_id,
            row=row,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):

        # ==========================
        # 💌 檢查伺服器
        # ==========================

        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ 此功能只能在伺服器內使用。",
                ephemeral=True,
            )
            return

        # ==========================
        # 💌 找身分組
        # ==========================

        role = interaction.guild.get_role(self.role_id)

        if role is None:
            await interaction.response.send_message(
                f"❌ 找不到「{self.role_name}」身分組，請聯絡管理員。",
                ephemeral=True,
            )
            return

        # ==========================
        # 💌 找成員
        # ==========================

        member = interaction.guild.get_member(
            interaction.user.id
        )

        if member is None:
            try:
                member = await interaction.guild.fetch_member(
                    interaction.user.id
                )
            except Exception:
                await interaction.response.send_message(
                    "❌ 無法取得你的成員資料，請稍後再試。",
                    ephemeral=True,
                )
                return

        try:

            # ==========================
            # 💌 已有身分組 → 移除
            # ==========================

            if role in member.roles:

                await member.remove_roles(role)

                await interaction.response.send_message(
                    f"📩 已取消 **{self.role_name}**",
                    ephemeral=True,
                )

            # ==========================
            # 💌 沒有身分組 → 領取
            # ==========================

            else:

                await member.add_roles(role)

                await interaction.response.send_message(
                    f"📩 已取得 **{self.role_name}**",
                    ephemeral=True,
                )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Bot 沒有管理這個身分組的權限。\n"
                "請確認 Bot 的身分組位置高於這四個身分組。",
                ephemeral=True,
            )

        except Exception as e:

            print(
                f"❌ 媽咪身分組操作錯誤：{e}"
            )

            await interaction.response.send_message(
                "❌ 身分組操作失敗，請稍後再試。",
                ephemeral=True,
            )


# ==========================
# 💌 媽咪身分組面板
# ==========================


class MommyRoleView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

        # 第一排
        self.add_item(
            MommyRoleButton(
                "小貓媽咪的小月牙",
                MOMMY_ROLES["小貓媽咪的小月牙"],
                "mommy_role_cat",
                row=0,
            )
        )

        self.add_item(
            MommyRoleButton(
                "韓馨媽咪的小極光",
                MOMMY_ROLES["韓馨媽咪的小極光"],
                "mommy_role_hanxin",
                row=0,
            )
        )

        self.add_item(
            MommyRoleButton(
                "星弦媽咪的小太陽",
                MOMMY_ROLES["星弦媽咪的小太陽"],
                "mommy_role_xingxian",
                row=0,
            )
        )

        # 第二排
        self.add_item(
            MommyRoleButton(
                "曦璃媽咪的向日葵",
                MOMMY_ROLES["曦璃媽咪的向日葵"],
                "mommy_role_xili",
                row=1,
            )
        )


# ==========================
# 💌 發送媽咪身分組面板
# ==========================


async def mommy_role_panel(
    interaction: discord.Interaction,
):

    # ==========================
    # 💌 管理員限制
    # ==========================

    if interaction.user.id not in BOT_ADMINS:

        await interaction.response.send_message(
            "❌ 只有管理員可以使用此指令。",
            ephemeral=True,
        )
        return

    # ==========================
    # 💌 Embed
    # ==========================

    embed = discord.Embed(
        title="💌 媽咪專屬身分組",
        description=(
            "請看完以上規範後 🌱\n"
            "在下面按鈕領取各媽咪專屬頻道角色！\n\n"
            "📩 **可以複選喔！**\n"
            "📩 點擊按鈕即可領取身分組\n"
            "📩 再次點擊即可取消身分組"
        ),
        color=discord.Color.blurple(),
    )

    embed.add_field(
        name="🌙 可選擇的專屬身分組",
        value=(
            "📩 **小貓媽咪的小月牙**\n"
            "📩 **韓馨媽咪的小極光**\n"
            "📩 **星弦媽咪的小太陽**\n"
            "📩 **曦璃媽咪的向日葵**"
        ),
        inline=False,
    )

    embed.set_footer(
        text="🌙 Moon Bot ・ 媽咪專屬身分組系統"
    )

    # ==========================
    # 💌 發送面板
    # ==========================

    await interaction.response.send_message(
        embed=embed,
        view=MommyRoleView(),
    )


# ==========================
# 💌 系統初始化
# ==========================

_initialized = False


def setup_mommy_roles(bot):

    global _initialized

    if _initialized:
        return

    # ==========================
    # 💌 註冊永久 View
    # ==========================

    bot.add_view(
        MommyRoleView()
    )

    # ==========================
    # 💌 註冊 Slash Command
    # ==========================

    command = app_commands.Command(
        name="媽咪身分組",
        description="發送媽咪專屬身分組面板",
        callback=mommy_role_panel,
    )

    bot.tree.add_command(command)

    _initialized = True

    print("✅ 媽咪身分組系統已載入")