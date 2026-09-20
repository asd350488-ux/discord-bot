# -*- coding: utf-8 -*-

# ==========================
# 🌙 Moon Bot｜音樂系統
# ==========================

import asyncio
import random
import sqlite3
from pathlib import Path

import discord
from discord import app_commands
import yt_dlp


# ==========================
# 🎵 yt-dlp 設定
# ==========================

# yt-dlp 目前的 YouTube 完整解析需要 EJS + JavaScript runtime。
# Render 會由 build script 安裝 Deno；這裡自動尋找 Deno 路徑。
DENO_CANDIDATES = [
    str(Path.cwd() / ".deno" / "bin" / "deno"),
    str(Path(__file__).resolve().parents[1] / ".deno" / "bin" / "deno"),
    "/opt/render/project/src/.deno/bin/deno",
    "/root/.deno/bin/deno",
    "/usr/local/bin/deno",
    "/usr/bin/deno",
]

DENO_PATH = next(
    (path for path in DENO_CANDIDATES if Path(path).is_file()),
    None,
)

YTDL_OPTIONS = {

    "format": "bestaudio/best",

    "noplaylist": True,

    "quiet": True,

    "no_warnings": False,

    "verbose": False,

    "default_search": "ytsearch",

    "source_address": "0.0.0.0",

    "extract_flat": False,

    # YouTube EJS challenge solver。
    "remote_components": {"ejs:github"},

}

if DENO_PATH:
    YTDL_OPTIONS["js_runtimes"] = {
        "deno": {
            "path": DENO_PATH,
        },
    }

FFMPEG_OPTIONS = {

    "before_options": (
        "-reconnect 1 "
        "-reconnect_streamed 1 "
        "-reconnect_delay_max 5"
    ),

    "options": "-vn",

}

ytdl = yt_dlp.YoutubeDL(
    YTDL_OPTIONS
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
        requester=None,
    ):

        self.title = title
        self.url = url
        self.stream_url = stream_url
        self.duration = duration or 0
        self.thumbnail = thumbnail
        self.uploader = uploader
        self.webpage_url = webpage_url or url
        self.requester = requester

    @property
    def duration_text(self):

        if self.duration <= 0:
            return "未知"

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

    def peek(self):

        if not self.songs:
            return None

        return self.songs[0]

    def remove(
        self,
        index: int,
    ):

        if index < 0 or index >= len(self.songs):
            return None

        return self.songs.pop(index)

    def __len__(self):

        return len(self.songs)

    def __iter__(self):

        return iter(self.songs)


# ==========================
# 🎵 音樂播放器
# ==========================

class MusicPlayer:

    def __init__(self):

        self.guild_id = None

        self.queue = MusicQueue()

        self.current = None

        self.volume = 50

        self.voice_client = None

        self.source = None

        self.panel_message = None

        self.text_channel = None

        self.is_playing = False

        self.is_paused = False

        self.loop_one = False

        self.loop_queue = False

        self.shuffle = False

        self.after_task = None

        self.disconnect_task = None

        self.play_token = 0


music_players = {}


# ==========================
# 🎵 YouTube 資訊解析
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


async def extract_song_info(
    keyword: str,
    requester=None,
):

    try:

        data = await get_youtube_data(
            keyword
        )

    except Exception as e:

        print(
            f"[Moon Music] yt-dlp 解析失敗：{type(e).__name__}: {e}"
        )

        return None

    if not data:
        return None

    if "entries" in data:

        entries = data.get(
            "entries",
            [],
        )

        entries = [
            entry
            for entry in entries
            if entry
        ]

        if not entries:
            return None

        data = entries[0]

    webpage_url = data.get(
        "webpage_url",
        "",
    )

    stream_url = data.get(
        "url",
        "",
    )

    if not webpage_url:
        webpage_url = data.get(
            "original_url",
            "",
        )

    if not stream_url:
        return None

    return Song(

        title=data.get(
            "title",
            "未知歌曲",
        ),

        url=webpage_url,

        stream_url=stream_url,

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

        webpage_url=webpage_url,

        requester=requester,

    )


# ==========================
# 🎵 播放來源
# ==========================

class MusicSource:

    def __init__(
        self,
        song: Song,
        volume: int = 50,
    ):

        self.song = song

        self.volume = max(
            0,
            min(
                100,
                volume,
            ),
        )

    def create_audio(self):

        audio = discord.FFmpegPCMAudio(

            self.song.stream_url,

            **FFMPEG_OPTIONS,

        )

        return discord.PCMVolumeTransformer(
            audio,
            volume=self.volume / 100,
        )


