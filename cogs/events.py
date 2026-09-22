import json
import logging
import os
import random
import unicodedata

import discord
from discord.ext import commands


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Nome do cargo a ser atribuído automaticamente
        self.auto_role_name = os.getenv("AUTO_ROLE_NAME", "zｚＺ").strip()
        
        # Carrega as respostas automáticas do JSON
        self.auto_responses = self._load_auto_responses()
    
    def _load_auto_responses(self) -> dict:
        """Carrega o dicionário de gírias e respostas automáticas do JSON"""
        json_path = os.path.join(os.path.dirname(__file__), "..", "data", "auto_responses.json")
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                logging.info(f"✅ Auto-respostas carregadas: {len(data)} gírias")
                return data
        except FileNotFoundError:
            logging.warning(f"⚠️ Ficheiro {json_path} não encontrado. Auto-respostas desativadas.")
            return {}
        except json.JSONDecodeError as e:
            logging.error(f"❌ Erro ao ler JSON de auto-respostas: {e}")
            return {}
    
    def _remove_accents(self, text: str) -> str:
        """Remove acentos de uma string"""
        nfd = unicodedata.normalize('NFD', text)
        return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Bot {self.bot.user} is online!")
        
        # Set Rich Presence (Bot Status)
        activity = discord.Activity(
            type=discord.ActivityType.listening,
            name="/help"
        )
        await self.bot.change_presence(activity=activity, status=discord.Status.online)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Detecta gírias nas mensagens e responde automaticamente"""
        # Ignora mensagens do próprio bot
        if message.author.bot:
            return
        
        # Converte a mensagem para minúsculas para comparação
        message_lower = message.content.lower()
        message_no_accents = self._remove_accents(message_lower)
        
        # Divide a mensagem em palavras (separadas por espaços, vírgulas, etc.)
        import re
        words = re.findall(r'\b\w+\b', message_lower)
        words_no_accents = re.findall(r'\b\w+\b', message_no_accents)
        
        # Verifica se alguma gíria está na mensagem (com ou sem acentos)
        for slang, responses in self.auto_responses.items():
            slang_lower = slang.lower()
            slang_no_accents = self._remove_accents(slang_lower)
            
            # Para gírias multi-palavra (ex: "na boa"), procura na mensagem completa
            if ' ' in slang_lower:
                if slang_lower in message_lower or slang_no_accents in message_no_accents:
                    response = random.choice(responses)
                    try:
                        await message.channel.send(response)
                        logging.info(f"✅ Auto-resposta enviada para gíria '{slang}' no canal {message.channel.name}")
                    except Exception as e:
                        logging.error(f"Erro ao enviar auto-resposta: {e}")
                    break
            # Para gírias de uma palavra, verifica se é uma palavra completa
            else:
                if slang_lower in words or slang_no_accents in words_no_accents:
                    response = random.choice(responses)
                    try:
                        await message.channel.send(response)
                        logging.info(f"✅ Auto-resposta enviada para gíria '{slang}' no canal {message.channel.name}")
                    except Exception as e:
                        logging.error(f"Erro ao enviar auto-resposta: {e}")
                    break

    @commands.Cog.listener()
    async def on_error(self, event_method, *args, **kwargs):
        logging.exception("Unhandled error in %s", event_method)

    async def _send_command_error(self, destination, error):
        logging.exception("Error during command: %s", error)
        try:
            embed = discord.Embed(
                title="❌ Erro",
                description="Ocorreu um erro ao executar o comando. Tenta novamente em breve.",
                color=discord.Color.red()
            )
            if isinstance(destination, discord.Interaction):
                if destination.response.is_done():
                    await destination.followup.send(embed=embed, ephemeral=True)
                else:
                    await destination.response.send_message(embed=embed, ephemeral=True)
            else:
                await destination.send(embed=embed)
        except Exception:
            logging.exception("Failed to send error message to user")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        await self._send_command_error(ctx, error)

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction, error):
        await self._send_command_error(interaction, error)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Mensagem de boas-vindas para novos membros"""
        # Atribui cargo automaticamente (nome deve coincidir exatamente com o do servidor)
        if self.auto_role_name:
            role = discord.utils.get(member.guild.roles, name=self.auto_role_name)
            if role:
                me = member.guild.me or member.guild.get_member(self.bot.user.id)
                if not me:
                    logging.warning("⚠️ Não foi possível obter o membro do bot no servidor")
                elif not me.guild_permissions.manage_roles:
                    logging.warning("⚠️ O bot não tem permissão para Gerenciar Cargos")
                elif role.managed:
                    logging.warning(f"⚠️ O cargo '{self.auto_role_name}' é gerenciado e não pode ser atribuído")
                elif role >= me.top_role:
                    logging.warning(
                        f"⚠️ O cargo '{self.auto_role_name}' está acima (ou igual) ao cargo do bot"
                    )
                else:
                    try:
                        await member.add_roles(role, reason="Auto role para novo membro")
                        logging.info(f"✅ Cargo '{self.auto_role_name}' atribuído a {member.name}")
                    except Exception as e:
                        logging.error(f"Erro ao atribuir cargo '{self.auto_role_name}': {e}")
            else:
                logging.warning(
                    f"⚠️ Cargo '{self.auto_role_name}' não encontrado no servidor '{member.guild.name}'"
                )
        else:
            logging.warning("⚠️ AUTO_ROLE_NAME não definido; nenhum cargo será atribuído")

        # Tenta enviar mensagem no canal #welcome, caso contrário no #general
        channel = discord.utils.get(member.guild.text_channels, name="welcome") or \
                  discord.utils.get(member.guild.text_channels, name="general")
        
        rules_channel = discord.utils.get(member.guild.text_channels, name="rules")
        general_channel = discord.utils.get(member.guild.text_channels, name="geral🤳")

        rules_mention = rules_channel.mention if rules_channel else "#rules"
        general_mention = general_channel.mention if general_channel else "#geral"

        if channel:
            embed = discord.Embed(
                title="🎉 Bem-vindo ao Servidor!",
                description=f"Olá {member.mention}! Que alegria te ver aqui! 👋",
                color=discord.Color.green()
            )
            embed.add_field(
                name="📋 Primeiros Passos",
                value=f"1. Lê as regras no canal {rules_mention}\n2. Atenção aos updates no canal {general_mention}\n3. Aproveite o servidor!",
                inline=False
            )
            embed.add_field(
                name="ℹ️ Precisa de Ajuda?",
                value="Digite `/help` para ver todos os comandos disponíveis",
                inline=False
            )
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            embed.set_footer(text=f"Membro #{member.guild.member_count}", icon_url=member.guild.icon.url if member.guild.icon else None)
            
            try:
                await channel.send(embed=embed)
                logging.info(f"✅ Mensagem de boas-vindas enviada para {member.name}")
            except Exception as e:
                logging.error(f"Erro ao enviar mensagem de boas-vindas: {e}")
        
        # Envia uma mensagem privada para o novo membro
        try:
            welcome_dm = discord.Embed(
                title="👋 Bem-vindo!",
                description=f"Olá {member.mention}! Que fixe teres entrado no servidor {member.guild.name}.",
                color=discord.Color.blue()
            )
            welcome_dm.add_field(
                name="🏠 Estás no Servidor",
                value=f"{member.guild.name}",
                inline=False
            )
            welcome_dm.add_field(
                name="💬 Dica",
                value="Usa `/help` para descobrir todos os comandos disponíveis!",
                inline=False
            )
            await member.send(embed=welcome_dm)
            logging.info(f"✅ DM de boas-vindas enviada para {member.name}")
        except discord.Forbidden:
            logging.warning(f"⚠️ Não foi possível enviar DM para {member.name} (privado desativado)")


async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))

