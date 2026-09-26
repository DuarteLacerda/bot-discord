import asyncio
import json
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import discord
import aiohttp
from discord.ext import commands

from utils.components import ConfirmView, PaginatedView

# Exemplos de uso para comandos com parâmetros, mostrados em /help <comando>
COMMAND_EXAMPLES = {
    "play": "/play never gonna give you up",
    "tempo": "/tempo Lisboa",
    "hora": "/hora Tóquio",
    "previsao": "/previsao Porto",
    "warn": "/warn @Duarte Spam no chat",
    "warn_remove": "/warn_remove @Duarte 2",
    "kick": "/kick @Duarte Comportamento inadequado",
    "ban": "/ban @Duarte Violações repetidas das regras",
    "unban": "/unban 123456789012345678",
    "clear": "/clear 20",
    "lembrar": "/lembrar 2h Ir buscar a roupa à lavandaria",
    "lembrete_cancelar": "/lembrete_cancelar 3",
    "poll": "/poll Gostam do novo tema?\n/poll Qual o melhor dia? | Segunda | Quarta | Sexta",
    "poll_fechar": "/poll_fechar 123456789012345678",
    "escolher": "/escolher pizza sushi hambúrguer",
    "ppt": "/ppt pedra",
    "dado": "/dado 20",
    "8ball": "/8ball Vou passar no exame?",
    "adivinhar": "/adivinhar 7",
    "addxp": "/addxp @Duarte 500",
    "removexp": "/removexp @Duarte 100",
    "syncroles": "/syncroles @Duarte",
    "automod_antispam": "/automod_antispam on",
    "automod_antilinks": "/automod_antilinks off",
    "automod_whitelist_add": "/automod_whitelist_add youtube.com",
    "automod_whitelist_remove": "/automod_whitelist_remove youtube.com",
    "automod_addperm": "/automod_addperm @Duarte",
    "automod_removeperm": "/automod_removeperm @Duarte",
    "antiraid_config": "/antiraid_config 5 10 7",
    "modlog_canal": "/modlog_canal #logs-moderacao",
    "info": "/info @Duarte",
    "nivel": "/nivel @Duarte",
    "ticket": "/ticket Preciso de ajuda com a minha encomenda",
    "noticias": "/noticias tecnologia",
    "news": "/news tecnologia",
    "write": "/write Bem-vindos ao servidor!",
    "noticias_canal": "/noticias_canal #geral tecnologia",
}

# Uma cor distinta por categoria, para que cada página do /help se destaque
# visualmente e seja fácil identificar em que secção se está, de relance.
CATEGORY_COLORS = {
    "⚙️ Básico": discord.Color.light_gray(),
    "ℹ️ Informação": discord.Color.blue(),
    "🌤️ Meteorologia": discord.Color.from_rgb(86, 180, 233),
    "🎵 Música": discord.Color.purple(),
    "📊 Níveis": discord.Color.gold(),
    "🎮 Jogos - Termo": discord.Color.green(),
    "🎲 Jogos Rápidos": discord.Color.from_rgb(46, 204, 113),
    "💻 Desafios de Código": discord.Color.teal(),
    "⏰ Lembretes": discord.Color.orange(),
    "📊 Enquetes": discord.Color.from_rgb(155, 89, 182),
    "🛡️ Auto-Moderação": discord.Color.dark_teal(),
    "🎫 Tickets": discord.Color.from_rgb(52, 152, 219),
    "📰 Notícias": discord.Color.from_rgb(230, 126, 34),
    "🛡️ Auto-Moderação (Admin)": discord.Color.dark_red(),
    "🔨 Moderação": discord.Color.red(),
    "🚨 Anti-Raid": discord.Color.from_rgb(192, 57, 43),
    "👑 Admin": discord.Color.dark_gold(),
}
DEFAULT_HELP_COLOR = discord.Color.blurple()
DEFAULT_ADMIN_COLOR = discord.Color.red()


