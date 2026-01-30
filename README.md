# Discord Bot 🤖

A complete Discord bot with music system, levels/XP, and moderation tools.

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

### 💬 Auto-Responses
- Automatic detection of Portuguese slang (from Portugal)
- Gaming terminology responses
- Multiple random responses per keyword
- Accent-insensitive detection (works with "bué" or "bue")
- Easy to customize via JSON file

### 🛡️ Moderation
- Message clearing command
- Echo command (admins only)
- JSON-based rules system (easy to edit)

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

## Commands 📝

### General
- `l!ping` - Shows bot latency
- `l!sum <a> <b>` - Adds two numbers
- `l!tempo` / `l!weather` / `l!clima <city>` - Shows current weather for a city
- `l!hora` / `l!time` / `l!horario` / `l!timezone <city>` - Shows current time for a city
- `l!traduzir` / `l!translate` / `l!tr <dest> <text>` - Translates text between languages
- `l!info [@user]` - User information
- `l!server` / `l!guild` - Server information
- `l!rules` - Shows server rules
- `l!help` - Shows all commands (context-aware)

### Music
- `l!join` / `l!connect` - Joins your voice channel
- `l!play` / `l!p <term|link>` - Plays from YouTube or Spotify
- `l!skip` / `l!sk` - Skips current track
- `l!stop` / `l!s` - Stops and leaves
- `l!pause` / `l!pz` - Pauses
- `l!resume` / `l!r` - Resumes
- `l!queue` / `l!q` - Shows the queue
- `l!testtone` / `l!tone` - Tests audio with a tone
- `l!music` - Shows music commands

### Levels
- `l!level [@user]` - Shows level and XP
- `l!rank` - Server top 10 leaderboard
- `l!addxp @user <value>` - Adds XP (admins only)

### Termo Game
- `l!termo` - Starts a new Termo game (Portuguese Wordle)
- `l!termo_quit` - Exits current game
- `l!termo_stats [@user]` - Shows Termo statistics
- `l!termo_rank` - Shows Termo ranking

### Quick Games
- `l!ppt` / `l!pedrapapeltesoura` / `l!rps <rock|paper|scissors>` - Plays rock, paper, scissors
- `l!dado` / `l!dice` / `l!roll [sides]` - Rolls a dice with N sides
- `l!moeda` / `l!coin` / `l!flip` - Flips a coin
- `l!escolher` / `l!choose` / `l!pick <op1> <op2> ...` - Lets the bot choose for you
- `l!8ball` / `l!bola8` / `l!pergunta <question>` - Ask the magic 8-ball
- `l!adivinhar` / `l!guess` / `l!numero <number>` - Guess the number between 1 and 10
- `l!jogos` / `l!games` / `l!listarjogos` - Shows all available games

### Code Challenges
- `l!code` / `l!desafio` / `l!challenge` / `l!coding` - Starts a programming challenge
- `l!stats_code` - Shows code challenge statistics

### Admin Commands
- `l!write <message>` - Echoes message (admins only)
- `l!clear [amount]` - Deletes messages from channel (admins only)

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
├── main.py              # Bot initialization
├── cogs/
│   ├── bot_commands.py  # General commands and help
│   ├── music.py         # Music cog
│   ├── levels.py        # Levels cog
│   ├── events.py        # Event listeners and auto-responses
│   ├── termo.py         # Termo game
│   ├── code_challenges.py # Coding challenges
│   └── games.py         # Games
├── data/
│   ├── auto_responses.json # Slang auto-responses
│   ├── rules.json       # Server rules
│   ├── termo_palavras.json # Termo words
│   └── code_challenges.json # Challenge data
├── database/            # Database module
├── utils/               # Utility components
├── .env.example         # .env template
├── requirements.txt     # Python dependencies
└── README.md            # This file
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

## Contributing 🤝

Feel free to suggest improvements or report bugs!

## License 📄

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

**Bot Prefix:** `L!`  
**Version:** 2.0  
**Developed by:** Duarte Lacerda
