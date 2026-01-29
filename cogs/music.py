import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

import discord
from discord.ext import commands
from dotenv import load_dotenv

try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
except ImportError:
    spotipy = None

import yt_dlp

from utils.components import MusicPlayerView

load_dotenv()

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

YTDL_OPTS = {
    "format": "bestaudio[ext=webm]/bestaudio/best",
    "quiet": True,
    "noplaylist": False,
    "playlistend": 100,
    "default_search": "ytsearch",
    "skip_download": True,
    "no_warnings": True,
    "ignoreerrors": True,
}


def _build_spotify_client() -> Optional[Any]:
    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
    if not client_id or not client_secret or spotipy is None:
        return None
    return spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret))


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ytdl = yt_dlp.YoutubeDL(YTDL_OPTS)
        self.spotify = _build_spotify_client()
        self.queues: Dict[int, List[Dict[str, Any]]] = {}
        self.current: Dict[int, Dict[str, Any]] = {}

    async def cog_unload(self):
        for vc in self.bot.voice_clients:
            try:
                await vc.disconnect()
            except Exception:
                pass

    # ===== UTILITIES =====

    def _is_spotify_track(self, query: str) -> bool:
        q = query.strip().lower()
        if q.startswith("spotify:track:"):
            return True
        return "open.spotify.com" in q and "/track/" in q
    
    def _is_spotify_playlist(self, query: str) -> bool:
        q = query.strip().lower()
        if q.startswith("spotify:playlist:"):
            return True
        return "open.spotify.com" in q and "/playlist/" in q

    async def _spotify_to_query(self, url: str) -> str:
        if not self.spotify:
            return url
        try:
            track_id = url.split("track/")[-1].split("?")[0] if "track/" in url else url.split(":")[-1]
            data = self.spotify.track(track_id)
            name = data.get("name")
            artists = ", ".join(a["name"] for a in data.get("artists", []))
            return f"{name} {artists} audio"
        except Exception:
            logging.exception("Spotify fallback")
            return url
    
    async def _spotify_playlist_to_queries(self, url: str) -> List[str]:
        if not self.spotify:
            raise ValueError("Spotify credentials not configured. Set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET in .env")
        
        try:
            playlist_id = url.split("playlist/")[-1].split("?")[0] if "playlist/" in url else url.split(":")[-1]
            results = self.spotify.playlist_tracks(playlist_id, limit=100)
            tracks = results["items"]
            
            queries = []
            for item in tracks:
                if item and item.get("track"):
                    track = item["track"]
                    name = track.get("name", "")
                    artists = ", ".join(a["name"] for a in track.get("artists", []))
                    queries.append(f"{name} {artists} audio")
            
            return queries
        except Exception:
            logging.exception("Spotify playlist error")
            raise ValueError("Could not fetch Spotify playlist. Check the link and credentials.")

    async def _extract_info(self, search: str) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        
        if "youtube.com/watch" in search or "youtu.be" in search:
            search = search.split("&list=")[0]
        
        return await loop.run_in_executor(None, lambda: self.ytdl.extract_info(search, download=False))

    async def _resolve_track(self, query: str) -> List[Dict[str, Any]]:
        if self._is_spotify_track(query):
            query = await self._spotify_to_query(query)
        info = await self._extract_info(query)
        
        if "entries" in info:
            tracks = []
            for entry in info["entries"]:
                if entry and entry.get("url") and entry.get("title"):
                    tracks.append({
                        "title": entry.get("title", "Unknown"),
                        "webpage_url": entry.get("webpage_url"),
                        "url": entry.get("url"),
                    })
            return tracks if tracks else []
        
        return [{
            "title": info.get("title", "Unknown"),
            "webpage_url": info.get("webpage_url"),
            "url": info.get("url"),
        }]

    def _get_queue(self, guild_id: int) -> List[Dict[str, Any]]:
        return self.queues.setdefault(guild_id, [])

    async def _ensure_voice(self, ctx: commands.Context) -> Optional[discord.VoiceClient]:
        if not ctx.author.voice or not ctx.author.voice.channel:
            embed = discord.Embed(
                title="❌ Erro",
                description="Precisas estar num canal de voz.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return None
        
        channel = ctx.author.voice.channel
        permissions = channel.permissions_for(ctx.guild.me)
        if not permissions.connect:
            embed = discord.Embed(
                title="❌ Permissão Negada",
                description="Não tenho permissão para entrar no teu canal de voz.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return None
        if not permissions.speak:
            embed = discord.Embed(
                title="❌ Permissão Negada",
                description="Não tenho permissão para falar no teu canal de voz.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return None
        
        vc = ctx.voice_client
        if vc and vc.channel != channel:
            await vc.move_to(channel)
            return vc
        if not vc:
            try:
                vc = await channel.connect()
            except discord.errors.ClientException:
                embed = discord.Embed(
                    title="❌ Connection Failed",
                    description="Could not connect to voice channel.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return None
        return vc

    async def _play_next(self, guild: discord.Guild):
        queue = self._get_queue(guild.id)
        if not queue:
            self.current.pop(guild.id, None)
            return
        track = queue.pop(0)
        vc = guild.voice_client
        if not vc:
            return
        
        if not track.get("url"):
            logging.warning("Track without URL, skipping: %s", track.get("title"))
            await self._play_next(guild)
            return
        
        self.current[guild.id] = track
        source = discord.FFmpegPCMAudio(track["url"], **FFMPEG_OPTIONS)

        def after_play(err):
            if err:
                logging.exception("Playback error", exc_info=err)
            asyncio.run_coroutine_threadsafe(self._play_next(guild), self.bot.loop)

        vc.play(source, after=after_play)
        logging.info("Now playing: %s", track.get("title"))

    # ===== COMMANDS =====

    @commands.command(name="join", aliases=["connect"])
    async def join(self, ctx):
        """Join user's voice channel"""
        vc = await self._ensure_voice(ctx)
        if vc:
            embed = discord.Embed(
                title="🎵 Connected",
                description=f"Joined **{vc.channel.name}**",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)

    @commands.command(name="play", aliases=["p"])
    async def play(self, ctx, *, query: str):
        """Play song from YouTube or Spotify"""
        # Check if user is in AFK channel
        if ctx.author.voice and ctx.guild.afk_channel and ctx.author.voice.channel == ctx.guild.afk_channel:
            embed = discord.Embed(
                title="❌ Cannot Play",
                description="You cannot play music in the AFK channel.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        vc = await self._ensure_voice(ctx)
        if not vc:
            return
        
        embed = discord.Embed(
            title="🔍 Searching...",
            description=f"Looking for: `{query[:100]}`",
            color=discord.Color.yellow()
        )
        msg = await ctx.send(embed=embed)
        
        try:
            tracks = await self._resolve_track(query)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"Could not fetch track.\n\n`{str(e)[:150]}`",
                color=discord.Color.red()
            )
            await msg.edit(embed=error_embed)
            return
        
        tracks = [t for t in tracks if t.get("url")]
        if not tracks:
            error_embed = discord.Embed(
                title="❌ No Results",
                description="No videos available (may be private or deleted).",
                color=discord.Color.red()
            )
            await msg.edit(embed=error_embed)
            return
        
        queue = self._get_queue(ctx.guild.id)
        queue.extend(tracks)
        
        if len(tracks) == 1:
            result_embed = discord.Embed(
                title="✅ Added to Queue",
                description=f"**{tracks[0]['title']}**",
                color=discord.Color.green()
            )
        else:
            result_embed = discord.Embed(
                title="✅ Playlist Added",
                description=f"**{len(tracks)} songs** added to queue!",
                color=discord.Color.green()
            )
        
        if not vc.is_playing() and not vc.is_paused():
            await self._play_next(ctx.guild)
            view = MusicPlayerView(self)
            await msg.edit(embed=result_embed, view=view)
        else:
            await msg.edit(embed=result_embed)



    @commands.command(name="skip", aliases=["sk"])
    async def skip(self, ctx):
        """Skip current song"""
        vc = ctx.voice_client
        if not vc or not vc.is_playing():
            embed = discord.Embed(
                title="⏭️ Skip",
                description="Nothing to skip.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
        vc.stop()
        embed = discord.Embed(
            title="⏭️ Skipped",
            description="Skipping to next song...",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.command(name="stop", aliases=["s"])
    async def stop(self, ctx):
        """Stop music and leave channel"""
        vc = ctx.voice_client
        if vc:
            queue = self._get_queue(ctx.guild.id)
            queue.clear()
            self.current.pop(ctx.guild.id, None)
            vc.stop()
            await vc.disconnect()
            embed = discord.Embed(
                title="⏹️ Stopped",
                description="Music stopped and disconnected.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="⏹️ Stop",
                description="Not in a voice channel.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)

    @commands.command(name="pause", aliases=["pz"])
    async def pause(self, ctx):
        """Pause music"""
        vc = ctx.voice_client
        if vc and vc.is_playing():
            vc.pause()
            embed = discord.Embed(
                title="⏸️ Paused",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="⏸️ Pause",
                description="Nothing to pause.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)

    @commands.command(name="resume", aliases=["r"])
    async def resume(self, ctx):
        """Resume music"""
        vc = ctx.voice_client
        if vc and vc.is_paused():
            vc.resume()
            embed = discord.Embed(
                title="▶️ Resumed",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="▶️ Resume",
                description="Nothing to resume.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)

    @commands.command(name="queue", aliases=["q"])
    async def queue(self, ctx):
        """Show current queue"""
        queue = self._get_queue(ctx.guild.id)
        vc = ctx.voice_client

        lines = []
        current_track = self.current.get(ctx.guild.id)
        if vc and (vc.is_playing() or vc.is_paused()) and current_track:
            lines.append(f"🎵 **Now Playing:** {current_track.get('title', 'Unknown')}")
            if vc.is_paused():
                lines.append("*(paused)*")

        if not queue:
            if not lines:
                embed = discord.Embed(
                    title="🎵 Queue",
                    description="Queue is empty.",
                    color=discord.Color.blue()
                )
                await ctx.send(embed=embed)
                return
            embed = discord.Embed(
                title="🎵 Queue",
                description="\n".join(lines),
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return

        queued_lines = [f"**{i+1}.** {item.get('title', 'Unknown')}" for i, item in enumerate(queue)]
        lines.extend(queued_lines)

        chunks = []
        chunk = []
        total_chars = 0
        
        for line in lines:
            if total_chars + len(line) + 1 > 4000:
                chunks.append("\n".join(chunk))
                chunk = []
                total_chars = 0
            chunk.append(line)
            total_chars += len(line) + 1
        
        if chunk:
            chunks.append("\n".join(chunk))

        for i, chunk_text in enumerate(chunks):
            embed = discord.Embed(
                title=f"🎵 Queue (Part {i+1}/{len(chunks)})",
                description=chunk_text,
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)

    @commands.command(name="music")
    async def music(self, ctx):
        """Show music commands"""
        embed = discord.Embed(
            title="🎵 Music Commands",
            color=discord.Color.blue()
        )
        
        commands_list = [
            ("**join** / connect / j", "Join your voice channel"),
            ("**play** / p <search>", "Play from YouTube or Spotify"),
            ("**skip** / sk", "Skip current song"),
            ("**pause** / pz", "Pause playback"),
            ("**resume** / r", "Resume playback"),
            ("**stop** / s", "Stop and disconnect"),
            ("**queue** / q", "Show queue"),
        ]
        
        for cmd, desc in commands_list:
            embed.add_field(name=cmd, value=desc, inline=False)
        
        embed.set_footer(text="Use: L!<command>")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
