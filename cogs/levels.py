import asyncio
import logging
import random
from typing import Dict

import discord
from discord.ext import commands

from database import Database

# ===== BALANCE CONFIGURATION =====
XP_POR_CARACTERE = 0.5  # XP gained per character
XP_MIN_POR_MSG = 5      # Minimum XP per message
XP_MAX_POR_MSG = 50     # Maximum XP per message (cap to prevent spam)
COOLDOWN_SEGUNDOS = 10  # Cooldown between XP-giving messages
XP_BASE_NIVEL = 100     # XP needed to go from level 1 to 2
XP_MULTIPLICADOR = 1.15 # Multiplicador de XP per level (progression)
NIVEL_MAXIMO = 500      # Maximum level
LEVEL_ROLE_INTERVAL = 10  # A cada quantos níveis se ganha uma role nova
# ====================================

# ===== CASE OPENING REWARDS =====
PREMIOS = [
    {"nome": "💰 Small XP Bonus", "tipo": "xp", "valor": 50, "peso": 40},
    {"nome": "💎 Medium XP Bonus", "tipo": "xp", "valor": 150, "peso": 25},
    {"nome": "🌟 Large XP Bonus", "tipo": "xp", "valor": 300, "peso": 15},
    {"nome": "🔥 Epic XP Bonus", "tipo": "xp", "valor": 500, "peso": 10},
    {"nome": "⚡ 2x Multiplier (next 10 msgs)", "tipo": "multiplicador", "valor": 2, "peso": 8},
    {"nome": "🎁 Nothing special... but fun!", "tipo": "nada", "valor": 0, "peso": 2},
]
# ====================================


