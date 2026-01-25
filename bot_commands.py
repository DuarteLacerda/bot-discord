import asyncio
import json
import os

import discord
from discord.ext import commands

class Basic(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(aliases=["pong"])
    async def ping(self, ctx):
        await ctx.send("Pong!")

    @commands.command(aliases=["write"])
    @commands.has_permissions(administrator=True)
    async def escrever(self, ctx, *, message: str):
        await ctx.send(message)

    @escrever.error
    async def escrever_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Precisas de permissões de administrador para usar este comando.")

    @commands.command(aliases=["add"])
    async def somar(self, ctx, a: int, b: int):
        result = a + b
        await ctx.send(f"A soma de {a} e {b} é {result}.")

    @commands.command(aliases=["user"])
    async def info(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        embed = discord.Embed(title="Informações do Usuário", color=discord.Color.blue())
        embed.add_field(name="Nome", value=member.name, inline=True)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="Conta criada em", value=member.created_at.strftime("%d/%m/%Y %H:%M:%S"), inline=False)
        avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
        embed.set_thumbnail(url=avatar_url)
        await ctx.send(embed=embed)

    @commands.command(aliases=["server"])
    async def servidor(self, ctx):
        guild = ctx.guild
        embed = discord.Embed(title="Informações do Servidor", color=discord.Color.green())
        embed.add_field(name="Nome do Servidor", value=guild.name, inline=True)
        embed.add_field(name="Membros", value=guild.member_count, inline=False)
        embed.add_field(name="Criado em", value=guild.created_at.strftime("%d/%m/%Y %H:%M:%S"), inline=False)
        embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)
        await ctx.send(embed=embed)

    @commands.command(name="limpar", aliases=["clear"])
    @commands.has_permissions(administrator=True)
    async def limpar(self, ctx, quantidade: int = None):
        """Apaga mensagens do canal (apenas admins)."""
        if quantidade is None:
            # Apaga todas as mensagens (até limite do Discord de 14 dias)
            await ctx.send("⚠️ Tens a certeza que queres apagar todas as mensagens? Escreve `confirmar` nos próximos 10 segundos.")
            
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == "confirmar"
            
            try:
                await self.bot.wait_for("message", timeout=10.0, check=check)
                deleted = await ctx.channel.purge(limit=None)
                msg = await ctx.send(f"✅ {len(deleted)} mensagens apagadas.")
                await asyncio.sleep(3)
                await msg.delete()
            except asyncio.TimeoutError:
                await ctx.send("❌ Operação cancelada.")
        else:
            if quantidade <= 0:
                await ctx.send("❌ A quantidade deve ser positiva.")
                return
            # Apaga mensagens + o comando
            deleted = await ctx.channel.purge(limit=quantidade + 1)
            msg = await ctx.send(f"✅ {len(deleted) - 1} mensagens apagadas.")
            await asyncio.sleep(3)
            await msg.delete()

    @limpar.error
    async def limpar_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Precisas de permissões de administrador para usar este comando.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Uso correto: `l!limpar [quantidade]`")

    @commands.command(name="rules", aliases=["regras"])
    async def rules(self, ctx):
        """Mostra as regras do servidor."""
        rules_file = "rules.json"
        
        if not os.path.exists(rules_file):
            await ctx.send("❌ Ficheiro de regras não encontrado.")
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
            await ctx.send(f"❌ Erro ao carregar regras: {e}")

    @commands.command(name="help", aliases=["ajuda"])
    async def help_cmd(self, ctx):
        """Mostra todos os comandos disponíveis."""
        prefix = ctx.prefix or ""
        
        # Se é admin, mostra só comandos de admin
        if ctx.author.guild_permissions.administrator:
            gerais = [
                ("ping / pong", "responde Pong!"),
                ("escrever / write <mensagem>", "eco da mensagem (só admins)"),
                ("somar / add <a> <b>", "soma dois números"),
                ("info / user [@user]", "info do usuário"),
                ("servidor / server", "info do servidor"),
                ("rules / regras", "mostra as regras do servidor"),
                ("limpar / clear [quantidade]", "apaga mensagens do canal (só admins)"),
            ]

            musica = [
                ("join / entrar / j", "entra no teu canal de voz"),
                ("play / tocar / p <termo|link>", "busca YouTube ou Spotify"),
                ("ytplay / yttocar / ytp <termo|link yt>", "força YouTube"),
                ("splay / stocar / sp <link_spotify>", "toca link de faixa do Spotify"),
                ("skip / pular / sk", "pula a faixa atual"),
                ("stop / parar / s", "limpa fila e sai"),
                ("pause / pausar / pz", "pausa"),
                ("resume / retomar / r", "retoma"),
                ("fila / queue / q", "mostra a fila"),
                ("music_cmds / comandos_musica / mc", "lista comandos de música"),
            ]

            niveis = [
                ("nivel / level [@user]", "mostra nível e XP"),
                ("rank / ranking", "top 10 do servidor"),
                ("addxp / adicionarxp @user <valor>", "adiciona XP (só admins)"),
            ]

            termo = [
                ("termo / t", "inicia um jogo de Termo (adivinhar palavra)"),
                ("termosair / termodesistir", "desiste do jogo atual"),
                ("termostats / testats [@user]", "estatísticas de Termo"),
                ("termorank / termoranking", "ranking de jogadores de Termo"),
            ]

            embed = discord.Embed(title="Ajuda (Admin)", color=discord.Color.red())
            embed.add_field(
                name="Gerais (Admin)",
                value="\n".join(f"• {prefix}{cmd} — {desc}" for cmd, desc in gerais),
                inline=False,
            )
            embed.add_field(
                name="Música",
                value="\n".join(f"• {prefix}{cmd} — {desc}" for cmd, desc in musica),
                inline=False,
            )
            embed.add_field(
                name="Níveis",
                value="\n".join(f"• {prefix}{cmd} — {desc}" for cmd, desc in niveis),
                inline=False,
            )
            embed.add_field(
                name="Jogos 🎮",
                value="\n".join(f"• {prefix}{cmd} — {desc}" for cmd, desc in termo),
                inline=False,
            )
            await ctx.send(embed=embed)
        else:
            # Usuários normais veem só os comandos gerais
            gerais = [
                ("ping / pong", "responde Pong!"),
                ("somar / add <a> <b>", "soma dois números"),
                ("info / user [@user]", "info do usuário"),
                ("servidor / server", "info do servidor"),
                ("rules / regras", "mostra as regras do servidor"),
            ]

            musica = [
                ("join / entrar / j", "entra no teu canal de voz"),
                ("play / tocar / p <termo|link>", "busca YouTube ou Spotify"),
                ("ytplay / yttocar / ytp <termo|link yt>", "força YouTube"),
                ("splay / stocar / sp <link_spotify>", "toca link de faixa do Spotify"),
                ("skip / pular / sk", "pula a faixa atual"),
                ("stop / parar / s", "limpa fila e sai"),
                ("pause / pausar / pz", "pausa"),
                ("resume / retomar / r", "retoma"),
                ("fila / queue / q", "mostra a fila"),
                ("music_cmds / comandos_musica / mc", "lista comandos de música"),
            ]

            niveis = [
                ("nivel / level [@user]", "mostra nível e XP"),
                ("rank / ranking", "top 10 do servidor"),
            ]

            termo = [
                ("termo / t", "inicia um jogo de Termo (adivinhar palavra)"),
                ("termosair / termodesistir", "desiste do jogo atual"),
                ("termostats / testats [@user]", "estatísticas de Termo"),
                ("termorank / termoranking", "ranking de jogadores de Termo"),
            ]

            embed = discord.Embed(title="Ajuda", color=discord.Color.orange())
            embed.add_field(
                name="Gerais",
                value="\n".join(f"• {prefix}{cmd} — {desc}" for cmd, desc in gerais),
                inline=False,
            )
            embed.add_field(
                name="Música",
                value="\n".join(f"• {prefix}{cmd} — {desc}" for cmd, desc in musica),
                inline=False,
            )
            embed.add_field(
                name="Níveis",
                value="\n".join(f"• {prefix}{cmd} — {desc}" for cmd, desc in niveis),
                inline=False,
            )
            embed.add_field(
                name="Jogos 🎮",
                value="\n".join(f"• {prefix}{cmd} — {desc}" for cmd, desc in termo),
                inline=False,
            )
            await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Basic(bot))