def _chunk_lines(blocks: list, limit: int = 1000) -> list:
    """Divide os blocos (cada um pode já conter \\n internos) em grupos que
    cabem num campo de embed, sem nunca cortar um bloco a meio — garante
    que um comando e a sua descrição ficam sempre juntos e nunca são
    separados entre dois campos/páginas diferentes. Os blocos são juntos
    com uma linha em branco entre eles para arejar a leitura. O limite é
    propositadamente inferior a 1024 para sobrar espaço para as marcações
    ``` do bloco de código."""
    chunks = []
    current = []
    current_len = 0
    for block in blocks:
        block_len = len(block) + 2  # +2 pela linha em branco separadora
        if current and current_len + block_len > limit:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0
        current.append(block)
        current_len += block_len
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _format_section_lines(commands_list: list) -> list:
    """Formata cada comando como um bloco de duas linhas (comando +
    descrição indentada), prontas para ir dentro de um bloco de código
    (```). Cada bloco é devolvido como um único elemento (com \\n interno)
    para que _chunk_lines nunca separe o nome do comando da sua descrição
    ao dividir por campos — e evita o desalinhamento que ocorria quando o
    Discord fazia word-wrap de uma linha comando+descrição comprida num
    ecrã estreito (telemóvel)."""
    return [f"/{name}\n  → {desc}" for name, desc in commands_list]


def _category_color(section_title: str, fallback: discord.Color) -> discord.Color:
    return CATEGORY_COLORS.get(section_title, fallback)


