# ==========================
# 🌙 Moon Bot｜音樂系統
# ==========================

import discord
import asyncio

from discord.ext import commands
from discord import app_commands

# ==========================
# 🎵 音樂播放器
# ==========================

class MusicPlayer:

    def __init__(self):

        self.queue = []

        self.current = None

        self.volume = 50

        self.voice_client = None

        self.panel_message = None

        self.text_channel = None

        self.is_playing = False


music_players = {}

# ==========================
# 🎵 播放歌曲 Modal
# ==========================

class PlayMusicModal(
    discord.ui.Modal,
    title="🎵 播放歌曲"
):

    keyword = discord.ui.TextInput(
        label="歌曲名稱或 YouTube 連結",
        placeholder="例如：YOASOBI Idol 或 https://youtu.be/......",
        required=True,
        max_length=200,
    )

    async def on_submit(
        self,
        interaction: discord.Interaction,
    ):

        await interaction.response.send_message(
            f"🎵 你輸入了：{self.keyword.value}",
            ephemeral=True,
        )

# ==========================
# 🎵 音樂控制面板
# ==========================

class MusicPanelView(discord.ui.View):

    def __init__(self):

        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎵 播放歌曲",
        style=discord.ButtonStyle.success,
        row=0,
    )
    async def play_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        await interaction.response.send_modal(
            PlayMusicModal()
        )

    @discord.ui.button(
        label="📋 播放清單",
        style=discord.ButtonStyle.secondary,
        row=0,
    )
    async def queue_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        await interaction.response.send_message(
            "📋 播放清單功能開發中...",
            ephemeral=True,
        )

    @discord.ui.button(
        label="🎶 目前播放",
        style=discord.ButtonStyle.primary,
        row=0,
    )
    async def current_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        await interaction.response.send_message(
            "🎶 目前沒有播放任何歌曲。",
            ephemeral=True,
        )

# ==========================
# 🎵 建立音樂控制面板
# ==========================

def create_music_embed(player: MusicPlayer):

    embed = discord.Embed(
        title="🌙 Moon Music｜音樂控制中心",
        color=0xC77DFF,
    )

    if player.current:

        embed.add_field(
            name="🎵 目前播放",
            value=player.current,
            inline=False,
        )

    else:

        embed.add_field(
            name="🎵 目前播放",
            value="尚未播放任何歌曲",
            inline=False,
        )

    embed.add_field(
        name="📋 播放清單",
        value=f"{len(player.queue)} 首",
        inline=True,
    )

    embed.add_field(
        name="🔊 音量",
        value=f"{player.volume}%",
        inline=True,
    )

    if player.voice_client:

        status = "🟢 已連接語音頻道"

    else:

        status = "🔴 尚未加入語音頻道"

    embed.add_field(
        name="🎧 狀態",
        value=status,
        inline=False,
    )

    embed.set_footer(
        text="Moon Bot v2｜Music System"
    )

    return embed
    
# ==========================
# 🔄 更新音樂控制面板
# ==========================

async def update_music_panel(player: MusicPlayer):

    if (
        player.panel_message is None
        or player.text_channel is None
    ):
        return

    embed = create_music_embed(player)

    try:

        await player.panel_message.edit(
            embed=embed,
            view=MusicPanelView(),
        )

    except discord.NotFound:

        player.panel_message = None

    except discord.HTTPException:

        pass
        
# ==========================
# 🌙 建立音樂控制面板
# ==========================

@app_commands.command(
    name="音樂面板",
    description="建立 Moon Music 控制面板",
)
async def music_panel(
    interaction: discord.Interaction,
):

    guild_id = interaction.guild.id

    if guild_id not in music_players:

        music_players[guild_id] = MusicPlayer()

    player = music_players[guild_id]

    player.text_channel = interaction.channel

    embed = create_music_embed(player)

    message = await interaction.channel.send(
        embed=embed,
        view=MusicPanelView(),
    )

    player.panel_message = message

    await interaction.response.send_message(
        "✅ Moon Music 控制面板建立完成！",
        ephemeral=True,
    )
    
# ==========================
# 🌙 Moon Music Cog
# ==========================

class Music(commands.Cog):

    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot

    @app_commands.command(
        name="音樂面板",
        description="建立 Moon Music 控制面板",
    )
    async def music_panel(
        self,
        interaction: discord.Interaction,
    ):

        guild_id = interaction.guild.id

        if guild_id not in music_players:
            music_players[guild_id] = MusicPlayer()

        player = music_players[guild_id]

        player.text_channel = interaction.channel

        embed = create_music_embed(player)

        message = await interaction.channel.send(
            embed=embed,
            view=MusicPanelView(),
        )

        player.panel_message = message

        await interaction.response.send_message(
            "✅ Moon Music 控制面板建立完成！",
            ephemeral=True,
        )