# Bot Commands Reference

Complete reference for all SparkBot Discord commands.

## User Commands

### `/onboard`
Complete the onboarding process.

**Usage**: `/onboard firstname: John lastname: Doe`

**Parameters**:
- `firstname` (required): Your first name
- `lastname` (required): Your last name

**Example**:
```
/onboard firstname: Jane lastname: Smith
```

---

### `/help`
Display help information about available commands.

**Usage**: `/help`

---

### `/ping`
Check bot latency and responsiveness.

**Usage**: `/ping`

**Response**: Shows round-trip latency in milliseconds.

---

### `/about`
Display information about SparkBot.

**Usage**: `/about`

---

### `/server_info`
Get information about the current Discord server.

**Usage**: `/server_info`

**Shows**:
- Server name and ID
- Member count
- Channel count
- Role count
- Creation date

## Admin Commands

> **Note**: These commands require administrator permissions or Bot Admin role.

### `/remove`
Remove a user from the onboarding database and reset their nickname.

**Usage**: `/remove user: @username`

**Parameters**:
- `user` (required): The Discord user to remove

**Example**:
```
/remove user: @JohnDoe
```

---

### `/stats`
View server onboarding statistics.

**Usage**: `/stats`

**Shows**:
- Total members in database
- Onboarded members
- Pending members
- Completion rate

---

### `/list_members`
List all members in the onboarding database.

**Usage**: `/list_members`

**Note**: Shows first 20 members. For full list, use web interface.

---

### `/sync`
Manually sync slash commands with Discord.

**Usage**: `/sync`

**Note**: Use if commands aren't appearing or updating.

## Legacy Commands

These commands use the traditional prefix (default: `!`).

### `!nick`
View your current server nickname.

**Usage**: `!nick`

---

### `!setnick`
Change your nickname manually.

**Usage**: `!setnick [firstname] [lastname]`

**Example**:
```
!setnick John Doe
```

---

### `!reinit`
Re-initialize yourself in the database.

**Usage**: `!reinit`

**Note**: Use if you joined when bot was offline.

---

### `!99`
Get a random Brooklyn Nine-Nine quote.

**Usage**: `!99`

---

### `!shutdown`
Shutdown the bot (owner only).

**Usage**: `!shutdown`

**Required**: Bot owner permissions

## Button Interactions

### Welcome Message Buttons

The bot posts a welcome message with interactive buttons:

#### "Complete Onboarding" Button
- **Color**: Green
- **Action**: Opens onboarding modal
- **Requirements**: User not already onboarded

#### "What is Onboarding?" Button
- **Color**: Blue
- **Action**: Shows information about onboarding
- **Privacy**: Ephemeral (only you see it)

#### "Need Help?" Button
- **Color**: Gray
- **Action**: Shows help and support information
- **Privacy**: Ephemeral (only you see it)

## Modal Forms

### Onboarding Modal
Appears when clicking "Complete Onboarding".

**Fields**:
- First Name (required, max 50 characters)
- Last Name (required, max 50 characters)

**On Submit**:
1. Sets your nickname to "FirstName LastName"
2. Adds onboarded role (if configured)
3. Grants access to member channels
4. Logs completion in audit trail

## Permissions

### Command Visibility
- User commands: Visible to everyone
- Admin commands: Visible only to administrators

### Required Bot Permissions
- Send Messages
- Embed Links
- Use Slash Commands
- Manage Nicknames
- Manage Roles
- Read Message History

### Role Hierarchy
1. **Bot Owner**: Full control, can shutdown
2. **Server Admin**: All admin commands
3. **Bot Admin**: User management commands
4. **Onboarded Member**: User commands
5. **Everyone**: Can see welcome, use onboarding

## Error Messages

### Common Errors and Solutions

#### "You have already been onboarded!"
- **Cause**: Trying to onboard twice
- **Solution**: Use `/setnick` to change name

#### "You don't have permission to use this command"
- **Cause**: Insufficient permissions
- **Solution**: Contact server admin

#### "User not found in database"
- **Cause**: User never onboarded
- **Solution**: User needs to complete onboarding first

#### "Failed to update nickname"
- **Cause**: Bot lacks permissions or role hierarchy issue
- **Solution**: Check bot role position and permissions

## Command Cooldowns

To prevent spam, some commands have cooldowns:

- `/stats`: 10 seconds
- `/list_members`: 30 seconds
- `/sync`: 60 seconds

## Tips and Tricks

### For Users
1. Complete onboarding to access all channels
2. Use `/help` if confused
3. Contact admins for nickname changes after onboarding

### For Admins
1. Use web interface for bulk operations
2. Check audit logs for user actions
3. Configure roles before inviting users
4. Test commands in a private channel first

### For Developers
1. Commands are in `src/bot/cogs/`
2. Add new commands by creating cogs
3. Use `@app_commands.command()` for slash commands
4. Test in development server first

## Upcoming Features

- [ ] Bulk onboarding via CSV
- [ ] Custom onboarding questions
- [ ] Scheduled reminders for incomplete onboarding
- [ ] Role-based onboarding paths
- [ ] Integration with external verification

## Related Documentation

- [Web API Reference](web-api.md)
- [Database Schema](database-schema.md)
- [Configuration Guide](../guides/configuration.md)
- [Admin Panel Guide](../guides/admin-panel.md)