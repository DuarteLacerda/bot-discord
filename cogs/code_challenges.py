import json
import random
import discord
from discord.ext import commands
from discord import ui


class LanguageSelect(ui.Select):
    """Dropdown para selecionar a linguagem de programação"""
    def __init__(self):
        options = [
            discord.SelectOption(label="Python", emoji="🐍", description="Linguagem Python"),
            discord.SelectOption(label="JavaScript", emoji="🟨", description="Linguagem JavaScript"),
            discord.SelectOption(label="Java", emoji="☕", description="Linguagem Java"),
            discord.SelectOption(label="C++", emoji="⚡", description="Linguagem C++"),
            discord.SelectOption(label="C#", emoji="🎯", description="Linguagem C#"),
        ]
        super().__init__(placeholder="Escolhe a linguagem...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        # Guarda a linguagem escolhida
        self.view.selected_language = self.values[0].lower()
        
        # Atualiza a view para mostrar dificuldades
        await self.view.show_difficulty(interaction)


class DifficultySelect(ui.Select):
    """Dropdown para selecionar a dificuldade"""
    def __init__(self):
        options = [
            discord.SelectOption(label="Fácil", emoji="🟢", description="Desafios para iniciantes"),
            discord.SelectOption(label="Médio", emoji="🟡", description="Desafios intermédios"),
            discord.SelectOption(label="Difícil", emoji="🔴", description="Desafios avançados"),
        ]
        super().__init__(placeholder="Escolhe a dificuldade...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        # Guarda a dificuldade escolhida
        difficulty_map = {"Fácil": "facil", "Médio": "medio", "Difícil": "dificil"}
        self.view.selected_difficulty = difficulty_map[self.values[0]]
        
        # Mostra o desafio
        await self.view.show_challenge(interaction)


class BackButton(ui.Button):
    """Botão para voltar à seleção de linguagem"""
    def __init__(self):
        super().__init__(label="← Voltar", style=discord.ButtonStyle.gray)
    
    async def callback(self, interaction: discord.Interaction):
        await self.view.show_language(interaction)


class NewChallengeButton(ui.Button):
    """Botão para gerar novo desafio"""
    def __init__(self):
        super().__init__(label="🔄 Novo Desafio", style=discord.ButtonStyle.green)
    
    async def callback(self, interaction: discord.Interaction):
        await self.view.show_challenge(interaction)


class ChallengeView(ui.View):
    """View principal para o sistema de desafios"""
    def __init__(self, challenges_data):
        super().__init__(timeout=180)  # 3 minutos
        self.challenges_data = challenges_data
        self.selected_language = None
        self.selected_difficulty = None
        
        # Adiciona o selector de linguagem inicialmente
        self.add_item(LanguageSelect())
    
    async def show_language(self, interaction: discord.Interaction):
        """Mostra a seleção de linguagem"""
        self.clear_items()
        self.add_item(LanguageSelect())
        
        embed = discord.Embed(
            title="💻 Desafio de Programação",
            description="**Passo 1:** Escolhe a linguagem de programação",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Seleciona uma linguagem no menu abaixo")
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def show_difficulty(self, interaction: discord.Interaction):
        """Mostra a seleção de dificuldade"""
        self.clear_items()
        self.add_item(DifficultySelect())
        self.add_item(BackButton())
        
        # Emoji map para linguagens
        lang_emoji = {
            "python": "🐍",
            "javascript": "🟨",
            "java": "☕",
            "c++": "⚡",
            "csharp": "🎯"
        }
        
        embed = discord.Embed(
            title="💻 Desafio de Programação",
            description=f"**Linguagem:** {lang_emoji.get(self.selected_language, '💻')} {self.selected_language.title()}\n\n**Passo 2:** Escolhe a dificuldade",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Seleciona a dificuldade no menu abaixo")
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def show_challenge(self, interaction: discord.Interaction):
        """Mostra um desafio aleatório"""
        self.clear_items()
        self.add_item(NewChallengeButton())
        self.add_item(BackButton())
        
        # Obtém lista de desafios para a linguagem e dificuldade
        try:
            challenges = self.challenges_data[self.selected_language][self.selected_difficulty]
        except KeyError:
            embed = discord.Embed(
                title="❌ Erro",
                description=f"Não há desafios disponíveis para {self.selected_language} ({self.selected_difficulty})",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=self)
            return
        
        # Escolhe um desafio aleatório
        challenge = random.choice(challenges)
        
        # Emoji e cor por dificuldade
        difficulty_config = {
            "facil": {"emoji": "🟢", "color": discord.Color.green()},
            "medio": {"emoji": "🟡", "color": discord.Color.gold()},
            "dificil": {"emoji": "🔴", "color": discord.Color.red()}
        }
        
        config = difficulty_config[self.selected_difficulty]
        
        # Emoji por linguagem
        lang_emoji = {
            "python": "🐍",
            "javascript": "🟨",
            "java": "☕",
            "c++": "⚡",
            "csharp": "🎯"
        }
        
        embed = discord.Embed(
            title=f"{config['emoji']} {challenge['titulo']}",
            description=challenge['descricao'],
            color=config['color']
        )
        
        embed.add_field(
            name="📝 Exemplo",
            value=f"```{challenge['exemplo']}```",
            inline=False
        )
        
        embed.add_field(
            name="💡 Dica",
            value=challenge['dica'],
            inline=False
        )
        
        embed.set_footer(
            text=f"Linguagem: {lang_emoji.get(self.selected_language, '💻')} {self.selected_language.title()} | Dificuldade: {self.selected_difficulty.title()}"
        )
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_timeout(self):
        """Remove botões quando timeout"""
        self.clear_items()


class CodeChallenges(commands.Cog):
    """Cog para desafios de programação"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.load_challenges()
    
    def load_challenges(self):
        """Carrega os desafios do ficheiro JSON"""
        try:
            with open('data/code_challenges.json', 'r', encoding='utf-8') as f:
                self.challenges_data = json.load(f)
        except FileNotFoundError:
            self.challenges_data = {}
            print("⚠️ Ficheiro code_challenges.json não encontrado!")
    
    @commands.hybrid_command(aliases=['desafio', 'challenge', 'coding'])
    async def code(self, ctx):
        """Gera um desafio de programação por linguagem e dificuldade
        
        Uso: /code
        
        Linguagens disponíveis:
        • 🐍 Python
        • 🟨 JavaScript
        • ☕ Java
        • ⚡ C++
        • 🎯 C#
        
        Dificuldades:
        • 🟢 Fácil
        • 🟡 Médio
        • 🔴 Difícil
        """
        
        if not self.challenges_data:
            embed = discord.Embed(
                title="❌ Erro",
                description="Base de dados de desafios não está disponível!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Cria a view inicial
        view = ChallengeView(self.challenges_data)
        
        embed = discord.Embed(
            title="💻 Desafio de Programação",
            description="**Passo 1:** Escolhe a linguagem de programação\n\n"
                       "**Linguagens disponíveis:**\n"
                       "🐍 Python\n"
                       "🟨 JavaScript\n"
                       "☕ Java\n"
                       "⚡ C++\n"
                       "🎯 C#",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Seleciona uma linguagem no menu abaixo")
        
        await ctx.send(embed=embed, view=view)
    
    @commands.hybrid_command()
    async def stats_code(self, ctx):
        """Mostra estatísticas sobre os desafios disponíveis"""
        
        if not self.challenges_data:
            embed = discord.Embed(
                title="❌ Erro",
                description="Base de dados de desafios não está disponível!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="📊 Estatísticas dos Desafios",
            description="Número de desafios disponíveis por linguagem e dificuldade",
            color=discord.Color.purple()
        )
        
        lang_emoji = {
            "python": "🐍",
            "javascript": "🟨",
            "java": "☕",
            "cpp": "⚡",
            "csharp": "🎯"
        }
        
        total = 0
        for lang, difficulties in self.challenges_data.items():
            facil = len(difficulties.get('facil', []))
            medio = len(difficulties.get('medio', []))
            dificil = len(difficulties.get('dificil', []))
            lang_total = facil + medio + dificil
            total += lang_total
            
            embed.add_field(
                name=f"{lang_emoji.get(lang, '💻')} {lang.title()}",
                value=f"🟢 Fácil: {facil}\n🟡 Médio: {medio}\n🔴 Difícil: {dificil}\n**Total: {lang_total}**",
                inline=True
            )
        
        embed.set_footer(text=f"Total de desafios: {total}")
        
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(CodeChallenges(bot))
