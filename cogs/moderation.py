"""
Cog de Moderação
------------------
Sistema de avisos (warns) com histórico persistente, kick, ban, unban,
e um canal de log opcional onde todas as ações ficam registadas.

Comandos:
    L!warn @user <motivo>            - dá um aviso a alguém (admin ou mod automod)
    L!warnings [@user]               - lista os avisos de alguém (omite = os teus)
    L!warn_remove @user <id>         - remove um aviso específico (admin)
    L!kick @user [motivo]            - expulsa (precisa de Kick Members)
    L!ban @user [motivo]             - bane (precisa de Ban Members)
    L!unban <user_id>                - remove o ban (precisa de Ban Members)
    L!modlog_canal [#canal]          - define/mostra o canal de log (admin)

Se houver canal de log definido, todas as ações acima são registadas lá
automaticamente com autor, alvo, motivo e hora.
"""

import json
import os
from datetime import datetime, timezone

import discord
from discord.ext import commands

WARNINGS_FILE = os.path.join("data", "warnings.json")
MODLOG_FILE = os.path.join("data", "modlog.json")


def _load(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.warnings = _load(WARNINGS_FILE)   # guild_id -> user_id -> [warn, ...]
        self.modlog = _load(MODLOG_FILE)        # guild_id -> channel_id

    # ---------- helpers ----------

    def _is_automod_mod(self, member: discord.Member) -> bool:
        automod_cog = self.bot.get_cog("AutoMod")
        if not automod_cog:
            return False
        config = automod_cog._get_config(member.guild.id)
        return member.id in config["mods"]

    async def _can_warn(self, ctx: commands.Context) -> bool:
        return ctx.author.guild_permissions.administrator or self._is_automod_mod(ctx.author)

    async def _log(self, guild: discord.Guild, embed: discord.Embed):
        channel_id = self.modlog.get(str(guild.id))
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if channel:
            try:
                await channel.send(embed=embed)
            except discord.HTTPException:
                pass

    def _next_warn_id(self, guild_id: int, user_id: int) -> int:
        user_warns = self.warnings.get(str(guild_id), {}).get(str(user_id), [])
        return (max((w["id"] for w in user_warns), default=0) + 1)

    # ---------- warns ----------

    @commands.command(name="warn")
    async def warn(self, ctx: commands.Context, member: discord.Member, *, motivo: str = "Sem motivo especificado"):
        if not await self._can_warn(ctx):
            await ctx.send("❌ Precisas de ser admin ou moderador automod para avisar alguém.")
            return

        guild_key = str(ctx.guild.id)
        user_key = str(member.id)
        self.warnings.setdefault(guild_key, {}).setdefault(user_key, [])

        warn = {
            "id": self._next_warn_id(ctx.guild.id, member.id),
            "moderator_id": ctx.author.id,
            "reason": motivo,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        }
        self.warnings[guild_key][user_key].append(warn)
        _save(WARNINGS_FILE, self.warnings)

        total = len(self.warnings[guild_key][user_key])

        embed = discord.Embed(
            title="⚠️ Aviso Registado",
            color=discord.Color.orange(),
        )
        embed.add_field(name="Utilizador", value=member.mention, inline=True)
        embed.add_field(name="Total de avisos", value=str(total), inline=True)
        embed.add_field(name="Motivo", value=motivo, inline=False)
        await ctx.send(embed=embed)

        try:
            await member.send(
                f"Recebeste um aviso em **{ctx.guild.name}**.\nMotivo: {motivo}"
            )
        except discord.Forbidden:
            pass

        log_embed = discord.Embed(title="⚠️ Warn", color=discord.Color.orange())
        log_embed.add_field(name="Alvo", value=f"{member} ({member.id})", inline=False)
        log_embed.add_field(name="Moderador", value=str(ctx.author), inline=False)
        log_embed.add_field(name="Motivo", value=motivo, inline=False)
        log_embed.set_footer(text=warn["timestamp"])
        await self._log(ctx.guild, log_embed)

    @commands.command(name="warnings")
    async def warnings_cmd(self, ctx: commands.Context, member: discord.Member = None):
        target = member or ctx.author

        if target != ctx.author and not await self._can_warn(ctx):
            await ctx.send("❌ Só podes ver os teus próprios avisos.")
            return

        user_warns = self.warnings.get(str(ctx.guild.id), {}).get(str(target.id), [])
        if not user_warns:
            await ctx.send(f"{target.mention} não tem avisos.")
            return

        embed = discord.Embed(title=f"⚠️ Avisos de {target.display_name}", color=discord.Color.orange())
        for w in user_warns:
            moderator = ctx.guild.get_member(w["moderator_id"])
            mod_name = moderator.display_name if moderator else f"ID {w['moderator_id']}"
            embed.add_field(
                name=f"#{w['id']} — {w['timestamp']}",
                value=f"**Motivo:** {w['reason']}\n**Por:** {mod_name}",
                inline=False,
            )
        await ctx.send(embed=embed)

    @commands.command(name="warn_remove")
    @commands.has_permissions(administrator=True)
    async def warn_remove(self, ctx: commands.Context, member: discord.Member, warn_id: int):
        guild_key = str(ctx.guild.id)
        user_key = str(member.id)
        user_warns = self.warnings.get(guild_key, {}).get(user_key, [])

        alvo = next((w for w in user_warns if w["id"] == warn_id), None)
        if not alvo:
            await ctx.send("⚠️ Não encontrei esse aviso.")
            return

        user_warns.remove(alvo)
        _save(WARNINGS_FILE, self.warnings)
        await ctx.send(f"🗑️ Aviso #{warn_id} de {member.mention} removido.")

    # ---------- kick / ban ----------

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, motivo: str = "Sem motivo especificado"):
        try:
            await member.send(f"Foste expulso de **{ctx.guild.name}**.\nMotivo: {motivo}")
        except discord.Forbidden:
            pass

        try:
            await member.kick(reason=f"{ctx.author}: {motivo}")
        except discord.Forbidden:
            await ctx.send("❌ Não tenho permissões suficientes para expulsar esse membro.")
            return

        embed = discord.Embed(title="👢 Membro Expulso", color=discord.Color.red())
        embed.add_field(name="Utilizador", value=str(member), inline=True)
        embed.add_field(name="Motivo", value=motivo, inline=False)
        await ctx.send(embed=embed)

        log_embed = discord.Embed(title="👢 Kick", color=discord.Color.red())
        log_embed.add_field(name="Alvo", value=f"{member} ({member.id})", inline=False)
        log_embed.add_field(name="Moderador", value=str(ctx.author), inline=False)
        log_embed.add_field(name="Motivo", value=motivo, inline=False)
        await self._log(ctx.guild, log_embed)

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, *, motivo: str = "Sem motivo especificado"):
        try:
            await member.send(f"Foste banido de **{ctx.guild.name}**.\nMotivo: {motivo}")
        except discord.Forbidden:
            pass

        try:
            await member.ban(reason=f"{ctx.author}: {motivo}", delete_message_days=0)
        except discord.Forbidden:
            await ctx.send("❌ Não tenho permissões suficientes para banir esse membro.")
            return

        embed = discord.Embed(title="🔨 Membro Banido", color=discord.Color.dark_red())
        embed.add_field(name="Utilizador", value=str(member), inline=True)
        embed.add_field(name="Motivo", value=motivo, inline=False)
        await ctx.send(embed=embed)

        log_embed = discord.Embed(title="🔨 Ban", color=discord.Color.dark_red())
        log_embed.add_field(name="Alvo", value=f"{member} ({member.id})", inline=False)
        log_embed.add_field(name="Moderador", value=str(ctx.author), inline=False)
        log_embed.add_field(name="Motivo", value=motivo, inline=False)
        await self._log(ctx.guild, log_embed)

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user_id: int):
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user, reason=f"Unban por {ctx.author}")
        except discord.NotFound:
            await ctx.send("⚠️ Esse utilizador não está banido (ou o ID está errado).")
            return
        except discord.Forbidden:
            await ctx.send("❌ Não tenho permissões suficientes para remover o ban.")
            return

        embed = discord.Embed(title="✅ Ban Removido", color=discord.Color.green())
        embed.add_field(name="Utilizador", value=str(user), inline=True)
        await ctx.send(embed=embed)

        log_embed = discord.Embed(title="✅ Unban", color=discord.Color.green())
        log_embed.add_field(name="Alvo", value=f"{user} ({user.id})", inline=False)
        log_embed.add_field(name="Moderador", value=str(ctx.author), inline=False)
        await self._log(ctx.guild, log_embed)

    # ---------- canal de log ----------

    @commands.command(name="modlog_canal")
    @commands.has_permissions(administrator=True)
    async def modlog_canal(self, ctx: commands.Context, canal: discord.TextChannel = None):
        guild_key = str(ctx.guild.id)

        if canal is None:
            current_id = self.modlog.get(guild_key)
            if not current_id:
                await ctx.send("Não há canal de log definido. Usa `L!modlog_canal #canal` para definir.")
                return
            current = ctx.guild.get_channel(current_id)
            await ctx.send(f"Canal de log atual: {current.mention if current else '(canal apagado)'}")
            return

        self.modlog[guild_key] = canal.id
        _save(MODLOG_FILE, self.modlog)
        await ctx.send(f"✅ Canal de log definido para {canal.mention}.")

    # ---------- erros ----------

    @kick.error
    @ban.error
    @unban.error
    @warn_remove.error
    @modlog_canal.error
    async def moderation_perm_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Não tens permissões suficientes para usar este comando.")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("⚠️ Não encontrei esse membro.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("⚠️ Faltam argumentos. Confirma a sintaxe no `L!help`.")
        elif isinstance(error, commands.ChannelNotFound):
            await ctx.send("⚠️ Não encontrei esse canal.")

    @warn.error
    async def warn_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MemberNotFound):
            await ctx.send("⚠️ Não encontrei esse membro.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("⚠️ Uso: `L!warn @user <motivo>`")


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))