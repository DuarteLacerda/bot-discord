import asyncio
import json
import logging
import os
import random
from typing import Dict, List

import discord
from discord.ext import commands

# ===== CONFIGURAÇÃO DE BALANCEAMENTO =====
XP_POR_CARACTERE = 0.5  # XP ganho por caractere escrito
XP_MIN_POR_MSG = 5      # XP mínimo por mensagem (mesmo que seja curta)
XP_MAX_POR_MSG = 50     # XP máximo por mensagem (cap para evitar spam)
COOLDOWN_SEGUNDOS = 10  # Cooldown entre mensagens que dão XP
XP_BASE_NIVEL = 100     # XP necessário para subir do nível 1 para 2
XP_MULTIPLICADOR = 1.15 # Multiplicador de XP por nível (progressão)
NIVEL_MAXIMO = 500      # Nível máximo
# ==========================================

# ===== PRÊMIOS DO CASE OPENING =====
PREMIOS = [
    {"nome": "💰 Bônus de XP Pequeno", "tipo": "xp", "valor": 50, "peso": 40},
    {"nome": "💎 Bônus de XP Médio", "tipo": "xp", "valor": 150, "peso": 25},
    {"nome": "🌟 Bônus de XP Grande", "tipo": "xp", "valor": 300, "peso": 15},
    {"nome": "🔥 Bônus de XP Épico", "tipo": "xp", "valor": 500, "peso": 10},
    {"nome": "⚡ Multiplicador 2x (próximas 10 msgs)", "tipo": "multiplicador", "valor": 2, "peso": 8},
    {"nome": "🎁 Nada especial... mas foi divertido!", "tipo": "nada", "valor": 0, "peso": 2},
]
# ======================================

DATA_FILE = "levels_data.json"