# ==========================
# 🎵 重新取得串流網址
# ==========================

async def refresh_song_stream(
    song: Song,
):

    try:

        data = await get_youtube_data(
            song.webpage_url
        )

    except Exception:

        return False

    if not data:
        return False

    if "entries" in data:

        entries = data.get(
            "entries",
            [],
        )

        if not entries:
            return False

        data = entries[0]

    stream_url = data.get(
        "url",
        "",
    )

    if not stream_url:
        return False

    song.stream_url = stream_url

    return True


# ==========================
# 🎵 建立音樂 Embed
# ==========================

def create_music_embed(
    player: MusicPlayer,
):

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

    else:

        embed.add_field(
            name="🎵 目前播放",
            value="尚未播放任何歌曲",
            inline=False,
        )

    queue_preview = []

    for index, song in enumerate(
        player.queue.songs[:5],
        start=1,
    ):

        queue_preview.append(
            f"`{index}.` {song.title}"
        )

    if queue_preview:

        queue_text = "\n".join(
            queue_preview
        )

        if len(player.queue) > 5:

            queue_text += (
                f"\n…還有 "
                f"{len(player.queue) - 5} 首"
            )

    else:

        queue_text = "目前沒有待播歌曲"

    embed.add_field(
        name="📋 播放清單",
        value=queue_text,
        inline=False,
    )

    embed.add_field(
        name="🔊 音量",
        value=f"{player.volume}%",
        inline=True,
    )

    if player.loop_one:

        loop_text = "🔂 單曲循環"

    elif player.loop_queue:

        loop_text = "🔁 歌單循環"

    else:

        loop_text = "➡️ 一般播放"

    embed.add_field(
        name="🔁 播放模式",
        value=loop_text,
        inline=True,
    )

    if player.shuffle:

        shuffle_text = "🔀 已開啟"

    else:

        shuffle_text = "➡️ 關閉"

    embed.add_field(
        name="🎲 隨機",
        value=shuffle_text,
        inline=True,
    )

    if player.voice_client:

        if player.voice_client.is_paused():

            status = "⏸️ 已暫停"

        elif player.voice_client.is_playing():

            status = "🟢 播放中"

        else:

            status = "🟡 已連接"

    else:

        status = "🔴 尚未加入語音頻道"

    embed.add_field(
        name="🎧 狀態",
        value=status,
        inline=False,
    )

    embed.set_footer(
        text="Moon Bot v2｜Moon Music"
    )

    return embed


# ==========================
# 🔄 更新音樂控制面板
# ==========================

async def update_music_panel(
    player: MusicPlayer,
):

    if (
        player.panel_message is None
        or player.text_channel is None
    ):

        return

    embed = create_music_embed(
        player
    )

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

    await update_music_panel(
        player
    )


# ==========================
# ⏹️ 清除目前播放
# ==========================

async def clear_current_song(
    player: MusicPlayer,
):

    player.current = None

    player.source = None

    player.is_playing = False

    player.is_paused = False

    await update_music_panel(
        player
    )


# ==========================
# ▶️ 播放歌曲
# ==========================

async def play_song(
    player: MusicPlayer,
    song: Song,
):

    if player.voice_client is None:
        return False

    if not player.voice_client.is_connected():
        return False

    if player.voice_client.is_playing():

        player.voice_client.stop()

    if not song.stream_url:

        success = await refresh_song_stream(
            song
        )

        if not success:
            return False

    player.source = MusicSource(
        song,
        player.volume,
    )

    player.play_token += 1

    token = player.play_token

    loop = asyncio.get_running_loop()

    def after_play(error):

        asyncio.run_coroutine_threadsafe(
            handle_song_finished(
                player,
                token,
                error,
            ),
            loop,
        )

    try:

        player.voice_client.play(

            player.source.create_audio(),

            after=after_play,

        )

    except Exception:

        player.source = None

        return False

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

    if not player.voice_client.is_connected():
        return

    if player.voice_client.is_playing():
        return

    if player.voice_client.is_paused():
        return

    if player.current is not None:
        return

    song = player.queue.next()

    if song is None:

        await clear_current_song(
            player
        )

        return

    success = await play_song(
        player,
        song,
    )

    if not success:

        await clear_current_song(
            player
        )

        await start_player(
            player
        )


# ==========================
# ⏭️ 播放下一首
# ==========================

