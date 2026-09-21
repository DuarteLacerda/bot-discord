import io
import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, Optional

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TICKET_CATEGORY_NAME = os.getenv("TICKET_CATEGORY_NAME", "Tickets")
TICKET_STAFF_ROLE_NAME = os.getenv("TICKET_STAFF_ROLE_NAME", "Staff")
TICKET_LOG_CHANNEL_NAME = os.getenv("TICKET_LOG_CHANNEL_NAME", "ticket-logs")

DATA_FILE = "data/tickets.json"


def load_tickets() -> Dict[str, dict]:
    if not os.path.exists(DATA_FILE):
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_tickets(data: Dict[str, dict]):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def sanitize_channel_name(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9-]", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name[:90] or "utilizador"


def is_staff(member: discord.Member) -> bool:
    if member.guild_permissions.manage_guild:
        return True
    role = discord.utils.get(member.guild.roles, name=TICKET_STAFF_ROLE_NAME)
    return bool(role and role in member.roles)


class TicketReasonModal(discord.ui.Modal, title="Abrir Ticket"):
    motivo = discord.ui.TextInput(
        label="Qual é o motivo do ticket?",
        style=discord.TextStyle.paragraph,
        placeholder="Descreve a tua dúvida ou denúncia...",
        max_length=500,
        required=True,
    )

    def __init__(self, cog: "Tickets"):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self.cog.create_ticket(
            member=interaction.user,
            guild=interaction.guild,
            reason=str(self.motivo),
            interaction=interaction,
        )


class TicketPanelView(discord.ui.View):
    def __init__(self, cog: "Tickets"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Abrir Ticket",
        emoji="🎫",
        style=discord.ButtonStyle.blurple,
        custom_id="ticket:open",
    )
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketReasonModal(self.cog))


