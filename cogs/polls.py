"""
Cog de Enquetes
-----------------
Cria enquetes rápidas com reações. Fecham automaticamente ao fim de um
tempo (por defeito 24h) e o bot publica os resultados sozinho.

Comandos:
    /poll <pergunta>                                  -> sim/não, expira em 24h
    /poll <pergunta> | opção1 | opção2 | ...          -> até 10 opções, expira em 24h
    /poll <pergunta> | op1 | op2 | --tempo 2h         -> tempo customizado
    /poll_fechar <id_da_mensagem>                     -> fecha manualmente antes do tempo (autor ou admin)

Formatos de tempo aceites: combinações de número + unidade, ex: "30m", "2h", "3d".
Mínimo 5 minutos, máximo 7 dias.

Exemplos:
    /poll Devíamos jogar hoje à noite?
    /poll Qual jogo? | Valorant | LoL | Apex | CS2 | --tempo 1h
"""

import re
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

DEFAULT_SECONDS = 24 * 3600
MIN_SECONDS = 5 * 60
MAX_SECONDS = 7 * 86400

TIME_UNIT_SECONDS = {"m": 60, "h": 3600, "d": 86400}
TEMPO_FLAG_PATTERN = re.compile(r"--tempo\s+(\d+)([mhd])", re.IGNORECASE)


def parse_tempo_flag(texto: str):
    """Extrai '--tempo <n><unidade>' do texto. Devolve (texto_limpo, segundos|None)."""
    match = TEMPO_FLAG_PATTERN.search(texto)
    if not match:
        return texto, None
    value, unit = match.groups()
    seconds = int(value) * TIME_UNIT_SECONDS[unit.lower()]
    texto_limpo = texto[: match.start()] + texto[match.end():]
    return texto_limpo.strip(), seconds


class Polls(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # message_id -> {author_id, channel_id, question, options, expires_at}
        self.active_polls: dict[int, dict] = {}
        self.checker.start()

    def cog_unload(self):
        self.checker.cancel()

    # ---------- fecho automático ----------

    @tasks.loop(seconds=30)
    async def checker(self):
        now = datetime.now(timezone.utc).timestamp()
        expired = [mid for mid, p in self.active_polls.items() if p["expires_at"] <= now]
        for message_id in expired:
            await self._close_poll(message_id, closed_by=None)

    @checker.before_loop
    async def before_checker(self):
        await self.bot.wait_until_ready()

    async def _close_poll(self, message_id: int, closed_by: discord.Member | None):
        poll = self.active_polls.pop(message_id, None)
        if not poll:
            return

        channel = self.bot.get_channel(poll["channel_id"])
        if not channel:
            return

        try:
            msg = await channel.fetch_message(message_id)
        except discord.NotFound:
            return

        embed = discord.Embed(
            title="📊 Resultado da Enquete",
            description=poll["question"],
            color=discord.Color.green(),
        )

        if poll["options"]:
            for i, opt in enumerate(poll["options"]):
                emoji = NUMBER_EMOJIS[i]
                reaction = discord.utils.get(msg.reactions, emoji=emoji)
                count = (reaction.count - 1) if reaction else 0  # -1 remove o voto do bot
                embed.add_field(name=f"{emoji} {opt}", value=f"{count} voto(s)", inline=False)
        else:
            for emoji, label in [("👍", "Sim"), ("👎", "Não")]:
                reaction = discord.utils.get(msg.reactions, emoji=emoji)
                count = (reaction.count - 1) if reaction else 0
                embed.add_field(name=label, value=f"{count} voto(s)", inline=True)

        footer = "Fechada manualmente" if closed_by else "Fechada automaticamente (tempo esgotado)"
        embed.set_footer(text=footer)

        await channel.send(embed=embed)

    # ---------- comandos ----------

    @commands.hybrid_command(name="poll", aliases=["enquete", "votacao", "votação"])
    async def poll(self, ctx: commands.Context, *, texto: str):
        texto, custom_seconds = parse_tempo_flag(texto)

        if custom_seconds is not None:
            if custom_seconds < MIN_SECONDS or custom_seconds > MAX_SECONDS:
                await ctx.send("⚠️ O tempo tem de estar entre 5 minutos e 7 dias.")
                return
            duration = custom_seconds
        else:
            duration = DEFAULT_SECONDS

        parts = [p.strip() for p in texto.split("|") if p.strip()]
        if not parts:
            await ctx.send("⚠️ Precisas de escrever uma pergunta.")
            return

        question = parts[0]
        options = parts[1:]

        if len(options) > 10:
            await ctx.send("⚠️ Máximo de 10 opções por enquete.")
            return

        expires_at = datetime.now(timezone.utc).timestamp() + duration
        expires_str = datetime.fromtimestamp(expires_at, tz=timezone.utc).strftime("%d/%m %H:%M UTC")

        if not options:
            embed = discord.Embed(
                title="📊 Enquete",
                description=question,
                color=discord.Color.blurple(),
            )
            embed.set_footer(text=f"Criada por {ctx.author.display_name} • Expira {expires_str}")
            msg = await ctx.send(embed=embed)
            await msg.add_reaction("👍")
            await msg.add_reaction("👎")
        else:
            lines = [f"{NUMBER_EMOJIS[i]} {opt}" for i, opt in enumerate(options)]
            embed = discord.Embed(
                title="📊 Enquete",
                description=question + "\n\n" + "\n".join(lines),
                color=discord.Color.blurple(),
            )
            embed.set_footer(text=f"Criada por {ctx.author.display_name} • Expira {expires_str}")
            msg = await ctx.send(embed=embed)
            for i in range(len(options)):
                await msg.add_reaction(NUMBER_EMOJIS[i])

        self.active_polls[msg.id] = {
            "author_id": ctx.author.id,
            "channel_id": ctx.channel.id,
            "question": question,
            "options": options or None,
            "expires_at": expires_at,
        }

    @commands.hybrid_command(name="poll_fechar", aliases=["poll_close", "enquete_fechar"])
    async def poll_fechar(self, ctx: commands.Context, message_id: int):
        poll = self.active_polls.get(message_id)
        if not poll:
            await ctx.send("⚠️ Não encontrei essa enquete (ou já foi fechada / bot reiniciou entretanto).")
            return

        is_admin = ctx.author.guild_permissions.administrator
        if ctx.author.id != poll["author_id"] and not is_admin:
            await ctx.send("⚠️ Só o autor da enquete ou um admin pode fechá-la.")
            return

        await self._close_poll(message_id, closed_by=ctx.author)


async def setup(bot: commands.Bot):
    await bot.add_cog(Polls(bot))