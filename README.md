# Discord Bot 🤖

A complete Discord bot with music system, levels/XP, word games, reminders, polls, auto-moderation, and moderation tools.

## Features ✨

### 🎵 Music
- YouTube playback
- Queue system
- Controls: play, skip, pause, resume, stop
- Playlist support (maximum 100 tracks)
- Case opening with rewards when playing music

### 📊 Level System
- Progression from 1 to 500 levels
- XP gain per message
- Leaderboard (top 10)
- Automatic case opening on level up
- Various rewards (XP, bonuses, etc.)

### 🌤️ Weather & Time
- Current weather for any city worldwide
- Local time for any city
- 7-day weather forecast with detailed information
- Temperature, precipitation, and wind speed data

### 💬 Auto-Responses
- Automatic detection of Portuguese slang (from Portugal)
- Gaming terminology responses
- Multiple random responses per keyword
- Accent-insensitive detection (works with "bué" or "bue")
- Easy to customize via JSON file

### 🎮 Games
- **Termo**: Portuguese Wordle with statistics and rankings
- **Quick Games**: Rock-paper-scissors, dice, coin flip, 8-ball, number guessing
- **Code Challenges**: Programming challenges to practice coding

### ⏰ Reminders
- Set a reminder with a natural duration (`10m`, `2h`, `1d2h30m`)
- Delivered by DM, falling back to the channel if DMs are closed
- List and cancel your own pending reminders
- Persists across restarts (`data/reminders.json`)

### 📊 Polls
- Quick yes/no polls or up to 10 custom options, voted on via reactions
- Auto-close after a configurable time (24h by default, `--tempo` flag to customize)
- Manual close available to the poll's author or an admin
- Results posted automatically when a poll closes

### 🛡️ Auto-Moderation
- **Anti-spam**: rapid message bursts are deleted and the sender is timed out
- **Anti-links**: messages containing non-whitelisted links are deleted automatically
- Per-server on/off switches for the whole system or each check individually
- Domain whitelist, fully configurable
- Own permission system independent of Discord roles: grant/revoke an "automod moderator" status that exempts a user from checks and lets them view current settings
- All settings persisted per server (`data/automod.json`)

### 🔨 Moderation
- Warn system with persistent per-user history (`data/warnings.json`)
- Kick and ban (respecting real Discord permissions), with automatic DM to the affected user
- Unban by user ID
- Optional mod-log channel: every warn/kick/ban/unban is automatically logged there

### 🎫 Tickets
- Create private tickets with the staff
- Manage and resolve tickets efficiently
- Log all ticket interactions

### 🔧 Others
- Ping/pong
- User information
- Server information
- Context-aware help (shows different commands to admins)

## Installation 🚀

### Prerequisites
- Python 3.8+
- FFmpeg
- Node.js (for yt-dlp)

### Step by step

```bash
# 1. Clone the repository
git clone git@github.com:DuarteLacerda/bot-discord.git
cd bot-discord

# 2. Create the .env file
cp .env.example .env
# Edit .env and add:
# - DISCORD_BOT_TOKEN (required)
# - AUTO_ROLE_NAME (optional)

# 3. Create the virtual environment
python3 -m venv Venv
source Venv/bin/activate  # Linux/Mac
# or
Venv\Scripts\activate  # Windows

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the bot
python main.py
```

## Configuration ⚙️

### Environment Variables (.env)
```env
# Discord Bot Token
DISCORD_BOT_TOKEN=your_discord_bot_token_here

# Ticket Configuration
TICKET_CATEGORY_NAME=your_ticket_category_name_here
TICKET_STAFF_ROLE_NAME=your_staff_role_name_here
TICKET_LOG_CHANNEL_NAME=your_log_channel_name_here

```

When inviting the application, include the `bot` and `applications.commands` scopes. Slash commands are synchronized globally at startup and can take a while to appear in Discord.

### XP Balancing
Edit the top of `cogs/levels.py`:
```python
XP_POR_CARACTERE = 0.5      # XP per character
NIVEL_MAXIMO = 500           # Maximum level
XP_MULTIPLICADOR = 1.15      # Exponential growth
```

### Edit Rules
Edit `data/rules.json` to add/remove server rules. No need to restart the bot!

The file uses this structure:
```json
{
    "title": "📜 Regras do Servidor",
    "color": "0xFF5733",
    "rules": [
        {
            "number": 1,
            "title": "Respeito",
            "description": "Respeita todos os membros."
        }
    ],
    "footer": "Última atualização: 22/01/2026"
}
```

### Auto-Responses
Edit `data/auto_responses.json` to customize slang responses:
```json
{
    "bué": [
        "Isso é bué fixe mesmo",
        "Bué mesmo, como sempre."
    ],
    "gg": [
        "GG! Boa partida, bro",
        "GG well played!"
    ]
}
```
The bot automatically responds when it detects these keywords in messages (case and accent insensitive).

Restart the bot after changing this file so the new responses are loaded.

### Termo Words
Edit `data/termo_palavras.json` to add or remove valid five-letter words from Termo. The file must contain a JSON array of words:
```json
[
    "carro",
    "porta",
    "ponte"
]
```