class Levels(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = Database()
        self.cooldowns: Dict[int, Dict[int, float]] = {}  # {guild_id: {user_id: timestamp}}

    def _xp_para_proximo_nivel(self, nivel: int) -> int:
        """Calculate XP needed to level up"""
        return int(XP_BASE_NIVEL * (XP_MULTIPLICADOR ** (nivel - 1)))

    def _calcular_nivel(self, xp: int) -> int:
        """Calculate level based on total XP"""
        nivel = 1
        xp_acumulado = 0
        while nivel < NIVEL_MAXIMO:
            xp_necessario = self._xp_para_proximo_nivel(nivel)
            if xp < xp_acumulado + xp_necessario:
                break
            xp_acumulado += xp_necessario
            nivel += 1
        return nivel

    def _sortear_premio(self) -> Dict:
        """Raffle a reward based on weights"""
        pesos = [p["peso"] for p in PREMIOS]
        return random.choices(PREMIOS, weights=pesos, k=1)[0]

    def _milestones_atingidos(self, nivel_anterior: int, nivel_novo: int) -> list[int]:
        """Devolve a lista de marcos (múltiplos de LEVEL_ROLE_INTERVAL) ultrapassados"""
        primeiro_marco = ((nivel_anterior // LEVEL_ROLE_INTERVAL) + 1) * LEVEL_ROLE_INTERVAL
        return list(range(primeiro_marco, nivel_novo + 1, LEVEL_ROLE_INTERVAL))

    async def _get_or_create_level_role(self, guild: discord.Guild, nivel: int) -> discord.Role | None:
        """Obtém (ou cria) a role visual correspondente a este marco de nível"""
        nome_role = f"Nível {nivel}"
        role = discord.utils.get(guild.roles, name=nome_role)
        if role:
            return role
        try:
            role = await guild.create_role(
                name=nome_role,
                permissions=discord.Permissions.none(),
                color=discord.Color.gold(),
                hoist=False,
                mentionable=False,
                reason="Criação automática de role de nível",
            )
            return role
        except discord.Forbidden:
            logging.warning(f"Sem permissão para criar a role '{nome_role}' em {guild.name}")
            return None

    async def _award_level_roles(self, member: discord.Member, nivel_anterior: int, nivel_novo: int):
        """Atribui todas as roles de nível ultrapassadas entre nivel_anterior e nivel_novo"""
        marcos = self._milestones_atingidos(nivel_anterior, nivel_novo)
        for marco in marcos:
            role = await self._get_or_create_level_role(member.guild, marco)
            if role and role not in member.roles:
                try:
                    await member.add_roles(role, reason=f"Atingiu o nível {marco}")
                except discord.Forbidden:
                    logging.warning(f"Sem permissão para atribuir a role '{role.name}' a {member}")

    async def _abrir_case(self, channel: discord.TextChannel, member: discord.Member) -> Dict:
        """Simulate case opening and return reward"""
        msg = await channel.send(f"🎁 {member.mention} is opening a reward box...")
        await asyncio.sleep(1)
        await msg.edit(content=f"🎁 {member.mention} is opening a reward box... 🔄")
        await asyncio.sleep(1)
        
        premio = self._sortear_premio()
        
        embed = discord.Embed(
            title="🎉 Reward Obtained!",
            description=f"**{premio['nome']}**",
            color=discord.Color.gold(),
        )
        embed.set_footer(text="Level Up! New level reached!")
        
        await msg.edit(content=None, embed=embed)
        return premio

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bots and messages without guild
        if message.author.bot or not message.guild:
            return

        guild_id = message.guild.id
        user_id = message.author.id

        # Cooldown
        import time
        now = time.time()
        if guild_id not in self.cooldowns:
            self.cooldowns[guild_id] = {}
        last_msg = self.cooldowns[guild_id].get(user_id, 0)
        if now - last_msg < COOLDOWN_SEGUNDOS:
            return
        self.cooldowns[guild_id][user_id] = now

        # Calculate XP gained
        caracteres = len(message.content)
        xp_ganho = caracteres * XP_POR_CARACTERE
        xp_ganho = max(XP_MIN_POR_MSG, min(xp_ganho, XP_MAX_POR_MSG))

        # Update data
        user_data = self.db.get_user_data(guild_id, user_id)
        if not user_data:
            user_data = {"xp": 0, "level": 1, "multiplicador": 1, "msgs_mult": 0}
        
        # Apply multiplier if active
        if user_data["multiplicador"] > 1 and user_data["msgs_mult"] > 0:
            xp_ganho *= user_data["multiplicador"]
            user_data["msgs_mult"] -= 1
            if user_data["msgs_mult"] <= 0:
                user_data["multiplicador"] = 1
        
        nivel_anterior = user_data["level"]
        user_data["xp"] += int(xp_ganho)
        nivel_novo = self._calcular_nivel(user_data["xp"])

        if nivel_novo > nivel_anterior and nivel_novo <= NIVEL_MAXIMO:
            user_data["level"] = nivel_novo
            self.db.set_user_data(guild_id, user_id, user_data["xp"], user_data["level"], user_data["multiplicador"], user_data["msgs_mult"])
            await self._award_level_roles(message.author, nivel_anterior, nivel_novo)
            try:
                premio = await self._abrir_case(message.channel, message.author)
                
                if premio["tipo"] == "xp":
                    user_data["xp"] += premio["valor"]
                    nivel_pos_bonus = self._calcular_nivel(user_data["xp"])
                    if nivel_pos_bonus > nivel_novo:
                        user_data["level"] = nivel_pos_bonus
                        await self._award_level_roles(message.author, nivel_novo, nivel_pos_bonus)
                        result_embed = discord.Embed(
                            title="🚀 Level Up!",
                            description=f"{message.author.mention} gained enough XP to level up again! Now at level **{nivel_pos_bonus}**!",
                            color=discord.Color.green()
                        )
                        await message.channel.send(embed=result_embed)
                elif premio["tipo"] == "multiplicador":
                    user_data["multiplicador"] = premio["valor"]
                    user_data["msgs_mult"] = 10
                
                self.db.set_user_data(guild_id, user_id, user_data["xp"], user_data["level"], user_data["multiplicador"], user_data["msgs_mult"])
            except Exception:
                logging.exception("Failed to open case")
        else:
            # Save changes
            self.db.set_user_data(guild_id, user_id, user_data["xp"], user_data["level"], user_data["multiplicador"], user_data["msgs_mult"])

    @commands.hybrid_command(name="nivel")
    async def level(self, ctx, member: discord.Member = None):
        """Show user level and XP"""
        member = member or ctx.author
        if not ctx.guild:
            embed = discord.Embed(
                title="❌ Erro",
                description="Este comando está disponível apenas em servidores.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        user_data = self.db.get_user_data(ctx.guild.id, member.id)
        if not user_data:
            user_data = {"xp": 0, "level": 1, "multiplicador": 1, "msgs_mult": 0}
        nivel = user_data["level"]
        xp_atual = user_data["xp"]

        xp_acumulado = 0
        for lvl in range(1, nivel):
            xp_acumulado += self._xp_para_proximo_nivel(lvl)

        xp_no_nivel = xp_atual - xp_acumulado
        xp_necessario = self._xp_para_proximo_nivel(nivel) if nivel < NIVEL_MAXIMO else 0

        embed = discord.Embed(title=f"📊 Nível de {member.display_name}", color=discord.Color.gold())
        embed.add_field(name="Nível", value=f"{nivel}/{NIVEL_MAXIMO}", inline=True)
        embed.add_field(name="XP Total", value=f"{xp_atual}", inline=True)

        # Mostra a role de nível mais alta já conquistada
        role_marco = (nivel // LEVEL_ROLE_INTERVAL) * LEVEL_ROLE_INTERVAL
        if role_marco > 0:
            embed.add_field(name="🏅 Cargo", value=f"Nível {role_marco}", inline=True)

        if user_data.get("multiplicador", 1) > 1 and user_data.get("msgs_mult", 0) > 0:
            embed.add_field(
                name="⚡ Multiplicador Ativo",
                value=f"{user_data['multiplicador']}x ({user_data['msgs_mult']} msgs restantes)",
                inline=False,
            )

        if nivel < NIVEL_MAXIMO:
            embed.add_field(
                name="Progresso",
                value=f"{xp_no_nivel}/{xp_necessario} XP para nível {nivel + 1}",
                inline=False,
            )
        else:
            embed.add_field(name="Estado", value="🏆 Nível Máximo Alcançado!", inline=False)

        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="rank")
    async def rank(self, ctx):
        """Show top 10 leaderboard"""
        if not ctx.guild:
            embed = discord.Embed(
                title="❌ Erro",
                description="Este comando está disponível apenas em servidores.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        ranking = self.db.get_leaderboard(ctx.guild.id, 10)
        if not ranking:
            embed = discord.Embed(
                title="🏆 Top 10",
                description="Sem dados de níveis neste servidor.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(title=f"🏆 Top 10 - {ctx.guild.name}", color=discord.Color.purple())
        lines = []
        for i, (user_id, level, xp) in enumerate(ranking, 1):
            member = ctx.guild.get_member(user_id)
            name = member.display_name if member else f"Utilizador {user_id}"
            lines.append(f"{i}. **{name}** - Nível {level} ({xp} XP)")

        embed.description = "\n".join(lines) if lines else "Sem utilizadores no ranking."
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="addxp")
    @commands.has_permissions(administrator=True)
    async def addxp(self, ctx, member: discord.Member, xp: int):
        """Add XP to a user (admin only)"""
        if not ctx.guild:
            embed = discord.Embed(
                title="❌ Erro",
                description="Este comando está disponível apenas em servidores.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        if xp <= 0:
            embed = discord.Embed(
                title="❌ Erro",
                description="A quantidade de XP a adicionar deve ser positiva.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        user_data = self.db.get_user_data(ctx.guild.id, member.id)
        if not user_data:
            user_data = {"xp": 0, "level": 1, "multiplicador": 1, "msgs_mult": 0}
        
        nivel_anterior = user_data["level"]
        user_data["xp"] += xp
        nivel_novo = self._calcular_nivel(user_data["xp"])

        if nivel_novo > nivel_anterior and nivel_novo <= NIVEL_MAXIMO:
            user_data["level"] = nivel_novo
            await self._award_level_roles(member, nivel_anterior, nivel_novo)

        self.db.set_user_data(ctx.guild.id, member.id, user_data["xp"], user_data["level"], user_data["multiplicador"], user_data["msgs_mult"])
        
        level_up_text = f"\nNovo nível: **{nivel_novo}**!" if nivel_novo > nivel_anterior else ""
        embed = discord.Embed(
            title="✅ XP Adicionado",
            description=f"Adicionados **{xp} XP** a {member.mention}.{level_up_text}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @addxp.error
    async def addxp_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Permissão Negada",
                description="Precisas de permissões de administrador para usar este comando.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MemberNotFound):
            embed = discord.Embed(
                title="❌ Erro",
                description="Utilizador não encontrado.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                title="❌ Erro",
                description="Uso: `/addxp @user quantidade`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            
    @commands.hybrid_command(name="removexp")
    @commands.has_permissions(administrator=True)
    async def removexp(self, ctx, member: discord.Member, xp: int):
        """Remove XP a um utilizador (apenas admin)"""
        if not ctx.guild:
            embed = discord.Embed(
                title="❌ Erro",
                description="Este comando está disponível apenas em servidores.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        if xp <= 0:
            embed = discord.Embed(
                title="❌ Erro",
                description="A quantidade de XP a remover deve ser positiva.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        user_data = self.db.get_user_data(ctx.guild.id, member.id)
        if not user_data:
            user_data = {"xp": 0, "level": 1, "multiplicador": 1, "msgs_mult": 0}

        nivel_anterior = user_data["level"]
        user_data["xp"] = max(0, user_data["xp"] - xp)
        nivel_novo = self._calcular_nivel(user_data["xp"])
        user_data["level"] = nivel_novo

        self.db.set_user_data(ctx.guild.id, member.id, user_data["xp"], user_data["level"], user_data["multiplicador"], user_data["msgs_mult"])

        level_down_text = f"\nNovo nível: **{nivel_novo}**." if nivel_novo < nivel_anterior else ""
        embed = discord.Embed(
            title="✅ XP Removido",
            description=f"Removidos **{xp} XP** a {member.mention}.{level_down_text}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @removexp.error
    async def removexp_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Permissão Negada",
                description="Precisas de permissões de administrador para usar este comando.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MemberNotFound):
            embed = discord.Embed(
                title="❌ Erro",
                description="Utilizador não encontrado.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                title="❌ Erro",
                description="Uso: `/removexp @user quantidade`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(name="syncroles")
    @commands.has_permissions(administrator=True)
    async def syncroles(self, ctx, member: discord.Member = None):
        """Sincroniza os cargos de nível de um membro com o nível que já tem"""
        member = member or ctx.author
        if not ctx.guild:
            embed = discord.Embed(
                title="❌ Erro",
                description="Este comando está disponível apenas em servidores.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        user_data = self.db.get_user_data(ctx.guild.id, member.id)
        if not user_data:
            embed = discord.Embed(
                title="❌ Erro",
                description="Sem dados de nível para este utilizador.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        nivel = user_data["level"]
        marcos = range(LEVEL_ROLE_INTERVAL, nivel + 1, LEVEL_ROLE_INTERVAL)
        atribuidas = []
        falhas = []
        for marco in marcos:
            role = await self._get_or_create_level_role(ctx.guild, marco)
            if role and role not in member.roles:
                try:
                    await member.add_roles(role, reason="Sincronização manual de roles de nível")
                    atribuidas.append(role.name)
                except discord.Forbidden:
                    falhas.append(role.name)

        if atribuidas:
            desc = f"✅ Atribuídas: {', '.join(atribuidas)}"
        else:
            desc = "Já tinhas todas as roles correspondentes ao teu nível."
        if falhas:
            desc += f"\n⚠️ Sem permissão para atribuir: {', '.join(falhas)}"

        embed = discord.Embed(
            title="🔄 Sincronização de Cargos",
            description=desc,
            color=discord.Color.green() if atribuidas else discord.Color.blue()
        )
        await ctx.send(embed=embed)

    @syncroles.error
    async def syncroles_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Permissão Negada",
                description="Precisas de permissões de administrador para usar este comando.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MemberNotFound):
            embed = discord.Embed(
                title="❌ Erro",
                description="Utilizador não encontrado.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            
async def setup(bot: commands.Bot):
    await bot.add_cog(Levels(bot))