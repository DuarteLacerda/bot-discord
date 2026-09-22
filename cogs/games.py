import random
import discord
from discord.ext import commands


class Games(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @commands.hybrid_command(name='ppt', aliases=['pedrapapeltesoura', 'rps'])
    async def pedra_papel_tesoura(self, ctx, escolha: str = None):
        """Jogue pedra, papel ou tesoura! Uso: /ppt <pedra|papel|tesoura>"""
        opcoes = {
            'pedra': '🪨',
            'papel': '📄',
            'tesoura': '✂️'
        }
        
        # Aliases para facilitar
        aliases = {
            'pedra': ['pedra', 'rock', 'r', 'p'],
            'papel': ['papel', 'paper', 'pa'],
            'tesoura': ['tesoura', 'scissors', 's', 't']
        }
        
        if not escolha:
            embed = discord.Embed(
                title="🎮 Pedra, Papel ou Tesoura",
                description="Escolhe uma opção:\n🪨 **Pedra**\n📄 **Papel**\n✂️ **Tesoura**",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Uso: /ppt <pedra|papel|tesoura>")
            await ctx.send(embed=embed)
            return
        
        # Normalizar escolha do usuário
        escolha = escolha.lower()
        escolha_usuario = None
        for opcao, alias_list in aliases.items():
            if escolha in alias_list:
                escolha_usuario = opcao
                break
        
        if not escolha_usuario:
            await ctx.send("❌ Escolhe **pedra**, **papel** ou **tesoura**!")
            return
        
        # Bot escolhe aleatoriamente
        escolha_bot = random.choice(list(opcoes.keys()))
        
        # Determinar vencedor
        resultado = self._determinar_vencedor_ppt(escolha_usuario, escolha_bot)
        
        # Criar embed com resultado
        cores = {
            'vitoria': discord.Color.green(),
            'derrota': discord.Color.red(),
            'empate': discord.Color.gold()
        }
        
        mensagens = {
            'vitoria': '🎉 **Parabéns! Tu ganhaste!**',
            'derrota': '😔 **Eu ganhei desta vez!**',
            'empate': '🤝 **Empate!**'
        }
        
        embed = discord.Embed(
            title="🎮 Pedra, Papel, Tesoura",
            description=mensagens[resultado],
            color=cores[resultado]
        )
        embed.add_field(name="Tu escolheste", value=f"{opcoes[escolha_usuario]} {escolha_usuario.capitalize()}", inline=True)
        embed.add_field(name="Eu escolhi", value=f"{opcoes[escolha_bot]} {escolha_bot.capitalize()}", inline=True)
        
        await ctx.send(embed=embed)
    
    def _determinar_vencedor_ppt(self, jogador, bot):
        """Determina o vencedor do jogo pedra-papel-tesoura"""
        if jogador == bot:
            return 'empate'
        
        vitorias = {
            'pedra': 'tesoura',
            'papel': 'pedra',
            'tesoura': 'papel'
        }
        
        if vitorias[jogador] == bot:
            return 'vitoria'
        return 'derrota'
    
    @commands.hybrid_command(name='dado', aliases=['dice', 'roll'])
    async def rolar_dado(self, ctx, lados: int = 6):
        """Rola um dado! Uso: /dado [número de lados]"""
        if lados < 2:
            await ctx.send("❌ O dado precisa ter pelo menos 2 lados!")
            return
        
        if lados > 100:
            await ctx.send("❌ Máximo de 100 lados!")
            return
        
        resultado = random.randint(1, lados)
        
        emoji_dados = {
            1: '⚀', 2: '⚁', 3: '⚂', 4: '⚃', 5: '⚄', 6: '⚅'
        }
        
        emoji = emoji_dados.get(resultado, '🎲') if lados == 6 else '🎲'
        
        embed = discord.Embed(
            title=f"{emoji} Resultado do Dado",
            description=f"🎲 Rolaste um dado de **{lados}** lados\n\n**Resultado: {resultado}**",
            color=discord.Color.purple()
        )
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='moeda', aliases=['coin', 'flip'])
    async def atirar_moeda(self, ctx):
        """Atira uma moeda ao ar! Cara ou coroa?"""
        resultado = random.choice(['cara', 'coroa'])
        emoji = '🟡' if resultado == 'cara' else '🟢'
        
        embed = discord.Embed(
            title="🪙 Atirar a Moeda",
            description=f"{emoji} Saiu **{resultado.upper()}**!",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='escolher', aliases=['choose', 'pick'])
    async def escolher(self, ctx, opcoes: str):
        """Escolhe uma opção entre valores separados por |."""
        opcoes = [opcao.strip() for opcao in opcoes.split("|") if opcao.strip()]
        if len(opcoes) < 2:
            embed = discord.Embed(
                title="🎯 Escolher Opção",
                description="Preciso de pelo menos 2 opções para escolher!",
                color=discord.Color.red()
            )
            embed.set_footer(text='Uso: /escolher opção1 | opção2 | opção3')
            await ctx.send(embed=embed)
            return
        
        escolha = random.choice(opcoes)
        
        embed = discord.Embed(
            title="🎯 A Minha Escolha",
            description=f"Das {len(opcoes)} opções, eu escolho:\n\n**✨ {escolha}**",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='8ball', aliases=['bola8', 'pergunta'])
    async def bola_magica(self, ctx, *, pergunta: str = None):
        """Faz uma pergunta à bola mágica! Uso: /8ball <pergunta>"""
        if not pergunta:
            embed = discord.Embed(
                title="🔮 Bola Mágica",
                description="Faz-me uma pergunta e eu responderei!",
                color=discord.Color.purple()
            )
            embed.set_footer(text="Uso: /8ball <tua pergunta>")
            await ctx.send(embed=embed)
            return
        
        respostas_positivas = [
            "✅ Sim, com certeza!",
            "✅ É certo que sim!",
            "✅ Sem dúvida!",
            "✅ Podes contar com isso!",
            "✅ As estrelas indicam que sim!",
            "✅ Com toda a certeza!",
            "✅ Muito provável!",
            "✅ Parece que sim!"
        ]
        
        respostas_neutras = [
            "🤔 Talvez...",
            "🤔 Não tenho a certeza...",
            "🤔 Pergunta-me mais tarde.",
            "🤔 É melhor não te dizer agora.",
            "🤔 Concentra-te e pergunta de novo.",
            "🤔 As respostas não são claras.",
            "🤔 Tenta outra vez."
        ]
        
        respostas_negativas = [
            "❌ Não contes com isso.",
            "❌ A minha resposta é não.",
            "❌ As minhas fontes dizem que não.",
            "❌ Não parece provável.",
            "❌ Muito duvidoso.",
            "❌ Não, definitivamente não.",
            "❌ Impossível!"
        ]
        
        todas_respostas = respostas_positivas + respostas_neutras + respostas_negativas
        resposta = random.choice(todas_respostas)
        
        embed = discord.Embed(
            title="🔮 Bola Mágica",
            color=discord.Color.purple()
        )
        embed.add_field(name="❓ Pergunta", value=pergunta, inline=False)
        embed.add_field(name="💭 Resposta", value=resposta, inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='adivinhar', aliases=['guess', 'numero'])
    async def adivinhar_numero(self, ctx, palpite: int = None):
        """Tenta adivinhar o número entre 1 e 10! Uso: /adivinhar <número>"""
        numero_secreto = random.randint(1, 10)
        
        if palpite is None:
            embed = discord.Embed(
                title="🎲 Adivinhar o Número",
                description="Estou a pensar num número entre **1 e 10**!\nTenta adivinhar!",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Uso: /adivinhar <número>")
            await ctx.send(embed=embed)
            return
        
        if palpite < 1 or palpite > 10:
            await ctx.send("❌ Escolhe um número entre 1 e 10!")
            return
        
        if palpite == numero_secreto:
            embed = discord.Embed(
                title="🎉 Acertaste!",
                description=f"O número era mesmo **{numero_secreto}**!\n\nParabéns! 🎊",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="😔 Erraste!",
                description=f"Pensaste em **{palpite}** mas o número era **{numero_secreto}**!\n\nTenta outra vez!",
                color=discord.Color.red()
            )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='jogos', aliases=['games', 'listarjogos'])
    async def listar_jogos(self, ctx):
        """Mostra todos os jogos disponíveis"""
        embed = discord.Embed(
            title="🎮 Jogos Disponíveis",
            description="Diverte-te com estes jogos rápidos!",
            color=discord.Color.blurple()
        )
        
        jogos = [
            ("🪨📄✂️ Pedra, Papel, Tesoura", "`/ppt <pedra|papel|tesoura>`", "Joga o clássico jogo!"),
            ("🎲 Rolar Dado", "`/dado [lados]`", "Rola um dado de N lados"),
            ("🪙 Atirar Moeda", "`/moeda`", "Cara ou coroa?"),
            ("🎯 Escolher", "`/escolher opção1 | opção2`", "Deixa-me escolher por ti"),
            ("🔮 Bola Mágica", "`/8ball <pergunta>`", "Faz uma pergunta ao destino"),
            ("🎲 Adivinhar Número", "`/adivinhar <número>`", "Adivinha o número entre 1 e 10")
        ]
        
        for nome, comando, descricao in jogos:
            embed.add_field(
                name=f"{nome}",
                value=f"{descricao}\n{comando}",
                inline=False
            )
        
        embed.set_footer(text="Diverte-te! 🎉")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Games(bot))
