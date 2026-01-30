import logging
import os
import discord

from discord import ui
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.DEBUG)


class MyBot(commands.Bot):
    async def setup_hook(self):
        # Carrega extensões antes de conectar
        for ext in ["cogs.bot_commands", "cogs.events", "cogs.music", "cogs.levels", "cogs.termo", "cogs.code_challenges", "cogs.games"]:
            try:
                logging.info(f"Loading extension: {ext}")
                await self.load_extension(ext)
                logging.info(f"✅ Loaded: {ext}")
            except Exception as e:
                logging.exception(f"❌ Falha ao carregar a extensão {ext}: {e}")
        
        # Log all loaded commands
        logging.info(f"Total commands loaded: {len(self.commands)}")
        for cmd in self.commands:
            logging.info(f"  - {cmd.name} (aliases: {cmd.aliases})")


intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True
bot = MyBot(command_prefix='L!', intents=intents, help_command=None)

@bot.event
async def on_command_error(ctx, error):
    """Error handler global para comandos"""
    logging.error(f"Error in command {ctx.command}: {error}")
    logging.exception(error)
    
    # Send error to channel
    try:
        embed = discord.Embed(
            title="❌ Erro no Comando",
            description=f"```{str(error)[:500]}```",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    except:
        pass

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Define a variável de ambiente DISCORD_BOT_TOKEN antes de iniciar o bot.")

bot.run(TOKEN)