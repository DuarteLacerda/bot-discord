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
except ImportError:  # Spotipy é opcional; usamos fallback se não estiver instalado
    spotipy = None

import yt_dlp

load_dotenv()

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

YTDL_OPTS = {
    "format": "bestaudio[ext=webm]/bestaudio/best",
    "quiet": True,
    "noplaylist": False,
    "playlistend": 20,
    "default_search": "ytsearch",
    "skip_download": True,
    "no_warnings": True,
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

    async def cog_unload(self):
        # Para áudio em todos os servidores quando o cog descarrega
        for vc in self.bot.voice_clients:
            try:
                await vc.disconnect()
            except Exception:
                pass

    # Utilitários
    def _is_spotify_track(self, query: str) -> bool:
        q = query.strip().lower()
        if q.startswith("spotify:track:"):
            return True
        return "open.spotify.com" in q and "/track/" in q

    async def _spotify_to_query(self, url: str) -> str:
        """Converte um link de faixa do Spotify em uma string de busca no YouTube."""
        if not self.spotify:
            return url  # Fallback: usa o próprio link como termo de busca
        try:
            track_id = url.split("track/")[-1].split("?")[0] if "track/" in url else url.split(":")[-1]
            data = self.spotify.track(track_id)
            name = data.get("name")
            artists = ", ".join(a["name"] for a in data.get("artists", []))
            return f"{name} {artists} audio"
        except Exception:
            logging.exception("Falha ao resolver faixa do Spotify; usando fallback de busca")
            return url

    async def _extract_info(self, search: str) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.ytdl.extract_info(search, download=False))

    async def _resolve_track(self, query: str) -> Dict[str, Any]:
        if self._is_spotify_track(query):
            query = await self._spotify_to_query(query)
        info = await self._extract_info(query)
        if "entries" in info:
            info = info["entries"][0]
        return {
            "title": info.get("title", "desconhecido"),
            "webpage_url": info.get("webpage_url"),
            "url": info.get("url"),
        }

    async def _resolve_youtube(self, query: str) -> Dict[str, Any]:
        info = await self._extract_info(query)
        if "entries" in info:
            info = info["entries"][0]
        return {
            "title": info.get("title", "desconhecido"),
            "webpage_url": info.get("webpage_url"),
            "url": info.get("url"),
        }

    async def _resolve_spotify(self, query: str) -> Dict[str, Any]:
        if not self._is_spotify_track(query):
            raise ValueError("Fornece um link de faixa do Spotify.")
        yt_query = await self._spotify_to_query(query)
        # Se não temos credenciais do Spotify, caímos em fallback textual
        if "open.spotify.com" in yt_query:
            track_id = yt_query.split("/track/")[-1].split("?")[0]
            search = track_id
        elif yt_query.startswith("spotify:track:"):
            search = yt_query.split(":")[-1]
        else:
            search = yt_query

        info = await self._extract_info(search)
        if "entries" in info:
            info = info["entries"][0]
        return {
            "title": info.get("title", "desconhecido"),
            "webpage_url": info.get("webpage_url"),
            "url": info.get("url"),
        }

    def _get_queue(self, guild_id: int) -> List[Dict[str, Any]]:
        return self.queues.setdefault(guild_id, [])

    async def _ensure_voice(self, ctx: commands.Context) -> Optional[discord.VoiceClient]:
        # Verifica se o usuário está num canal de voz
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("❌ Precisas de estar num canal de voz para usar comandos de música.")
            return None
        
        channel = ctx.author.voice.channel
        
        # Verifica se o bot tem permissão para conectar ao canal
        permissions = channel.permissions_for(ctx.guild.me)
        if not permissions.connect:
            await ctx.send("❌ Não tenho permissão para entrar no teu canal de voz.")
            return None
        if not permissions.speak:
            await ctx.send("❌ Não tenho permissão para falar no teu canal de voz.")
            return None
        
        vc = ctx.voice_client
        if vc and vc.channel != channel:
            await vc.move_to(channel)
            return vc
        if not vc:
            try:
                vc = await channel.connect()
            except discord.errors.ClientException:
                await ctx.send("❌ Não consegui conectar ao canal de voz.")
                return None
        return vc

    async def _play_next(self, guild: discord.Guild):
        queue = self._get_queue(guild.id)
        if not queue:
            return
        track = queue.pop(0)
        vc = guild.voice_client
        if not vc:
            return
        source = discord.FFmpegPCMAudio(track["url"], **FFMPEG_OPTIONS)
        vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self._play_next(guild), self.bot.loop))
        text = f"Tocando agora: {track['title']}"
        # Não temos ctx aqui; apenas log
        logging.info(text)

    # Comandos
    @commands.command(name="join", aliases=["entrar", "j"])
    async def join(self, ctx):
        vc = await self._ensure_voice(ctx)
        if vc:
            await ctx.send(f"Conectado a {vc.channel.name}.")

    @commands.command(name="play", aliases=["tocar", "p"])
    async def play(self, ctx, *, query: str):
        vc = await self._ensure_voice(ctx)
        if not vc:
            return
        await ctx.send("Buscando faixa...")
        try:
            track = await self._resolve_track(query)
        except Exception:
            logging.exception("Falha ao resolver faixa")
            await ctx.send("Não consegui obter a faixa. Tenta outro termo ou link.")
            return
        queue = self._get_queue(ctx.guild.id)
        queue.append(track)
        await ctx.send(f"Adicionado à fila: {track['title']}")
        if not vc.is_playing():
            await self._play_next(ctx.guild)

    @commands.command(name="ytplay", aliases=["yttocar", "ytp"])
    async def ytplay(self, ctx, *, query: str):
        """Força busca no YouTube (texto ou link)."""
        vc = await self._ensure_voice(ctx)
        if not vc:
            return
        await ctx.send("Buscando no YouTube...")
        try:
            track = await self._resolve_youtube(query)
        except Exception:
            logging.exception("Falha ao resolver faixa do YouTube")
            await ctx.send("Não consegui obter a faixa. Tenta outro termo ou link do YouTube.")
            return
        queue = self._get_queue(ctx.guild.id)
        queue.append(track)
        await ctx.send(f"Adicionado à fila (YT): {track['title']}")
        if not vc.is_playing():
            await self._play_next(ctx.guild)

    @commands.command(name="splay", aliases=["stocar", "sp"])
    async def splay(self, ctx, *, url: str):
        """Toca a partir de link do Spotify (converte para busca no YouTube)."""
        vc = await self._ensure_voice(ctx)
        if not vc:
            return
        if not self._is_spotify_track(url):
            await ctx.send("Envia um link de faixa do Spotify.")
            return
        await ctx.send("Buscando no Spotify/YouTube...")
        try:
            track = await self._resolve_spotify(url)
        except Exception:
            logging.exception("Falha ao resolver faixa do Spotify")
            await ctx.send("Não consegui obter a faixa do Spotify.")
            return
        queue = self._get_queue(ctx.guild.id)
        queue.append(track)
        await ctx.send(f"Adicionado à fila (Spotify): {track['title']}")
        if not vc.is_playing():
            await self._play_next(ctx.guild)

    @commands.command(name="skip", aliases=["pular", "sk"])
    async def skip(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.is_playing():
            await ctx.send("Nada tocando.")
            return
        vc.stop()
        await ctx.send("Pulando...")

    @commands.command(name="stop", aliases=["parar", "s"])
    async def stop(self, ctx):
        vc = ctx.voice_client
        if vc:
            queue = self._get_queue(ctx.guild.id)
            queue.clear()
            vc.stop()
            await vc.disconnect()
            await ctx.send("Parado e desconectado.")
        else:
            await ctx.send("Não estou em um canal de voz.")

    @commands.command(name="pause", aliases=["pausar", "pz"])
    async def pause(self, ctx):
        vc = ctx.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await ctx.send("Pausado.")
        else:
            await ctx.send("Nada para pausar.")

    @commands.command(name="resume", aliases=["retomar", "r"])
    async def resume(self, ctx):
        vc = ctx.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await ctx.send("Retomado.")
        else:
            await ctx.send("Nada para retomar.")

    @commands.command(name="fila", aliases=["queue", "q"])
    async def fila(self, ctx):
        queue = self._get_queue(ctx.guild.id)
        if not queue:
            await ctx.send("Fila vazia.")
            return
        lines = [f"{i+1}. {item['title']}" for i, item in enumerate(queue)]
        await ctx.send("\n".join(lines))

    @commands.command(name="music_cmds", aliases=["comandos_musica", "mc"])
    async def music_cmds(self, ctx):
        """Lista comandos de música disponíveis."""
        prefix = ctx.prefix or ""
        cmds = [
            ("join / entrar / j", "entra no teu canal de voz"),
            ("play / tocar / p <termo|link>", "busca YouTube ou Spotify automaticamente"),
            ("ytplay / yttocar / ytp <termo|link>", "força busca no YouTube"),
            ("splay / stocar / sp <link_spotify>", "toca link de faixa do Spotify"),
            ("skip / pular / sk", "pula a faixa atual"),
            ("stop / parar / s", "limpa fila e sai do canal"),
            ("pause / pausar / pz", "pausa a reprodução"),
            ("resume / retomar / r", "retoma se estiver pausado"),
            ("fila / queue / q", "mostra a fila atual"),
        ]
        lines = [f"• `{prefix}{name}` — {desc}" for name, desc in cmds]
        embed = discord.Embed(
            title="🎵 Comandos de Música",
            description="\n".join(lines),
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📋 Requisitos",
            value="• Precisas estar num canal de voz\n• O bot precisa ter permissão para conectar e falar",
            inline=False
        )
        embed.set_footer(text="Usa os comandos para tocar músicas do YouTube ou Spotify!")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
