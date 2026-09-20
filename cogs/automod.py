"""
Cog de Auto-Moderação
-----------------------
Anti-spam + anti-links, com um sistema de permissões próprio do bot
(independente dos cargos do Discord): utilizadores com permissão de
"moderador automod" ficam isentos das verificações e podem configurar
o sistema, sem precisarem de ser administradores.

Comandos:
    Estado / configuração (admin do Discord apenas):
        L!automod                          - mostra o estado atual
        L!automod_on / L!automod_off       - liga/desliga tudo
        L!automod_antispam <on|off>        - liga/desliga só o anti-spam
        L!automod_antilinks <on|off>       - liga/desliga só o anti-links
        L!automod_whitelist_add <domínio>  - permite um domínio (ex: youtube.com)
        L!automod_whitelist_remove <dom.>  - remove um domínio da whitelist
        L!automod_whitelist               - lista domínios permitidos

    Permissões (dar/remover: admin do Discord apenas; ver: todos):
        L!automod_addperm @user     - dá a alguém permissão de moderador automod
        L!automod_removeperm @user  - remove essa permissão
        L!automod_perms             - lista quem tem essa permissão

Quem tem "permissão automod" (ou é administrador) fica isento do
anti-spam e anti-links, e pode usar os comandos de configuração acima.
"""

import json
import os
import re
import time
from collections import defaultdict, deque
from datetime import timedelta

import discord
from discord.ext import commands

CONFIG_FILE = os.path.join("data", "automod.json")

DEFAULT_GUILD_CONFIG = {
    "enabled": True,
    "anti_spam": True,
    "anti_links": True,
    "mods": [],                # lista de user_id com permissão automod
    "whitelist_domains": [],   # domínios sempre permitidos no anti-links
}

# --- anti-spam: N mensagens em WINDOW segundos dispara ação ---
SPAM_MSG_LIMIT = 5
SPAM_WINDOW_SECONDS = 6
SPAM_TIMEOUT_MINUTES = 5

URL_PATTERN = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)
DOMAIN_PATTERN = re.compile(r"(?:https?://)?(?:www\.)?([^/\s]+)", re.IGNORECASE)


def extract_domain(url: str) -> str:
    match = DOMAIN_PATTERN.match(url)
    return match.group(1).lower() if match else url.lower()


