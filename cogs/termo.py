import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional

import discord
from discord.ext import commands
from discord.ui import Modal, TextInput, View, Button, button
from database import Database
from zoneinfo import ZoneInfo

# Daily word tracking
DAILY_FILE = "data/termo_daily.json"
TIMEZONE = ZoneInfo("Europe/Lisbon")
DAILY_EPOCH = datetime(2024, 1, 1, tzinfo=TIMEZONE).date()

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


class TermoModal(Modal, title="Faz a Tua Tentativa"):
    word = TextInput(
        label="Palavra com 5 letras",
        placeholder="Escreve uma palavra com 5 letras...",
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
        """Process the termo when modal is submitted"""
        try:
            # Defer immediately to avoid timeout
            await interaction.response.defer()
            
            logging.info(f"=== TERMO MODAL SUBMITTED ===")
            attempt = self.word.value.strip().upper()
            logging.info(f"User {self.user_id} submitted: {attempt}")
            
            # Validate attempt
            if not attempt.isalpha():
                embed = discord.Embed(
                    title="❌ Palavra Inválida",
                    description="Usa apenas letras!",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Check if user has active game
            if self.user_id not in self.cog.active_games:
                embed = discord.Embed(
                    title="❌ Sem Jogo Ativo",
                    description="A tua sessão de jogo expirou. Começa um novo jogo com `/termo`",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
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
            word_termoed = attempt == secret_word
            
            embed = self.cog._create_game_embed(
                game["attempts"],
                num_attempts,
                word_termoed,
                secret_word,
                interaction.user
            )

            view = None
            if not word_termoed and num_attempts < MAX_ATTEMPTS:
                # Provide the termo button again with the response
                view = TermoGameView(self.cog, self.user_id, self.guild_id)

            game_message = game.get("message")
            if game_message:
                await game_message.edit(embed=embed, view=view)
            else:
                # Fallback: send a new message if original is missing
                await interaction.followup.send(embed=embed, view=view)
            
            # Check game end
            if word_termoed:
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
                # Defeat — o card público já foi editado acima, sem revelar a palavra
                # A palavra só é revelada em privado a quem jogou
                await self.cog._reveal_word_privately(
                    interaction, interaction.user, secret_word, discord.Color.red()
                )

                # Update statistics
                data = self.cog._get_player_data(self.guild_id, self.user_id)
                data["games"] += 1
                self.cog._save_player_data(self.guild_id, self.user_id, data)
                
                del self.cog.active_games[self.user_id]
        except Exception as e:
            logging.exception(f"Error in modal submit: {e}")
            try:
                embed = discord.Embed(
                    title="❌ Erro",
                    description=f"Erro ao processar tentativa: {str(e)[:100]}",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            except Exception as send_error:
                logging.exception(f"Could not send error message: {send_error}")


class TermoGameView(View):
    """View with button to open the termo modal"""
    
    def __init__(self, cog: 'Termo', user_id: int, guild_id: int):
        # Keep the view alive while the bot is up; avoids interaction failures after timeout
        super().__init__(timeout=None)
        self.cog = cog
        self.user_id = user_id
        self.guild_id = guild_id
    
    @button(label="Fazer Tentativa", style=discord.ButtonStyle.primary, emoji="🎯")
    async def termo_button(self, interaction: discord.Interaction, button: Button):
        try:
            logging.info(f"=== TERMO BUTTON CLICKED ===")
            logging.info(f"Button clicker ID: {interaction.user.id}, game player ID: {self.user_id}")
            
            # Check if the button was pressed by the game player
            if interaction.user.id != self.user_id:
                logging.info(f"Button clicked by wrong user")
                embed = discord.Embed(
                    title="❌ Não é o Teu Jogo",
                    description="Este jogo pertence a outra pessoa!",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            try:
                logging.info(f"Creating modal for user={interaction.user.id} in guild={interaction.guild.id}")
                # Show the modal
                modal = TermoModal(self.cog, self.user_id, self.guild_id)
                logging.info(f"Modal instance created: {modal}")
                await interaction.response.send_modal(modal)
                logging.info("Modal shown successfully")
            except Exception as e:
                logging.exception(f"Error showing modal: {e}")
                embed = discord.Embed(
                    title="❌ Erro",
                    description=f"Falha ao abrir o formulário: {str(e)}",
                    color=discord.Color.red()
                )
                try:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except:
                    logging.exception("Could not send error message")
        except Exception as e:
            logging.exception(f"Error in termo_button: {e}")


class Termo(commands.Cog):
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
                logging.info(f"Loaded {len(self.words)} words for Termo.")
            except Exception:
                logging.exception("Failed to load Termo words.")
                self.words = []
        else:
            logging.warning(f"Words file not found at {WORDS_FILE}")
            self.words = []

    def _load_daily(self) -> dict:
        if not os.path.exists(DAILY_FILE):
            return {}
        try:
            with open(DAILY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_daily(self, data: dict):
        os.makedirs(os.path.dirname(DAILY_FILE), exist_ok=True)
        with open(DAILY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _today_str(self) -> str:
        return datetime.now(TIMEZONE).date().isoformat()

    def _has_played_today(self, guild_id: int, user_id: int) -> bool:
        daily = self._load_daily()
        return daily.get(str(guild_id), {}).get(str(user_id)) == self._today_str()

    def _mark_played_today(self, guild_id: int, user_id: int):
        daily = self._load_daily()
        daily.setdefault(str(guild_id), {})[str(user_id)] = self._today_str()
        self._save_daily(daily)
        
    def _unmark_played_today(self, guild_id: int, user_id: int):
        """Remove a marca de 'jogou hoje', usado quando o jogador desiste sem terminar"""
        daily = self._load_daily()
        guild_key = str(guild_id)
        user_key = str(user_id)
        if daily.get(guild_key, {}).get(user_key) == self._today_str():
            del daily[guild_key][user_key]
            self._save_daily(daily)

    def _next_reset_timestamp(self) -> int:
        """Epoch (segundos) da próxima meia-noite em Europe/Lisbon"""
        now = datetime.now(TIMEZONE)
        tomorrow = now.date() + timedelta(days=1)
        reset_dt = datetime.combine(tomorrow, datetime.min.time(), tzinfo=TIMEZONE)
        return int(reset_dt.timestamp())

    def _migrate_legacy_data(self):
        """Migra dados antigos em JSON para SQLite, se existirem"""
        try:
            migrated = self.db.migrate_termo_from_json(GAME_DATA_FILE)
            if migrated:
                logging.info("Termo data migrated from JSON to SQLite.")
        except Exception:
            logging.exception("Failed to migrate legacy Termo data.")

    def _get_player_data(self, guild_id: int, user_id: int) -> Dict:
        """Get player data from database"""
        return self.db.get_termo_stats(guild_id, user_id)

    def _save_player_data(self, guild_id: int, user_id: int, data: Dict):
        """Persist player data to database"""
        self.db.set_termo_stats(
            guild_id,
            user_id,
            data.get("games", 0),
            data.get("wins", 0),
            data.get("total_attempts", 0),
        )

    def _pick_word(self) -> str:
        """Escolhe a palavra do dia (mesma para todos, determinística pela data)"""
        if not self.words:
            return "termo"  # fallback
        days_since_epoch = (datetime.now(TIMEZONE).date() - DAILY_EPOCH).days
        index = days_since_epoch % len(self.words)
        return self.words[index].upper()

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

    def _create_game_embed(self, attempts: list, num_attempts: int, word_termoed: bool = False, secret_word: str = "", player: Optional[discord.User] = None) -> discord.Embed:
        """Create embed showing game state"""
        if word_termoed:
            color = discord.Color.green()
            title = "🎉 Parabéns! Acertaste a palavra!"
        elif num_attempts >= MAX_ATTEMPTS:
            color = discord.Color.red()
            title = "😔 Fim do Jogo!"
        else:
            color = discord.Color.blue()
            title = f"🎮 Jogo - Tentativa {num_attempts}/{MAX_ATTEMPTS}"
        
        embed = discord.Embed(title=title, color=color)

        # Explicitly show whose game this is
        if player:
            avatar = player.avatar.url if player.avatar else player.default_avatar.url
            embed.set_author(name=f"Jogo de {player.display_name}", icon_url=avatar)
            embed.set_footer(text=f"Jogador: {player}")
        
        # Show previous attempts (nunca mostra a palavra em texto, só os quadrados de cor)
        if attempts:
            history = "\n".join([
                ''.join(att['result'])
                for att in attempts
            ])
            embed.add_field(name="Tentativas", value=history, inline=False)
        
        # Instructions
        if not word_termoed and num_attempts < MAX_ATTEMPTS:
            embed.add_field(
                name="Como Jogar",
                value=f"Escreve uma palavra com {WORD_SIZE} letras.\n🟩 = Letra correta\n🟨 = Letra existe mas posição errada\n⬜ = Letra não está na palavra",
                inline=False
            )
        elif not word_termoed and num_attempts >= MAX_ATTEMPTS:
            # A palavra nunca é revelada na mensagem pública, só em privado a quem jogou
            embed.add_field(
                name="Resultado",
                value="A palavra foi enviada em privado a quem jogou.",
                inline=False
            )
        
        return embed

    async def _reveal_word_privately(self, target, user: discord.abc.User, word: str, color: discord.Color):
        """
        Revela a palavra secreta apenas ao jogador que jogou, nunca a toda a gente.
        `target` pode ser uma Interaction (usa followup ephemeral) ou um Context
        (usa ephemeral se veio de slash command, senão cai para DM).
        """
        embed = discord.Embed(
            title="📖 A Palavra Era...",
            description=f"A palavra secreta era **{word}**.",
            color=color
        )
        try:
            if isinstance(target, discord.Interaction):
                await target.followup.send(embed=embed, ephemeral=True)
            elif getattr(target, "interaction", None) is not None:
                # Hybrid command invocado como slash: dá para ser ephemeral
                await target.send(embed=embed, ephemeral=True)
            else:
                # Comando de texto: não há ephemeral, então enviamos por DM
                await user.send(embed=embed)
        except discord.Forbidden:
            logging.warning(f"Não foi possível enviar DM a {user.id} com a palavra secreta (DMs fechadas).")
        except Exception:
            logging.exception("Não foi possível revelar a palavra em privado")

    async def _give_xp_reward(self, interaction: discord.Interaction, num_attempts: int):
        """Give XP reward based on number of attempts"""
        try:
            xp_gained = XP_REWARDS.get(num_attempts, 25)
            logging.info(f"Giving {xp_gained} XP to user {interaction.user.id}")
            
            # Get Levels cog to give XP
            levels_cog = self.bot.get_cog("Levels")
            if levels_cog:
                try:
                    user_data = levels_cog.db.get_user_data(interaction.guild.id, interaction.user.id)
                    if not user_data:
                        user_data = {"xp": 0, "level": 1, "multiplicador": 1, "msgs_mult": 0}
                    
                    level_before = user_data["level"]
                    user_data["xp"] += xp_gained
                    level_after = levels_cog._calcular_nivel(user_data["xp"])
                    
                    if level_after > level_before:
                        user_data["level"] = level_after
                    
                    levels_cog.db.set_user_data(interaction.guild.id, interaction.user.id, user_data["xp"], user_data["level"], user_data["multiplicador"], user_data["msgs_mult"])
                    logging.info(f"XP updated for user {interaction.user.id}")
                    
                    embed = discord.Embed(
                        title="💰 XP Ganho!",
                        description=f"Ganhaste **{xp_gained} XP** por completar o jogo em {num_attempts} tentativas!",
                        color=discord.Color.gold()
                    )
                    try:
                        await interaction.followup.send(embed=embed)
                        logging.info(f"XP reward message sent")
                    except Exception as e:
                        logging.warning(f"Could not send XP reward message: {e}")
                        # Fallback to channel send
                        await interaction.channel.send(embed=embed)
                except Exception as e:
                    logging.exception(f"Error updating XP: {e}")
            else:
                logging.warning("Levels cog not found")
                embed = discord.Embed(
                    title="🎁 Jogo Completo!",
                    description=f"Completaste o jogo em {num_attempts} tentativas!",
                    color=discord.Color.blue()
                )
                await interaction.followup.send(embed=embed)
        except Exception as e:
            logging.exception(f"Error in _give_xp_reward: {e}")

    @commands.hybrid_command(name="termo")
    async def termo(self, ctx):
        """Começa o desafio diário de adivinhação de palavras"""
        try:
            logging.info(f"=== TERMO COMMAND STARTED ===")
            user_id = ctx.author.id
            logging.info(f"User: {user_id}, Guild: {ctx.guild.id}")

            # Check if already has an active game
            if user_id in self.active_games:
                embed = discord.Embed(
                    title="❌ Jogo Ativo",
                    description="Já tens um jogo ativo! Termina-o primeiro ou usa `/termo_quit` para sair.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return

            # Check if already played today's word
            if self._has_played_today(ctx.guild.id, user_id):
                reset_ts = self._next_reset_timestamp()
                embed = discord.Embed(
                    title="🕐 Já Jogaste Hoje",
                    description=f"O Termo de hoje já foi jogado! Volta amanhã.\nPróximo desafio: <t:{reset_ts}:R>",
                    color=discord.Color.orange()
                )
                await ctx.send(embed=embed)
                return

            # Start new game (marca logo o dia como usado, mesmo que o jogo seja abandonado)
            secret_word = self._pick_word()
            self._mark_played_today(ctx.guild.id, user_id)
            logging.info(f"Secret word: {secret_word}")
            self.active_games[user_id] = {
                "word": secret_word,
                "attempts": [],
                "channel": ctx.channel,
                "guild_id": ctx.guild.id,
                "message": None,
            }
            
            # Create single comprehensive embed with button
            embed = discord.Embed(
                title="🎮 Jogo Iniciado!",
                description=(
                    f"Jogo de {ctx.author.mention}. Adivinha uma palavra de {WORD_SIZE} letras em {MAX_ATTEMPTS} tentativas.\n\n"
                    "**Feedback:**\n🟩 letra correta na posição\n🟨 letra existe mas posição errada\n⬜ letra não está na palavra"
                ),
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Estado",
                value=f"Tentativas: 0/{MAX_ATTEMPTS}",
                inline=False
            )
            embed.add_field(
                name="Como Jogar",
                value="Usa o botão abaixo para enviar as tuas tentativas.",
                inline=False
            )
            embed.set_footer(text="Apenas o dono do jogo pode usar o botão. Usa `/termo_quit` para sair.")
            
            # Create view with button
            view = TermoGameView(self, user_id, ctx.guild.id)
            logging.info("About to send game message")
            msg = await ctx.send(embed=embed, view=view)
            logging.info(f"Game message sent: {msg.id}")
            # Keep reference to edit later instead of spamming new messages
            self.active_games[user_id]["message"] = msg
            logging.info(f"=== TERMO COMMAND COMPLETED ===")
        except Exception as e:
            logging.exception(f"Error in termo command: {e}")
            try:
                embed = discord.Embed(
                    title="❌ Erro",
                    description=f"Erro ao iniciar jogo: {str(e)}",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
            except:
                pass

    @commands.hybrid_command(name="termo_quit")
    async def termo_exit(self, ctx):
        """Sai do jogo atual"""
        user_id = ctx.author.id
        
        if user_id not in self.active_games:
            embed = discord.Embed(
                title="❌ Sem Jogo Ativo",
                description="Não tens nenhum jogo ativo.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        word = self.active_games[user_id]["word"]
        del self.active_games[user_id]

        # Desistir não conta como ter jogado — pode voltar a tentar hoje
        self._unmark_played_today(ctx.guild.id, user_id)

        embed = discord.Embed(
            title="😔 Jogo Cancelado",
            description="Cancelaste o jogo.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)

        # A palavra nunca fica visível para todos, só para quem jogou
        await self._reveal_word_privately(ctx, ctx.author, word, discord.Color.orange())

    @commands.hybrid_command(name="termo_stats")
    async def termo_stats(self, ctx, member: discord.Member = None):
        """Mostra as estatísticas do jogo de um jogador"""
        member = member or ctx.author
        
        data = self._get_player_data(ctx.guild.id, member.id)
        
        games = data["games"]
        wins = data["wins"]
        total_attempts = data["total_attempts"]
        
        if games == 0:
            embed = discord.Embed(
                title="📊 Estatísticas do Jogo",
                description=f"{member.mention} ainda não jogou!",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return
        
        win_rate = (wins / games) * 100 if games > 0 else 0
        avg_attempts = total_attempts / wins if wins > 0 else 0
        
        embed = discord.Embed(
            title=f"📊 Estatísticas do Jogo - {member.display_name}",
            color=discord.Color.blue()
        )
        embed.add_field(name="🎮 Jogos", value=str(games), inline=True)
        embed.add_field(name="🏆 Vitórias", value=str(wins), inline=True)
        embed.add_field(name="📈 Taxa de Vitória", value=f"{win_rate:.1f}%", inline=True)
        
        if wins > 0:
            embed.add_field(name="🎯 Média de Tentativas", value=f"{avg_attempts:.1f}", inline=True)
        
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="termo_rank")
    async def termo_rank(self, ctx):
        """Mostra o ranking do jogo no servidor"""
        guild_stats = [s for s in self.db.get_termo_leaderboard(ctx.guild.id) if s["games"] > 0]

        if not guild_stats:
            embed = discord.Embed(
                title="📊 Ranking do Jogo",
                description="Ainda não há estatísticas de jogo neste servidor!",
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
            title="🏆 Ranking do Jogo",
            color=discord.Color.gold()
        )

        # Show top 10
        for i, data in enumerate(ranking[:10], 1):
            user_id = data["user_id"]
            try:
                member = await ctx.guild.fetch_member(user_id)
                name = member.display_name
            except:
                name = f"Utilizador {user_id}"
            
            wins = data["wins"]
            games = data["games"]
            win_rate = (wins / games * 100) if games > 0 else 0
            avg = (data["total_attempts"] / wins) if wins > 0 else 0
            
            medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
            
            embed.add_field(
                name=f"{medal} {name}",
                value=f"🏆 {wins} vitórias | 📈 {win_rate:.0f}% | 🎯 {avg:.1f} méd",
                inline=False
            )
        
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Termo(bot))