class TicketControlView(discord.ui.View):
    def __init__(self, cog: "Tickets"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Fechar",
        emoji="🔒",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket:close",
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.close_ticket(interaction)

    @discord.ui.button(
        label="Apagar",
        emoji="🗑️",
        style=discord.ButtonStyle.danger,
        custom_id="ticket:delete",
    )
    async def delete_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.delete_ticket(interaction)


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.tickets: Dict[str, dict] = load_tickets()

    async def cog_load(self):
        self.bot.add_view(TicketPanelView(self))
        self.bot.add_view(TicketControlView(self))

    # ===== HELPERS =====

    def _user_has_open_ticket(self, guild_id: int, user_id: int) -> Optional[int]:
        for channel_id, info in self.tickets.items():
            if (
                info.get("guild_id") == guild_id
                and info.get("user_id") == user_id
                and info.get("status") == "open"
            ):
                return int(channel_id)
        return None

    async def _get_or_create_category(self, guild: discord.Guild) -> Optional[discord.CategoryChannel]:
        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if category:
            return category
        try:
            return await guild.create_category(TICKET_CATEGORY_NAME)
        except discord.Forbidden:
            return None

    async def _get_log_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        return discord.utils.get(guild.text_channels, name=TICKET_LOG_CHANNEL_NAME)

    # ===== CORE LOGIC =====

    async def create_ticket(
        self,
        member: discord.Member,
        guild: discord.Guild,
        reason: str,
        interaction: Optional[discord.Interaction] = None,
        ctx: Optional[commands.Context] = None,
    ):
        async def respond(embed: discord.Embed):
            if interaction:
                await interaction.followup.send(embed=embed, ephemeral=True)
            elif ctx:
                await ctx.send(embed=embed)

        existing = self._user_has_open_ticket(guild.id, member.id)
        if existing:
            embed = discord.Embed(
                title="⚠️ Ticket já aberto",
                description=f"Já tens um ticket aberto: <#{existing}>",
                color=discord.Color.orange(),
            )
            await respond(embed)
            return

        category = await self._get_or_create_category(guild)
        if not category:
            embed = discord.Embed(
                title="❌ Erro",
                description="Não foi possível criar a categoria de tickets (permissões insuficientes).",
                color=discord.Color.red(),
            )
            await respond(embed)
            return

        staff_role = discord.utils.get(guild.roles, name=TICKET_STAFF_ROLE_NAME)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, manage_channels=True, read_message_history=True
            ),
        }
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, manage_messages=True, read_message_history=True
            )

        base_name = f"ticket-{sanitize_channel_name(member.name)}"
        channel_name = base_name
        suffix = 1
        existing_names = {c.name for c in category.text_channels}
        while channel_name in existing_names:
            suffix += 1
            channel_name = f"{base_name}-{suffix}"

        try:
            channel = await guild.create_text_channel(
                channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Ticket de {member} (ID: {member.id})",
            )
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Erro",
                description="Não tenho permissão para criar o canal do ticket.",
                color=discord.Color.red(),
            )
            await respond(embed)
            return

        self.tickets[str(channel.id)] = {
            "guild_id": guild.id,
            "user_id": member.id,
            "status": "open",
            "reason": reason,
            "created_at": datetime.utcnow().isoformat(),
        }
        save_tickets(self.tickets)

        welcome_embed = discord.Embed(
            title="🎫 Novo Ticket",
            description=f"Olá {member.mention}! A equipa vai responder em breve.\n\n**Motivo:**\n{reason}",
            color=discord.Color.blurple(),
        )
        welcome_embed.set_footer(text=f"Aberto por {member}")
        mention_text = f"{member.mention}" + (f" {staff_role.mention}" if staff_role else "")
        await channel.send(
            content=mention_text,
            embed=welcome_embed,
            view=TicketControlView(self),
            allowed_mentions=discord.AllowedMentions(users=True, roles=True),
        )

        confirm_embed = discord.Embed(
            title="✅ Ticket Criado",
            description=f"O teu ticket foi criado: {channel.mention}",
            color=discord.Color.green(),
        )
        await respond(confirm_embed)

    async def close_ticket(self, interaction: discord.Interaction):
        channel_id = str(interaction.channel.id)
        info = self.tickets.get(channel_id)
        if not info:
            await interaction.response.send_message(
                "Este canal não é um ticket válido.", ephemeral=True
            )
            return

        if info["status"] == "closed":
            await interaction.response.send_message("Este ticket já está fechado.", ephemeral=True)
            return

        is_owner = interaction.user.id == info["user_id"]
        if not (is_owner or is_staff(interaction.user)):
            await interaction.response.send_message(
                "Não tens permissão para fechar este ticket.", ephemeral=True
            )
            return

        overwrite = interaction.channel.overwrites_for(interaction.guild.get_member(info["user_id"]))
        overwrite.send_messages = False
        member = interaction.guild.get_member(info["user_id"])
        if member:
            await interaction.channel.set_permissions(member, overwrite=overwrite)

        info["status"] = "closed"
        save_tickets(self.tickets)

        embed = discord.Embed(
            title="🔒 Ticket Fechado",
            description="Este ticket foi fechado. Um membro da staff pode reabri-lo ou apagá-lo.",
            color=discord.Color.orange(),
        )
        await interaction.response.send_message(embed=embed)

    async def delete_ticket(self, interaction: discord.Interaction):
        channel_id = str(interaction.channel.id)
        info = self.tickets.get(channel_id)
        if not info:
            await interaction.response.send_message(
                "Este canal não é um ticket válido.", ephemeral=True
            )
            return

        if not is_staff(interaction.user):
            await interaction.response.send_message(
                "Apenas a staff pode apagar tickets.", ephemeral=True
            )
            return

        await interaction.response.send_message("A gerar transcript e a apagar o canal...", ephemeral=True)

        transcript_file = await self._build_transcript(interaction.channel)
        log_channel = await self._get_log_channel(interaction.guild)
        if log_channel:
            member = interaction.guild.get_member(info["user_id"])
            log_embed = discord.Embed(
                title="🗑️ Ticket Apagado",
                description=(
                    f"**Utilizador:** {member.mention if member else info['user_id']}\n"
                    f"**Motivo:** {info.get('reason', 'N/A')}\n"
                    f"**Apagado por:** {interaction.user.mention}"
                ),
                color=discord.Color.dark_grey(),
            )
            await log_channel.send(embed=log_embed, file=transcript_file)

        self.tickets.pop(channel_id, None)
        save_tickets(self.tickets)

        try:
            await interaction.channel.delete()
        except discord.Forbidden:
            logging.warning("Sem permissão para apagar o canal do ticket %s", channel_id)

    async def _build_transcript(self, channel: discord.TextChannel) -> discord.File:
        lines = []
        async for message in channel.history(limit=None, oldest_first=True):
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M")
            content = message.content or ""
            if message.embeds:
                content += " [embed]"
            if message.attachments:
                attachment_links = ", ".join(a.url for a in message.attachments)
                content += f" [anexos: {attachment_links}]"
            lines.append(f"[{timestamp}] {message.author}: {content}")

        buffer = io.StringIO("\n".join(lines) if lines else "(sem mensagens)")
        return discord.File(fp=io.BytesIO(buffer.getvalue().encode("utf-8")), filename=f"transcript-{channel.name}.txt")

    # ===== COMMANDS =====

    @commands.command(name="ticketpanel")
    @commands.has_permissions(manage_guild=True)
    async def ticketpanel(self, ctx: commands.Context):
        """Posta o painel de abertura de tickets neste canal (admin)"""
        embed = discord.Embed(
            title="🎫 Suporte",
            description="Precisas de ajuda ou queres reportar algo?\nClica no botão abaixo para abrir um ticket privado com a staff.",
            color=discord.Color.blurple(),
        )
        await ctx.send(embed=embed, view=TicketPanelView(self))
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass

    @commands.command(name="ticket")
    async def ticket(self, ctx: commands.Context, *, reason: str = "Sem motivo especificado"):
        """Abre um ticket diretamente por comando"""
        await self.create_ticket(member=ctx.author, guild=ctx.guild, reason=reason, ctx=ctx)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))