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

### 🛡️ Moderation
- Message clearing command
- Echo command (admins only)
- JSON-based rules system (easy to edit)

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
