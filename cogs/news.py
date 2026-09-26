import os
import json
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

import discord
import aiohttp
from discord.ext import commands, tasks

CONFIG_FILE = "data/news_config.json"
LISBOA = ZoneInfo("Europe/Lisbon")
HORAS_ENVIO = [dtime(hour=8, tzinfo=LISBOA), dtime(hour=13, tzinfo=LISBOA), dtime(hour=20, tzinfo=LISBOA)]


class News(commands.Cog):
    CATEGORIAS_NOTICIAS = {
        "geral": "general",
        "negocios": "business",
        "entretenimento": "entertainment",
        "saude": "health",
        "ciencia": "science",
        "desporto": "sports",
        "tecnologia": "technology",
    }

    CATEGORIA_EMOJIS = {
        "geral": "📰",
        "negocios": "💼",
        "entretenimento": "🎬",
        "saude": "🏥",
        "ciencia": "🔬",
        "desporto": "⚽",
        "tecnologia": "💻",
    }

    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("GNEWS_KEY")
        self.config = self._load_config()
        self.auto_news.start()

    def cog_unload(self):
        self.auto_news.cancel()

    # ---------- configuração persistida (canal + categoria por servidor) ----------

    def _load_config(self) -> dict:
        if not os.path.exists(CONFIG_FILE):
            return {}
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_config(self):
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    # ---------- obtenção de notícias ----------

    async def _fetch_news(self, categoria_pt: str):
        categoria = self.CATEGORIAS_NOTICIAS.get(categoria_pt)
        if not categoria:
            return "invalid_category"

        if not self.api_key:
            raise RuntimeError("GNEWS_KEY não está configurada no .env")

        url = "https://gnews.io/api/v4/top-headlines"
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params={
                    "category": categoria,
                    "lang": "pt",
                    "country": "pt",
                    "max": 5,
                    "apikey": self.api_key,
                },
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Falha ao consultar notícias (status {resp.status})")
                data = await resp.json()

        return data.get("articles", [])[:5]

    def _build_embed(self, categoria: str, articles: list) -> discord.Embed:
        emoji = self.CATEGORIA_EMOJIS.get(categoria, "📰")
        embed = discord.Embed(
            title=f"{emoji} Notícias — {categoria.capitalize()}",
            color=discord.Color.blue()
        )

        primeira_imagem = None
        for i, artigo in enumerate(articles, start=1):
            titulo = artigo.get("title", "Sem título")
            link = artigo.get("url", "")
            fonte = artigo.get("source", {}).get("name", "Fonte desconhecida")
            descricao = artigo.get("description") or ""
            if len(descricao) > 150:
                descricao = descricao[:150].rsplit(" ", 1)[0] + "…"

            publicado = artigo.get("publishedAt")
            data_str = ""
            if publicado:
                try:
                    dt = datetime.fromisoformat(publicado.replace("Z", "+00:00"))
                    data_str = f" • {dt.strftime('%d/%m %H:%M')}"
                except ValueError:
                    pass

            valor = f"{descricao}\n[Ler mais]({link}) — *{fonte}{data_str}*" if descricao else f"[Ler mais]({link}) — *{fonte}{data_str}*"
            embed.add_field(name=f"{i}. {titulo}"[:256], value=valor, inline=False)

            if not primeira_imagem and artigo.get("image"):
                primeira_imagem = artigo["image"]

        if primeira_imagem:
            embed.set_thumbnail(url=primeira_imagem)

        embed.set_footer(text=f"Fonte: GNews • {len(articles)} artigos")
        embed.timestamp = discord.utils.utcnow()
        return embed

    # ---------- comando manual ----------

    @commands.hybrid_command(name="noticias")
    async def noticias(self, ctx, *, categoria: str = "geral"):
        """Mostra as últimas notícias de uma categoria"""
        categoria = categoria.lower()

        try:
            result = await self._fetch_news(categoria)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Erro ao obter notícias",
                description=f"Falha ao consultar o serviço de notícias: {e}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        if result == "invalid_category":
            categorias = ", ".join(self.CATEGORIAS_NOTICIAS.keys())
            embed = discord.Embed(
                title="❌ Categoria Inválida",
                description=f"Escolhe uma de: {categorias}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        if not result:
            embed = discord.Embed(
                title="🔎 Sem notícias",
                description="Não encontrei notícias para essa categoria.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return

        await ctx.send(embed=self._build_embed(categoria, result))
        
    @commands.hybrid_command(name="news")
    async def news_alias(self, ctx, *, categoria: str = "geral"):
        """Mostra as últimas notícias de uma categoria (atalho para /noticias)"""
        await self.noticias(ctx, categoria=categoria)

    # ---------- configuração do canal automático (admin) ----------

    @commands.hybrid_command(name="noticias_canal")
    @commands.has_permissions(administrator=True)
    async def noticias_canal(self, ctx, canal: discord.TextChannel = None, categoria: str = "geral"):
        """Define o canal onde as notícias são enviadas automaticamente às 8h, 13h e 20h"""
        categoria = categoria.lower()
        if categoria not in self.CATEGORIAS_NOTICIAS:
            categorias = ", ".join(self.CATEGORIAS_NOTICIAS.keys())
            embed = discord.Embed(
                title="❌ Categoria Inválida",
                description=f"Escolhe uma de: {categorias}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        if canal is None:
            self.config.pop(str(ctx.guild.id), None)
            self._save_config()
            embed = discord.Embed(
                title="✅ Envio automático desativado",
                description="As notícias automáticas foram desligadas para este servidor.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            return

        self.config[str(ctx.guild.id)] = {"channel_id": canal.id, "categoria": categoria}
        self._save_config()

        embed = discord.Embed(
            title="✅ Canal configurado",
            description=f"As notícias de **{categoria}** vão ser enviadas em {canal.mention} às 8h, 13h e 20h.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @noticias_canal.error
    async def noticias_canal_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Permissão Negada",
                description="Precisas de permissões de administrador para usar este comando.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                title="❌ Sintaxe Inválida",
                description="Uso: `/noticias_canal <#canal> [categoria]`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    # ---------- envio automático ----------

    @tasks.loop(time=HORAS_ENVIO)
    async def auto_news(self):
        for guild_id, cfg in self.config.items():
            channel = self.bot.get_channel(cfg.get("channel_id"))
            if channel is None:
                continue

            categoria = cfg.get("categoria", "geral")
            try:
                result = await self._fetch_news(categoria)
            except Exception:
                continue

            if not result or result == "invalid_category":
                continue

            try:
                await channel.send(embed=self._build_embed(categoria, result))
            except discord.HTTPException:
                continue

    @auto_news.before_loop
    async def before_auto_news(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(News(bot))