class AutoMod(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.configs: dict[str, dict] = self._load()
        # guild_id -> user_id -> deque[(timestamp, message)]
        self._recent_messages: dict[int, dict[int, deque]] = defaultdict(lambda: defaultdict(deque))

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
            self.configs[key] = dict(DEFAULT_GUILD_CONFIG)
            self._save()
        return self.configs[key]

    # ---------- permissões ----------

    def _is_exempt(self, member: discord.Member) -> bool:
        if member.guild_permissions.administrator:
            return True
        config = self._get_config(member.guild.id)
        return member.id in config["mods"]

    def _check_automod_perm():
        """Decorator: admin OU tem permissão automod."""
        async def predicate(ctx: commands.Context) -> bool:
            if ctx.author.guild_permissions.administrator:
                return True
            cog: AutoMod = ctx.bot.get_cog("AutoMod")
            config = cog._get_config(ctx.guild.id)
            return ctx.author.id in config["mods"]
        return commands.check(predicate)

    # ---------- listener principal ----------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        config = self._get_config(message.guild.id)
        if not config["enabled"]:
            return

        member = message.author
        if self._is_exempt(member):
            return

        if config["anti_links"] and await self._check_links(message, config):
            return  # mensagem já apagada, não verifica spam sobre ela

        if config["anti_spam"]:
            await self._check_spam(message)

    # ---------- anti-links ----------

    async def _check_links(self, message: discord.Message, config: dict) -> bool:
        urls = URL_PATTERN.findall(message.content)
        if not urls:
            return False

        for url in urls:
            domain = extract_domain(url)
            if any(domain == d or domain.endswith("." + d) for d in config["whitelist_domains"]):
                continue

            # domínio não permitido -> apaga e avisa
            try:
                await message.delete()
            except discord.HTTPException:
                pass

            embed = discord.Embed(
                title="🔗 Link Removido",
                description=f"{message.author.mention}, links não estão autorizados neste servidor.",
                color=discord.Color.orange(),
            )
            try:
                warning = await message.channel.send(embed=embed)
                await warning.delete(delay=6)
            except discord.HTTPException:
                pass
            return True

        return False

    # ---------- anti-spam ----------

    async def _check_spam(self, message: discord.Message):
        now = time.time()
        guild_id = message.guild.id
        user_id = message.author.id

        history = self._recent_messages[guild_id][user_id]
        history.append((now, message))

        while history and now - history[0][0] > SPAM_WINDOW_SECONDS:
            history.popleft()

        if len(history) < SPAM_MSG_LIMIT:
            return

        # dispara: apaga as mensagens recentes e aplica timeout
        messages_to_delete = [msg for _, msg in history]
        history.clear()

        for msg in messages_to_delete:
            try:
                await msg.delete()
            except discord.HTTPException:
                pass

        member = message.author
        try:
            await member.timeout(
                discord.utils.utcnow() + timedelta(minutes=SPAM_TIMEOUT_MINUTES),
                reason="Auto-mod: spam detectado",
            )
        except (discord.Forbidden, discord.HTTPException):
            pass

        embed = discord.Embed(
            title="🚫 Spam Detectado",
            description=(
                f"{member.mention} foi silenciado por {SPAM_TIMEOUT_MINUTES} minutos "
                f"por enviar mensagens demasiado rápido."
            ),
            color=discord.Color.red(),
        )
        try:
            await message.channel.send(embed=embed)
        except discord.HTTPException:
            pass

    # ---------- comandos: estado geral ----------

    @commands.command(name="automod")
    async def automod_status(self, ctx: commands.Context):
        config = self._get_config(ctx.guild.id)
        embed = discord.Embed(title="🛡️ Auto-Moderação", color=discord.Color.blurple())
        embed.add_field(name="Estado geral", value="✅ Ligado" if config["enabled"] else "❌ Desligado", inline=True)
        embed.add_field(name="Anti-Spam", value="✅ Ligado" if config["anti_spam"] else "❌ Desligado", inline=True)
        embed.add_field(name="Anti-Links", value="✅ Ligado" if config["anti_links"] else "❌ Desligado", inline=True)
        embed.add_field(
            name="Domínios na whitelist",
            value=str(len(config["whitelist_domains"])) or "0",
            inline=True,
        )
        embed.add_field(name="Moderadores automod", value=str(len(config["mods"])), inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="automod_on")
    @commands.has_permissions(administrator=True)
    async def automod_on(self, ctx: commands.Context):
        config = self._get_config(ctx.guild.id)
        config["enabled"] = True
        self._save()
        await ctx.send("✅ Auto-moderação ligada.")

    @commands.command(name="automod_off")
    @commands.has_permissions(administrator=True)
    async def automod_off(self, ctx: commands.Context):
        config = self._get_config(ctx.guild.id)
        config["enabled"] = False
        self._save()
        await ctx.send("❌ Auto-moderação desligada.")

    @commands.command(name="automod_antispam")
    @commands.has_permissions(administrator=True)
    async def automod_antispam(self, ctx: commands.Context, estado: str):
        config = self._get_config(ctx.guild.id)
        if estado.lower() not in ("on", "off"):
            await ctx.send("⚠️ Usa `on` ou `off`.")
            return
        config["anti_spam"] = estado.lower() == "on"
        self._save()
        await ctx.send(f"Anti-spam {'ligado' if config['anti_spam'] else 'desligado'}.")

    @commands.command(name="automod_antilinks")
    @commands.has_permissions(administrator=True)
    async def automod_antilinks(self, ctx: commands.Context, estado: str):
        config = self._get_config(ctx.guild.id)
        if estado.lower() not in ("on", "off"):
            await ctx.send("⚠️ Usa `on` ou `off`.")
            return
        config["anti_links"] = estado.lower() == "on"
        self._save()
        await ctx.send(f"Anti-links {'ligado' if config['anti_links'] else 'desligado'}.")

    # ---------- comandos: whitelist de domínios ----------

    @commands.command(name="automod_whitelist_add")
    @commands.has_permissions(administrator=True)
    async def automod_whitelist_add(self, ctx: commands.Context, dominio: str):
        config = self._get_config(ctx.guild.id)
        dominio = dominio.lower().strip()
        if dominio in config["whitelist_domains"]:
            await ctx.send(f"`{dominio}` já está na whitelist.")
            return
        config["whitelist_domains"].append(dominio)
        self._save()
        await ctx.send(f"✅ `{dominio}` adicionado à whitelist.")

    @commands.command(name="automod_whitelist_remove")
    @commands.has_permissions(administrator=True)
    async def automod_whitelist_remove(self, ctx: commands.Context, dominio: str):
        config = self._get_config(ctx.guild.id)
        dominio = dominio.lower().strip()
        if dominio not in config["whitelist_domains"]:
            await ctx.send(f"`{dominio}` não está na whitelist.")
            return
        config["whitelist_domains"].remove(dominio)
        self._save()
        await ctx.send(f"🗑️ `{dominio}` removido da whitelist.")

    @commands.command(name="automod_whitelist")
    async def automod_whitelist(self, ctx: commands.Context):
        config = self._get_config(ctx.guild.id)
        domains = config["whitelist_domains"]
        if not domains:
            await ctx.send("A whitelist está vazia.")
            return
        embed = discord.Embed(
            title="✅ Domínios Permitidos",
            description="\n".join(f"• {d}" for d in domains),
            color=discord.Color.green(),
        )
        await ctx.send(embed=embed)

    # ---------- comandos: permissões automod ----------

    @commands.command(name="automod_addperm")
    @commands.has_permissions(administrator=True)
    async def automod_addperm(self, ctx: commands.Context, member: discord.Member):
        config = self._get_config(ctx.guild.id)
        if member.id in config["mods"]:
            await ctx.send(f"{member.mention} já tem permissão de moderador automod.")
            return
        config["mods"].append(member.id)
        self._save()
        await ctx.send(f"✅ {member.mention} agora tem permissão de moderador automod (isento + pode configurar).")

    @commands.command(name="automod_removeperm")
    @commands.has_permissions(administrator=True)
    async def automod_removeperm(self, ctx: commands.Context, member: discord.Member):
        config = self._get_config(ctx.guild.id)
        if member.id not in config["mods"]:
            await ctx.send(f"{member.mention} não tinha essa permissão.")
            return
        config["mods"].remove(member.id)
        self._save()
        await ctx.send(f"🗑️ Permissão de moderador automod removida de {member.mention}.")

    @commands.command(name="automod_perms")
    async def automod_perms(self, ctx: commands.Context):
        config = self._get_config(ctx.guild.id)
        admins = [m for m in ctx.guild.members if m.guild_permissions.administrator]
        mod_ids = config["mods"]

        embed = discord.Embed(title="🛡️ Permissões de Auto-Moderação", color=discord.Color.blurple())

        admin_text = "\n".join(f"• {m.mention} (admin)" for m in admins) or "—"
        embed.add_field(name="Administradores (sempre isentos)", value=admin_text, inline=False)

        if mod_ids:
            mod_text = "\n".join(f"• <@{uid}>" for uid in mod_ids)
        else:
            mod_text = "Nenhum moderador automod atribuído."
        embed.add_field(name="Moderadores automod (permissão dada)", value=mod_text, inline=False)

        await ctx.send(embed=embed)

    # ---------- erros ----------

    @automod_on.error
    @automod_off.error
    @automod_antispam.error
    @automod_antilinks.error
    @automod_whitelist_add.error
    @automod_whitelist_remove.error
    @automod_addperm.error
    @automod_removeperm.error
    async def automod_perm_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Precisas de ser administrador para usar este comando.")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("⚠️ Não encontrei esse membro.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("⚠️ Faltam argumentos. Confirma a sintaxe no `L!help`.")


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoMod(bot))