class Levels(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data: Dict[int, Dict[int, Dict]] = {}  # {guild_id: {user_id: {"xp": x, "level": y, "multiplicador": m, "msgs_mult": n}}}
        self.cooldowns: Dict[int, Dict[int, float]] = {}  # {guild_id: {user_id: timestamp}}
        self._load_data()

    def _load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    raw = json.load(f)
                    # Converte strings de volta para ints
                    self.data = {
                        int(guild_id): {int(user_id): data for user_id, data in users.items()}
                        for guild_id, users in raw.items()
                    }
                logging.info("Dados de níveis carregados.")
            except Exception:
                logging.exception("Falha ao carregar dados de níveis.")
                self.data = {}

    def _save_data(self):
        try:
            with open(DATA_FILE, "w") as f:
                json.dump(self.data, f, indent=2)
        except Exception:
            logging.exception("Falha ao salvar dados de níveis.")

    def _get_user_data(self, guild_id: int, user_id: int) -> Dict:
        if guild_id not in self.data:
            self.data[guild_id] = {}
        if user_id not in self.data[guild_id]:
            self.data[guild_id][user_id] = {
                "xp": 0,
                "level": 1,
                "multiplicador": 1,
                "msgs_mult": 0,
            }
        # Migração para dados antigos
        user = self.data[guild_id][user_id]
        if "multiplicador" not in user:
            user["multiplicador"] = 1
        if "msgs_mult" not in user:
            user["msgs_mult"] = 0
        return user

    def _xp_para_proximo_nivel(self, nivel: int) -> int:
        """Calcula XP necessário para subir de nível."""
        return int(XP_BASE_NIVEL * (XP_MULTIPLICADOR ** (nivel - 1)))

    def _calcular_nivel(self, xp: int) -> int:
        """Calcula nível baseado no XP total."""
        nivel = 1
        xp_acumulado = 0
        while nivel < NIVEL_MAXIMO:
            xp_necessario = self._xp_para_proximo_nivel(nivel)
            if xp < xp_acumulado + xp_necessario:
                break
            xp_acumulado += xp_necessario
            nivel += 1
        return nivel

    def _sortear_premio(self) -> Dict:
        """Sorteia um prêmio baseado nos pesos."""
        pesos = [p["peso"] for p in PREMIOS]
        return random.choices(PREMIOS, weights=pesos, k=1)[0]

    async def _abrir_case(self, channel: discord.TextChannel, member: discord.Member) -> Dict:
        """Simula abertura de case e retorna o prêmio."""
        msg = await channel.send(f"🎁 {member.mention} está abrindo uma caixa de prêmios...")
        await asyncio.sleep(1)
        await msg.edit(content=f"🎁 {member.mention} está abrindo uma caixa de prêmios... 🔄")
        await asyncio.sleep(1)
        
        premio = self._sortear_premio()
        
        embed = discord.Embed(
            title="🎉 Prêmio Obtido!",
            description=f"**{premio['nome']}**",
            color=discord.Color.gold(),
        )
        embed.set_footer(text=f"Level Up! Novo nível alcançado!")
        
        await msg.edit(content=None, embed=embed)
        return premio

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignora bots e mensagens sem guild
        if message.author.bot or not message.guild:
            return

        guild_id = message.guild.id
        user_id = message.author.id

        # Cooldown
        import time
        now = time.time()
        if guild_id not in self.cooldowns:
            self.cooldowns[guild_id] = {}
        last_msg = self.cooldowns[guild_id].get(user_id, 0)
        if now - last_msg < COOLDOWN_SEGUNDOS:
            return
        self.cooldowns[guild_id][user_id] = now

        # Calcula XP ganho
        caracteres = len(message.content)
        xp_ganho = caracteres * XP_POR_CARACTERE
        xp_ganho = max(XP_MIN_POR_MSG, min(xp_ganho, XP_MAX_POR_MSG))

        # Atualiza dados
        user_data = self._get_user_data(guild_id, user_id)
        
        # Aplica multiplicador se ativo
        if user_data["multiplicador"] > 1 and user_data["msgs_mult"] > 0:
            xp_ganho *= user_data["multiplicador"]
            user_data["msgs_mult"] -= 1
            if user_data["msgs_mult"] <= 0:
                user_data["multiplicador"] = 1
        
        nivel_anterior = user_data["level"]
        user_data["xp"] += int(xp_ganho)
        nivel_novo = self._calcular_nivel(user_data["xp"])

        if nivel_novo > nivel_anterior and nivel_novo <= NIVEL_MAXIMO:
            user_data["level"] = nivel_novo
            self._save_data()
            try:
                # Abre case e aplica prêmio
                premio = await self._abrir_case(message.channel, message.author)
                
                if premio["tipo"] == "xp":
                    user_data["xp"] += premio["valor"]
                    # Recalcula nível após bônus
                    nivel_pos_bonus = self._calcular_nivel(user_data["xp"])
                    if nivel_pos_bonus > nivel_novo:
                        user_data["level"] = nivel_pos_bonus
                        await message.channel.send(
                            f"🚀 {message.author.mention} ganhou XP suficiente para subir mais um nível! Agora está no nível **{nivel_pos_bonus}**!"
                        )
                elif premio["tipo"] == "multiplicador":
                    user_data["multiplicador"] = premio["valor"]
                    user_data["msgs_mult"] = 10
                
                self._save_data()
            except Exception:
                logging.exception("Falha ao abrir case")
        else:
            # Salva periodicamente (a cada 10 mensagens processadas)
            if user_id % 10 == 0:
                self._save_data()

    @commands.command(name="nivel", aliases=["level"])
    async def nivel(self, ctx, member: discord.Member = None):
        """Mostra o nível e XP de um usuário."""
        member = member or ctx.author
        if not ctx.guild:
            await ctx.send("Comando disponível apenas em servidores.")
            return

        user_data = self._get_user_data(ctx.guild.id, member.id)
        nivel = user_data["level"]
        xp_atual = user_data["xp"]

        # Calcula XP acumulado até o nível atual
        xp_acumulado = 0
        for lvl in range(1, nivel):
            xp_acumulado += self._xp_para_proximo_nivel(lvl)

        xp_no_nivel = xp_atual - xp_acumulado
        xp_necessario = self._xp_para_proximo_nivel(nivel) if nivel < NIVEL_MAXIMO else 0

        embed = discord.Embed(title=f"Nível de {member.display_name}", color=discord.Color.gold())
        embed.add_field(name="Nível", value=f"{nivel}/{NIVEL_MAXIMO}", inline=True)
        embed.add_field(name="XP Total", value=f"{xp_atual}", inline=True)
        
        # Mostra multiplicador ativo
        if user_data.get("multiplicador", 1) > 1 and user_data.get("msgs_mult", 0) > 0:
            embed.add_field(
                name="⚡ Multiplicador Ativo",
                value=f"{user_data['multiplicador']}x ({user_data['msgs_mult']} msgs restantes)",
                inline=False,
            )
        
        if nivel < NIVEL_MAXIMO:
            embed.add_field(
                name="Progresso",
                value=f"{xp_no_nivel}/{xp_necessario} XP para nível {nivel + 1}",
                inline=False,
            )
        else:
            embed.add_field(name="Status", value="🏆 Nível Máximo Atingido!", inline=False)

        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="rank", aliases=["ranking"])
    async def rank(self, ctx):
        """Mostra o top 10 do servidor."""
        if not ctx.guild:
            await ctx.send("Comando disponível apenas em servidores.")
            return

        guild_data = self.data.get(ctx.guild.id, {})
        if not guild_data:
            await ctx.send("Nenhum dado de nível disponível neste servidor.")
            return

        # Ordena por XP total
        ranking = sorted(guild_data.items(), key=lambda x: x[1]["xp"], reverse=True)[:10]

        embed = discord.Embed(title=f"🏆 Top 10 - {ctx.guild.name}", color=discord.Color.purple())
        lines = []
        for i, (user_id, data) in enumerate(ranking, 1):
            member = ctx.guild.get_member(user_id)
            name = member.display_name if member else f"Usuário {user_id}"
            lines.append(f"{i}. **{name}** - Nível {data['level']} ({data['xp']} XP)")

        embed.description = "\n".join(lines) if lines else "Nenhum usuário no ranking."
        await ctx.send(embed=embed)

    @commands.command(name="addxp", aliases=["adicionarxp"])
    @commands.has_permissions(administrator=True)
    async def addxp(self, ctx, member: discord.Member, xp: int):
        """Adiciona XP a um usuário (apenas admins)."""
        if not ctx.guild:
            await ctx.send("Comando disponível apenas em servidores.")
            return
        
        if xp <= 0:
            await ctx.send("O valor de XP deve ser positivo.")
            return
        
        user_data = self._get_user_data(ctx.guild.id, member.id)
        nivel_anterior = user_data["level"]
        user_data["xp"] += xp
        nivel_novo = self._calcular_nivel(user_data["xp"])
        
        if nivel_novo > nivel_anterior and nivel_novo <= NIVEL_MAXIMO:
            user_data["level"] = nivel_novo
        
        self._save_data()
        
        await ctx.send(
            f"✅ Adicionado **{xp} XP** para {member.mention}. "
            f"{'Novo nível: **' + str(nivel_novo) + '**!' if nivel_novo > nivel_anterior else ''}"
        )

    @addxp.error
    async def addxp_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Precisas de permissões de administrador para usar este comando.")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ Membro não encontrado.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Uso correto: `l!addxp @usuário quantidade`")


async def setup(bot: commands.Bot):
    await bot.add_cog(Levels(bot))
