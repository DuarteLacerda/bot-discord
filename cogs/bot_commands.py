import asyncio
import json
import os

import discord
from discord.ext import commands

from utils.components import ConfirmView


class Basic(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

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

    @commands.command()
    async def guild(self, ctx):
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
                ("info [@user]", "mostrar informações do utilizador"),
                ("guild", "mostrar informações do servidor"),
                ("rules", "mostrar regras do servidor"),
                ("clear [amount]", "apagar mensagens (apenas admin)"),
            ]

            music = [
                ("join / connect", "juntar ao canal de voz"),
                ("play / p <term|link>", "tocar do YouTube ou Spotify"),
                ("skip / sk", "saltar música atual"),
                ("stop / s", "parar e sair"),
                ("pause / pz", "pausar"),
                ("resume / r", "retomar"),
                ("queue / q", "mostrar fila"),
                ("music", "mostrar comandos de música"),
            ]

            levels = [
                ("level [@user]", "mostrar nível e XP do utilizador"),
                ("rank", "mostrar top 10 do ranking"),
                ("addxp @user <value>", "adicionar XP (apenas admin)"),
            ]

            games = [
                ("termo", "começa um novo jogo de Termo"),
                ("termo_quit / quit", "sai do jogo atual"),
                ("termo_stats / stats [@user]", "mostra as estatísticas do jogo"),
                ("termo_rank / rank", "mostra o ranking do jogo"),
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
                name="🎮 Jogos",
                value=games_text,
                inline=False,
            )
            
            embed.set_footer(text="Usa ` L!help` para detalhes")
            await ctx.send(embed=embed)
        else:
            general = [
                ("ping", "responde com pong"),
                ("sum <a> <b>", "somar dois números"),
                ("info [@user]", "mostrar informações do utilizador"),
                ("guild", "mostrar informações do servidor"),
                ("rules", "mostrar regras do servidor"),
            ]

            music = [
                ("join / connect", "juntar ao canal de voz"),
                ("play / p <term|link>", "tocar do YouTube ou Spotify"),
                ("skip / sk", "saltar música atual"),
                ("stop / s", "parar e sair"),
                ("pause / pz", "pausar"),
                ("resume / r", "retomar"),
                ("queue / q", "mostrar fila"),
                ("music", "mostrar comandos de música"),
            ]

            levels = [
                ("level [@user]", "mostrar nível e XP do utilizador"),
                ("rank", "mostrar top 10 do ranking"),
            ]

            games = [
                ("termo", "começa um novo jogo de Termo"),
                ("termo_quit / quit", "sai do jogo atual"),
                ("termo_stats / stats [@user]", "mostra as estatísticas do jogo"),
                ("termo_rank / rank", "mostra o ranking do jogo"),
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
                name="🎮 Jogos",
                value=games_text,
                inline=False,
            )
            
            embed.set_footer(text="Usa ` L!help` para detalhes")
            await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Basic(bot))

