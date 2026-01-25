import logging

import discord
from discord.ext import commands


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"O bot {self.bot.user} está online!")
        
        # Configura o Rich Presence (Status do bot)
        activity = discord.Activity(
            type=discord.ActivityType.listening,
            name="L!help"
        )
        await self.bot.change_presence(activity=activity, status=discord.Status.online)

    @commands.Cog.listener()
    async def on_error(self, event_method, *args, **kwargs):
        logging.exception("Erro não tratado em %s", event_method)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        logging.exception("Erro durante comando: %s", error)
        try:
            await ctx.send("Ocorreu um erro ao executar esse comando. Tenta novamente em instantes.")
        except Exception:
            logging.exception("Falha ao enviar mensagem de erro para o usuário")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel = discord.utils.get(member.guild.text_channels, name="general")
        if channel:
            await channel.send(f"Bem-vindo ao servidor, {member.mention}!")


async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))