async def play_next(
    player: MusicPlayer,
):

    if player.voice_client is None:
        return

    if not player.voice_client.is_connected():
        return

    next_song = None

    if player.current:

        finished_song = player.current

        if player.loop_one:

            next_song = finished_song

        elif player.loop_queue:

            player.queue.add(
                finished_song
            )

    if next_song is None:

        next_song = player.queue.next()

    if next_song is None:

        await clear_current_song(
            player
        )

        return

    success = await play_song(
        player,
        next_song,
    )

    if not success:

        await clear_current_song(
            player
        )

        await play_next(
            player
        )


# ==========================
# 🎵 播放完成處理
# ==========================

async def handle_song_finished(
    player: MusicPlayer,
    token: int,
    error=None,
):

    if token != player.play_token:
        return

    player.is_playing = False
    player.is_paused = False
    player.source = None

    if error:

        print(
            f"[Moon Music] 播放錯誤：{error}"
        )

    await play_next(
        player
    )


# ==========================
# ⏸️ 暫停
# ==========================

async def pause_player(
    player: MusicPlayer,
):

    if (
        player.voice_client
        and player.voice_client.is_playing()
    ):

        player.voice_client.pause()

        player.is_paused = True
        player.is_playing = False

        await update_music_panel(
            player
        )

        return True

    return False


# ==========================
# ▶️ 繼續
# ==========================

async def resume_player(
    player: MusicPlayer,
):

    if (
        player.voice_client
        and player.voice_client.is_paused()
    ):

        player.voice_client.resume()

        player.is_paused = False
        player.is_playing = True

        await update_music_panel(
            player
        )

        return True

    return False


# ==========================
# ⏭️ 跳過
# ==========================

async def skip_player(
    player: MusicPlayer,
):

    if (
        player.voice_client is None
        or not player.voice_client.is_connected()
    ):

        return False

    if not player.voice_client.is_playing() and not player.voice_client.is_paused():
        return False

    player.play_token += 1

    player.current = None
    player.is_playing = False
    player.is_paused = False

    player.voice_client.stop()

    await play_next(
        player
    )

    await update_music_panel(
        player
    )

    return True


# ==========================
# ⏹️ 停止
# ==========================

async def stop_player(
    player: MusicPlayer,
):

    player.play_token += 1

    if player.voice_client:

        if (
            player.voice_client.is_playing()
            or player.voice_client.is_paused()
        ):

            player.voice_client.stop()

    player.queue.clear()

    player.current = None

    player.source = None

    player.is_playing = False

    player.is_paused = False

    await update_music_panel(
        player
    )


# ==========================
# 🔊 設定音量
# ==========================

async def set_volume(
    player: MusicPlayer,
    volume: int,
):

    volume = max(
        0,
        min(
            100,
            int(volume),
        ),
    )

    player.volume = volume

    if (
        player.source
        and isinstance(
            player.source,
            MusicSource,
        )
    ):

        pass

    await update_music_panel(
        player
    )


# ==========================
# 🔀 隨機播放
# ==========================

async def shuffle_queue(
    player: MusicPlayer,
):

    player.shuffle = True

    player.queue.shuffle()

    await update_music_panel(
        player
    )


# ==========================
# 🔁 切換循環模式
# ==========================

async def toggle_loop(
    player: MusicPlayer,
):

    if player.loop_one:

        player.loop_one = False
        player.loop_queue = True

    elif player.loop_queue:

        player.loop_queue = False
        player.loop_one = False

    else:

        player.loop_one = True

    await update_music_panel(
        player
    )


# ==========================
# 🎲 套用隨機播放
# ==========================

async def apply_shuffle(
    player: MusicPlayer,
):

    if not player.shuffle:
        return

    player.queue.shuffle()


# ==========================
# 🔌 取得或建立 Player
# ==========================

def get_music_player(
    guild_id: int,
):

    if guild_id not in music_players:

        player = MusicPlayer()

        player.guild_id = guild_id

        music_players[guild_id] = player

    return music_players[guild_id]


# ==========================
# 🎵 播放歌曲 Modal
# ==========================

