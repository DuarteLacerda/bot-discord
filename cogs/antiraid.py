"""
Cog de Anti-Raid
-------------------
Deteta rajadas de membros a entrar em pouco tempo e ativa um "lockdown"
automático: sobe o verification level do servidor ao máximo (impede
contas muito recentes de interagir/entrar) e expulsa quem entrou na
rajada com uma conta demasiado nova. Reverte sozinho ao fim de um
tempo configurável.

Comandos (todos admin, exceto o status):
    /antiraid                          - mostra o estado atual
    /antiraid_on / /antiraid_off       - liga/desliga o sistema
    /antiraid_config <n> <segs> <dias> - configura sensibilidade
    /antiraid_lockdown_on              - ativa lockdown manualmente
    /antiraid_lockdown_off             - desativa lockdown manualmente

Configuração por defeito: 5 entradas em 10 segundos dispara o
lockdown; contas com menos de 7 dias são expulsas durante o lockdown;
o lockdown dura 15 minutos e reverte sozinho.
"""

import json
import os
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands, tasks

CONFIG_FILE = os.path.join("data", "antiraid.json")

DEFAULT_CONFIG = {
    "enabled": True,
    "join_threshold": 5,       # nº de entradas...
    "window_seconds": 10,      # ...neste intervalo, dispara o lockdown
    "min_account_age_days": 7, # contas mais novas que isto são expulsas durante o lockdown
    "lockdown_minutes": 15,    # duração do lockdown antes de reverter sozinho
    "lockdown_until": None,    # timestamp (epoch) ou None
    "original_verification_level": None,
}

VERIFICATION_NAMES = {
    discord.VerificationLevel.none: "Nenhuma",
    discord.VerificationLevel.low: "Baixa",
    discord.VerificationLevel.medium: "Média",
    discord.VerificationLevel.high: "Alta",
    discord.VerificationLevel.highest: "Altíssima",
}


