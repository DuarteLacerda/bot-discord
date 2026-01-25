import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)


class MyBot(commands.Bot):
    async def setup_hook(self):
        # Carrega extensões antes de conectar
        for ext in ["bot_commands", "events", "music", "levels", "termo"]:
            try:
                await self.load_extension(ext)
            except Exception:
                logging.exception("Falha ao carregar a extensão %s", ext)


intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True
bot = MyBot(command_prefix='L!', intents=intents, help_command=None)

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Define a variável de ambiente DISCORD_BOT_TOKEN antes de iniciar o bot.")

bot.run(TOKEN)