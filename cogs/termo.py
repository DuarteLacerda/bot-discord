import asyncio
import json
import logging
import os
import random
from datetime import datetime, timedelta
from typing import Dict, Optional

import discord
from discord.ext import commands
from discord.ui import Modal, TextInput, View, Button, button
from database import Database

# Game configuration
MAX_ATTEMPTS = 6
WORD_SIZE = 5

# XP rewards based on number of attempts
XP_REWARDS = {
    1: 500,  # Getting it right on first try is very hard!
    2: 300,
    3: 200,
    4: 150,
    5: 100,
    6: 50,
}

# File with game words
WORDS_FILE = "data/termo_palavras.json"
# File with player data
GAME_DATA_FILE = "data/game_data.json"


class GuessModal(Modal, title="Make Your Guess"):
    word = TextInput(
        label="5-letter Word",
        placeholder="Enter a 5-letter word...",
        min_length=5,
        max_length=5,
        required=True
    )
    
    def __init__(self, cog, user_id, guild_id):
        super().__init__()
        self.cog = cog
        self.user_id = user_id
        self.guild_id = guild_id
    
    async def on_submit(self, interaction: discord.Interaction):
        """Process the guess when modal is submitted"""
        try:
            attempt = self.word.value.strip().upper()
            logging.info(f"User {self.user_id} submitted: {attempt}")
            
            # Validate attempt
            if not attempt.isalpha():
                embed = discord.Embed(
                    title="❌ Invalid Word",
                    description="Only use letters!",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Check if user has active game
            if self.user_id not in self.cog.active_games:
                embed = discord.Embed(
                    title="❌ No Active Game",
                    description="Your game session has expired. Start a new game with `L!guess`",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            game = self.cog.active_games[self.user_id]
            secret_word = game["word"]
            
            # Process attempt
            result = self.cog._check_attempt(secret_word, attempt)
            
            game["attempts"].append({
                "word": attempt,
                "result": result
            })
            
            num_attempts = len(game["attempts"])
            word_guessed = attempt == secret_word
            
            # Defer and edit the existing game message to avoid clutter
            await interaction.response.defer()

            embed = self.cog._create_game_embed(
                game["attempts"],
                num_attempts,
                word_guessed,
                secret_word,
                interaction.user
            )

            view = None
            if not word_guessed and num_attempts < MAX_ATTEMPTS:
                # Provide the guess button again with the response
                view = GuessGameView(self.cog, self.user_id, self.guild_id)

            game_message = game.get("message")
            if game_message:
                await game_message.edit(embed=embed, view=view)
            else:
                # Fallback: send a new message if original is missing
                await interaction.followup.send(embed=embed, view=view)
            
            # Check game end
            if word_guessed:
                # Victory!
                await asyncio.sleep(0.5)  # Small delay to ensure response was processed
                await self.cog._give_xp_reward(interaction, num_attempts)
                
                # Update statistics
                data = self.cog._get_player_data(self.guild_id, self.user_id)
                data["games"] += 1
                data["wins"] += 1
                data["total_attempts"] += num_attempts
                self.cog._save_player_data(self.guild_id, self.user_id, data)
                
                del self.cog.active_games[self.user_id]
                
            elif num_attempts >= MAX_ATTEMPTS:
                # Defeat
                defeat_embed = discord.Embed(
                    title="😢 Game Over",
                    description=f"Better luck next time! The word was: **{secret_word}**",
                    color=discord.Color.red()
                )
                await interaction.channel.send(embed=defeat_embed)
                
                # Update statistics
                data = self.cog._get_player_data(self.guild_id, self.user_id)
                data["games"] += 1
                self.cog._save_player_data(self.guild_id, self.user_id, data)
                
                del self.cog.active_games[self.user_id]
        except Exception as e:
            logging.exception(f"Error in modal submit: {e}")
            try:
                embed = discord.Embed(
                    title="❌ Error",
                    description="An error occurred processing your guess.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                pass


class GuessGameView(View):
    """View with button to open the guess modal"""
    
    def __init__(self, cog: 'Guess', user_id: int, guild_id: int):
        # Keep the view alive while the bot is up; avoids interaction failures after timeout
        super().__init__(timeout=None)
        self.cog = cog
        self.user_id = user_id
        self.guild_id = guild_id
    
    @button(label="Make Guess", style=discord.ButtonStyle.primary, emoji="🎯")
    async def guess_button(self, interaction: discord.Interaction, button: Button):
        # Check if the button was pressed by the game player
        if interaction.user.id != self.user_id:
            embed = discord.Embed(
                title="❌ Not Your Game",
                description="This game belongs to someone else!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            logging.info(f"Opening modal for user={interaction.user.id} in guild={interaction.guild.id}")
            # Show the modal
            modal = GuessModal(self.cog, self.user_id, self.guild_id)
            await interaction.response.send_modal(modal)
            logging.info("Modal shown successfully")
        except Exception as e:
            logging.exception(f"Error showing modal: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to open guess modal. Try again.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class Guess(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = Database()
        self.words: list = []
        self.active_games: Dict[int, Dict] = {}  # {user_id: {"word": str, "attempts": [], "channel": channel}}
        self._load_words()
        self._migrate_legacy_data()

    def _load_words(self):
        """Load word list from file"""
        if os.path.exists(WORDS_FILE):
            try:
                with open(WORDS_FILE, "r", encoding="utf-8") as f:
                    self.words = json.load(f)
                logging.info(f"Loaded {len(self.words)} words for Guess.")
            except Exception:
                logging.exception("Failed to load Guess words.")
                self.words = []
        else:
            logging.warning(f"Words file not found at {WORDS_FILE}")
            self.words = []

    def _migrate_legacy_data(self):
        """Migra dados antigos em JSON para SQLite, se existirem"""
        try:
            migrated = self.db.migrate_guess_from_json(GAME_DATA_FILE)
            if migrated:
                logging.info("Guess data migrated from JSON to SQLite.")
        except Exception:
            logging.exception("Failed to migrate legacy Guess data.")

    def _get_player_data(self, guild_id: int, user_id: int) -> Dict:
        """Get player data from database"""
        return self.db.get_guess_stats(guild_id, user_id)

    def _save_player_data(self, guild_id: int, user_id: int, data: Dict):
        """Persist player data to database"""
        self.db.set_guess_stats(
            guild_id,
            user_id,
            data.get("games", 0),
            data.get("wins", 0),
            data.get("total_attempts", 0),
        )

    def _pick_word(self) -> str:
        """Pick a random word from the list"""
        if not self.words:
            return "guess"  # fallback
        return random.choice(self.words).upper()

    def _check_attempt(self, secret_word: str, attempt: str) -> list:
        """
        Check the attempt and return list of results:
        🟩 = correct letter in correct position
        🟨 = correct letter in wrong position
        ⬜ = letter not in word
        """
        resultado = []
        secret_word = secret_word.upper()
        attempt = attempt.upper()
        
        # Count letter occurrences in secret word
        count = {}
        for letter in secret_word:
            count[letter] = count.get(letter, 0) + 1
        
        # First pass: mark correct letters (🟩)
        status = ["⬜"] * len(attempt)
        for i, letter in enumerate(attempt):
            if i < len(secret_word) and letter == secret_word[i]:
                status[i] = "🟩"
                count[letter] -= 1
        
        # Second pass: mark wrong position letters (🟨)
        for i, letter in enumerate(attempt):
            if status[i] == "⬜" and letter in count and count[letter] > 0:
                status[i] = "🟨"
                count[letter] -= 1
        
        return status

    def _create_game_embed(self, attempts: list, num_attempts: int, word_guessed: bool = False, secret_word: str = "", player: Optional[discord.User] = None) -> discord.Embed:
        """Create embed showing game state"""
        if word_guessed:
            color = discord.Color.green()
            title = "🎉 Congratulations! You guessed the word!"
        elif num_attempts >= MAX_ATTEMPTS:
            color = discord.Color.red()
            title = f"😔 Game Over! The word was: **{secret_word}**"
        else:
            color = discord.Color.blue()
            title = f"🎮 Guess - Attempt {num_attempts}/{MAX_ATTEMPTS}"
        
        embed = discord.Embed(title=title, color=color)

        # Explicitly show whose game this is
        if player:
            avatar = player.avatar.url if player.avatar else player.default_avatar.url
            embed.set_author(name=f"Jogo de {player.display_name}", icon_url=avatar)
            embed.set_footer(text=f"Jogador: {player}")
        
        # Show previous attempts
        if attempts:
            history = "\n".join([
                f"{att['word']} {''.join(att['result'])}"
                for att in attempts
            ])
            embed.add_field(name="Attempts", value=history, inline=False)
        
        # Instructions
        if not word_guessed and num_attempts < MAX_ATTEMPTS:
            embed.add_field(
                name="How to Play",
                value=f"Type a word with {WORD_SIZE} letters.\n🟩 = Correct letter\n🟨 = Letter exists but wrong position\n⬜ = Letter not in word",
                inline=False
            )
        
        return embed

    async def _give_xp_reward(self, interaction: discord.Interaction, num_attempts: int):
        """Give XP reward based on number of attempts"""
        xp_gained = XP_REWARDS.get(num_attempts, 25)
        
        # Get Levels cog to give XP
        levels_cog = self.bot.get_cog("Levels")
        if levels_cog:
            user_data = levels_cog.db.get_user_data(interaction.guild.id, interaction.user.id)
            if not user_data:
                user_data = {"xp": 0, "level": 1, "multiplicador": 1, "msgs_mult": 0}
            
            level_before = user_data["level"]
            user_data["xp"] += xp_gained
            level_after = levels_cog._calcular_nivel(user_data["xp"])
            
            if level_after > level_before:
                user_data["level"] = level_after
            
            levels_cog.db.set_user_data(interaction.guild.id, interaction.user.id, user_data["xp"], user_data["level"], user_data["multiplicador"], user_data["msgs_mult"])
            
            embed = discord.Embed(
                title="💰 XP Earned!",
                description=f"You earned **{xp_gained} XP** for completing the game in {num_attempts} attempts!",
                color=discord.Color.gold()
            )
            try:
                await interaction.followup.send(embed=embed)
            except:
                # If followup fails, send to channel instead
                await interaction.channel.send(embed=embed)
        else:
            embed = discord.Embed(
                title="🎁 Game Complete!",
                description=f"You completed the game in {num_attempts} attempts!",
                color=discord.Color.blue()
            )
            await interaction.followup.send(embed=embed)

    @commands.command(name="guess")
    async def guess(self, ctx):
        """Start a new word guessing game"""
        user_id = ctx.author.id
        
        # Check if already has an active game
        if user_id in self.active_games:
            embed = discord.Embed(
                title="❌ Active Game",
                description="You already have an active game! Finish it first or use `guessexit` to quit.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Start new game
        secret_word = self._pick_word()
        self.active_games[user_id] = {
            "word": secret_word,
            "attempts": [],
            "channel": ctx.channel,
            "guild_id": ctx.guild.id,
            "message": None,
        }
        
        # Create single comprehensive embed with button
        embed = discord.Embed(
            title="🎮 Guess Game Started!",
            description=(
                f"Jogo de {ctx.author.mention}. Adivinha uma palavra de {WORD_SIZE} letras em {MAX_ATTEMPTS} tentativas.\n\n"
                "**Feedback:**\n🟩 letra certa no sítio\n🟨 letra existe mas posição errada\n⬜ letra não está na palavra"
            ),
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Status",
            value=f"Attempts: 0/{MAX_ATTEMPTS}",
            inline=False
        )
        embed.add_field(
            name="How to Play",
            value="Usa o botão abaixo para enviar as tuas tentativas.",
            inline=False
        )
        embed.set_footer(text="Apenas o dono do jogo pode usar o botão. Usa 'L!guessexit' para sair.")
        
        # Create view with button
        view = GuessGameView(self, user_id, ctx.guild.id)
        msg = await ctx.send(embed=embed, view=view)
        # Keep reference to edit later instead of spamming new messages
        self.active_games[user_id]["message"] = msg

    @commands.command(name="guessexit")
    async def guess_exit(self, ctx):
        """Quit the current game"""
        user_id = ctx.author.id
        
        if user_id not in self.active_games:
            embed = discord.Embed(
                title="❌ No Active Game",
                description="You don't have any active game.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        word = self.active_games[user_id]["word"]
        del self.active_games[user_id]
        
        embed = discord.Embed(
            title="😔 Game Quit",
            description=f"You quit the game. The word was: **{word}**",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)

    @commands.command(name="guessstats")
    async def guess_stats(self, ctx, member: discord.Member = None):
        """Show game statistics for a player"""
        member = member or ctx.author
        
        data = self._get_player_data(ctx.guild.id, member.id)
        
        games = data["games"]
        wins = data["wins"]
        total_attempts = data["total_attempts"]
        
        if games == 0:
            embed = discord.Embed(
                title="📊 Game Statistics",
                description=f"{member.mention} hasn't played Guess yet!",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return
        
        win_rate = (wins / games) * 100 if games > 0 else 0
        avg_attempts = total_attempts / wins if wins > 0 else 0
        
        embed = discord.Embed(
            title=f"📊 Game Statistics - {member.display_name}",
            color=discord.Color.blue()
        )
        embed.add_field(name="🎮 Games", value=str(games), inline=True)
        embed.add_field(name="🏆 Wins", value=str(wins), inline=True)
        embed.add_field(name="📈 Win Rate", value=f"{win_rate:.1f}%", inline=True)
        
        if wins > 0:
            embed.add_field(name="🎯 Average Attempts", value=f"{avg_attempts:.1f}", inline=True)
        
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        
        await ctx.send(embed=embed)

    @commands.command(name="guessrank")
    async def guess_rank(self, ctx):
        """Show game leaderboard on the server"""
        guild_stats = [s for s in self.db.get_guess_leaderboard(ctx.guild.id) if s["games"] > 0]

        if not guild_stats:
            embed = discord.Embed(
                title="📊 Game Leaderboard",
                description="No game statistics yet on this server!",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return

        def sort_key(entry):
            wins = entry["wins"]
            avg_attempts = entry["total_attempts"] / wins if wins else float("inf")
            return (wins, -avg_attempts)

        ranking = sorted(guild_stats, key=sort_key, reverse=True)

        embed = discord.Embed(
            title="🏆 Game Leaderboard",
            color=discord.Color.gold()
        )

        # Show top 10
        for i, data in enumerate(ranking[:10], 1):
            user_id = data["user_id"]
            try:
                member = await ctx.guild.fetch_member(user_id)
                name = member.display_name
            except:
                name = f"User {user_id}"
            
            wins = data["wins"]
            games = data["games"]
            win_rate = (wins / games * 100) if games > 0 else 0
            avg = (data["total_attempts"] / wins) if wins > 0 else 0
            
            medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
            
            embed.add_field(
                name=f"{medal} {name}",
                value=f"🏆 {wins} wins | 📈 {win_rate:.0f}% | 🎯 {avg:.1f} avg",
                inline=False
            )
        
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Guess(bot))