Use lowercase words without accents and restart the bot after changing the file.

### Code Challenges
Edit `data/code_challenges.json` to add challenges. Organize them by language and difficulty (`facil`, `medio` or `dificil`):
```json
{
    "python": {
        "facil": [
            {
                "titulo": "Soma de Dois Números",
                "descricao": "Cria uma função que soma dois números.",
                "exemplo": "soma(5, 3) → 8",
                "dica": "Usa o operador +"
            }
        ]
    }
}
```

Each challenge needs `titulo`, `descricao`, `exemplo` and `dica`. Restart the bot after changing this file.

### Auto-Moderation
Configured per server via commands (see below), not a file to edit by hand. Defaults:
- Anti-spam: 5 messages in 6 seconds triggers a 5-minute timeout
- Anti-links: any link outside the whitelist is deleted

Adjust the thresholds by editing the constants at the top of `cogs/automod.py` (`SPAM_MSG_LIMIT`, `SPAM_WINDOW_SECONDS`, `SPAM_TIMEOUT_MINUTES`).

### Data Files

| File | Purpose | Manual editing |
| --- | --- | --- |
| `data/rules.json` | Server rules shown by `/rules`. | Yes |
| `data/auto_responses.json` | Keywords and automatic responses. | Yes, then restart the bot |
| `data/termo_palavras.json` | Valid five-letter words for Termo. | Yes, then restart the bot |
| `data/code_challenges.json` | Programming challenges grouped by language and difficulty. | Yes, then restart the bot |
| `data/automod.json` | Per-server auto-moderation settings. | Yes, but prefer the `/automod_*` commands; restart afterwards |
| `data/antiraid.json` | Per-server anti-raid settings and lockdown state. | Yes, but prefer the `/antiraid_*` commands; restart afterwards |
| `data/tickets.json` | Ticket records and configuration. | Yes, with care; prefer managing tickets through Discord |
| `data/modlog.json` | Configured moderation log channels. | Yes, but `/modlog_canal` is safer; restart afterwards |
| `data/reminders.json` | Pending reminders. Created when the first reminder is saved. | Yes, with care; prefer `/lembrar` and `/lembrete_cancelar` |
| `data/warnings.json` | Warning history. Created when the first warning is saved. | Yes, with care; prefer the moderation commands |

All JSON files can be edited manually, but configuration and runtime files must keep their existing structure. Stop the bot before editing them, make a backup first and restart it afterwards. Changes made through commands are safer because they are validated and saved automatically.

## Commands 📝

Commands are available through Discord's slash-command menu. Type `/` in a channel to browse them and select the command you need.

### ⚙️ Basic
- `/ping` - Shows bot latency
- `/sum <a> <b>` - Adds two numbers

### ℹ️ Information
- `/info [@user]` - User information
- `/server` - Server information
- `/rules` - Shows server rules

### 🌤️ Weather
- `/tempo <city>` - Shows current weather for a city
- `/hora <city>` - Shows the current time for a city
- `/previsao <city>` - 7-day weather forecast

### 🎵 Music
- `/join` - Joins your voice channel
- `/play <term|link>` - Plays from YouTube or Spotify
- `/skip` - Skips the current track
- `/stop` - Stops playback and leaves
- `/pause` - Pauses playback
- `/resume` - Resumes playback
- `/queue` - Shows the queue
- `/testtone` - Tests audio with a tone
- `/music` - Shows music commands

### 📊 Levels
- `/level [@user]` - Shows level and XP
- `/rank` - Server top 10 leaderboard

### 🎮 Termo Game
- `/termo` - Starts a new Termo game (Portuguese Wordle)
- `/termo_quit` - Exits the current game
- `/termo_stats [@user]` - Shows Termo statistics
- `/termo_rank` - Shows the Termo ranking

### 🎲 Quick Games
- `/ppt <rock|paper|scissors>` - Rock, paper, scissors
- `/dado [sides]` - Rolls a dice with N sides
- `/moeda` - Flips a coin
- `/escolher <option1 | option2>` - Lets the bot choose for you
- `/adivinhar <number>` - Guess the number between 1 and 10
- `/8ball <question>` - Ask the magic 8-ball
- `/jogos` - Shows all available games

### 💻 Code Challenges
- `/code` - Starts a programming challenge
- `/stats_code` - Shows code challenge statistics

### ⏰ Reminders
- `/lembrar <tempo> <mensagem>` - Creates a reminder (e.g. `10m`, `2h`, `1d`, `1d2h30m`)
- `/lembretes` - Lists your pending reminders
- `/lembrete_cancelar <id>` - Cancels a reminder

### 📊 Polls
- `/poll <question>` - Yes/no poll (👍/👎), expires in 24h by default
- `/poll <question> | opt1 | opt2 | ...` - Multiple-choice poll (up to 10 options)
- `/poll <question> | opt1 | opt2 | --tempo 2h` - Custom expiry (5 min to 7 days)
- `/poll_fechar <message_id>` - Closes a poll early and shows results (author or admin)