class AntiRaid(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.configs: dict[str, dict] = self._load()
        # guild_id -> deque[timestamp] das entradas recentes
        self._recent_joins: dict[int, deque] = defaultdict(deque)
        self.checker.start()

    def cog_unload(self):
        self.checker.cancel()

    # ---------- persistência ----------

    def _load(self) -> dict:
        if not os.path.exists(CONFIG_FILE):
            return {}
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self):
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.configs, f, ensure_ascii=False, indent=2)

    def _get_config(self, guild_id: int) -> dict:
        key = str(guild_id)
        if key not in self.configs:
            self.configs[key] = dict(DEFAULT_CONFIG)
            self._save()
        return self.configs[key]

    # ---------- log (reaproveita o canal de mod-log, se existir) ----------

    async def _log(self, guild: discord.Guild, embed: discord.Embed):
        mod_cog = self.bot.get_cog("Moderation")
        if mod_cog:
            await mod_cog._log(guild, embed)

    # ---------- lockdown ----------

    def _is_locked_down(self, config: dict) -> bool:
        return bool(config["lockdown_until"] and config["lockdown_until"] > time.time())

    async def _activate_lockdown(self, guild: discord.Guild, config: dict, reason: str):
        if config["original_verification_level"] is None:
            config["original_verification_level"] = guild.verification_level.value

        try:
            await guild.edit(
                verification_level=discord.VerificationLevel.highest,
                reason=f"Anti-raid: {reason}",
            )
        except discord.Forbidden:
            pass

        config["lockdown_until"] = time.time() + config["lockdown_minutes"] * 60
        self._save()

        embed = discord.Embed(title="🚨 Lockdown Ativado", color=discord.Color.dark_red())
        embed.add_field(name="Motivo", value=reason, inline=False)
        embed.add_field(name="Duração", value=f"{config['lockdown_minutes']} minutos", inline=True)
        embed.add_field(name="Verification level", value="Altíssima (temporário)", inline=True)
        await self._log(guild, embed)

        try:
            system_channel = guild.system_channel
            if system_channel:
                await system_channel.send(embed=embed)
        except discord.HTTPException:
            pass

    async def _deactivate_lockdown(self, guild: discord.Guild, config: dict, automatic: bool):
        original = config.get("original_verification_level")
        if original is not None:
            try:
                await guild.edit(
                    verification_level=discord.VerificationLevel(original),
                    reason="Anti-raid: lockdown terminado",
                )
            except discord.Forbidden:
                pass

        config["lockdown_until"] = None
        config["original_verification_level"] = None
        self._save()

        embed = discord.Embed(
            title="✅ Lockdown Terminado",
            description="Revertido automaticamente." if automatic else "Revertido manualmente.",
            color=discord.Color.green(),
        )
        await self._log(guild, embed)

    @tasks.loop(seconds=30)
    async def checker(self):
        now = time.time()
        for guild_id, config in list(self.configs.items()):
            if config["lockdown_until"] and config["lockdown_until"] <= now:
                guild = self.bot.get_guild(int(guild_id))
                if guild:
                    await self._deactivate_lockdown(guild, config, automatic=True)

    @checker.before_loop
    async def before_checker(self):
        await self.bot.wait_until_ready()

    # ---------- listener principal ----------

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        config = self._get_config(guild.id)
        if not config["enabled"]:
            return

        now = time.time()
        joins = self._recent_joins[guild.id]
        joins.append(now)
        while joins and now - joins[0] > config["window_seconds"]:
            joins.popleft()

        # já em lockdown: expulsa contas muito novas imediatamente
        if self._is_locked_down(config):
            account_age_days = (datetime.now(timezone.utc) - member.created_at).days
            if account_age_days < config["min_account_age_days"]:
                try:
                    await member.kick(reason="Anti-raid: conta muito recente durante lockdown")
                    embed = discord.Embed(
                        title="👢 Conta Expulsa (Lockdown)",
                        description=f"{member} (conta com {account_age_days} dia(s))",
                        color=discord.Color.red(),
                    )
                    await self._log(guild, embed)
                except discord.Forbidden:
                    pass
            return

        # não está em lockdown: verifica se a rajada dispara um novo
        if len(joins) >= config["join_threshold"]:
            joins.clear()
            await self._activate_lockdown(
                guild, config, reason=f"{config['join_threshold']} entradas em {config['window_seconds']}s"
            )

    # ---------- comandos ----------

    @commands.hybrid_command(name="antiraid")
    async def antiraid_status(self, ctx: commands.Context):
        config = self._get_config(ctx.guild.id)
        embed = discord.Embed(title="🚨 Anti-Raid", color=discord.Color.blurple())
        embed.add_field(name="Estado", value="✅ Ligado" if config["enabled"] else "❌ Desligado", inline=True)
        embed.add_field(
            name="Lockdown", value="🔒 Ativo" if self._is_locked_down(config) else "🔓 Inativo", inline=True
        )
        embed.add_field(
            name="Sensibilidade",
            value=f"{config['join_threshold']} entradas / {config['window_seconds']}s",
            inline=False,
        )
        embed.add_field(name="Idade mínima da conta", value=f"{config['min_account_age_days']} dias", inline=True)
        embed.add_field(name="Duração do lockdown", value=f"{config['lockdown_minutes']} min", inline=True)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="antiraid_on")
    @commands.has_permissions(administrator=True)
    async def antiraid_on(self, ctx: commands.Context):
        config = self._get_config(ctx.guild.id)
        config["enabled"] = True
        self._save()
        await ctx.send("✅ Anti-raid ligado.")

    @commands.hybrid_command(name="antiraid_off")
    @commands.has_permissions(administrator=True)
    async def antiraid_off(self, ctx: commands.Context):
        config = self._get_config(ctx.guild.id)
        config["enabled"] = False
        self._save()
        await ctx.send("❌ Anti-raid desligado.")

    @commands.hybrid_command(name="antiraid_config")
    @commands.has_permissions(administrator=True)
    async def antiraid_config(self, ctx: commands.Context, entradas: int, segundos: int, dias_conta: int):
        if entradas < 2 or segundos < 1 or dias_conta < 0:
            await ctx.send("⚠️ Valores inválidos.")
            return

        config = self._get_config(ctx.guild.id)
        config["join_threshold"] = entradas
        config["window_seconds"] = segundos
        config["min_account_age_days"] = dias_conta
        self._save()

        await ctx.send(
            f"✅ Configurado: **{entradas}** entradas em **{segundos}s** disparam lockdown; "
            f"contas com menos de **{dias_conta} dias** são expulsas durante o lockdown."
        )

    @commands.hybrid_command(name="antiraid_lockdown_on")
    @commands.has_permissions(administrator=True)
    async def antiraid_lockdown_on(self, ctx: commands.Context):
        config = self._get_config(ctx.guild.id)
        if self._is_locked_down(config):
            await ctx.send("⚠️ Já está em lockdown.")
            return
        await self._activate_lockdown(ctx.guild, config, reason=f"ativado manualmente por {ctx.author}")
        await ctx.send("🔒 Lockdown ativado manualmente.")

    @commands.hybrid_command(name="antiraid_lockdown_off")
    @commands.has_permissions(administrator=True)
    async def antiraid_lockdown_off(self, ctx: commands.Context):
        config = self._get_config(ctx.guild.id)
        if not self._is_locked_down(config):
            await ctx.send("⚠️ Não está em lockdown.")
            return
        await self._deactivate_lockdown(ctx.guild, config, automatic=False)
        await ctx.send("🔓 Lockdown desativado manualmente.")

    # ---------- erros ----------

    @antiraid_on.error
    @antiraid_off.error
    @antiraid_config.error
    @antiraid_lockdown_on.error
    @antiraid_lockdown_off.error
    async def antiraid_perm_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Precisas de ser administrador para usar este comando.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("⚠️ Uso: `/antiraid_config <entradas> <segundos> <dias_conta>`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("⚠️ Os três valores têm de ser números inteiros.")


async def setup(bot: commands.Bot):
    await bot.add_cog(AntiRaid(bot))