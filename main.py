import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
from dotenv import load_dotenv
import sqlite3
import logging
from datetime import datetime, timezone
from discord import ui, Interaction
import random
import sys

async def welcome_message():
    # Find the #welcome channel
    welcome_channel_id = os.getenv('WELCOME_CHANNEL_ID')
    if not welcome_channel_id:
        raise ValueError("WELCOME_CHANNEL_ID environment variable is not set")
    welcome_channel_id = int(welcome_channel_id)
    welcome_channel = discord.utils.get(client.get_all_channels(), id=welcome_channel_id)

    # Check if welcome message has already been sent in the channel
    async for message in welcome_channel.history(limit=100):
        if message.author == client.user and message.embeds:
            print(f'Welcome message found. Message ID: {message.id}')
            return  # If the welcome message is found, exit the function

    # Send welcome message in the #welcome channel
    print(f'No welcome message found, creating one now')
    view = discord.ui.View()
    button = discord.ui.Button(label="Complete Onboarding")
    view.add_item(button)
    embed = discord.Embed(title="Welcome to the Server!", description="Here's how to get started:")
    # embed.set_thumbnail(url=ctx.guild.icon)
    embed.add_field(name="Step 1:",
                    value="Read the server rules in [#rules](https://discord.com/channels/1207801896656568480/1207802982574596137) channel.")
    embed.add_field(name="Step 2:",
                    value="Check out some cool posts over in [#projects](https://discord.com/channels/1207801896656568480/1207807674075320390).")
    embed.add_field(name="Step 3:", value="Complete Onboarding procedure to unlock the rest of the server.")
    embed.set_footer(text="Enjoy your stay!")
    await welcome_channel.send(embed=embed, view=OnboardButtons())

async def update_nickname(member, firstname, lastname):     #update server nickname from DB
    nickname = f"{firstname} {lastname}"
    with sqlite3.connect('member_data.db') as conn:
        c = conn.cursor()
        c.execute("UPDATE members SET nickname = ?, firstname = ?, lastname = ? WHERE user_id = ?", (nickname, firstname, lastname, member.id))
        conn.commit()
        print(f'Updated DB nickname for: {member}, {firstname}, {lastname}, {nickname}')
    await member.edit(nick=nickname)

async def remove_user(user):        #Remove user from DB and delete server nickname
    with sqlite3.connect('member_data.db') as conn:
        c = conn.cursor()
        c.execute("DELETE FROM members WHERE user_id = ?", (user.id,))
        conn.commit()
    if user:
        await user.edit(nick=None)
        role = discord.utils.get(user.guild.roles, name="Maker")    #Remove role "Maker" from user
        await user.remove_roles(role)

async def update_onboard(member):           #increase onboarding status by 1
    logging.info(f'Updating onboarding for: {member.display_name} {member.id}')

    # Connect to the database using a context manager
    with sqlite3.connect('member_data.db') as conn:
        c = conn.cursor()

        c.execute("SELECT onboarding_status FROM members WHERE user_id = ?", (member.id,))
        row = c.fetchone()

        if row is None:
            logging.error("No matching user found in the database.")
            return

        status = row[0]
        status += 1

        c.execute("UPDATE members SET onboarding_status = ? WHERE user_id = ?",
            (status, member.id))

        conn.commit()
        logging.warning(f'Updated onboarding for {member.display_name}: {status}')

async def add_member_to_role(member, role_name):
    print(f"Adding {role_name} role to {member.display_name}")
    role = discord.utils.get(member.guild.roles, name=role_name)        # Get role from guild
    if role:
        await member.add_roles(role)
        print(f"Added role '{role_name}' to member '{member.display_name}'")
    else:
        print(f"Role '{role_name}' not found in server '{member.guild.name}'")

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(filename='SparkBot.log', level=logging.INFO)

# Define intents
intents = discord.Intents.all()

# Connect to SQLite database
with sqlite3.connect('member_data.db') as conn:
    c = conn.cursor()

    # Create table with fields if it doesn't exist already
    c.execute('''CREATE TABLE IF NOT EXISTS members (
                user_id INTEGER PRIMARY KEY, 
                username TEXT, nickname TEXT, 
                firstname TEXT, lastname TEXT,
                join_datetime TEXT, 
                onboarding_status INTEGER, 
                last_change_datetime TEXT
            )''')

    conn.commit()


class PersistentViewBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents().all()
        super().__init__(command_prefix=commands.when_mentioned_or("/"), intents=intents)
    async def setup_hook(self) -> None:
        self.add_view(OnboardButtons())
        #self.add_view(OnboardButtons())            #Add More views with more add_view commands.

client = PersistentViewBot()

class OnboardModal(discord.ui.Modal, title="Onboarding: "):
    first_name = discord.ui.TextInput(
        style=discord.TextStyle.short,
        label="First name",
        required=True,
        placeholder="John "
    )
    last_name = discord.ui.TextInput(
        style=discord.TextStyle.short,
        label="Last Name",
        required=True,
        placeholder="Doe"
    )
    async def on_submit(self, interaction: discord.InteractionResponse):
        await interaction.response.send_message("Thanks for completing Onboarding! If you have any questions, don't hesitate to reach out!", ephemeral=True)
        #await interaction.response.defer()
        await update_nickname(member=self.user, firstname=self.first_name.value, lastname=self.last_name.value)
        await update_onboard(member=self.user)
        role_to_add = "Maker"
        await add_member_to_role(member=self.user, role_name=role_to_add)
        # print(f'First name: {self.first_name.value}')
        # print(f'Last Name: {self.last_name.value}')
        # print(f'User: {self.user.id}')
        
    async def on_error(self, interaction: discord.Interaction, error):
        ...

class OnboardButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
                                        #Button that sends modal (Popup)
    @discord.ui.button(label="Complete Onboarding", style=discord.ButtonStyle.green, custom_id="1")
    async def onboard(self, interaction: discord.InteractionResponse, button: discord.ui.Button):
        onboard_modal = OnboardModal()
        onboard_modal.user = interaction.user

        if interaction.user.nick:
            await interaction.response.send_message(content="You have already been onboarded! To change your onboarding status, please reach out to the Moderators", ephemeral=True)
        else:
            await interaction.response.send_modal(onboard_modal)


                                        #Button that sends ephemeral embed describing the onboarding process
    @discord.ui.button(label="What is Onboarding?", style=discord.ButtonStyle.blurple, custom_id="2")
    async def aboutonboard(self, interaction: discord.InteractionResponse, button: discord.ui.Button):
        embed = discord.Embed(title="What is onboarding?",
                              description="Welcome to our Discord server! We're thrilled to have you join our community. To unlock the full experience and access more parts of the server, we ask that you complete the member onboarding process. This involves providing some personal data, which helps us tailor your experience and ensure a safe and engaging environment for everyone.")
        embed.add_field(name="Why Complete Onboarding?",
                        value="Completing the onboarding process not only grants you access to additional server features but also allows you to actively participate in discussions, events, and activities. While it's optional, incomplete onboarding results in limited access to the server, with read-only privileges.",
                        inline=False)
        embed.add_field(name="What Information is Collected?",
                        value="When you complete onboarding, the following information is stored securely in our database: ",
                        inline=False)
        embed.add_field(name=" ",
                        value="-Discord ID: Your unique identifier on Discord. ",
                        inline=False)
        embed.add_field(name=" ",
                        value="-Nickname: The name you choose to display in the server.",
                        inline=False)
        embed.add_field(name=" ",
                        value="-Server Join Date: The date you joined our community",
                        inline=False)
        embed.add_field(name=" ",
                        value="-Server Access Level: Information about your permissions within the server.",
                        inline=False)
        embed.add_field(name="Agreement to Server Rules",
                        value="By completing the onboarding process, you agree to abide by the rules and guidelines set forth in our Discord server. These rules are in place to ensure a respectful and inclusive environment for all members.",
                        inline=False)
        embed.add_field(name="Privacy and Data Usage",
                        value="We take your privacy seriously. Any data provided during the onboarding process is handled in accordance with our privacy policy. By completing onboarding, you consent to: ",
                        inline=False)
        embed.add_field(name=" ",
                        value="-Public Visibility: Your posts and comments may be made publicly visible not only within the Discord server but also on our website, social media platforms, blog, and other related channels. ",
                        inline=False)
        embed.add_field(name=" ",
                        value="-Data Storage: Your inputted information will be stored securely by our server for administrative and community management purposes.",
                        inline=False)

        embed.add_field(name="Get Started",
                        value='Ready to complete the onboarding process? Simply click the "Complete Onboarding" Button in the #welcome channel. If you have any questions or concerns about the process, feel free to reach out to our moderation team for assistance. '
                              "Thank you for joining our community and for taking the time to complete the onboarding process. We look forward to getting to know you better and engaging with you in meaningful discussions and activities!",
                        inline=False)
        await interaction.response.send_message(embed=embed ,ephemeral=True)