class PlayMusicModal(
    discord.ui.Modal,
    title="🎵 播放歌曲",
):

    keyword = discord.ui.TextInput(
        label="歌曲名稱或 YouTube 連結",
        placeholder=(
            "例如：YOASOBI Idol "
            "或 YouTube 連結"
        ),
        required=True,
        max_length=200,
    )

    async def on_submit(
        self,
        interaction: discord.Interaction,
    ):

        await interaction.response.defer(
            ephemeral=True
        )

        if interaction.guild is None:

            await interaction.followup.send(
                "❌ 這個功能只能在伺服器使用。",
                ephemeral=True,
            )

            return

        if not interaction.user.voice:

            await interaction.followup.send(
                "❌ 請先加入語音頻道。",
                ephemeral=True,
            )

            return

        guild_id = interaction.guild.id

        player = get_music_player(
            guild_id
        )

        voice_channel = interaction.user.voice.channel

        if player.voice_client is None:

            try:

                player.voice_client = await voice_channel.connect()

            except Exception as error:

                await interaction.followup.send(
                    f"❌ 無法加入語音頻道：{error}",
                    ephemeral=True,
                )

                return

        elif (
            player.voice_client.channel.id
            != voice_channel.id
        ):

            try:

                await player.voice_client.move_to(
                    voice_channel
                )

            except Exception:

                await interaction.followup.send(
                    "❌ 無法切換到你的語音頻道。",
                    ephemeral=True,
                )

                return

        player.text_channel = interaction.channel

        song = await extract_song_info(
            self.keyword.value.strip(),
            requester=interaction.user,
        )

        if song is None:

            await interaction.followup.send(
                "❌ 找不到這首歌曲，請確認名稱或 YouTube 連結。",
                ephemeral=True,
            )

            return

        player.queue.add(
            song
        )

        await apply_shuffle(
            player
        )

        was_playing = (
            player.voice_client.is_playing()
            or player.voice_client.is_paused()
            or player.current is not None
        )

        await start_player(
            player
        )

        if was_playing:

            message = (
                f"📋 已加入播放清單：\n"
                f"**{song.title}**\n"
                f"目前前方還有 "
                f"{len(player.queue)} 首歌曲。"
            )

        else:

            message = (
                f"🎵 開始播放：\n"
                f"**{song.title}**"
            )

        await interaction.followup.send(
            message,
            ephemeral=True,
        )


# ==========================
# 🎵 音樂控制面板
# ==========================

