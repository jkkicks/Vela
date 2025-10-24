"""Onboarding views with buttons and modals"""
import discord
from discord import ui, Interaction
import logging
from datetime import datetime
from src.shared.database import get_session
from src.shared.models import Member, Role, AuditLog
from sqlmodel import select

logger = logging.getLogger(__name__)


class OnboardingModal(discord.ui.Modal, title="Complete Onboarding"):
    """Modal for collecting user information during onboarding"""

    first_name = discord.ui.TextInput(
        style=discord.TextStyle.short,
        label="First Name",
        required=True,
        placeholder="John",
        min_length=1,
        max_length=50
    )

    last_name = discord.ui.TextInput(
        style=discord.TextStyle.short,
        label="Last Name",
        required=True,
        placeholder="Doe",
        min_length=1,
        max_length=50
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None

    async def on_submit(self, interaction: Interaction):
        """Handle modal submission"""
        try:
            # Update member in database
            nickname = f"{self.first_name.value} {self.last_name.value}"
            onboarded_role_id = None

            with next(get_session()) as session:
                # Get or create member record
                db_member = session.exec(
                    select(Member).where(
                        Member.user_id == interaction.user.id,
                        Member.guild_id == interaction.guild.id
                    )
                ).first()

                if not db_member:
                    db_member = Member(
                        user_id=interaction.user.id,
                        guild_id=interaction.guild.id,
                        username=interaction.user.name,
                        join_datetime=interaction.user.joined_at
                    )
                    session.add(db_member)

                # Update member information
                db_member.firstname = self.first_name.value
                db_member.lastname = self.last_name.value
                db_member.nickname = nickname
                db_member.onboarding_status = 1
                db_member.onboarding_completed_at = datetime.utcnow()
                db_member.last_change_datetime = datetime.utcnow()

                session.commit()

                # Get onboarded role (retrieve ID while session is open)
                onboarded_role = session.exec(
                    select(Role).where(
                        Role.guild_id == interaction.guild.id,
                        Role.role_type == "onboarded"
                    )
                ).first()

                if onboarded_role:
                    onboarded_role_id = onboarded_role.role_id

                # Log the action
                audit_log = AuditLog(
                    guild_id=interaction.guild.id,
                    user_id=interaction.user.id,
                    discord_username=interaction.user.name,
                    action="onboarding_modal_completed",
                    details={
                        "firstname": self.first_name.value,
                        "lastname": self.last_name.value,
                        "nickname": nickname
                    }
                )
                session.add(audit_log)
                session.commit()

            # Update Discord nickname (with error handling)
            try:
                await interaction.user.edit(nick=nickname)
            except discord.Forbidden:
                logger.warning(f"Missing permission to change nickname for {interaction.user.name}")
            except Exception as e:
                logger.warning(f"Could not update nickname for {interaction.user.name}: {e}")

            # Add role if configured (with error handling)
            if onboarded_role_id:
                logger.info(f"Attempting to add role {onboarded_role_id} to {interaction.user.name}")
                try:
                    role = interaction.guild.get_role(onboarded_role_id)
                    if role:
                        await interaction.user.add_roles(role)
                        logger.info(f"✓ Successfully added role {role.name} to {interaction.user.name}")
                    else:
                        logger.warning(f"✗ Onboarded role {onboarded_role_id} not found in guild {interaction.guild.id}")
                except discord.Forbidden as e:
                    logger.warning(f"✗ Missing permission to add role to {interaction.user.name}: {e}")
                except Exception as e:
                    logger.error(f"✗ Could not add role to {interaction.user.name}: {e}", exc_info=True)
            else:
                logger.info(f"No onboarded role configured for guild {interaction.guild.id}")

            await interaction.response.send_message(
                f"✅ Thanks for completing onboarding, {nickname}!\n"
                "If you have any questions, don't hesitate to reach out!",
                ephemeral=True
            )

            logger.info(f"User {interaction.user.name} completed onboarding as {nickname}")

        except Exception as e:
            logger.error(f"Error in onboarding modal: {e}", exc_info=True)
            await interaction.response.send_message(
                "❌ An error occurred during onboarding. Please try again or contact an administrator.",
                ephemeral=True
            )

    async def on_error(self, interaction: Interaction, error: Exception):
        """Handle errors in the modal"""
        logger.error(f"Onboarding modal error: {error}")
        await interaction.response.send_message(
            "An error occurred. Please try again.",
            ephemeral=True
        )


class OnboardingView(discord.ui.View):
    """Persistent view with onboarding buttons"""

    def __init__(self):
        super().__init__(timeout=None)  # Persistent view

    @discord.ui.button(
        label="Complete Onboarding",
        style=discord.ButtonStyle.success,
        custom_id="sparkbot:onboard",
        emoji="✅"
    )
    async def onboard_button(self, interaction: Interaction, button: discord.ui.Button):
        """Handle onboarding button click"""
        # Check if user is already onboarded
        with next(get_session()) as session:
            db_member = session.exec(
                select(Member).where(
                    Member.user_id == interaction.user.id,
                    Member.guild_id == interaction.guild.id
                )
            ).first()

            if db_member and db_member.onboarding_status > 0:
                await interaction.response.send_message(
                    "✅ You have already completed onboarding!\n"
                    "To change your nickname, please use the `/setnick` command or contact a moderator.",
                    ephemeral=True
                )
                return

        # Show the onboarding modal
        modal = OnboardingModal()
        modal.user = interaction.user
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="What is Onboarding?",
        style=discord.ButtonStyle.primary,
        custom_id="sparkbot:about",
        emoji="❓"
    )
    async def about_button(self, interaction: Interaction, button: discord.ui.Button):
        """Handle about button click"""
        embed = discord.Embed(
            title="What is Onboarding?",
            description=(
                "Welcome to our Discord server! We're thrilled to have you join our community. "
                "To unlock the full experience and access more parts of the server, "
                "we ask that you complete the member onboarding process."
            ),
            color=discord.Color.blue()
        )

        embed.add_field(
            name="Why Complete Onboarding?",
            value=(
                "Completing the onboarding process grants you:\n"
                "• Access to additional server channels\n"
                "• Ability to participate in discussions\n"
                "• Access to member-only features\n"
                "• A personalized server experience"
            ),
            inline=False
        )

        embed.add_field(
            name="What Information is Collected?",
            value=(
                "• **First and Last Name**: For your server nickname\n"
                "• **Discord ID**: Your unique identifier\n"
                "• **Join Date**: When you joined our community\n"
                "• **Onboarding Status**: Your progress in the server"
            ),
            inline=False
        )

        embed.add_field(
            name="Privacy & Data Usage",
            value=(
                "We take your privacy seriously:\n"
                "• Data is stored securely in our database\n"
                "• Information is used only for server management\n"
                "• You can request data removal at any time\n"
                "• We never share your data with third parties"
            ),
            inline=False
        )

        embed.add_field(
            name="Get Started",
            value=(
                "Ready to join? Click the **Complete Onboarding** button to begin!\n"
                "If you have questions, feel free to reach out to our moderation team."
            ),
            inline=False
        )

        embed.set_footer(text="Thank you for joining our community!")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="Need Help?",
        style=discord.ButtonStyle.secondary,
        custom_id="sparkbot:help",
        emoji="🤝"
    )
    async def help_button(self, interaction: Interaction, button: discord.ui.Button):
        """Handle help button click"""
        embed = discord.Embed(
            title="Need Help?",
            description="We're here to assist you!",
            color=discord.Color.gold()
        )

        embed.add_field(
            name="Common Issues",
            value=(
                "**Can't complete onboarding?**\n"
                "Make sure you fill in both your first and last name.\n\n"
                "**Already onboarded?**\n"
                "Use `/setnick` to change your nickname.\n\n"
                "**Technical issues?**\n"
                "Contact a moderator for assistance."
            ),
            inline=False
        )

        embed.add_field(
            name="Contact Support",
            value=(
                "• Ping an @Admin or @Moderator\n"
                "• Use the support ticket system (if available)\n"
                "• Send a DM to a staff member"
            ),
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)