"""Onboarding views with buttons and modals"""

import discord
from discord import Interaction
import logging
from datetime import datetime
from src.shared.database import get_session
from src.shared.models import Member, Role, AuditLog, Guild, Channel
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
                    db_member.last_change_datetime = datetime.utcnow()

                    # Force SQLAlchemy to detect the change to extra_data
                    from sqlalchemy.orm import attributes

                    attributes.flag_modified(db_member, "extra_data")

                    # Get guild settings
                    guild = session.exec(
                        select(Guild).where(Guild.guild_id == interaction.guild.id)
                    ).first()
                    if guild and guild.settings:
                        guild_settings = guild.settings

                    # Check approval mode
                    approval_mode = guild_settings.get(
                        "onboarding_approval_mode", "auto"
                    )

                    if approval_mode == "manual":
                        # Manual approval mode - set status to pending (0 or -1)
                        db_member.onboarding_status = 0
                    else:
                        # Auto approval mode - set status to approved
                        db_member.onboarding_status = 1
                        db_member.onboarding_completed_at = datetime.utcnow()

                    session.commit()

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

                # Handle based on approval mode
                if approval_mode == "manual":
                    # Send approval request to the approval channel
                    with next(get_session()) as approval_session:
                        approval_channel = approval_session.exec(
                            select(Channel).where(
                                Channel.guild_id == interaction.guild.id,
                                Channel.channel_type == "onboarding_approval",
                            )
                        ).first()

                        if approval_channel:
                            try:
                                channel = interaction.guild.get_channel(
                                    approval_channel.channel_id
                                )
                                if channel:
                                    # Create approval embed
                                    embed = discord.Embed(
                                        title="📋 Onboarding Approval Request",
                                        description=f"**{interaction.user.mention}** ({interaction.user.name}) has submitted an onboarding request.",
                                        color=discord.Color.orange(),
                                        timestamp=datetime.utcnow(),
                                    )

                                    # Add field values
                                    embed.add_field(
                                        name="Nickname", value=nickname, inline=True
                                    )
                                    embed.add_field(
                                        name="User ID",
                                        value=str(interaction.user.id),
                                        inline=True,
                                    )

                                    # Add custom fields
                                    for field_name, field_value in field_values.items():
                                        embed.add_field(
                                            name=field_name.replace("_", " ").title(),
                                            value=field_value,
                                            inline=True,
                                        )

                                    embed.set_thumbnail(
                                        url=interaction.user.display_avatar.url
                                    )
                                    embed.set_footer(
                                        text=f"Submitted by {interaction.user.name}"
                                    )

                                    # Create approve/deny buttons view (we'll create this below)
                                    approval_view = OnboardingApprovalView(
                                        interaction.user.id, interaction.guild.id
                                    )

                                    # Send the approval request
                                    await channel.send(embed=embed, view=approval_view)

                                    logger.info(
                                        f"Sent approval request for {interaction.user.name} to channel {channel.name}"
                                    )
                                else:
                                    logger.warning(
                                        f"Approval channel {approval_channel.channel_id} not found"
                                    )
                            except Exception as e:
                                logger.error(
                                    f"Error sending approval request: {e}",
                                    exc_info=True,
                                )

                    # Notify user that their request is pending
                    await interaction.response.send_message(
                        f"✅ Thanks for submitting your onboarding request, {nickname}!\n"
                        "Your request is pending approval. You'll be notified once it's reviewed.",
                        ephemeral=True,
                    )

                    logger.info(
                        f"User {interaction.user.name} submitted onboarding request (pending approval)"
                    )

                else:
                    # Auto approval mode - process immediately
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
        # Load config from the guild that the interaction is from
        try:
            with next(get_session()) as session:
                guild = session.exec(
                    select(Guild).where(Guild.guild_id == interaction.guild.id)
                ).first()

                if guild and guild.settings:
                    help_config = guild.settings.get(
                        "help_button_config",
                        {
                            "enabled": True,
                            "button_text": "Need Help?",
                            "message_content": "We're here to assist you! If you need help with onboarding or have any questions, please contact a moderator or admin.",
                        },
                    )
                else:
                    help_config = {
                        "enabled": True,
                        "button_text": "Need Help?",
                        "message_content": "We're here to assist you! If you need help with onboarding or have any questions, please contact a moderator or admin.",
                    }
        except Exception as e:
            logger.error(f"Error loading help button config in callback: {e}")
            help_config = {
                "enabled": True,
                "button_text": "Need Help?",
                "message_content": "We're here to assist you! If you need help with onboarding or have any questions, please contact a moderator or admin.",
            }

        message_content = help_config.get(
            "message_content",
            "We're here to assist you! If you need help with onboarding or have any questions, please contact a moderator or admin.",
        )

        await interaction.response.send_message(message_content, ephemeral=True)


