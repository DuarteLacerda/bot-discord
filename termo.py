import asyncio
import json
import logging
import os
import random
from datetime import datetime, timedelta
from typing import Dict, Optional

import discord
from discord.ext import commands

# Configurações do Termo
MAX_TENTATIVAS = 6
TAMANHO_PALAVRA = 5

# Recompensas de XP baseadas no número de tentativas
RECOMPENSAS_XP = {
    1: 500,  # Acertar de primeira é muito difícil!
    2: 300,
    3: 200,
    4: 150,
    5: 100,
    6: 50,
}

# Arquivo com as palavras do jogo
PALAVRAS_FILE = "termo_palavras.json"
# Arquivo com dados dos jogadores
TERMO_DATA_FILE = "termo_data.json"


class Termo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.palavras: list = []
        self.jogos_ativos: Dict[int, Dict] = {}  # {user_id: {"palavra": str, "tentativas": [], "canal": channel}}
        self.dados_jogadores: Dict[int, Dict[int, Dict]] = {}  # {guild_id: {user_id: {"jogos": int, "vitorias": int, "tentativas_media": float}}}
        self._carregar_palavras()
        self._carregar_dados()

    def _carregar_palavras(self):
        """Carrega lista de palavras ou cria uma padrão."""
        if os.path.exists(PALAVRAS_FILE):
            try:
                with open(PALAVRAS_FILE, "r", encoding="utf-8") as f:
                    self.palavras = json.load(f)
                logging.info(f"Carregadas {len(self.palavras)} palavras para o Termo.")
            except Exception:
                logging.exception("Falha ao carregar palavras do Termo.")
                self._criar_palavras_padrao()
        else:
            self._criar_palavras_padrao()

    def _criar_palavras_padrao(self):
        """Cria lista padrão de palavras portuguesas de 5 letras."""
        self.palavras = [
            "carro", "porta", "ponte", "livro", "praia", "monte", "terra", "mundo",
            "festa", "campo", "plano", "grito", "coisa", "tempo", "chave", "tinta",
            "caixa", "pedra", "gosto", "folha", "noite", "manha", "tarde", "vapor",
            "trilho", "musica", "pintar", "gritar", "saltar", "correr", "dormir", "subir",
            "andar", "falar", "ouvir", "cheirar", "tocar", "banco", "risco", "calor",
            "frio", "vento", "chuva", "neve", "gelo", "fogueira", "brasa", "chama",
            "fumo", "nuvem", "estrela", "lunar", "solar", "cosmos", "planeta", "cometa",
            "astro", "orbita", "fusao", "plasma", "atomo", "quark", "neutrino", "massa",
            "forca", "energia", "poder", "metal", "ferro", "cobre", "ouro", "prata",
            "bronze", "cristal", "vidro", "pedra", "rocha", "areia", "lama", "barro",
            "argila", "terra", "solo", "chao", "piso", "base", "fundo", "topo",
            "cume", "pico", "vale", "colina", "morro", "serra", "cordilheira", "monte"
        ]
        # Salva as palavras
        try:
            with open(PALAVRAS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.palavras, f, indent=2, ensure_ascii=False)
            logging.info(f"Criado ficheiro com {len(self.palavras)} palavras padrão.")
        except Exception:
            logging.exception("Falha ao criar ficheiro de palavras.")

    def _carregar_dados(self):
        """Carrega dados de estatísticas dos jogadores."""
        if os.path.exists(TERMO_DATA_FILE):
            try:
                with open(TERMO_DATA_FILE, "r") as f:
                    raw = json.load(f)
                    self.dados_jogadores = {
                        int(guild_id): {int(user_id): data for user_id, data in users.items()}
                        for guild_id, users in raw.items()
                    }
                logging.info("Dados do Termo carregados.")
            except Exception:
                logging.exception("Falha ao carregar dados do Termo.")
                self.dados_jogadores = {}

    def _salvar_dados(self):
        """Salva dados de estatísticas dos jogadores."""
        try:
            with open(TERMO_DATA_FILE, "w") as f:
                json.dump(self.dados_jogadores, f, indent=2)
        except Exception:
            logging.exception("Falha ao salvar dados do Termo.")

    def _get_dados_jogador(self, guild_id: int, user_id: int) -> Dict:
        """Obtém ou cria dados de um jogador."""
        if guild_id not in self.dados_jogadores:
            self.dados_jogadores[guild_id] = {}
        if user_id not in self.dados_jogadores[guild_id]:
            self.dados_jogadores[guild_id][user_id] = {
                "jogos": 0,
                "vitorias": 0,
                "total_tentativas": 0,
            }
        return self.dados_jogadores[guild_id][user_id]

    def _escolher_palavra(self) -> str:
        """Escolhe uma palavra aleatória da lista."""
        if not self.palavras:
            return "termo"  # fallback
        return random.choice(self.palavras).upper()

    def _verificar_tentativa(self, palavra_secreta: str, tentativa: str) -> list:
        """
        Verifica a tentativa e retorna lista de resultados:
        🟩 = letra correta na posição correta
        🟨 = letra correta na posição errada
        ⬜ = letra não existe na palavra
        """
        resultado = []
        palavra_secreta = palavra_secreta.upper()
        tentativa = tentativa.upper()
        
        # Conta ocorrências de cada letra na palavra secreta
        contagem = {}
        for letra in palavra_secreta:
            contagem[letra] = contagem.get(letra, 0) + 1
        
        # Primeira passagem: marca letras corretas (🟩)
        status = ["⬜"] * len(tentativa)
        for i, letra in enumerate(tentativa):
            if i < len(palavra_secreta) and letra == palavra_secreta[i]:
                status[i] = "🟩"
                contagem[letra] -= 1
        
        # Segunda passagem: marca letras na posição errada (🟨)
        for i, letra in enumerate(tentativa):
            if status[i] == "⬜" and letra in contagem and contagem[letra] > 0:
                status[i] = "🟨"
                contagem[letra] -= 1
        
        return status

    def _criar_embed_jogo(self, tentativas: list, num_tentativas: int, palavra_acertada: bool = False, palavra_secreta: str = "") -> discord.Embed:
        """Cria embed mostrando o estado do jogo."""
        if palavra_acertada:
            cor = discord.Color.green()
            titulo = "🎉 Parabéns! Acertaste a palavra!"
        elif num_tentativas >= MAX_TENTATIVAS:
            cor = discord.Color.red()
            titulo = f"😔 Fim de jogo! A palavra era: **{palavra_secreta}**"
        else:
            cor = discord.Color.blue()
            titulo = f"🎮 Termo - Tentativa {num_tentativas}/{MAX_TENTATIVAS}"
        
        embed = discord.Embed(title=titulo, color=cor)
        
        # Mostra tentativas anteriores
        if tentativas:
            historico = "\n".join([
                f"{tent['palavra']} {''.join(tent['resultado'])}"
                for tent in tentativas
            ])
            embed.add_field(name="Tentativas", value=historico, inline=False)
        
        # Instruções
        if not palavra_acertada and num_tentativas < MAX_TENTATIVAS:
            embed.add_field(
                name="Como jogar",
                value="Digite uma palavra de 5 letras.\n🟩 = Letra correta\n🟨 = Letra existe mas na posição errada\n⬜ = Letra não existe",
                inline=False
            )
        
        return embed

    async def _dar_recompensa_xp(self, ctx: commands.Context, num_tentativas: int):
        """Dá XP ao jogador baseado no número de tentativas."""
        xp_ganho = RECOMPENSAS_XP.get(num_tentativas, 25)
        
        # Obtém o cog de Levels para dar XP
        levels_cog = self.bot.get_cog("Levels")
        if levels_cog:
            user_data = levels_cog._get_user_data(ctx.guild.id, ctx.author.id)
            nivel_anterior = user_data["level"]
            user_data["xp"] += xp_ganho
            nivel_novo = levels_cog._calcular_nivel(user_data["xp"])
            
            if nivel_novo > nivel_anterior:
                user_data["level"] = nivel_novo
            
            levels_cog._save_data()
            
            await ctx.send(f"💰 Ganhaste **{xp_ganho} XP** por completar o Termo em {num_tentativas} tentativas!")
        else:
            await ctx.send(f"🎁 Completaste o Termo em {num_tentativas} tentativas!")

    @commands.command(name="termo", aliases=["t"])
    async def termo(self, ctx):
        """Inicia um novo jogo de Termo."""
        user_id = ctx.author.id
        
        # Verifica se já há um jogo ativo
        if user_id in self.jogos_ativos:
            await ctx.send("❌ Já tens um jogo ativo! Termina-o primeiro ou usa `!termosair` para desistir.")
            return
        
        # Inicia novo jogo
        palavra_secreta = self._escolher_palavra()
        self.jogos_ativos[user_id] = {
            "palavra": palavra_secreta,
            "tentativas": [],
            "canal": ctx.channel,
            "guild_id": ctx.guild.id,
        }
        
        embed = self._criar_embed_jogo([], 0)
        await ctx.send(embed=embed)
        await ctx.send(f"{ctx.author.mention}, o teu jogo começou! Envia uma palavra de {TAMANHO_PALAVRA} letras.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Escuta mensagens para processar tentativas do jogo."""
        # Ignora bots e mensagens de DM
        if message.author.bot or not message.guild:
            return
        
        user_id = message.author.id
        
        # Verifica se o usuário tem jogo ativo
        if user_id not in self.jogos_ativos:
            return
        
        jogo = self.jogos_ativos[user_id]
        
        # Verifica se é no canal correto
        if message.channel.id != jogo["canal"].id:
            return
        
        # Verifica se é um comando (ignora comandos)
        if message.content.startswith(("!", "?", ".", "/")):
            return
        
        tentativa = message.content.strip().upper()
        
        # Valida a tentativa
        if len(tentativa) != TAMANHO_PALAVRA:
            await message.channel.send(f"❌ A palavra deve ter exatamente {TAMANHO_PALAVRA} letras!")
            return
        
        if not tentativa.isalpha():
            await message.channel.send("❌ Usa apenas letras!")
            return
        
        # Processa a tentativa
        palavra_secreta = jogo["palavra"]
        resultado = self._verificar_tentativa(palavra_secreta, tentativa)
        
        jogo["tentativas"].append({
            "palavra": tentativa,
            "resultado": resultado
        })
        
        num_tentativas = len(jogo["tentativas"])
        palavra_acertada = tentativa == palavra_secreta
        
        # Mostra resultado
        embed = self._criar_embed_jogo(
            jogo["tentativas"],
            num_tentativas,
            palavra_acertada,
            palavra_secreta
        )
        await message.channel.send(embed=embed)
        
        # Verifica fim de jogo
        if palavra_acertada:
            # Vitória!
            await self._dar_recompensa_xp(await self.bot.get_context(message), num_tentativas)
            
            # Atualiza estatísticas
            dados = self._get_dados_jogador(jogo["guild_id"], user_id)
            dados["jogos"] += 1
            dados["vitorias"] += 1
            dados["total_tentativas"] += num_tentativas
            self._salvar_dados()
            
            del self.jogos_ativos[user_id]
            
        elif num_tentativas >= MAX_TENTATIVAS:
            # Derrota
            await message.channel.send(f"😢 Não conseguiste desta vez, {message.author.mention}! Tenta novamente com `!termo`")
            
            # Atualiza estatísticas
            dados = self._get_dados_jogador(jogo["guild_id"], user_id)
            dados["jogos"] += 1
            self._salvar_dados()
            
            del self.jogos_ativos[user_id]

    @commands.command(name="termosair", aliases=["termodesistir"])
    async def termo_sair(self, ctx):
        """Desiste do jogo atual de Termo."""
        user_id = ctx.author.id
        
        if user_id not in self.jogos_ativos:
            await ctx.send("❌ Não tens nenhum jogo ativo.")
            return
        
        palavra = self.jogos_ativos[user_id]["palavra"]
        del self.jogos_ativos[user_id]
        
        await ctx.send(f"😔 Desististe do jogo. A palavra era: **{palavra}**")

    @commands.command(name="termostats", aliases=["testats"])
    async def termo_stats(self, ctx, member: discord.Member = None):
        """Mostra estatísticas de Termo de um jogador."""
        member = member or ctx.author
        
        dados = self._get_dados_jogador(ctx.guild.id, member.id)
        
        jogos = dados["jogos"]
        vitorias = dados["vitorias"]
        total_tentativas = dados["total_tentativas"]
        
        if jogos == 0:
            await ctx.send(f"📊 {member.mention} ainda não jogou Termo!")
            return
        
        taxa_vitoria = (vitorias / jogos) * 100 if jogos > 0 else 0
        media_tentativas = total_tentativas / vitorias if vitorias > 0 else 0
        
        embed = discord.Embed(
            title=f"📊 Estatísticas de Termo - {member.display_name}",
            color=discord.Color.blue()
        )
        embed.add_field(name="🎮 Jogos", value=str(jogos), inline=True)
        embed.add_field(name="🏆 Vitórias", value=str(vitorias), inline=True)
        embed.add_field(name="📈 Taxa de Vitória", value=f"{taxa_vitoria:.1f}%", inline=True)
        
        if vitorias > 0:
            embed.add_field(name="🎯 Média de Tentativas", value=f"{media_tentativas:.1f}", inline=True)
        
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        
        await ctx.send(embed=embed)

    @commands.command(name="termorank", aliases=["termoranking"])
    async def termo_rank(self, ctx):
        """Mostra ranking de jogadores de Termo no servidor."""
        if ctx.guild.id not in self.dados_jogadores:
            await ctx.send("📊 Ainda não há dados de Termo neste servidor!")
            return
        
        dados_guild = self.dados_jogadores[ctx.guild.id]
        
        # Ordena por vitórias
        ranking = sorted(
            [(user_id, dados) for user_id, dados in dados_guild.items() if dados["jogos"] > 0],
            key=lambda x: (x[1]["vitorias"], -x[1]["total_tentativas"] / max(x[1]["vitorias"], 1)),
            reverse=True
        )
        
        if not ranking:
            await ctx.send("📊 Ainda não há dados de Termo neste servidor!")
            return
        
        embed = discord.Embed(
            title="🏆 Ranking de Termo",
            color=discord.Color.gold()
        )
        
        # Mostra top 10
        for i, (user_id, dados) in enumerate(ranking[:10], 1):
            try:
                member = await ctx.guild.fetch_member(user_id)
                nome = member.display_name
            except:
                nome = f"Usuário {user_id}"
            
            vitorias = dados["vitorias"]
            jogos = dados["jogos"]
            taxa = (vitorias / jogos * 100) if jogos > 0 else 0
            media = (dados["total_tentativas"] / vitorias) if vitorias > 0 else 0
            
            medalha = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
            
            embed.add_field(
                name=f"{medalha} {nome}",
                value=f"🏆 {vitorias} vitórias | 📈 {taxa:.0f}% | 🎯 {media:.1f} tent.",
                inline=False
            )
        
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Termo(bot))
