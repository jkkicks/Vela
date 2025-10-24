# Discord Setup Guide

Complete guide for setting up Discord bot and OAuth application.

## Table of Contents
- [Creating a Discord Application](#creating-a-discord-application)
- [Bot Configuration](#bot-configuration)
- [OAuth2 Setup](#oauth2-setup)
- [Permissions](#permissions)
- [Inviting Bot to Server](#inviting-bot-to-server)

## Creating a Discord Application

### Step 1: Access Developer Portal
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Enter a name (e.g., "SparkBot")
4. Click "Create"

### Step 2: Save Application ID
1. In the "General Information" tab
2. Copy the "Application ID" (this is your CLIENT_ID)
3. Save it for later use

## Bot Configuration

### Step 1: Create Bot
1. Navigate to the "Bot" section in left sidebar
2. Click "Add Bot"
3. Confirm by clicking "Yes, do it!"

### Step 2: Configure Bot Settings
1. **Username**: Set your bot's username
2. **Icon**: Upload a bot avatar (optional)
3. **Public Bot**: Uncheck if you want only you to invite the bot
4. **Require OAuth2 Code Grant**: Leave unchecked

### Step 3: Get Bot Token
1. Under "Token", click "Reset Token"
2. Click "Yes, do it!"
3. Copy the token immediately (you won't see it again!)
4. **Never share this token publicly**

Add to your `.env` file:
```env
BOT_TOKEN=your_bot_token_here
```

### Step 4: Configure Intents
Enable these Privileged Gateway Intents:
- ✅ Server Members Intent
- ✅ Message Content Intent
- ✅ Presence Intent (optional)

## OAuth2 Setup

### Step 1: Configure OAuth2
1. Navigate to "OAuth2" → "General" in sidebar
2. Add Redirect URLs:
   - Development: `http://localhost:8000/auth/callback`
   - Production: `https://yourdomain.com/auth/callback`

### Step 2: Get OAuth Credentials
1. Copy "Client ID" (if you haven't already)
2. Reset and copy "Client Secret"

Add to your `.env` file:
```env
DISCORD_CLIENT_ID=your_client_id_here
DISCORD_CLIENT_SECRET=your_client_secret_here
DISCORD_REDIRECT_URI=http://localhost:8000/auth/callback
```

## Permissions

### Bot Permissions Required
The bot needs these permissions to function:

**Essential Permissions:**
- ✅ View Channels
- ✅ Send Messages
- ✅ Send Messages in Threads
- ✅ Embed Links
- ✅ Read Message History
- ✅ Use Slash Commands
- ✅ Manage Nicknames
- ✅ Manage Roles

**Optional Permissions:**
- Add Reactions
- Attach Files
- Use External Emojis
- Connect (for voice features)

### Calculating Permission Integer
1. Go to "OAuth2" → "URL Generator"
2. Select "bot" and "applications.commands" scopes
3. Select required permissions
4. The permission integer will be shown in the URL

Example: `permissions=414600398912`

## Inviting Bot to Server

### Method 1: OAuth2 URL Generator
1. Go to "OAuth2" → "URL Generator"
2. Select Scopes:
   - ✅ bot
   - ✅ applications.commands
3. Select Bot Permissions (as listed above)
4. Copy the generated URL
5. Open URL in browser
6. Select your server
7. Click "Authorize"

### Method 2: Manual URL
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=414600398912&scope=bot%20applications.commands
```

Replace `YOUR_CLIENT_ID` with your application ID.

### Method 3: From SparkBot Web Interface
Once SparkBot is running:
1. Go to http://localhost:8000/admin/config
2. Click "Generate Bot Invite Link"
3. Use the generated link

## Server Configuration

### Required Roles
Create these roles in your Discord server:

1. **Onboarded Role** (given after onboarding)
   - Name: "Member" or "Onboarded"
   - Permissions: Access to member channels
   - Position: Above @everyone

2. **Bot Admin Role** (for bot administrators)
   - Name: "Bot Admin"
   - Permissions: Administrator or Manage Server
   - Position: High in hierarchy

### Channel Setup
1. **Welcome Channel**
   - Where the onboarding message appears
   - Visible to @everyone
   - Bot needs Send Messages permission

2. **Member Channels**
   - Visible only to onboarded role
   - Regular server channels

### Getting IDs
To get Discord IDs, enable Developer Mode:
1. Discord Settings → Advanced → Developer Mode: ON
2. Right-click on server/channel/role → Copy ID

## First Run Configuration

When you first run SparkBot:

1. **Via Web Interface** (http://localhost:8000/setup):
   ```
   Guild ID: [Your Server ID]
   Guild Name: [Your Server Name]
   Bot Token: [Your Bot Token]
   Discord Admin ID: [Your User ID]
   Welcome Channel ID: [Optional]
   Onboarded Role ID: [Optional]
   ```

2. **Via Environment Variables**:
   ```env
   BOT_TOKEN=your_bot_token
   GUILD_ID=your_guild_id
   DISCORD_CLIENT_ID=your_client_id
   DISCORD_CLIENT_SECRET=your_client_secret
   ```

## Troubleshooting

### Bot Not Coming Online
- Verify bot token is correct
- Check bot is in the server
- Ensure intents are enabled
- Check console for errors

### OAuth Login Not Working
- Verify redirect URI matches exactly
- Check client ID and secret
- Ensure user is in the same server as bot

### Commands Not Showing
- Wait 1 hour for global commands to sync
- Or use guild-specific commands for instant update
- Try `/sync` command (admin only)

### Permission Issues
- Ensure bot role is high enough in hierarchy
- Check channel-specific permissions
- Verify required intents are enabled

## Security Best Practices

1. **Never commit tokens to git**
   - Use `.env` file
   - Add `.env` to `.gitignore`

2. **Regenerate tokens if exposed**
   - Bot token
   - Client secret
   - API keys

3. **Use environment-specific configs**
   - Different tokens for dev/prod
   - Separate OAuth applications

4. **Limit bot permissions**
   - Only grant necessary permissions
   - Use role hierarchy properly

## Next Steps

- [Complete First Run Setup](first-run.md)
- [Configure Web Interface](configuration.md)
- [Test Bot Commands](../api/bot-commands.md)
- [Set Up Production Deployment](../deployment/production.md)