class OnboardingApprovalView(discord.ui.View):
    """View with approve/deny buttons for onboarding requests"""

    def __init__(self, user_id: int = None, guild_id: int = None):
        super().__init__(timeout=None)  # Persistent view
        self.user_id = user_id
        self.guild_id = guild_id

    def _parse_custom_id(self, custom_id: str) -> tuple[int, int]:
        """Parse user_id and guild_id from custom_id format: vela:approve_onboarding:user_id:guild_id"""
        parts = custom_id.split(":")
        if len(parts) >= 4:
            return int(parts[2]), int(parts[3])
        return self.user_id, self.guild_id

    async def check_approver_permission(self, interaction: Interaction) -> bool:
        """Check if the user has permission to approve/deny requests"""
        with next(get_session()) as session:
            # Get all approver roles for this guild
            approver_roles = session.exec(
                select(Role).where(
                    Role.guild_id == self.guild_id,
                    Role.role_type == "onboarding_approver",
                )
            ).all()

            logger.info(
                f"Checking approval permission for {interaction.user.name} in guild {self.guild_id}"
            )
            logger.info(f"Found {len(approver_roles)} approver roles in database")

            if not approver_roles:
                logger.warning(
                    f"No approver roles configured for guild {self.guild_id}"
                )
                return False

            # Check if user has any of the approver roles
            approver_role_ids = [role.role_id for role in approver_roles]
            user_role_ids = [role.id for role in interaction.user.roles]

            logger.info(f"Approver role IDs from DB: {approver_role_ids}")
            logger.info(f"User's role IDs from Discord: {user_role_ids}")
            logger.info(
                f"User's role names: {[role.name for role in interaction.user.roles]}"
            )

            has_permission = any(
                role_id in user_role_ids for role_id in approver_role_ids
            )
            logger.info(f"Permission check result: {has_permission}")

            return has_permission

    @discord.ui.button(
        label="Approve",
        style=discord.ButtonStyle.success,
        custom_id="vela:approve_onboarding",
        emoji="✅",
    )
    async def approve_button(self, interaction: Interaction, button: discord.ui.Button):
        """Handle approve button click"""
        # Extract user_id and guild_id from the message embed
        if not self.user_id or not self.guild_id:
            # Parse from embed
            if interaction.message.embeds:
                embed = interaction.message.embeds[0]
                # Extract user_id from the "User ID" field
                for field in embed.fields:
                    if field.name == "User ID":
                        self.user_id = int(field.value)
                        break
                # Guild ID is from the interaction
                self.guild_id = interaction.guild.id

        if not self.user_id or not self.guild_id:
            await interaction.response.send_message(
                "❌ Could not determine user information from this request.",
                ephemeral=True,
            )
            return

        # Check permission
        if not await self.check_approver_permission(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to approve onboarding requests.",
                ephemeral=True,
            )
            return

        try:
            # Extract values we need from database before session closes
            member_nickname = None
            guild_settings = {}
            onboarded_role_id = None

            with next(get_session()) as session:
                # Get the member
                db_member = session.exec(
                    select(Member).where(
                        Member.user_id == self.user_id,
                        Member.guild_id == self.guild_id,
                    )
                ).first()

                if not db_member:
                    await interaction.response.send_message(
                        "❌ Member not found in database.", ephemeral=True
                    )
                    return

                # Extract nickname before session closes
                member_nickname = db_member.nickname

                # Update member status
                db_member.onboarding_status = 1
                db_member.onboarding_completed_at = datetime.utcnow()

                # Get guild settings
                guild = session.exec(
                    select(Guild).where(Guild.guild_id == self.guild_id)
                ).first()
                guild_settings = guild.settings if guild and guild.settings else {}

                # Get onboarded role
                onboarded_role = session.exec(
                    select(Role).where(
                        Role.guild_id == self.guild_id,
                        Role.role_type == "onboarded",
                    )
                ).first()

                # Extract role_id before session closes
                if onboarded_role:
                    onboarded_role_id = onboarded_role.role_id

                # Log the approval
                audit_log = AuditLog(
                    guild_id=self.guild_id,
                    user_id=interaction.user.id,
                    discord_username=interaction.user.name,
                    action="onboarding_approved",
                    details={
                        "approved_user_id": self.user_id,
                        "approved_by": interaction.user.name,
                    },
                )
                session.add(audit_log)
                session.commit()

            # Get the Discord member
            guild = interaction.guild
            member = guild.get_member(self.user_id)

            if member:
                # Update nickname if enabled
                if guild_settings.get("set_nickname", True) and member_nickname:
                    try:
                        await member.edit(nick=member_nickname)
                        logger.info(
                            f"✓ Updated nickname for {member.name} to {member_nickname}"
                        )
                    except discord.Forbidden:
                        logger.warning(
                            f"Missing permission to change nickname for {member.name}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Could not update nickname for {member.name}: {e}"
                        )

                # Add role if configured and enabled
                if guild_settings.get("auto_role", True) and onboarded_role_id:
                    try:
                        role = guild.get_role(onboarded_role_id)
                        if role:
                            await member.add_roles(role)
                            logger.info(f"✓ Added role {role.name} to {member.name}")
                    except Exception as e:
                        logger.error(f"Could not add role to {member.name}: {e}")

                # Send DM to the user notifying them of approval
                try:
                    await member.send(
                        f"✅ Your onboarding request has been approved! Welcome to {guild.name}!"
                    )
                except (discord.Forbidden, discord.HTTPException):
                    logger.info(
                        f"Could not send DM to {member.name} (DMs might be disabled)"
                    )

            # Update the embed to show it's been approved
            original_embed = interaction.message.embeds[0]
            original_embed.color = discord.Color.green()
            original_embed.title = "✅ Onboarding Request Approved"
            original_embed.add_field(
                name="Approved By",
                value=interaction.user.mention,
                inline=False,
            )
            original_embed.timestamp = datetime.utcnow()

            # Disable the buttons
            for item in self.children:
                item.disabled = True

            await interaction.response.edit_message(embed=original_embed, view=self)

            logger.info(
                f"Onboarding request for user {self.user_id} approved by {interaction.user.name}"
            )

        except Exception as e:
            logger.error(f"Error approving onboarding request: {e}", exc_info=True)
            await interaction.response.send_message(
                f"❌ Error approving request: {str(e)}", ephemeral=True
            )

    @discord.ui.button(
        label="Deny",
        style=discord.ButtonStyle.danger,
        custom_id="vela:deny_onboarding",
        emoji="❌",
    )
    async def deny_button(self, interaction: Interaction, button: discord.ui.Button):
        """Handle deny button click"""
        # Extract user_id and guild_id from the message embed
        if not self.user_id or not self.guild_id:
            # Parse from embed
            if interaction.message.embeds:
                embed = interaction.message.embeds[0]
                # Extract user_id from the "User ID" field
                for field in embed.fields:
                    if field.name == "User ID":
                        self.user_id = int(field.value)
                        break
                # Guild ID is from the interaction
                self.guild_id = interaction.guild.id

        if not self.user_id or not self.guild_id:
            await interaction.response.send_message(
                "❌ Could not determine user information from this request.",
                ephemeral=True,
            )
            return

        # Check permission
        if not await self.check_approver_permission(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to deny onboarding requests.",
                ephemeral=True,
            )
            return

        try:
            with next(get_session()) as session:
                # Get the member
                db_member = session.exec(
                    select(Member).where(
                        Member.user_id == self.user_id,
                        Member.guild_id == self.guild_id,
                    )
                ).first()

                if not db_member:
                    await interaction.response.send_message(
                        "❌ Member not found in database.", ephemeral=True
                    )
                    return

                # Update member status to denied (-1)
                db_member.onboarding_status = -1

                # Log the denial
                audit_log = AuditLog(
                    guild_id=self.guild_id,
                    user_id=interaction.user.id,
                    discord_username=interaction.user.name,
                    action="onboarding_denied",
                    details={
                        "denied_user_id": self.user_id,
                        "denied_by": interaction.user.name,
                    },
                )
                session.add(audit_log)
                session.commit()

            # Get the Discord member and send DM
            guild = interaction.guild
            member = guild.get_member(self.user_id)

            if member:
                try:
                    await member.send(
                        f"❌ Your onboarding request for {guild.name} has been denied. "
                        "Please contact a moderator for more information."
                    )
                except (discord.Forbidden, discord.HTTPException):
                    logger.info(
                        f"Could not send DM to {member.name} (DMs might be disabled)"
                    )

            # Update the embed to show it's been denied
            original_embed = interaction.message.embeds[0]
            original_embed.color = discord.Color.red()
            original_embed.title = "❌ Onboarding Request Denied"
            original_embed.add_field(
                name="Denied By",
                value=interaction.user.mention,
                inline=False,
            )
            original_embed.timestamp = datetime.utcnow()

            # Disable the buttons
            for item in self.children:
                item.disabled = True

            await interaction.response.edit_message(embed=original_embed, view=self)

            logger.info(
                f"Onboarding request for user {self.user_id} denied by {interaction.user.name}"
            )

        except Exception as e:
            logger.error(f"Error denying onboarding request: {e}", exc_info=True)
            await interaction.response.send_message(
                f"❌ Error denying request: {str(e)}", ephemeral=True
            )