@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    await welcome_message()
    try:            #sync slash commands
        synced = await client.tree.sync()
        print(f'Slash Commands Synced. {str(len(synced))} Total Commands {synced}')
    except Exception as e:
        print(e)

    print("Members in the DB:")

    with sqlite3.connect('member_data.db') as conn:
        c = conn.cursor()

        c.execute("SELECT user_id, username, nickname FROM members")
        for row in c.fetchall():
            print(f'  ID: {row[0]} User: {row[1]} Nick: {row[2]}')

    # Display web dashboard info
    api_port = os.getenv('API_PORT', '8000')
    print("\n" + "="*50)
    print("Bot is ready!")
    print(f"Web Dashboard: http://localhost:{api_port}")
    print("="*50 + "\n")

@client.command(name='reinit')
async def cmd_reinit(ctx):
    """Re-initialize a user in the database (i.e. if the bot wasn't listening when they joined)"""
    await on_member_join(ctx.author)
    await ctx.send("Reinitialized!")

@client.command(name='nick')
async def cmd_nick(ctx):
    """View current nickname"""
    await ctx.send(f'You are {ctx.author.nick}')

@client.command(name='setnick')
async def cmd_setnick(ctx, arg1, arg2):
    """Change nickname (use two words separated by a space)"""
    await update_nickname(ctx.author, arg1, arg2)
    await ctx.send(f'You are now {ctx.author.nick}')

@client.command(name='99')
async def cmd_nine_nine(ctx):
    brooklyn_99_quotes = [
        'I\'m the human form of the 💯 emoji.',
        'Bingpot!',
        (
            'Cool. Cool cool cool cool cool cool cool, '
            'no doubt no doubt no doubt no doubt.'
        ),
    ]

    response = random.choice(brooklyn_99_quotes)
    await ctx.send(response)

@client.command(name='shutdown')
async def cmd_shutdown(ctx):
    """Shutdown the bot"""
    await ctx.send("Shutting down!")
    sys.exit()

# @client.event
# async def on_message(message):
#     if message.author == client.user:
#         return

#     brooklyn_99_quotes = [
#         'I\'m the human form of the 💯 emoji.',
#         'Bingpot!',
#         (
#             'Cool. Cool cool cool cool cool cool cool, '
#             'no doubt no doubt no doubt no doubt.'
#         ),
#     ]

#     if message.content == '/99':
#         response = random.choice(brooklyn_99_quotes)
#         await message.channel.send(response)

@client.event
async def on_member_join(member):
    await welcome_message()

    with sqlite3.connect('member_data.db') as conn:
        c = conn.cursor()

        # Check if member already exists in the database
        c.execute("SELECT * FROM members WHERE user_id = ?", (member.id,))

        existing_member = c.fetchone()

        if not existing_member:  # If it's the member's first time joining
            # Add new member to the database
            c.execute(
                "INSERT OR REPLACE INTO members (user_id, username, join_datetime, onboarding_status, last_change_datetime) VALUES (?, ?, ?, ?, ?)",
                (member.id, member.name, member.joined_at.isoformat(), 0, datetime.now(timezone.utc).isoformat()))
            conn.commit()

            # Update member nickname
            await member.edit(nick=c.execute("SELECT nickname FROM members WHERE user_id = ?", (member.id,)).fetchone()[0])

            # Log member join
            logging.warning(f'Member {member.name} joined the server.')
        else:
            logging.info(f'Member {member.name} rejoined the server.')

@client.tree.command(name="remove", description="Remove user from database, and remove user's nickname")
@app_commands.describe(member="The member you want to remove")
async def remove(interaction: discord.Integration, member: discord.Member):
    await remove_user(member)
    await interaction.response.send_message(f"User {member.display_name} Removed", ephemeral=True)

@client.event
async def on_member_remove(member):
    # Log member leave
    logging.warning(f'Member {member.name} left the server.')


# Load bot token and welcome channel id from .env file
TOKEN = os.getenv('BOT_TOKEN')
WELCOME_CHANNEL_ID = os.getenv('WELCOME_CHANNEL_ID')
GUILD_ID = str(os.getenv('GUILD_ID'))

# Start bot
client.run(TOKEN)
