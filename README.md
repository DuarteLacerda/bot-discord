# Discord Bot 🤖

A complete Discord bot with music system, levels/XP, word games, reminders, polls, auto-moderation, and moderation tools.

## Features ✨

### 🎵 Music
- YouTube playback
- Queue system
- Controls: play, skip, pause, resume, stop
- Playlist support (maximum 20 tracks)
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

### 🔧 Others
- Ping/pong
- User information
- Server information
- Context-aware help (shows different commands to admins)
- Text translation between languages
- Server status (Minecraft/CS:GO)

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
DISCORD_BOT_TOKEN=your_token_here

AUTO_ROLE_NAME=Your Role Name
```

### XP Balancing
Edit the top of `cogs/levels.py`:
```python
XP_POR_CARACTERE = 0.5      # XP per character
NIVEL_MAXIMO = 500           # Maximum level
XP_MULTIPLICADOR = 1.15      # Exponential growth
```

### Edit Rules
Edit `data/rules.json` to add/remove server rules. No need to restart the bot!

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

### Auto-Moderation
Configured per server via commands (see below), not a file to edit by hand. Defaults:
- Anti-spam: 5 messages in 6 seconds triggers a 5-minute timeout
- Anti-links: any link outside the whitelist is deleted

Adjust the thresholds by editing the constants at the top of `cogs/automod.py` (`SPAM_MSG_LIMIT`, `SPAM_WINDOW_SECONDS`, `SPAM_TIMEOUT_MINUTES`).

## Commands 📝

### ⚙️ Basic
- `L!ping` - Shows bot latency
- `L!sum <a> <b>` - Adds two numbers

### ℹ️ Information
- `L!info [@user]` - User information
- `L!server` / `L!guild` - Server information
- `L!rules` - Shows server rules
- `L!serverstatus <ip>` - Minecraft/CS:GO server status

### 🌤️ Weather
- `L!tempo` / `L!weather` / `L!clima <city>` - Shows current weather for a city
- `L!hora` / `L!time` / `L!horario` / `L!timezone <city>` - Shows current time for a city
- `L!previsao` / `L!previsão` / `L!forecast <city>` - 7-day weather forecast

### 🔧 Utilities
- `L!traduzir` / `L!translate` / `L!tr <dest> <text>` - Translates text between languages

### 🎵 Music
- `L!join` / `L!connect` / `L!j` - Joins your voice channel
- `L!play` / `L!p <term|link>` - Plays from YouTube or Spotify
- `L!skip` / `L!sk` - Skips current track
- `L!stop` / `L!s` - Stops and leaves
- `L!pause` / `L!pz` - Pauses
- `L!resume` / `L!r` - Resumes
- `L!queue` / `L!q` - Shows the queue
- `L!testtone` / `L!tone` - Tests audio with a tone
- `L!music` - Shows music commands

### 📊 Levels
- `L!level [@user]` - Shows level and XP
- `L!rank` - Server top 10 leaderboard

### 🎮 Termo Game
- `L!termo` - Starts a new Termo game (Portuguese Wordle)
- `L!termo_quit` / `L!quit` - Exits current game
- `L!termo_stats` / `L!stats [@user]` - Shows Termo statistics
- `L!termo_rank` - Shows Termo ranking

### 🎲 Quick Games
- `L!ppt` / `L!pedrapapeltesoura` / `L!rps <rock|paper|scissors>` - Rock, paper, scissors
- `L!dado` / `L!dice` / `L!roll [sides]` - Rolls a dice with N sides
- `L!moeda` / `L!coin` / `L!flip` - Flips a coin
- `L!escolher` / `L!choose` / `L!pick <op1> <op2> ...` - Lets the bot choose for you
- `L!8ball` / `L!bola8` / `L!pergunta <question>` - Ask the magic 8-ball
- `L!adivinhar` / `L!guess` / `L!numero <number>` - Guess the number between 1 and 10
- `L!jogos` / `L!games` / `L!listarjogos` - Shows all available games

### 💻 Code Challenges
- `L!code` / `L!desafio` / `L!challenge` / `L!coding` - Starts a programming challenge
- `L!stats_code` - Shows code challenge statistics

### ⏰ Reminders
- `L!lembrar <tempo> <mensagem>` - Creates a reminder (e.g. `10m`, `2h`, `1d`, `1d2h30m`)
- `L!lembretes` - Lists your pending reminders
- `L!lembrete_cancelar <id>` - Cancels a reminder

### 📊 Polls
- `L!poll <question>` - Yes/no poll (👍/👎), expires in 24h by default
- `L!poll <question> | opt1 | opt2 | ...` - Multiple-choice poll (up to 10 options)
- `L!poll <question> | opt1 | opt2 | --tempo 2h` - Custom expiry (5 min to 7 days)
- `L!poll_fechar <message_id>` - Closes a poll early and shows results (author or admin)

### 🛡️ Auto-Moderation
- `L!automod` - Shows current auto-moderation status
- `L!automod_whitelist` - Lists whitelisted domains
- `L!automod_perms` - Lists who has automod moderator permission
- `L!automod_on` / `L!automod_off` - Enables/disables the whole system *(admin)*
- `L!automod_antispam <on|off>` - Toggles anti-spam only *(admin)*
- `L!automod_antilinks <on|off>` - Toggles anti-links only *(admin)*
- `L!automod_whitelist_add <domain>` - Allows a domain (e.g. `youtube.com`) *(admin)*
- `L!automod_whitelist_remove <domain>` - Removes a domain from the whitelist *(admin)*
- `L!automod_addperm @user` - Grants automod moderator permission *(admin)*
- `L!automod_removeperm @user` - Revokes that permission *(admin)*

### 🔨 Moderation
- `L!warn @user <reason>` - Warns a member *(admin or automod moderator)*
- `L!warnings [@user]` - Shows warning history (omit = your own)
- `L!warn_remove @user <id>` - Removes a specific warning *(admin)*
- `L!kick @user [reason]` - Kicks a member *(requires Kick Members)*
- `L!ban @user [reason]` - Bans a member *(requires Ban Members)*
- `L!unban <user_id>` - Removes a ban *(requires Ban Members)*
- `L!modlog_canal [#channel]` - Sets or shows the mod-log channel *(admin)*

### 👑 Admin Commands
- `L!write <message>` - Echoes message
- `L!clear [amount]` - Deletes messages from the channel
- `L!addxp @user <value>` - Adds XP to a user

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
│   ├── auto_responses.json  # Slang auto-responses
│   ├── rules.json           # Server rules
│   ├── termo_palavras.json  # Termo words
│   ├── code_challenges.json # Challenge data
│   ├── reminders.json       # Pending reminders
│   ├── automod.json         # Per-server auto-mod settings
│   ├── warnings.json        # Per-server warning history
│   └── modlog.json          # Per-server mod-log channel
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
- `aiohttp` - Async HTTP client
- `deep-translator` - Text translation
- `langdetect` - Language detection
- `mcstatus` - Minecraft server status
- `a2s` - Source engine query protocol
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

### Translation doesn't work
- Check if internet connection is available
- Verify language codes are correct (e.g., 'en', 'pt', 'es')

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

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

**Bot Prefix:** `L!`  
**Version:** 2.1  
**Developed by:** Duarte Lacerda