### 🛡️ Auto-Moderation
- `/automod` - Shows current auto-moderation status
- `/automod_whitelist` - Lists whitelisted domains
- `/automod_perms` - Lists users with automod moderator permission
- `/automod_on` / `/automod_off` - Enables/disables the whole system *(admin)*
- `/automod_antispam <on|off>` - Toggles anti-spam only *(admin)*
- `/automod_antilinks <on|off>` - Toggles anti-links only *(admin)*
- `/automod_whitelist_add <domain>` - Allows a domain (e.g. `youtube.com`) *(admin)*
- `/automod_whitelist_remove <domain>` - Removes a domain from the whitelist *(admin)*
- `/automod_addperm @user` - Grants automod moderator permission *(admin)*
- `/automod_removeperm @user` - Revokes that permission *(admin)*

### 🔨 Moderation
- `/warn @user <reason>` - Warns a member *(admin or automod moderator)*
- `/warnings [@user]` - Shows warning history (omit = your own)
- `/warn_remove @user <id>` - Removes a specific warning *(admin)*
- `/kick @user [reason]` - Kicks a member *(requires Kick Members)*
- `/ban @user [reason]` - Bans a member *(requires Ban Members)*
- `/unban <user_id>` - Removes a ban *(requires Ban Members)*
- `/modlog_canal [#channel]` - Sets or shows the mod-log channel *(admin)*

### 🎫 Tickets
- `/ticket <reason>` - Opens a private ticket with the staff
- `/ticketpanel` - Posts the ticket opening panel

### 👑 Admin Commands
- `/write <message>` - Echoes message
- `/clear [amount]` - Deletes messages from the channel
- `/addxp @user <value>` - Adds XP to a user

## Running in Background (Linux)

### With systemd
```bash
# The service is already configured in discord-bot.service

# Start
systemctl --user start discord-bot

# Check status
systemctl --user status discord-bot

# View logs
journalctl --user -u discord-bot -f

# Auto-start on boot
systemctl --user enable discord-bot
```

### With screen
```bash
screen -S discordbot
source Venv/bin/activate
python main.py
# Press Ctrl+A then D to detach

# Reconnect
screen -r discordbot
```

## Project Structure 📂

```
discord-bot/
├── main.py                  # Bot initialization
├── cogs/
│   ├── bot_commands.py      # General commands and help
│   ├── music.py             # Music cog
│   ├── levels.py            # Levels cog
│   ├── events.py            # Event listeners and auto-responses
│   ├── termo.py             # Termo game
│   ├── code_challenges.py   # Coding challenges
│   ├── games.py             # Games
│   ├── reminders.py         # Reminders
│   ├── polls.py             # Polls
│   ├── automod.py           # Anti-spam / anti-links + permission system
│   └── moderation.py        # Warns, kick, ban, mod-log
├── data/
│   ├── antiraid.json         # Per-server anti-raid settings
│   ├── auto_responses.json  # Slang auto-responses
│   ├── automod.json          # Per-server auto-mod settings
│   ├── code_challenges.json  # Challenge data
│   ├── modlog.json           # Moderation log channels
│   ├── reminders.json        # Created at runtime for pending reminders
│   ├── rules.json           # Server rules
│   ├── termo_palavras.json  # Termo words
│   ├── tickets.json          # Ticket records
│   └── warnings.json         # Created at runtime for warning history
├── database/                # Database module
├── utils/                   # Utility components
├── .env.example              # .env template
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Dependencies 📦

- `discord.py` - Discord bot framework
- `python-dotenv` - Environment variables management
- `yt-dlp` - YouTube video downloader
- `PyNaCl` - Voice support for Discord
- `davey` - Discord voice encryption support
- `aiohttp` - Async HTTP client
- `audioop-lts` - Audio processing

> Reminders, polls, auto-moderation and moderation use only the standard library plus `discord.py` — no extra dependencies needed.

## Troubleshooting 🔧

### "ModuleNotFoundError: No module named 'discord'"
```bash
source Venv/bin/activate
pip install -r requirements.txt
```

### Bot doesn't play music
- Check if FFmpeg is installed: `ffmpeg -version`
- Make sure you're in a voice channel
- Check bot permissions in voice channels

### Database errors
- Ensure the `database/` directory has write permissions
- Check if Discord bot has proper guild permissions

### Bot doesn't respond to auto-responses
- Verify `data/auto_responses.json` is properly formatted
- Check if bot has message permissions in the channel
- Ensure the keywords are in the JSON file

### Auto-mod timeout isn't working
- Confirm the bot has the **Moderate Members** (Timeout Members) permission on the server
- Deletion of spam messages will still work even if the timeout silently fails

### Kick/ban commands say "permissões insuficientes"
- Confirm the bot has **Kick Members** / **Ban Members** respectively
- Confirm the bot's role is positioned above the target member's role in the role list

## Contributing 🤝

Feel free to suggest improvements or report bugs!

## License 📄
 
This project is licensed under the [PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/). See the [LICENSE](LICENSE) file for details.
 
---

**Version:** 2.1  
**Developed by:** Duarte Lacerda
