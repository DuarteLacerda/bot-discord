import asyncio
import json
import os

import discord
from discord.ext import commands

from utils.components import ConfirmView


class Basic(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        """Responds with pong"""
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Latency: {self.bot.latency * 1000:.0f}ms",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def write(self, ctx, *, message: str):
        """Echo a message (admin only)"""
        embed = discord.Embed(
            description=message,
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    @write.error
    async def write_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need administrator permissions to use this command.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.command()
    async def sum(self, ctx, a: int, b: int):
        """Add two numbers"""
        result = a + b
        embed = discord.Embed(
            title="🧮 Sum Result",
            description=f"**{a}** + **{b}** = **{result}**",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def info(self, ctx, member: discord.Member = None):
        """Show user information"""
        member = member or ctx.author
        embed = discord.Embed(title="👤 User Information", color=discord.Color.blue())
        embed.add_field(name="Username", value=member.name, inline=True)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(
            name="Account Created",
            value=member.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            inline=False
        )
        avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
        embed.set_thumbnail(url=avatar_url)
        await ctx.send(embed=embed)

    @commands.command()
    async def guild(self, ctx):
        """Show server information"""
        guild = ctx.guild
        embed = discord.Embed(title="🏰 Server Information", color=discord.Color.green())
        embed.add_field(name="Server Name", value=guild.name, inline=True)
        embed.add_field(name="Members", value=guild.member_count, inline=False)
        embed.add_field(
            name="Created",
            value=guild.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            inline=False
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)
        await ctx.send(embed=embed)

    @commands.command(name="clear")
    @commands.has_permissions(administrator=True)
    async def clear(self, ctx, amount: int = None):
        """Delete messages from channel (admin only)"""
        if amount is None:
            embed = discord.Embed(
                title="⚠️ Confirmation",
                description="Are you sure you want to delete all messages? Type `confirm` in the next 10 seconds.",
                color=discord.Color.orange()
            )
            msg = await ctx.send(embed=embed)
            
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == "confirm"
            
            try:
                await self.bot.wait_for("message", timeout=10.0, check=check)
                deleted = await ctx.channel.purge(limit=None)
                result_embed = discord.Embed(
                    title="✅ Cleared",
                    description=f"Deleted **{len(deleted)}** messages.",
                    color=discord.Color.green()
                )
                result_msg = await ctx.send(embed=result_embed)
                await asyncio.sleep(3)
                await result_msg.delete()
            except asyncio.TimeoutError:
                timeout_embed = discord.Embed(
                    title="❌ Cancelled",
                    description="Operation timed out.",
                    color=discord.Color.red()
                )
                await msg.edit(embed=timeout_embed)
        else:
            if amount <= 0:
                embed = discord.Embed(
                    title="❌ Error",
                    description="The amount must be positive.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
            deleted = await ctx.channel.purge(limit=amount + 1)
            result_embed = discord.Embed(
                title="✅ Cleared",
                description=f"Deleted **{len(deleted) - 1}** messages.",
                color=discord.Color.green()
            )
            result_msg = await ctx.send(embed=result_embed)
            await asyncio.sleep(3)
            await result_msg.delete()

    @clear.error
    async def clear_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need administrator permissions to use this command.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                title="❌ Invalid Syntax",
                description="Usage: `l!clear [amount]`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.command(name="rules")
    async def rules(self, ctx):
        """Show server rules"""
        rules_file = "data/rules.json"
        
        if not os.path.exists(rules_file):
            embed = discord.Embed(
                title="❌ Error",
                description="Rules file not found.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        try:
            with open(rules_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            embed = discord.Embed(
                title=data.get("title", "Server Rules"),
                color=int(data.get("color", "0x3498db").replace("0x", ""), 16),
            )
            
            for rule in data.get("rules", []):
                embed.add_field(
                    name=f"{rule['number']}. {rule['title']}",
                    value=rule['description'],
                    inline=False,
                )
            
            if "footer" in data:
                embed.set_footer(text=data["footer"])
            
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to load rules: {e}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.command(name="help")
    async def help_cmd(self, ctx):
        """Show all available commands"""
        prefix = ctx.prefix or "l!"
        
        if ctx.author.guild_permissions.administrator:
            general = [
                ("ping", "responds with pong"),
                ("write <message>", "echo message (admin only)"),
                ("sum <a> <b>", "add two numbers"),
                ("info [@user]", "show user info"),
                ("guild", "show server info"),
                ("rules", "show server rules"),
                ("clear [amount]", "delete messages (admin only)"),
            ]

            music = [
                ("join / connect", "join your voice channel"),
                ("play / p <term|link>", "play from YouTube or Spotify"),
                ("skip / sk", "skip current song"),
                ("stop / s", "stop and leave"),
                ("pause / pz", "pause"),
                ("resume / r", "resume"),
                ("queue / q", "show queue"),
                ("music", "show music commands"),
            ]

            levels = [
                ("level [@user]", "show user level and XP"),
                ("rank", "show top 10 leaderboard"),
                ("addxp @user <value>", "add XP (admin only)"),
            ]

            games = [
                ("guess", "start a word guessing game"),
                ("guessexit", "quit current game"),
                ("guessstats [@user]", "show game statistics"),
                ("guessrank", "show game leaderboard"),
            ]

            embed = discord.Embed(title="📖 Help (Admin)", color=discord.Color.red())
            embed.add_field(
                name="General (Admin)",
                value="\n".join(f"• **{prefix}{cmd}** — {desc}" for cmd, desc in general),
                inline=False,
            )
            embed.add_field(
                name="🎵 Music",
                value="\n".join(f"• **{prefix}{cmd}** — {desc}" for cmd, desc in music),
                inline=False,
            )
            embed.add_field(
                name="📊 Levels",
                value="\n".join(f"• **{prefix}{cmd}** — {desc}" for cmd, desc in levels),
                inline=False,
            )
            embed.add_field(
                name="🎮 Games",
                value="\n".join(f"• **{prefix}{cmd}** — {desc}" for cmd, desc in games),
                inline=False,
            )
            await ctx.send(embed=embed)
        else:
            general = [
                ("ping", "responds with pong"),
                ("sum <a> <b>", "add two numbers"),
                ("info [@user]", "show user info"),
                ("guild", "show server info"),
                ("rules", "show server rules"),
            ]

            music = [
                ("join / connect", "join your voice channel"),
                ("play / p <term|link>", "play from YouTube or Spotify"),
                ("skip / sk", "skip current song"),
                ("stop / s", "stop and leave"),
                ("pause / pz", "pause"),
                ("resume / r", "resume"),
                ("queue / q", "show queue"),
                ("music", "show music commands"),
            ]

            levels = [
                ("level [@user]", "show user level and XP"),
                ("rank", "show top 10 leaderboard"),
            ]

            games = [
                ("guess", "start a word guessing game"),
                ("guessexit", "quit current game"),
                ("guessstats [@user]", "show game statistics"),
                ("guessrank", "show game leaderboard"),
            ]

            embed = discord.Embed(title="📖 Help", color=discord.Color.orange())
            embed.add_field(
                name="General",
                value="\n".join(f"• **{prefix}{cmd}** — {desc}" for cmd, desc in general),
                inline=False,
            )
            embed.add_field(
                name="🎵 Music",
                value="\n".join(f"• **{prefix}{cmd}** — {desc}" for cmd, desc in music),
                inline=False,
            )
            embed.add_field(
                name="📊 Levels",
                value="\n".join(f"• **{prefix}{cmd}** — {desc}" for cmd, desc in levels),
                inline=False,
            )
            embed.add_field(
                name="🎮 Games",
                value="\n".join(f"• **{prefix}{cmd}** — {desc}" for cmd, desc in games),
                inline=False,
            )
            await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Basic(bot))