class HelpView(discord.ui.View):
    """Menu de ajuda com dropdown para saltar direto a uma categoria,
    mais botões Início/Anterior/Seguinte para quem prefere navegar em sequência."""

    def __init__(self, embeds: list, section_titles: list, author_id: int, timeout: float = 60):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.section_titles = section_titles
        self.author_id = author_id
        self.index = 0
        self.message = None  # definido depois do ctx.send

        self.select = discord.ui.Select(
            placeholder="📂 Escolhe uma categoria...",
            options=self._build_select_options(),
        )
        self.select.callback = self._on_select
        self.add_item(self.select)

    def _build_select_options(self) -> list:
        # Discord só permite 25 opções por select — corta se algum dia crescer mais que isso.
        # A opção da categoria atual fica marcada como "default" para se destacar no menu.
        return [
            discord.SelectOption(
                label=title[:100],
                value=str(i),
                default=(i == self.index),
            )
            for i, title in enumerate(self.section_titles)
        ][:25]

    def _sync(self):
        """Atualiza o placeholder do select e o estado dos botões para refletir a página atual."""
        self.select.options = self._build_select_options()
        self.select.placeholder = f"📂 {self.section_titles[self.index][:90]}"
        self.home_button.disabled = self.index == 0

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Usa `/help` para abrires o teu próprio menu.", ephemeral=True
            )
            return False
        return True

    async def _on_select(self, interaction: discord.Interaction):
        self.index = int(self.select.values[0])
        self._sync()
        await interaction.response.edit_message(embed=self.embeds[self.index], view=self)

    @discord.ui.button(label="Início", emoji="🏠", style=discord.ButtonStyle.secondary, row=1)
    async def home_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = 0
        self._sync()
        await interaction.response.edit_message(embed=self.embeds[self.index], view=self)

    @discord.ui.button(label="Anterior", emoji="◀", style=discord.ButtonStyle.secondary, row=1)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index - 1) % len(self.embeds)
        self._sync()
        await interaction.response.edit_message(embed=self.embeds[self.index], view=self)

    @discord.ui.button(label="Seguinte", emoji="▶", style=discord.ButtonStyle.secondary, row=1)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index + 1) % len(self.embeds)
        self._sync()
        await interaction.response.edit_message(embed=self.embeds[self.index], view=self)

    @discord.ui.button(label="Fechar", emoji="✖", style=discord.ButtonStyle.danger, row=1)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.message.delete()
        except discord.HTTPException:
            pass

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class Basic(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def _guild_branding(guild: discord.Guild):
        """Nome e ícone do servidor, para usar em set_author() nos embeds de ajuda"""
        if guild is None:
            return {"name": "Mensagens Diretas", "icon_url": None}
        icon_url = guild.icon.url if guild.icon else None
        return {"name": guild.name, "icon_url": icon_url}

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

    async def _fetch_forecast(self, city: str):
        """Obtém previsão meteorológica para os próximos 7 dias"""
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
                    "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
                    "timezone": "auto",
                },
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError("Falha ao consultar previsão")
                forecast_data = await resp.json()

            daily = forecast_data.get("daily") or {}
            daily_units = forecast_data.get("daily_units") or {}

            return {
                "location": location,
                "dates": daily.get("time", []),
                "weather_codes": daily.get("weather_code", []),
                "temp_max": daily.get("temperature_2m_max", []),
                "temp_min": daily.get("temperature_2m_min", []),
                "precipitation": daily.get("precipitation_sum", []),
                "wind_speed": daily.get("wind_speed_10m_max", []),
                "units": {
                    "temp": daily_units.get("temperature_2m_max", "°C"),
                    "precipitation": daily_units.get("precipitation_sum", "mm"),
                    "wind": daily_units.get("wind_speed_10m_max", "km/h"),
                }
            }

    @commands.hybrid_command()
    async def ping(self, ctx):
        """Responde com pong"""
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Latência: {self.bot.latency * 1000:.0f}ms",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command()
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

    @commands.hybrid_command()
    async def sum(self, ctx, a: int, b: int):
        """Somar dois números"""
        result = a + b
        embed = discord.Embed(
            title="🧮 Resultado da Soma",
            description=f"**{a}** + **{b}** = **{result}**",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="tempo", aliases=["weather", "clima"])
    async def tempo(self, ctx, *, city: str = None):
        """Mostra o tempo atual de uma cidade"""
        if not city:
            embed = discord.Embed(
                title="❌ Sintaxe Inválida",
                description="Uso: `/tempo <cidade>`",
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

    @commands.hybrid_command(name="hora", aliases=["time", "horario", "timezone"])
    async def hora(self, ctx, *, city: str = None):
        """Mostra a hora atual de uma cidade"""
        if not city:
            embed = discord.Embed(
                title="❌ Sintaxe Inválida",
                description="Uso: `/hora <cidade>`",
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

    @commands.hybrid_command(name="previsao", aliases=["forecast", "previsão"])
    async def previsao(self, ctx, *, city: str = None):
        """Mostra a previsão meteorológica para os próximos 7 dias"""
        if not city:
            embed = discord.Embed(
                title="❌ Sintaxe Inválida",
                description="Uso: `/previsao <cidade>`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        try:
            data = await self._fetch_forecast(city)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Erro ao obter previsão",
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

        dates = data.get("dates", [])
        weather_codes = data.get("weather_codes", [])
        temp_max = data.get("temp_max", [])
        temp_min = data.get("temp_min", [])
        precipitation = data.get("precipitation", [])
        wind_speed = data.get("wind_speed", [])
        units = data.get("units", {})

        embed = discord.Embed(
            title="📅 Previsão para 7 Dias",
            description=data.get("location", city),
            color=discord.Color.blue()
        )

        # Adicionar previsão para cada dia
        for i in range(min(7, len(dates))):
            try:
                date_str = dates[i]
                date_obj = datetime.fromisoformat(date_str)
                day_name = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"][date_obj.weekday()]
                formatted_date = f"{day_name}, {date_obj.strftime('%d/%m')}"
            except Exception:
                formatted_date = dates[i]

            weather_desc = self._weather_description(weather_codes[i]) if i < len(weather_codes) else "—"
            t_max = f"{temp_max[i]:.1f}{units.get('temp', '°C')}" if i < len(temp_max) else "—"
            t_min = f"{temp_min[i]:.1f}{units.get('temp', '°C')}" if i < len(temp_min) else "—"
            precip = f"{precipitation[i]:.1f}{units.get('precipitation', 'mm')}" if i < len(precipitation) else "—"
            wind = f"{wind_speed[i]:.1f}{units.get('wind', 'km/h')}" if i < len(wind_speed) else "—"

            field_value = f"**{weather_desc}**\n🌡️ {t_min} - {t_max}\n💧 Precipitação: {precip}\n💨 Vento: {wind}"
            embed.add_field(name=formatted_date, value=field_value, inline=True)

        embed.set_footer(text="Fonte: Open-Meteo")
        await ctx.send(embed=embed)

    @commands.hybrid_command()
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

    @commands.hybrid_command(aliases=["guild"])
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
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="clear")
    @commands.has_permissions(administrator=True)
    async def clear(self, ctx, amount: int = None):
        """Apagar mensagens do canal (apenas admin)"""
        await ctx.defer(ephemeral=True)
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
                description="Uso: `/clear [valor]`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(name="regras")
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

    # ---------- helper: constrói as secções de ajuda ----------

    def _build_help_sections(self, is_admin: bool) -> list:
        basic = [
            ("ping", "responde com pong"),
            ("sum <a> <b>", "somar dois números"),
        ]

        info = [
            ("info [@user]", "mostrar informações do utilizador"),
            ("server / guild", "mostrar informações do servidor"),
            ("regras", "mostrar regras do servidor"),
        ]

        weather = [
            ("tempo <cidade>", "mostra o tempo atual"),
            ("hora <cidade>", "mostra a hora atual"),
            ("previsao <cidade>", "previsão para 7 dias"),
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
            ("nivel [@user]", "mostrar nível e XP"),
            ("rank", "mostrar top 10 do ranking"),
        ]

        games = [
            ("termo", "começa um novo jogo de Termo"),
            ("termo_quit / quit", "sai do jogo atual"),
            ("termo_stats / stats [@user]", "estatísticas do Termo"),
            ("termo_rank", "ranking do Termo"),
        ]

        quick_games = [
            ("ppt <pedra|papel|tesoura>", "pedra, papel ou tesoura"),
            ("dado [lados]", "rola um dado de N lados"),
            ("moeda", "atira uma moeda ao ar"),
            ("escolher <op1> <op2> ...", "deixa o bot escolher"),
            ("8ball <pergunta>", "pergunta à bola mágica"),
            ("adivinhar <número>", "adivinha o número (1-10)"),
            ("jogos", "mostra todos os jogos"),
        ]

        code = [
            ("code / desafio", "desafio de programação"),
            ("stats_code", "estatísticas dos desafios"),
        ]

        reminders = [
            ("lembrar <tempo> <mensagem>", "cria um lembrete (ex: 10m, 2h, 1d)"),
            ("lembretes", "lista os teus lembretes pendentes"),
            ("lembrete_cancelar <id>", "cancela um lembrete"),
        ]

        polls = [
            ("poll <pergunta>", "cria enquete sim/não"),
            ("poll <pergunta> | op1 | op2 ...", "cria enquete de opções (até 10)"),
            ("poll_fechar <id_mensagem>", "fecha enquete e mostra resultados"),
        ]

        automod_geral = [
            ("automod", "mostra o estado da auto-moderação"),
            ("automod_whitelist", "lista domínios permitidos"),
            ("automod_perms", "lista quem tem permissão de mod automod"),
        ]

        tickets = [
            ("ticket <motivo>", "abre um ticket privado com a staff"),
        ]

        news = [
            ("noticias [categoria]", "últimas notícias (geral, tecnologia, desporto, etc.)"),
        ]

        sections = [
            ("⚙️ Básico", basic),
            ("ℹ️ Informação", info),
            ("🌤️ Meteorologia", weather),
            ("🎵 Música", music),
            ("📊 Níveis", levels),
            ("🎮 Jogos - Termo", games),
            ("🎲 Jogos Rápidos", quick_games),
            ("💻 Desafios de Código", code),
            ("⏰ Lembretes", reminders),
            ("📊 Enquetes", polls),
            ("🛡️ Auto-Moderação", automod_geral),
            ("🎫 Tickets", tickets),
            ("📰 Notícias", news),
        ]

        if is_admin:
            automod_admin = [
                ("automod_on / automod_off", "liga/desliga tudo"),
                ("automod_antispam <on|off>", "liga/desliga anti-spam"),
                ("automod_antilinks <on|off>", "liga/desliga anti-links"),
                ("automod_whitelist_add <dom.>", "permite um domínio"),
                ("automod_whitelist_remove <dom.>", "remove um domínio"),
                ("automod_addperm @user", "dá permissão de mod automod"),
                ("automod_removeperm @user", "remove essa permissão"),
            ]

            moderation = [
                ("warn @user <motivo>", "dá um aviso"),
                ("warnings [@user]", "lista avisos"),
                ("warn_remove @user <id>", "remove um aviso"),
                ("kick @user [motivo]", "expulsa um membro"),
                ("ban @user [motivo]", "bane um membro"),
                ("unban <user_id>", "remove um ban"),
                ("modlog_canal [#canal]", "define/mostra o canal de log"),
            ]

            antiraid = [
                ("antiraid", "mostra o estado do anti-raid"),
                ("antiraid_on / antiraid_off", "liga/desliga"),
                ("antiraid_config <n> <s> <dias>", "ajusta sensibilidade"),
                ("antiraid_lockdown_on/off", "ativa/desativa lockdown manual"),
            ]

            admin = [
                ("write <message>", "ecoar mensagem"),
                ("clear [amount]", "apagar mensagens do canal"),
                ("addxp @user <value>", "adicionar XP a um utilizador"),
                ("removexp @user <value>", "remover XP a um utilizador"),
                ("syncroles [@user]", "sincroniza os cargos de nível com o nível atual"),
                ("ticketpanel", "posta o painel de abertura de tickets"),
                ("noticias_canal <#canal> [categoria]", "define o canal de notícias automáticas (8h, 13h, 20h)"),
            ]

            sections.append(("🛡️ Auto-Moderação (Admin)", automod_admin))
            sections.append(("🔨 Moderação", moderation))
            sections.append(("🚨 Anti-Raid", antiraid))
            sections.append(("👑 Admin", admin))

        return sections

    def _find_command_category(self, cmd: commands.Command, sections: list) -> str:
        """Encontra em que secção do /help um comando está listado, comparando
        pelo nome principal e pelos aliases."""
        names = {cmd.name} | set(cmd.aliases)
        for section_title, commands_list in sections:
            for key, _desc in commands_list:
                tokens = set(re.split(r'[ /<\[\]]+', key)) - {""}
                if names & tokens:
                    return section_title
        return "—"

    def _build_command_detail_embed(self, cmd: commands.Command, ctx, sections: list) -> discord.Embed:
        """Constrói o embed de detalhe para /help <comando>: sintaxe, aliases, categoria e exemplo"""
        usage = f"/{cmd.qualified_name}"
        if cmd.signature:
            usage += f" {cmd.signature}"

        category = self._find_command_category(cmd, sections)
        color = _category_color(category, discord.Color.blurple())

        embed = discord.Embed(
            title=f"📖 /{cmd.qualified_name}",
            description=f"*{cmd.help or cmd.short_doc or 'Sem descrição disponível.'}*",
            color=color,
        )
        embed.set_author(**self._guild_branding(ctx.guild))
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        embed.add_field(name="📌 Categoria", value=category, inline=True)
        embed.add_field(name="🧭 Sintaxe", value=f"```{usage}```", inline=False)

        if cmd.aliases:
            aliases = " • ".join(f"`/{a}`" for a in cmd.aliases)
            embed.add_field(name="🔀 Aliases", value=aliases, inline=False)

        example = COMMAND_EXAMPLES.get(cmd.name)
        if example:
            embed.add_field(name="💡 Exemplo", value=f"```{example}```", inline=False)

        embed.set_footer(text="/help para veres todos os comandos")
        return embed

    @commands.hybrid_command(name="help")
    async def help_cmd(self, ctx, comando: str = None):
        """Mostrar todos os comandos disponíveis, ou detalhes de um comando específico"""
        is_admin = ctx.author.guild_permissions.administrator
        sections = self._build_help_sections(is_admin)

        if comando:
            cmd = self.bot.get_command(comando.lstrip("/"))
            if cmd is None:
                embed = discord.Embed(
                    title="❌ Comando não encontrado",
                    description=f"Não encontrei nenhum comando chamado `{comando}`.\nUsa `/help` sem argumentos para veres a lista completa.",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            embed = self._build_command_detail_embed(cmd, ctx, sections)
            await ctx.send(embed=embed)
            return

        title = "📖 Central de Ajuda — Admin" if is_admin else "📖 Central de Ajuda"
        default_color = DEFAULT_ADMIN_COLOR if is_admin else DEFAULT_HELP_COLOR
        branding = self._guild_branding(ctx.guild)

        total_categories = len(sections)
        total_commands = sum(len(cmds) for _, cmds in sections)

        embeds = []
        for page, (section_title, commands_list) in enumerate(sections, start=1):
            lines = _format_section_lines(commands_list)
            chunks = _chunk_lines(lines) or ["(sem comandos)"]
            color = _category_color(section_title, default_color)

            embed = discord.Embed(
                title=title,
                description=(
                    f"**{total_categories} categorias • {total_commands} comandos**\n"
                    "Escolhe uma categoria no menu abaixo 👇 ou usa `/help <comando>` para detalhes.\n"
                    "─────────────────────────"
                ),
                color=color,
            )
            embed.set_author(**branding)
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

            for i, chunk in enumerate(chunks):
                field_name = (
                    f"{section_title}  •  {len(commands_list)} comando(s)"
                    if i == 0
                    else f"{section_title} (cont.)"
                )
                embed.add_field(name=field_name, value=f"```{chunk}```", inline=False)

            embed.set_footer(
                text=f"📄 Categoria {page}/{total_categories}  •  {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url,
            )
            embeds.append(embed)

        section_titles = [s[0] for s in sections]
        view = HelpView(embeds, section_titles, author_id=ctx.author.id)
        view._sync()
        message = await ctx.send(embed=embeds[0], view=view)
        view.message = message


async def setup(bot: commands.Bot):
    await bot.add_cog(Basic(bot))