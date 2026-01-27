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
            try:
                # Open case and apply reward
                premio = await self._abrir_case(message.channel, message.author)
                
                if premio["tipo"] == "xp":
                    user_data["xp"] += premio["valor"]
                    # Recalculate level after bonus
                    nivel_pos_bonus = self._calcular_nivel(user_data["xp"])
                    if nivel_pos_bonus > nivel_novo:
                        user_data["level"] = nivel_pos_bonus
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

    @commands.command(name="level")
    async def level(self, ctx, member: discord.Member = None):
        """Show user level and XP"""
        member = member or ctx.author
        if not ctx.guild:
            embed = discord.Embed(
                title="❌ Error",
                description="This command is only available in servers.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        user_data = self.db.get_user_data(ctx.guild.id, member.id)
        if not user_data:
            user_data = {"xp": 0, "level": 1, "multiplicador": 1, "msgs_mult": 0}
        nivel = user_data["level"]
        xp_atual = user_data["xp"]

        # Calculate cumulative XP up to current level
        xp_acumulado = 0
        for lvl in range(1, nivel):
            xp_acumulado += self._xp_para_proximo_nivel(lvl)

        xp_no_nivel = xp_atual - xp_acumulado
        xp_necessario = self._xp_para_proximo_nivel(nivel) if nivel < NIVEL_MAXIMO else 0

        embed = discord.Embed(title=f"📊 Level of {member.display_name}", color=discord.Color.gold())
        embed.add_field(name="Level", value=f"{nivel}/{NIVEL_MAXIMO}", inline=True)
        embed.add_field(name="Total XP", value=f"{xp_atual}", inline=True)
        
        # Show active multiplier
        if user_data.get("multiplicador", 1) > 1 and user_data.get("msgs_mult", 0) > 0:
            embed.add_field(
                name="⚡ Active Multiplier",
                value=f"{user_data['multiplicador']}x ({user_data['msgs_mult']} msgs left)",
                inline=False,
            )
        
        if nivel < NIVEL_MAXIMO:
            embed.add_field(
                name="Progress",
                value=f"{xp_no_nivel}/{xp_necessario} XP for level {nivel + 1}",
                inline=False,
            )
        else:
            embed.add_field(name="Status", value="🏆 Maximum Level Reached!", inline=False)

        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="rank")
    async def rank(self, ctx):
        """Show top 10 leaderboard"""
        if not ctx.guild:
            embed = discord.Embed(
                title="❌ Error",
                description="This command is only available in servers.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        ranking = self.db.get_leaderboard(ctx.guild.id, 10)
        if not ranking:
            embed = discord.Embed(
                title="🏆 Top 10",
                description="No level data available on this server.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(title=f"🏆 Top 10 - {ctx.guild.name}", color=discord.Color.purple())
        lines = []
        for i, (user_id, level, xp) in enumerate(ranking, 1):
            member = ctx.guild.get_member(user_id)
            name = member.display_name if member else f"User {user_id}"
            lines.append(f"{i}. **{name}** - Level {level} ({xp} XP)")

        embed.description = "\n".join(lines) if lines else "No users in ranking."
        await ctx.send(embed=embed)

    @commands.command(name="addxp")
    @commands.has_permissions(administrator=True)
    async def addxp(self, ctx, member: discord.Member, xp: int):
        """Add XP to a user (admin only)"""
        if not ctx.guild:
            embed = discord.Embed(
                title="❌ Error",
                description="This command is only available in servers.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        if xp <= 0:
            embed = discord.Embed(
                title="❌ Error",
                description="XP value must be positive.",
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
        
        self.db.set_user_data(ctx.guild.id, member.id, user_data["xp"], user_data["level"], user_data["multiplicador"], user_data["msgs_mult"])
        
        level_up_text = f"\nNew level: **{nivel_novo}**!" if nivel_novo > nivel_anterior else ""
        embed = discord.Embed(
            title="✅ XP Added",
            description=f"Added **{xp} XP** to {member.mention}.{level_up_text}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @addxp.error
    async def addxp_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need administrator permissions to use this command.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MemberNotFound):
            embed = discord.Embed(
                title="❌ Error",
                description="Member not found.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                title="❌ Error",
                description="Usage: `l!addxp @user amount`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Levels(bot))

