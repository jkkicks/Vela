"""Onboarding views with buttons and modals"""

import discord
from discord import Interaction
import logging
from datetime import datetime
from src.shared.database import get_session
from src.shared.models import Member, Role, AuditLog, Guild
from sqlmodel import select

logger = logging.getLogger(__name__)


def create_onboarding_modal(guild_id: int):
    """Factory function to create a dynamic onboarding modal based on guild settings"""

    # Fetch guild settings to get configured fields
    with next(get_session()) as session:
        guild = session.exec(select(Guild).where(Guild.guild_id == guild_id)).first()

        # Get configured fields from settings, or use defaults
        if guild and guild.settings and "onboarding_fields" in guild.settings:
            fields_config = guild.settings["onboarding_fields"]
        else:
            # Default fields if none configured
            fields_config = [
                {
                    "name": "first_name",
                    "label": "First Name",
                    "placeholder": "John",
                    "max_length": 50,
                    "required": True,
                },
                {
                    "name": "last_name",
                    "label": "Last Name",
                    "placeholder": "Doe",
                    "max_length": 50,
                    "required": True,
                },
            ]

        # Get nickname template
        nickname_template = None
        if guild and guild.settings and "nickname_template" in guild.settings:
            nickname_template = guild.settings["nickname_template"]

    # Create modal class dynamically
    class DynamicOnboardingModal(discord.ui.Modal, title="Complete Onboarding"):
        """Dynamically generated modal for collecting user information"""

        def __init__(self):
            super().__init__()
            self.guild_id = guild_id
            self.fields_config = fields_config
            self.nickname_template = nickname_template
            self.field_inputs = {}

            # Dynamically add text inputs based on configuration
            for field_config in fields_config:
                text_input = discord.ui.TextInput(
                    style=discord.TextStyle.short,
                    label=field_config["label"],
                    placeholder=field_config.get("placeholder", ""),
                    required=field_config.get("required", True),
                    max_length=field_config.get("max_length", 100),
                    min_length=1 if field_config.get("required", True) else 0,
                )
                # Store reference to access values later
                self.field_inputs[field_config["name"]] = text_input
                self.add_item(text_input)

        async def on_submit(self, interaction: Interaction):
            """Handle modal submission"""
            try:
                # Collect all field values
                field_values = {}
                for field_name, text_input in self.field_inputs.items():
                    field_values[field_name] = text_input.value

                # Generate nickname from template or default
                if self.nickname_template:
                    nickname = self.nickname_template
                    for field_name, field_value in field_values.items():
                        nickname = nickname.replace(f"{{{field_name}}}", field_value)
                    # Truncate to Discord's 32 character limit
                    nickname = nickname[:32]
                else:
                    # Default: use first_name and last_name if available
                    first_name = field_values.get("first_name", "")
                    last_name = field_values.get("last_name", "")
                    if first_name and last_name:
                        nickname = f"{first_name} {last_name}"[:32]
                    else:
                        # Use first available field value
                        nickname = (
                            list(field_values.values())[0][:32]
                            if field_values
                            else interaction.user.name
                        )

                onboarded_role_id = None
                guild_settings = {}

                with next(get_session()) as session:
                    # Get or create member record
                    db_member = session.exec(
                        select(Member).where(
                            Member.user_id == interaction.user.id,
                            Member.guild_id == interaction.guild.id,
                        )
                    ).first()

                    if not db_member:
                        db_member = Member(
                            user_id=interaction.user.id,
                            guild_id=interaction.guild.id,
                            username=interaction.user.name,
                            join_datetime=interaction.user.joined_at,
                        )
                        session.add(db_member)

                    # Update member information with collected field values
                    # Store standard fields if they exist
                    if "first_name" in field_values:
                        db_member.firstname = field_values["first_name"]
                    if "last_name" in field_values:
                        db_member.lastname = field_values["last_name"]
                    if "email" in field_values:
                        db_member.email = field_values["email"]

                    # Store all field values in extra_data for custom fields
                    if db_member.extra_data is None:
                        db_member.extra_data = {}
                    db_member.extra_data["onboarding_fields"] = field_values

                    db_member.nickname = nickname
                    db_member.onboarding_status = 1
                    db_member.onboarding_completed_at = datetime.utcnow()
                    db_member.last_change_datetime = datetime.utcnow()

                    # Force SQLAlchemy to detect the change to extra_data
                    from sqlalchemy.orm import attributes

                    attributes.flag_modified(db_member, "extra_data")

                    session.commit()

                    # Get guild settings
                    guild = session.exec(
                        select(Guild).where(Guild.guild_id == interaction.guild.id)
                    ).first()
                    if guild and guild.settings:
                        guild_settings = guild.settings

                    # Get onboarded role (retrieve ID while session is open)
                    onboarded_role = session.exec(
                        select(Role).where(
                            Role.guild_id == interaction.guild.id,
                            Role.role_type == "onboarded",
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
                        details={"nickname": nickname, "fields": field_values},
                    )
                    session.add(audit_log)
                    session.commit()

                # Update Discord nickname if enabled (with error handling)
                if guild_settings.get("set_nickname", True):
                    try:
                        await interaction.user.edit(nick=nickname)
                        logger.info(
                            f"✓ Updated nickname for {interaction.user.name} to {nickname}"
                        )
                    except discord.Forbidden:
                        logger.warning(
                            f"Missing permission to change nickname for {interaction.user.name}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Could not update nickname for {interaction.user.name}: {e}"
                        )

                # Add role if configured and enabled (with error handling)
                if guild_settings.get("auto_role", True) and onboarded_role_id:
                    logger.info(
                        f"Attempting to add role {onboarded_role_id} to {interaction.user.name}"
                    )
                    try:
                        role = interaction.guild.get_role(onboarded_role_id)
                        if role:
                            await interaction.user.add_roles(role)
                            logger.info(
                                f"✓ Successfully added role {role.name} to {interaction.user.name}"
                            )
                        else:
                            logger.warning(
                                f"✗ Onboarded role {onboarded_role_id} not found in guild {interaction.guild.id}"
                            )
                    except discord.Forbidden as e:
                        logger.warning(
                            f"✗ Missing permission to add role to {interaction.user.name}: {e}"
                        )
                    except Exception as e:
                        logger.error(
                            f"✗ Could not add role to {interaction.user.name}: {e}",
                            exc_info=True,
                        )
                else:
                    logger.info(
                        f"No onboarded role configured or auto_role disabled for guild {interaction.guild.id}"
                    )

                await interaction.response.send_message(
                    f"✅ Thanks for completing onboarding, {nickname}!\n"
                    "If you have any questions, don't hesitate to reach out!",
                    ephemeral=True,
                )

                logger.info(
                    f"User {interaction.user.name} completed onboarding as {nickname}"
                )

            except Exception as e:
                logger.error(f"Error in onboarding modal: {e}", exc_info=True)
                await interaction.response.send_message(
                    "❌ An error occurred during onboarding. Please try again or contact an administrator.",
                    ephemeral=True,
                )

        async def on_error(self, interaction: Interaction, error: Exception):
            """Handle errors in the modal"""
            logger.error(f"Onboarding modal error: {error}")
            await interaction.response.send_message(
                "An error occurred. Please try again.", ephemeral=True
            )

    return DynamicOnboardingModal()


class OnboardingView(discord.ui.View):
    """Persistent view with onboarding buttons"""

    def __init__(self, guild_id: int = None):
        super().__init__(timeout=None)  # Persistent view
        self.guild_id = guild_id

        # Load help button configuration from guild settings
        self.help_config = self._load_help_config()

        # Only add the help button if it's enabled
        if self.help_config.get("enabled", True):
            help_button = discord.ui.Button(
                label=self.help_config.get("button_text", "Need Help?"),
                style=discord.ButtonStyle.secondary,
                custom_id="vela:help",
                emoji="🤝",
            )
            help_button.callback = self.help_button_callback
            self.add_item(help_button)

    def _load_help_config(self):
        """Load help button configuration from database"""
        if not self.guild_id:
            return {"enabled": True}

        try:
            with next(get_session()) as session:
                guild = session.exec(
                    select(Guild).where(Guild.guild_id == self.guild_id)
                ).first()

                if guild and guild.settings:
                    return guild.settings.get(
                        "help_button_config",
                        {
                            "enabled": True,
                            "button_text": "Need Help?",
                            "message_content": "We're here to assist you! If you need help with onboarding or have any questions, please contact a moderator or admin.",
                        },
                    )
        except Exception as e:
            logger.error(f"Error loading help button config: {e}")

        return {
            "enabled": True,
            "button_text": "Need Help?",
            "message_content": "We're here to assist you! If you need help with onboarding or have any questions, please contact a moderator or admin.",
        }

    @discord.ui.button(
        label="Complete Onboarding",
        style=discord.ButtonStyle.success,
        custom_id="vela:onboard",
        emoji="✅",
    )
    async def onboard_button(self, interaction: Interaction, button: discord.ui.Button):
        """Handle onboarding button click"""
        # Check if user is already onboarded and if prevent_reonboarding is enabled
        with next(get_session()) as session:
            db_member = session.exec(
                select(Member).where(
                    Member.user_id == interaction.user.id,
                    Member.guild_id == interaction.guild.id,
                )
            ).first()

            # Get guild settings
            guild = session.exec(
                select(Guild).where(Guild.guild_id == interaction.guild.id)
            ).first()

            prevent_reonboarding = True
            if guild and guild.settings:
                prevent_reonboarding = guild.settings.get("prevent_reonboarding", True)

            if prevent_reonboarding and db_member and db_member.onboarding_status > 0:
                await interaction.response.send_message(
                    "✅ You have already completed onboarding!\n"
                    "To change your nickname, please use the `/setnick` command or contact a moderator.",
                    ephemeral=True,
                )
                return

        # Show the dynamically generated onboarding modal
        modal = create_onboarding_modal(interaction.guild.id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="What is Onboarding?",
        style=discord.ButtonStyle.primary,
        custom_id="vela:about",
        emoji="❓",
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
            color=discord.Color.blue(),
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
            inline=False,
        )

        embed.add_field(
            name="What Information is Collected?",
            value=(
                "• **First and Last Name**: For your server nickname\n"
                "• **Discord ID**: Your unique identifier\n"
                "• **Join Date**: When you joined our community\n"
                "• **Onboarding Status**: Your progress in the server"
            ),
            inline=False,
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
            inline=False,
        )

        embed.add_field(
            name="Get Started",
            value=(
                "Ready to join? Click the **Complete Onboarding** button to begin!\n"
                "If you have questions, feel free to reach out to our moderation team."
            ),
            inline=False,
        )

        embed.set_footer(text="Thank you for joining our community!")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def help_button_callback(self, interaction: Interaction):
        """Handle help button click"""
        # Reload config in case it changed
        help_config = self._load_help_config()

        message_content = help_config.get(
            "message_content",
            "We're here to assist you! If you need help with onboarding or have any questions, please contact a moderator or admin.",
        )

        await interaction.response.send_message(message_content, ephemeral=True)
