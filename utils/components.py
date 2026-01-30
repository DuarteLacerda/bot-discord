"""
Reusable Discord.py components (Views, Buttons, Selects)
"""

import discord
from discord.ext import commands


class MusicPlayerView(discord.ui.View):
    """Control panel for music playback"""
    
    def __init__(self, music_cog: commands.Cog, timeout: int = 180):
        super().__init__(timeout=timeout)
        self.music_cog = music_cog
    
    @discord.ui.button(label="⏸ Pause", style=discord.ButtonStyle.grey)
    async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.defer()
            # Update message or send feedback
        else:
            await interaction.response.send_message("❌ Nothing to pause", ephemeral=True)
    
    @discord.ui.button(label="▶ Resume", style=discord.ButtonStyle.grey)
    async def resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await interaction.response.defer()
        else:
            await interaction.response.send_message("❌ Nothing to resume", ephemeral=True)
    
    @discord.ui.button(label="⏭ Skip", style=discord.ButtonStyle.blurple)
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await interaction.response.defer()
        else:
            await interaction.response.send_message("❌ Nothing to skip", ephemeral=True)
    
    @discord.ui.button(label="⏹ Stop", style=discord.ButtonStyle.red)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            queue = self.music_cog.queues.get(interaction.guild_id, [])
            queue.clear()
            self.music_cog.current.pop(interaction.guild_id, None)
            vc.stop()
            await vc.disconnect()
            await interaction.response.defer()
        else:
            await interaction.response.send_message("❌ Not in voice channel", ephemeral=True)


class ConfirmView(discord.ui.View):
    """Simple Yes/No confirmation dialog"""
    
    def __init__(self, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.result = None
    
    @discord.ui.button(label="✅ Yes", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.result = True
        await interaction.response.defer()
        self.stop()
    
    @discord.ui.button(label="❌ No", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.result = False
        await interaction.response.defer()
        self.stop()


class PaginatedView(discord.ui.View):
    """Paginated embed navigator"""
    
    def __init__(self, embeds: list, timeout: int = 180):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.current_page = 0
        self.message = None
        self._sync_buttons()

    def _sync_buttons(self):
        if hasattr(self, "previous"):
            self.previous.disabled = self.current_page == 0
    
    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.grey)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self._sync_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="▶ Next", style=discord.ButtonStyle.grey)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.embeds:
            await interaction.response.defer()
            return

        if self.current_page < len(self.embeds) - 1:
            self.current_page += 1
        else:
            self.current_page = 0

        self._sync_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
    
    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()
