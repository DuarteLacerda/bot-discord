import logging
import os

import discord
from discord.ext import commands


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.auto_role_name = os.getenv("AUTO_ROLE_NAME", "")

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
                title="❌ Erro",
                description="Ocorreu um erro ao executar o comando. Tenta novamente em breve.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except Exception:
            logging.exception("Failed to send error message to user")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Mensagem de boas-vindas para novos membros"""
        # Atribui cargo automaticamente (nome deve coincidir exatamente com o do servidor)
        if self.auto_role_name:
            role = discord.utils.get(member.guild.roles, name=self.auto_role_name)
            if role:
                try:
                    await member.add_roles(role, reason="Auto role para novo membro")
                    logging.info(f"✅ Cargo '{self.auto_role_name}' atribuído a {member.name}")
                except Exception as e:
                    logging.error(f"Erro ao atribuir cargo '{self.auto_role_name}': {e}")
            else:
                logging.warning(
                    f"⚠️ Cargo '{self.auto_role_name}' não encontrado no servidor '{member.guild.name}'"
                )

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
                value="Digite `L!help` para ver todos os comandos disponíveis",
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
                value="Usa `L!help` para descobrir todos os comandos disponíveis!",
                inline=False
            )
            await member.send(embed=welcome_dm)
            logging.info(f"✅ DM de boas-vindas enviada para {member.name}")
        except discord.Forbidden:
            logging.warning(f"⚠️ Não foi possível enviar DM para {member.name} (privado desativado)")


async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))

