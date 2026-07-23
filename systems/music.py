# ==========================
# 🌙 Moon Bot｜音樂系統
# ==========================

import discord
import asyncio
import random

from discord.ext import commands
from discord import app_commands
from discord import FFmpegPCMAudio

# ==========================
# 🎵 yt-dlp 設定
# ==========================

import yt_dlp

YTDL_OPTIONS = {

    "format": "bestaudio/best",

    "noplaylist": True,

    "quiet": True,

    "no_warnings": True,

    "default_search": "ytsearch",

    "source_address": "0.0.0.0",

}

FFMPEG_OPTIONS = {

    "before_options": (
        "-reconnect 1 "
        "-reconnect_streamed 1 "
        "-reconnect_delay_max 5"
    ),

    "options": "-vn",

}

# ==========================
# 🎵 YouTube 資訊解析
# ==========================

ytdl = yt_dlp.YoutubeDL(
    YTDL_OPTIONS
)

# ==========================
# 🎵 取得 YouTube 資料
# ==========================

async def get_youtube_data(
    keyword: str,
):

    loop = asyncio.get_running_loop()

    return await loop.run_in_executor(

        None,

        lambda: ytdl.extract_info(

            keyword,

            download=False,

        ),

    )
    
# ==========================
# 🎵 建立 Song
# ==========================

async def extract_song_info(

    keyword: str,

    requester=None,

):

    data = await get_youtube_data(
        keyword
    )

    if data is None:

        return None

    if "entries" in data:

        entries = data.get(
            "entries",
            [],
        )

        if not entries:

            return None

        data = entries[0]

    return Song(

        title=data.get(
            "title",
            "未知歌曲",
        ),

        url=data.get(
            "webpage_url",
            "",
        ),

        stream_url=data.get(
            "url",
            "",
        ),

        duration=data.get(
            "duration",
            0,
        ),

        thumbnail=data.get(
            "thumbnail",
            "",
        ),

        uploader=data.get(
            "uploader",
            "未知作者",
        ),

        webpage_url=data.get(
            "webpage_url",
            "",
        ),

        requester=requester,

    )

# ==========================
# 🎵 歌曲資料
# ==========================

class Song:

    def __init__(
        self,
        title: str,
        url: str,
        stream_url: str = "",
        duration: int = 0,
        thumbnail: str = "",
        uploader: str = "",
        webpage_url: str = "",
        requester: discord.Member | None = None,
    ):

        self.title = title

        self.url = url

        self.stream_url = stream_url

        self.duration = duration

        self.thumbnail = thumbnail

        self.uploader = uploader

        self.webpage_url = webpage_url

        self.requester = requester

    @property
    def duration_text(self):

        minutes = self.duration // 60

        seconds = self.duration % 60

        return f"{minutes:02}:{seconds:02}"

    @property
    def requester_name(self):

        if self.requester:

            return self.requester.display_name

        return "未知"

    @property
    def requester_avatar(self):

        if self.requester:

            return self.requester.display_avatar.url

        return None

# ==========================
# 📋 播放清單
# ==========================

class MusicQueue:

    def __init__(self):

        self.songs = []

    def add(
        self,
        song: Song,
    ):

        self.songs.append(song)

    def next(self):

        if not self.songs:
            return None

        return self.songs.pop(0)

    def clear(self):

        self.songs.clear()

    def shuffle(self):

        random.shuffle(self.songs)

    def __len__(self):

        return len(self.songs)

    def __iter__(self):

        return iter(self.songs)

    def peek(self):

        if not self.songs:
            return None

        return self.songs[0]

# ==========================
# 🎵 播放來源
# ==========================

class MusicSource:

    def __init__(
        self,
        song: Song,
    ):

        self.song = song

    def create_audio(self):

        return FFmpegPCMAudio(

            self.song.stream_url,

            **FFMPEG_OPTIONS,

        )

# ==========================
# 🎵 音樂播放器
# ==========================

class MusicPlayer:

    def __init__(self):

        self.guild_id = None

        self.queue = MusicQueue()

        self.current = None

        self.voice_client = None
        
        self.source = None
        
        self.panel_message = None

        self.text_channel = None

        self.volume = 50

        self.is_playing = False

        self.is_paused = False

        self.loop_one = False

        self.loop_queue = False

        self.shuffle = False

        self.now_playing_task = None

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

        song = player.current

        embed.add_field(
            name="🎵 目前播放",
            value=(
                f"**{song.title}**\n"
                f"👤 {song.uploader}\n"
                f"⏱️ {song.duration_text}\n"
                f"❤️ 點歌者：{song.requester_name}"
            ),
            inline=False,
        )

        if song.thumbnail:

            embed.set_thumbnail(
                url=song.thumbnail
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
# 🎵 設定目前播放歌曲
# ==========================

async def set_current_song(
    player: MusicPlayer,
    song: Song,
):

    player.current = song

    player.is_playing = True

    player.is_paused = False

    await update_music_panel(player)
    
# ==========================
# ⏹️ 清除目前播放
# ==========================

async def clear_current_song(
    player: MusicPlayer,
):

    player.current = None

    player.is_playing = False

    player.is_paused = False

    await update_music_panel(player)
        
# ==========================
# ▶️ 播放歌曲
# ==========================

async def play_song(

    player: MusicPlayer,

    song: Song,

):

    if player.voice_client is None:

        return False

    player.source = MusicSource(
        song
    )

    player.voice_client.play(

        player.source.create_audio(),

    )

    await set_current_song(

        player,

        song,

    )

    return True
    
# ==========================
# ▶️ 啟動播放器
# ==========================

async def start_player(

    player: MusicPlayer,

):

    if player.voice_client is None:

        return

    if player.voice_client.is_playing():

        return

    if player.voice_client.is_paused():

        return

    song = player.queue.next()

    if song is None:

        await clear_current_song(
            player
        )

        return

    await play_song(

        player,

        song,

    )

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
    