class MusicPanelView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="🎵 播放歌曲",
        custom_id="moon_music_play",
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
        label="⏯️ 暫停 / 繼續",
        custom_id="moon_music_pause",
        style=discord.ButtonStyle.primary,
        row=0,
    )
    async def pause_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ 只能在伺服器使用。",
                ephemeral=True,
            )

            return

        player = get_music_player(
            interaction.guild.id
        )

        if player.voice_client is None:

            await interaction.response.send_message(
                "❌ 目前沒有連接語音頻道。",
                ephemeral=True,
            )

            return

        if player.voice_client.is_playing():

            success = await pause_player(
                player
            )

            message = (
                "⏸️ 音樂已暫停。"
                if success
                else "❌ 暫停失敗。"
            )

        elif player.voice_client.is_paused():

            success = await resume_player(
                player
            )

            message = (
                "▶️ 音樂已繼續播放。"
                if success
                else "❌ 無法繼續播放。"
            )

        else:

            message = "❌ 目前沒有正在播放的歌曲。"

        await interaction.response.send_message(
            message,
            ephemeral=True,
        )

    @discord.ui.button(
        label="⏭️ 跳過",
        custom_id="moon_music_skip",
        style=discord.ButtonStyle.secondary,
        row=0,
    )
    async def skip_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ 只能在伺服器使用。",
                ephemeral=True,
            )

            return

        player = get_music_player(
            interaction.guild.id
        )

        success = await skip_player(
            player
        )

        if success:

            message = "⏭️ 已跳過目前歌曲。"

        else:

            message = "❌ 目前沒有可以跳過的歌曲。"

        await interaction.response.send_message(
            message,
            ephemeral=True,
        )

    @discord.ui.button(
        label="⏹️ 停止",
        custom_id="moon_music_stop",
        style=discord.ButtonStyle.danger,
        row=0,
    )
    async def stop_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ 只能在伺服器使用。",
                ephemeral=True,
            )

            return

        player = get_music_player(
            interaction.guild.id
        )

        await stop_player(
            player
        )

        await interaction.response.send_message(
            "⏹️ 已停止播放並清空播放清單。",
            ephemeral=True,
        )

    @discord.ui.button(
        label="📋 播放清單",
        custom_id="moon_music_queue",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def queue_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ 只能在伺服器使用。",
                ephemeral=True,
            )

            return

        player = get_music_player(
            interaction.guild.id
        )

        if not player.queue.songs:

            await interaction.response.send_message(
                "📋 目前播放清單是空的。",
                ephemeral=True,
            )

            return

        lines = []

        for index, song in enumerate(
            player.queue.songs[:15],
            start=1,
        ):

            lines.append(
                f"`{index}.` {song.title}"
            )

        if len(player.queue) > 15:

            lines.append(
                f"\n…還有 "
                f"{len(player.queue) - 15} 首"
            )

        embed = discord.Embed(
            title="📋 Moon Music｜播放清單",
            description="\n".join(lines),
            color=0xC77DFF,
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    @discord.ui.button(
        label="🎶 目前播放",
        custom_id="moon_music_current",
        style=discord.ButtonStyle.primary,
        row=1,
    )
    async def current_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ 只能在伺服器使用。",
                ephemeral=True,
            )

            return

        player = get_music_player(
            interaction.guild.id
        )

        if player.current is None:

            await interaction.response.send_message(
                "🎶 目前沒有播放任何歌曲。",
                ephemeral=True,
            )

            return

        song = player.current

        embed = discord.Embed(
            title="🎶 目前播放",
            description=f"**{song.title}**",
            color=0xC77DFF,
        )

        embed.add_field(
            name="👤 作者",
            value=song.uploader or "未知",
            inline=True,
        )

        embed.add_field(
            name="⏱️ 長度",
            value=song.duration_text,
            inline=True,
        )

        embed.add_field(
            name="❤️ 點歌者",
            value=song.requester_name,
            inline=True,
        )

        if song.thumbnail:

            embed.set_thumbnail(
                url=song.thumbnail
            )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    @discord.ui.button(
        label="🔀 隨機",
        custom_id="moon_music_shuffle",
        style=discord.ButtonStyle.secondary,
        row=2,
    )
    async def shuffle_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ 只能在伺服器使用。",
                ephemeral=True,
            )

            return

        player = get_music_player(
            interaction.guild.id
        )

        if len(player.queue) < 2:

            await interaction.response.send_message(
                "❌ 播放清單至少需要 2 首歌曲才能隨機。",
                ephemeral=True,
            )

            return

        player.shuffle = not player.shuffle

        if player.shuffle:

            player.queue.shuffle()

            message = "🔀 已開啟隨機播放。"

        else:

            message = "➡️ 已關閉隨機播放。"

        await update_music_panel(
            player
        )

        await interaction.response.send_message(
            message,
            ephemeral=True,
        )

    @discord.ui.button(
        label="🔁 循環",
        custom_id="moon_music_loop",
        style=discord.ButtonStyle.secondary,
        row=2,
    )
    async def loop_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ 只能在伺服器使用。",
                ephemeral=True,
            )

            return

        player = get_music_player(
            interaction.guild.id
        )

        await toggle_loop(
            player
        )

        if player.loop_one:

            message = "🔂 已切換為單曲循環。"

        elif player.loop_queue:

            message = "🔁 已切換為歌單循環。"

        else:

            message = "➡️ 已關閉循環播放。"

        await interaction.response.send_message(
            message,
            ephemeral=True,
        )

    @discord.ui.button(
        label="🔊 音量",
        custom_id="moon_music_volume",
        style=discord.ButtonStyle.secondary,
        row=2,
    )
    async def volume_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        await interaction.response.send_modal(
            VolumeModal()
        )


# ==========================
# 🔊 音量 Modal
# ==========================

class VolumeModal(
    discord.ui.Modal,
    title="🔊 調整音量",
):

    volume = discord.ui.TextInput(
        label="音量 0～100",
        placeholder="例如：50",
        required=True,
        max_length=3,
    )

    async def on_submit(
        self,
        interaction: discord.Interaction,
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ 只能在伺服器使用。",
                ephemeral=True,
            )

            return

        try:

            value = int(
                self.volume.value
            )

        except ValueError:

            await interaction.response.send_message(
                "❌ 請輸入 0～100 的數字。",
                ephemeral=True,
            )

            return

        if value < 0 or value > 100:

            await interaction.response.send_message(
                "❌ 音量只能設定在 0～100。",
                ephemeral=True,
            )

            return

        player = get_music_player(
            interaction.guild.id
        )

        await set_volume(
            player,
            value,
        )

        await interaction.response.send_message(
            f"🔊 音量已設定為 **{value}%**。",
            ephemeral=True,
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

    if interaction.guild is None:

        await interaction.response.send_message(
            "❌ 這個功能只能在伺服器使用。",
            ephemeral=True,
        )

        return

    guild_id = interaction.guild.id

    player = get_music_player(
        guild_id
    )

    player.text_channel = interaction.channel

    embed = create_music_embed(
        player
    )

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
# 🌙 啟動音樂系統
# ==========================

def setup_music(
    bot,
):

    bot.tree.add_command(
        music_panel
    )

    bot.add_view(
        MusicPanelView()
    )
