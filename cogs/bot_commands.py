import asyncio
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import discord
import aiohttp
from discord.ext import commands

from utils.components import ConfirmView


class Basic(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def _weather_description(code: int) -> str:
        mapping = {
            0: "Céu limpo",
            1: "Principalmente limpo",
            2: "Parcialmente nublado",
            3: "Nublado",
            45: "Nevoeiro",
            48: "Nevoeiro com gelo",
            51: "Chuvisco leve",
            53: "Chuvisco moderado",
            55: "Chuvisco intenso",
            56: "Chuvisco gelado leve",
            57: "Chuvisco gelado intenso",
            61: "Chuva fraca",
            63: "Chuva moderada",
            65: "Chuva forte",
            66: "Chuva gelada leve",
            67: "Chuva gelada forte",
            71: "Neve fraca",
            73: "Neve moderada",
            75: "Neve forte",
            77: "Grãos de neve",
            80: "Aguaceiros fracos",
            81: "Aguaceiros moderados",
            82: "Aguaceiros fortes",
            85: "Aguaceiros de neve fracos",
            86: "Aguaceiros de neve fortes",
            95: "Trovoada",
            96: "Trovoada com granizo leve",
            99: "Trovoada com granizo forte",
        }
        return mapping.get(code, "Condições desconhecidas")

    async def _fetch_weather(self, city: str):
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        forecast_url = "https://api.open-meteo.com/v1/forecast"

        async with aiohttp.ClientSession() as session:
            async with session.get(
                geo_url,
                params={"name": city, "count": 1, "language": "pt", "format": "json"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError("Falha ao consultar geocoding")
                geo_data = await resp.json()

            results = geo_data.get("results") or []
            if not results:
                return None

            place = results[0]
            lat = place.get("latitude")
            lon = place.get("longitude")
            location = ", ".join(
                part
                for part in [place.get("name"), place.get("admin1"), place.get("country")]
                if part
            )

            async with session.get(
                forecast_url,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,weather_code",
                    "timezone": "auto",
                },
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError("Falha ao consultar previsão")
                weather_data = await resp.json()

            current = weather_data.get("current") or {}
            return {
                "location": location,
                "temperature": current.get("temperature_2m"),
                "unit": weather_data.get("current_units", {}).get("temperature_2m", "°C"),
                "code": current.get("weather_code"),
                "time": current.get("time"),
            }

    async def _fetch_time(self, city: str):
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        time_url = "https://api.open-meteo.com/v1/forecast"

        async with aiohttp.ClientSession() as session:
            async with session.get(
                geo_url,
                params={"name": city, "count": 1, "language": "pt", "format": "json"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError("Falha ao consultar geocoding")
                geo_data = await resp.json()

            results = geo_data.get("results") or []
            if not results:
                return None

            place = results[0]
            lat = place.get("latitude")
            lon = place.get("longitude")
            location = ", ".join(
                part
                for part in [place.get("name"), place.get("admin1"), place.get("country")]
                if part
            )

            async with session.get(
                time_url,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m",
                    "timezone": "auto",
                },
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError("Falha ao consultar horário")
                time_data = await resp.json()

            current = time_data.get("current") or {}
            return {
                "location": location,
                "time": current.get("time"),
                "timezone": time_data.get("timezone"),
            }

    @commands.command()
    async def ping(self, ctx):
        """Responde com pong"""
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Latência: {self.bot.latency * 1000:.0f}ms",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def write(self, ctx, *, message: str):
        """Ecoar mensagem (apenas admin)"""
        embed = discord.Embed(
            description=message,
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    @write.error
    async def write_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Permissão Negada",
                description="Precisas de permissões de administrador para usar este comando.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.command()
    async def sum(self, ctx, a: int, b: int):
        """Somar dois números"""
        result = a + b
        embed = discord.Embed(
            title="🧮 Resultado da Soma",
            description=f"**{a}** + **{b}** = **{result}**",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    @commands.command(name="tempo", aliases=["weather", "clima"])
    async def tempo(self, ctx, *, city: str = None):
        """Mostra o tempo atual de uma cidade"""
        if not city:
            embed = discord.Embed(
                title="❌ Sintaxe Inválida",
                description="Uso: `L!tempo <cidade>`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        try:
            data = await self._fetch_weather(city)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Erro ao obter o tempo",
                description=f"Falha ao consultar o serviço de meteorologia: {e}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        if not data:
            embed = discord.Embed(
                title="🔎 Cidade não encontrada",
                description="Não consegui encontrar essa cidade. Tenta novamente com outro nome.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return

        description = self._weather_description(data.get("code"))
        temperature = data.get("temperature")
        unit = data.get("unit") or "°C"

        embed = discord.Embed(
            title="🌤️ Tempo Atual",
            description=data.get("location", city),
            color=discord.Color.blue()
        )
        embed.add_field(name="Descrição", value=description, inline=False)
        if temperature is not None:
            embed.add_field(name="Temperatura", value=f"{temperature:.1f}{unit}", inline=True)
        if data.get("time"):
            embed.set_footer(text=f"Atualizado dia {data['time']}")
        await ctx.send(embed=embed)

    @commands.command(name="hora", aliases=["time", "horario", "timezone"])
    async def hora(self, ctx, *, city: str = None):
        """Mostra a hora atual de uma cidade"""
        if not city:
            embed = discord.Embed(
                title="❌ Sintaxe Inválida",
                description="Uso: `L!hora <cidade>`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        try:
            data = await self._fetch_time(city)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Erro ao obter horário",
                description=f"Falha ao consultar o serviço de horário: {e}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        if not data:
            embed = discord.Embed(
                title="🔎 Cidade não encontrada",
                description="Não consegui encontrar essa cidade. Tenta novamente com outro nome.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return

        raw_time = data.get("time")
        display_time = raw_time or "—"
        tz_name = data.get("timezone")

        if tz_name:
            try:
                now_local = datetime.now(ZoneInfo(tz_name))
                display_time = now_local.strftime("%d/%m/%Y %H:%M")
            except Exception:
                pass

        if display_time == raw_time and raw_time:
            try:
                display_time = datetime.fromisoformat(raw_time).strftime("%d/%m/%Y %H:%M")
            except ValueError:
                display_time = raw_time

        embed = discord.Embed(
            title="🕒 Hora Atual",
            description=data.get("location", city),
            color=discord.Color.blue()
        )
        embed.add_field(name="Hora local", value=display_time, inline=False)
        if tz_name:
            embed.set_footer(text=f"Fuso horário: {tz_name}")
        await ctx.send(embed=embed)

    @commands.command(name="traduzir", aliases=["translate", "tr"])
    async def traduzir(self, ctx, *args):
        """Traduz texto entre idiomas"""
        try:
            from deep_translator import GoogleTranslator, MyMemoryTranslator
        except Exception:
            embed = discord.Embed(
                title="❌ Tradução Indisponível",
                description="A dependência `deep-translator` não está instalada.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        try:
            from langdetect import detect
        except Exception:
            detect = None

        if len(args) < 2:
            embed = discord.Embed(
                title="❌ Sintaxe Inválida",
                description=(
                    "Uso: `L!traduzir <idioma_destino> <texto>`\n"
                    "Ou:  `L!traduzir <idioma_origem> <idioma_destino> <texto>`"
                ),
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        mm_supported = MyMemoryTranslator(source="en-GB", target="pt-PT").get_supported_languages(as_dict=True)
        mm_supported_names = set(mm_supported.keys())
        mm_supported_codes = set(mm_supported.values())

        def normalize_mymemory_lang(token: str):
            token_lower = token.lower()

            if token_lower in mm_supported_names:
                return mm_supported[token_lower]
            if token in mm_supported_codes:
                return token

            preferred = {
                "en": "en-US",
                "pt": "pt-PT",
                "es": "es-ES",
                "fr": "fr-FR",
                "de": "de-DE",
                "it": "it-IT",
            }
            if token_lower in preferred and preferred[token_lower] in mm_supported_codes:
                return preferred[token_lower]

            for code in mm_supported_codes:
                if code.lower().startswith(f"{token_lower}-"):
                    return code
            return None

        def normalize_google_lang(code: str):
            return code.split("-")[0] if code else code

        def is_lang(token: str) -> bool:
            token_lower = token.lower()
            return token_lower in mm_supported_names or token in mm_supported_codes

        if len(args) >= 3 and is_lang(args[0]) and is_lang(args[1]):
            source_lang = args[0]
            target_lang = args[1]
            text = " ".join(args[2:])
        else:
            source_lang = "auto"
            target_lang = args[0]
            text = " ".join(args[1:])

        target_code = normalize_mymemory_lang(target_lang)
        if not target_code:
            embed = discord.Embed(
                title="❌ Idioma Inválido",
                description=(
                    "Idioma de destino inválido. Usa um código suportado (ex.: `en`, `pt`, `es`)."
                ),
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        source_code = normalize_mymemory_lang(source_lang) if source_lang != "auto" else None
        if source_lang != "auto" and not source_code:
            embed = discord.Embed(
                title="❌ Idioma Inválido",
                description=(
                    "Idioma de origem inválido. Usa um código suportado (ex.: `pt`, `en`)."
                ),
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        if source_lang == "auto":
            if detect:
                try:
                    detected = detect(text)
                    source_code = normalize_mymemory_lang(detected) or detected
                except Exception:
                    source_code = None

        translated = None
        engine = "MyMemory"
        try:
            if not source_code:
                raise ValueError("source language not detected")
            translated = MyMemoryTranslator(source=source_code, target=target_code).translate(text)
        except Exception as e:
            try:
                engine = "Google"
                g_source = normalize_google_lang(source_code) if source_code else "auto"
                g_target = normalize_google_lang(target_code) if target_code else target_lang
                translated = GoogleTranslator(source=g_source, target=g_target).translate(text)
            except Exception as e2:
                embed = discord.Embed(
                    title="❌ Erro na Tradução",
                    description=f"Falha ao traduzir: {e2}",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return

        embed = discord.Embed(
            title="🌍 Tradução",
            color=discord.Color.green()
        )
        embed.add_field(name="Texto Original", value=text, inline=False)
        embed.add_field(name="Texto Traduzido", value=translated, inline=False)
        used_source = source_code or source_lang
        embed.set_footer(text=f"{used_source} → {target_code} via {engine}")
        await ctx.send(embed=embed)

    @commands.command()
    async def info(self, ctx, member: discord.Member = None):
        """Mostrar informações do utilizador"""
        member = member or ctx.author
        embed = discord.Embed(title="👤 Informações do Utilizador", color=discord.Color.blue())
        embed.add_field(name="Nome de Utilizador", value=member.name, inline=True)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(
            name="Conta Criada",
            value=member.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            inline=False
        )
        avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
        embed.set_thumbnail(url=avatar_url)
        await ctx.send(embed=embed)

    @commands.command(aliases=["guild"])
    async def server(self, ctx):
        """Mostrar informações do servidor"""
        guild = ctx.guild
        embed = discord.Embed(title="🏰 Informações do Servidor", color=discord.Color.green())
        embed.add_field(name="Nome do Servidor", value=guild.name, inline=True)
        embed.add_field(name="Membros", value=guild.member_count, inline=False)
        embed.add_field(
            name="Criado",
            value=guild.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            inline=False
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)
        await ctx.send(embed=embed)

    @commands.command(name="clear")
    @commands.has_permissions(administrator=True)
    async def clear(self, ctx, amount: int = None):
        """Apagar mensagens do canal (apenas admin)"""
        if amount is None:
            embed = discord.Embed(
                title="⚠️ Confirmação",
                description="Tens a certeza que queres apagar todas as mensagens? Escreve `confirm` nos próximos 10 segundos.",
                color=discord.Color.orange()
            )
            msg = await ctx.send(embed=embed)
            
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == "confirm"
            
            try:
                await self.bot.wait_for("message", timeout=10.0, check=check)
                deleted = await ctx.channel.purge(limit=None)
                result_embed = discord.Embed(
                    title="✅ Apagado",
                    description=f"Apagadas **{len(deleted)}** mensagens.",
                    color=discord.Color.green()
                )
                result_msg = await ctx.send(embed=result_embed)
                await asyncio.sleep(3)
                await result_msg.delete()
            except asyncio.TimeoutError:
                timeout_embed = discord.Embed(
                    title="❌ Cancelado",
                    description="Operação expirou.",
                    color=discord.Color.red()
                )
                await msg.edit(embed=timeout_embed)
        else:
            if amount <= 0:
                embed = discord.Embed(
                    title="❌ Erro",
                    description="O valor deve ser positivo.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
            deleted = await ctx.channel.purge(limit=amount + 1)
            result_embed = discord.Embed(
                title="✅ Apagado",
                description=f"Apagadas **{len(deleted) - 1}** mensagens.",
                color=discord.Color.green()
            )
            result_msg = await ctx.send(embed=result_embed)
            await asyncio.sleep(3)
            await result_msg.delete()

    @clear.error
    async def clear_error(self, ctx, error):
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
                description="Uso: `l!clear [valor]`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.command(name="rules")
    async def rules(self, ctx):
        """Mostrar regras do servidor"""
        rules_file = "data/rules.json"
        
        if not os.path.exists(rules_file):
            embed = discord.Embed(
                title="❌ Erro",
                description="Ficheiro de regras não encontrado.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        try:
            with open(rules_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            embed = discord.Embed(
                title=data.get("title", "Regras do Servidor"),
                color=int(data.get("color", "0x3498db").replace("0x", ""), 16),
            )
            
            for rule in data.get("rules", []):
                embed.add_field(
                    name=f"{rule['number']}. {rule['title']}",
                    value=rule['description'],
                    inline=False,
                )
            
            if "footer" in data:
                embed.set_footer(text=data["footer"])
            
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Erro",
                description=f"Falha ao carregar regras: {e}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.command(name="help")
    async def help_cmd(self, ctx):
        """Mostrar todos os comandos disponíveis"""
        prefix = ctx.prefix or "L!"
        
        if ctx.author.guild_permissions.administrator:
            general = [
                ("ping", "responde com pong"),
                ("write <message>", "ecoar mensagem (apenas admin)"),
                ("sum <a> <b>", "somar dois números"),
                ("tempo <cidade>", "mostra o tempo atual de uma cidade"),
                ("hora <cidade>", "mostra a hora atual de uma cidade"),
                ("traduzir <dest> <texto>", "traduz texto entre idiomas"),
                ("info [@user]", "mostrar informações do utilizador"),
                ("server / guild", "mostrar informações do servidor"),
                ("rules", "mostrar regras do servidor"),
                ("clear [amount]", "apagar mensagens do canal (apenas admin)"),
            ]

            music = [
                ("join / connect / j", "juntar ao canal de voz"),
                ("play / p <term|link>", "tocar do YouTube ou Spotify"),
                ("skip / sk", "saltar música atual"),
                ("stop / s", "parar e sair"),
                ("pause / pz", "pausar"),
                ("resume / r", "retomar"),
                ("queue / q", "mostrar fila"),
                ("testtone / tone", "testar áudio com tom"),
                ("music", "mostrar comandos de música"),
            ]

            levels = [
                ("level [@user]", "mostrar nível e XP do utilizador"),
                ("rank", "mostrar top 10 do ranking de XP"),
                ("addxp @user <value>", "adicionar XP"),
            ]

            games = [
                ("termo", "começa um novo jogo de Termo"),
                ("termo_quit / quit", "sai do jogo atual"),
                ("termo_stats / stats [@user]", "mostra as estatísticas do Termo"),
                ("termo_rank", "mostra o ranking do Termo"),
            ]

            quick_games = [
                ("ppt <pedra|papel|tesoura>", "joga pedra, papel ou tesoura"),
                ("dado [lados]", "rola um dado de N lados"),
                ("moeda", "atira uma moeda ao ar"),
                ("escolher <op1> <op2> ...", "deixa o bot escolher por ti"),
                ("8ball <pergunta>", "faz uma pergunta à bola mágica"),
                ("adivinhar <número>", "adivinha o número entre 1 e 10"),
                ("jogos", "mostra todos os jogos disponíveis"),
            ]

            code = [
                ("code / desafio", "começa um novo desafio de programação"),
                ("stats_code", "mostra estatísticas dos desafios"),
            ]

            embed = discord.Embed(
                title="📖 Ajuda (Admin)",
                description="Para mais informações sobre um comando, usa `L!help`",
                color=discord.Color.red()
            )
            
            general_text = "\n".join(f"` {prefix}{cmd:<25}` {desc}" for cmd, desc in general)
            embed.add_field(
                name="⚙️ Geral (Admin)",
                value=general_text,
                inline=False,
            )
            
            music_text = "\n".join(f"` {prefix}{cmd:<25}` {desc}" for cmd, desc in music)
            embed.add_field(
                name="🎵 Música",
                value=music_text,
                inline=False,
            )
            
            levels_text = "\n".join(f"` {prefix}{cmd:<25}` {desc}" for cmd, desc in levels)
            embed.add_field(
                name="📊 Níveis",
                value=levels_text,
                inline=False,
            )
            
            games_text = "\n".join(f"` {prefix}{cmd:<25}` {desc}" for cmd, desc in games)
            embed.add_field(
                name="🎮 Jogos - Termo",
                value=games_text,
                inline=False,
            )
            
            quick_games_text = "\n".join(f"` {prefix}{cmd:<25}` {desc}" for cmd, desc in quick_games)
            embed.add_field(
                name="🎲 Jogos Rápidos",
                value=quick_games_text,
                inline=False,
            )
            
            code_text = "\n".join(f"` {prefix}{cmd:<25}` {desc}" for cmd, desc in code)
            embed.add_field(
                name="💻 Desafios de Código",
                value=code_text,
                inline=False,
            )
            
            await ctx.send(embed=embed)
        else:
            general = [
                ("ping", "responde com pong"),
                ("sum <a> <b>", "somar dois números"),
                ("tempo <cidade>", "mostra o tempo atual de uma cidade"),
                ("hora <cidade>", "mostra a hora atual de uma cidade"),
                ("traduzir <dest> <texto>", "traduz texto entre idiomas"),
                ("info [@user]", "mostrar informações do utilizador"),
                ("server / guild", "mostrar informações do servidor"),
                ("rules", "mostrar regras do servidor"),
            ]

            music = [
                ("join / connect / j", "juntar ao canal de voz"),
                ("play / p <term|link>", "tocar do YouTube ou Spotify"),
                ("skip / sk", "saltar música atual"),
                ("stop / s", "parar e sair"),
                ("pause / pz", "pausar"),
                ("resume / r", "retomar"),
                ("queue / q", "mostrar fila"),
                ("testtone / tone", "testar áudio com tom"),
                ("music", "mostrar comandos de música"),
            ]

            levels = [
                ("level [@user]", "mostrar nível e XP do utilizador"),
                ("rank", "mostrar top 10 do ranking de XP"),
            ]

            games = [
                ("termo", "começa um novo jogo de Termo"),
                ("termo_quit / quit", "sai do jogo atual"),
                ("termo_stats / stats [@user]", "mostra as estatísticas do Termo"),
                ("termo_rank", "mostra o ranking do Termo"),
            ]

            quick_games = [
                ("ppt <pedra|papel|tesoura>", "joga pedra, papel ou tesoura"),
                ("dado [lados]", "rola um dado de N lados"),
                ("moeda", "atira uma moeda ao ar"),
                ("escolher <op1> <op2> ...", "deixa o bot escolher por ti"),
                ("8ball <pergunta>", "faz uma pergunta à bola mágica"),
                ("adivinhar <número>", "adivinha o número entre 1 e 10"),
                ("jogos", "mostra todos os jogos disponíveis"),
            ]

            code = [
                ("code / desafio", "começa um novo desafio de programação"),
                ("stats_code", "mostra estatísticas dos desafios"),
            ]

            embed = discord.Embed(
                title="📖 Ajuda",
                description="Para mais informações sobre um comando, usa `L!help`",
                color=discord.Color.blurple()
            )
            
            general_text = "\n".join(f"` {prefix}{cmd:<25}` {desc}" for cmd, desc in general)
            embed.add_field(
                name="⚙️ Geral",
                value=general_text,
                inline=False,
            )
            
            music_text = "\n".join(f"` {prefix}{cmd:<25}` {desc}" for cmd, desc in music)
            embed.add_field(
                name="🎵 Música",
                value=music_text,
                inline=False,
            )
            
            levels_text = "\n".join(f"` {prefix}{cmd:<25}` {desc}" for cmd, desc in levels)
            embed.add_field(
                name="📊 Níveis",
                value=levels_text,
                inline=False,
            )
            
            games_text = "\n".join(f"` {prefix}{cmd:<25}` {desc}" for cmd, desc in games)
            embed.add_field(
                name="🎮 Jogos - Termo",
                value=games_text,
                inline=False,
            )
            
            quick_games_text = "\n".join(f"` {prefix}{cmd:<25}` {desc}" for cmd, desc in quick_games)
            embed.add_field(
                name="🎲 Jogos Rápidos",
                value=quick_games_text,
                inline=False,
            )
            
            code_text = "\n".join(f"` {prefix}{cmd:<25}` {desc}" for cmd, desc in code)
            embed.add_field(
                name="💻 Desafios de Código",
                value=code_text,
                inline=False,
            )
            
            await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Basic(bot))

