"""
Cog de Lembretes
-----------------
Permite aos utilizadores criar lembretes que o bot envia mais tarde,
por DM ou no canal onde foi pedido.

Comandos:
    L!lembrar <tempo> <mensagem>   -> cria um lembrete (ex: L!lembrar 10m estudar POO)
    L!lembretes                    -> lista os teus lembretes pendentes
    L!lembrete_cancelar <id>       -> cancela um lembrete pelo id

Formatos de tempo aceites: combinações de números + unidade, ex: "1d2h30m", "45s", "3h".
Unidades: s (segundos), m (minutos), h (horas), d (dias).

Guarda os lembretes em data/reminders.json para sobreviverem a reinícios do bot,
tal como os outros ficheiros em data/.
"""

import json
import os
import re
import asyncio
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands, tasks

REMINDERS_FILE = os.path.join("data", "reminders.json")

TIME_UNIT_SECONDS = {
    "s": 1,
    "m": 60,
    "h": 3600,
    "d": 86400,
}

TIME_PATTERN = re.compile(r"(\d+)([smhd])")


def parse_duration(text: str) -> int | None:
    """Converte algo como '1d2h30m' em segundos. Devolve None se inválido."""
    matches = TIME_PATTERN.findall(text.lower())
    if not matches:
        return None
    total = 0
    for value, unit in matches:
        total += int(value) * TIME_UNIT_SECONDS[unit]
    return total if total > 0 else None


class Reminders(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reminders: list[dict] = self._load()
        self._next_id = (max((r["id"] for r in self.reminders), default=0) + 1)
        self.checker.start()

    def cog_unload(self):
        self.checker.cancel()

    # ---------- persistência ----------

    def _load(self) -> list[dict]:
        if not os.path.exists(REMINDERS_FILE):
            return []
        with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self):
        os.makedirs(os.path.dirname(REMINDERS_FILE), exist_ok=True)
        with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.reminders, f, ensure_ascii=False, indent=2)

    # ---------- loop em background ----------

    @tasks.loop(seconds=15)
    async def checker(self):
        now = datetime.now(timezone.utc).timestamp()
        due = [r for r in self.reminders if r["due_at"] <= now]
        if not due:
            return

        for reminder in due:
            await self._deliver(reminder)

        self.reminders = [r for r in self.reminders if r["due_at"] > now]
        self._save()

    @checker.before_loop
    async def before_checker(self):
        await self.bot.wait_until_ready()

    async def _deliver(self, reminder: dict):
        user = self.bot.get_user(reminder["user_id"])
        embed = discord.Embed(
            title="⏰ Lembrete!",
            description=reminder["message"],
            color=discord.Color.blurple(),
        )
        embed.set_footer(text=f"Criado em {reminder['created_at']}")

        sent = False
        if user:
            try:
                await user.send(embed=embed)
                sent = True
            except discord.Forbidden:
                pass  # DMs fechadas, tenta o canal

        if not sent:
            channel = self.bot.get_channel(reminder["channel_id"])
            if channel:
                try:
                    await channel.send(content=f"<@{reminder['user_id']}>", embed=embed)
                except discord.HTTPException:
                    pass

    # ---------- comandos ----------

    @commands.command(name="lembrar", aliases=["remind", "remindme"])
    async def lembrar(self, ctx: commands.Context, tempo: str, *, mensagem: str):
        segundos = parse_duration(tempo)
        if segundos is None:
            await ctx.send(
                "⚠️ Formato de tempo inválido. Usa algo como `10m`, `2h`, `1d`, `1d2h30m`."
            )
            return

        if segundos > 30 * 86400:
            await ctx.send("⚠️ O máximo é 30 dias.")
            return

        due_at = datetime.now(timezone.utc).timestamp() + segundos

        reminder = {
            "id": self._next_id,
            "user_id": ctx.author.id,
            "channel_id": ctx.channel.id,
            "message": mensagem,
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "due_at": due_at,
        }
        self._next_id += 1
        self.reminders.append(reminder)
        self._save()

        quando = datetime.fromtimestamp(due_at, tz=timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
        await ctx.send(
            f"✅ Lembrete #{reminder['id']} criado! Aviso-te a **{quando}**."
        )

    @commands.command(name="lembretes", aliases=["reminders"])
    async def lembretes(self, ctx: commands.Context):
        meus = [r for r in self.reminders if r["user_id"] == ctx.author.id]
        if not meus:
            await ctx.send("Não tens lembretes pendentes.")
            return

        embed = discord.Embed(title="📋 Os teus lembretes", color=discord.Color.blurple())
        for r in sorted(meus, key=lambda x: x["due_at"])[:10]:
            quando = datetime.fromtimestamp(r["due_at"], tz=timezone.utc).strftime("%d/%m %H:%M UTC")
            embed.add_field(
                name=f"#{r['id']} — {quando}",
                value=r["message"][:100],
                inline=False,
            )
        await ctx.send(embed=embed)

    @commands.command(name="lembrete_cancelar", aliases=["remind_cancel", "unremind"])
    async def lembrete_cancelar(self, ctx: commands.Context, reminder_id: int):
        alvo = next(
            (r for r in self.reminders if r["id"] == reminder_id and r["user_id"] == ctx.author.id),
            None,
        )
        if not alvo:
            await ctx.send("Não encontrei esse lembrete (ou não é teu).")
            return

        self.reminders.remove(alvo)
        self._save()
        await ctx.send(f"🗑️ Lembrete #{reminder_id} cancelado.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Reminders(bot))