import logging

import discord
from discord.ext import commands


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Bot {self.bot.user} is online!")
        
        # Set Rich Presence (Bot Status)
        activity = discord.Activity(
            type=discord.ActivityType.listening,
            name="L!help"
        )
        await self.bot.change_presence(activity=activity, status=discord.Status.online)

    @commands.Cog.listener()
    async def on_error(self, event_method, *args, **kwargs):
        logging.exception("Unhandled error in %s", event_method)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        logging.exception("Error during command: %s", error)
        try:
            embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while executing this command. Try again shortly.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except Exception:
            logging.exception("Failed to send error message to user")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel = discord.utils.get(member.guild.text_channels, name="general")
        if channel:
            embed = discord.Embed(
                title="👋 Welcome!",
                description=f"Welcome to the server, {member.mention}!",
                color=discord.Color.green()
            )
            await channel.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))

