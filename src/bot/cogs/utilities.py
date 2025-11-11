"""Utility commands cog"""

import discord
from discord.ext import commands
from discord import app_commands
import random
import logging
from src.bot.permissions import require_command_permission, command_permission_check

logger = logging.getLogger(__name__)


class UtilityCog(commands.Cog):
    """Utility and fun commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="99")
    @command_permission_check()
    async def cmd_nine_nine(self, ctx: commands.Context):
        """Brooklyn Nine-Nine quotes"""
        brooklyn_99_quotes = [
            "I'm the human form of the 💯 emoji.",
            "Bingpot!",
            "Cool. Cool cool cool cool cool cool cool, no doubt no doubt no doubt no doubt.",
            "Title of your sex tape.",
            "Noice!",
            "Toit!",
            "Nine-Nine!",
            "Terry loves yogurt.",
            "Bone?!",
            "I've only had Arlo for a day and a half, but if anything happened to him, I would kill everyone in this room and then myself.",
        ]
        response = random.choice(brooklyn_99_quotes)
        await ctx.send(response)

    @app_commands.command(name="ping", description="Check bot latency")
    @require_command_permission()
    async def slash_ping(self, interaction: discord.Interaction):
        """Check bot latency"""
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(
            f"🏓 Pong! Latency: {latency}ms", ephemeral=True
        )

    @app_commands.command(name="help", description="Get help with bot commands")
    @require_command_permission()
    async def slash_help(self, interaction: discord.Interaction):
        """Display help information"""
        embed = discord.Embed(
            title="Vela Help",
            description="Here are the available commands:",
            color=discord.Color.blue(),
        )

        # User commands
        embed.add_field(
            name="👤 User Commands",
            value=(
                "**/onboard** - Complete your onboarding\n"
                "**/nick** - View your current nickname\n"
                "**/setnick** - Change your nickname\n"
                "**/help** - Show this help message\n"
                "**/ping** - Check bot latency"
            ),
            inline=False,
        )

        # Admin commands
        embed.add_field(
            name="⚙️ Admin Commands",
            value=(
                "**/remove** - Remove a user from database\n"
                "**/stats** - View server statistics\n"
                "**/list_members** - List all members in database\n"
                "**/sync** - Sync slash commands"
            ),
            inline=False,
        )

        # Fun commands
        embed.add_field(
            name="🎮 Fun Commands",
            value=("**!99** - Get a Brooklyn Nine-Nine quote"),
            inline=False,
        )

        embed.set_footer(text="For more help, contact an administrator")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="about", description="About Vela")
    @require_command_permission()
    async def slash_about(self, interaction: discord.Interaction):
        """Display information about the bot"""
        embed = discord.Embed(
            title="About Vela",
            description=(
                "Vela is a modern Discord onboarding bot with a web management interface.\n\n"
                "**Features:**\n"
                "• Automated member onboarding\n"
                "• Web-based configuration panel\n"
                "• Database-driven settings\n"
                "• Multi-guild support\n"
                "• Comprehensive audit logging"
            ),
            color=discord.Color.green(),
        )

        embed.add_field(name="Framework", value="discord.py 2.3.2+", inline=True)
        embed.add_field(
            name="Database", value="SQLModel + SQLite/PostgreSQL", inline=True
        )
        embed.add_field(name="Python", value="3.9+", inline=True)

        embed.set_footer(text="Built with ❤️ using Python")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="server_info", description="Get information about this server"
    )
    @require_command_permission()
    async def slash_server_info(self, interaction: discord.Interaction):
        """Display server information"""
        guild = interaction.guild

        embed = discord.Embed(
            title=f"📊 {guild.name} Server Info", color=discord.Color.blue()
        )

        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)

        embed.add_field(name="Server ID", value=str(guild.id), inline=True)
        embed.add_field(name="Owner", value=str(guild.owner), inline=True)
        embed.add_field(name="Members", value=str(guild.member_count), inline=True)

        embed.add_field(name="Channels", value=str(len(guild.channels)), inline=True)
        embed.add_field(name="Roles", value=str(len(guild.roles)), inline=True)
        embed.add_field(name="Boost Level", value=str(guild.premium_tier), inline=True)

        embed.add_field(
            name="Created On",
            value=guild.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            inline=False,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    """Setup function to add cog to bot"""
    await bot.add_cog(UtilityCog(bot))
