# Discord Bot 🤖

A complete Discord bot with music system, levels/XP, and moderation tools.

## Features ✨

### 🎵 Music
- YouTube and Spotify playback
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
# - SPOTIPY_CLIENT_ID (optional)
# - SPOTIPY_CLIENT_SECRET (optional)

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
```
DISCORD_BOT_TOKEN=your_token_here
SPOTIPY_CLIENT_ID=your_spotify_id (optional)
SPOTIPY_CLIENT_SECRET=your_spotify_secret (optional)
```

### XP Balancing
Edit the top of `levels.py`:
```python
XP_POR_CARACTERE = 0.5      # XP per character
NIVEL_MAXIMO = 500           # Maximum level
XP_MULTIPLICADOR = 1.15      # Exponential growth
```

### Edit Rules
Edit `rules.json` to add/remove server rules. No need to restart the bot!

## Commands 📝

### General
- `l!ping` / `l!pong` - Replies Pong!
- `l!info` / `l!user [@user]` - User information
- `l!servidor` / `l!server` - Server information
- `l!rules` / `l!regras` - Shows server rules
- `l!help` / `l!ajuda` - Shows all commands (context-aware)

### Music
- `l!join` / `l!entrar` / `l!j` - Joins your voice channel
- `l!play` / `l!tocar` / `l!p <term|link>` - Search on YouTube or Spotify
- `l!ytplay` / `l!ytp <term>` - Force YouTube search
- `l!splay` / `l!sp <link>` - Plays Spotify link
- `l!skip` / `l!pular` / `l!sk` - Skips current track
- `l!stop` / `l!parar` / `l!s` - Clears queue and leaves
- `l!pause` / `l!pausar` / `l!pz` - Pauses
- `l!resume` / `l!retomar` / `l!r` - Resumes
- `l!fila` / `l!queue` / `l!q` - Shows the queue
- `l!music_cmds` / `l!mc` - Lists music commands

### Levels
- `l!nivel` / `l!level [@user]` - Shows level and XP
- `l!rank` / `l!ranking` - Server top 10
- `l!addxp` / `l!adicionarxp @user <value>` - Adds XP (admins only)

### Admins
- `l!limpar` / `l!clear [amount]` - Deletes messages from channel
- `l!escrever` / `l!write <message>` - Echoes message

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
├── bot_commands.py      # General commands and help
├── music.py             # Music cog
├── levels.py            # Levels cog
├── events.py            # Event listeners
├── levels_data.json     # User data (auto-generated)
├── rules.json           # Server rules
├── .env                 # Environment variables (DO NOT commit!)
├── .env.example         # .env template
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

## Dependencies 📦

- `discord.py` - Bot framework
- `python-dotenv` - Environment variables management
- `yt-dlp` - YouTube video download
- `spotipy` - Spotify API
- `PyNaCl` - Voice support

## Troubleshooting 🔧

### "ModuleNotFoundError: No module named 'discord'"
```bash
source Venv/bin/activate
pip install -r requirements.txt
```

### Bot doesn't play music
- Check if FFmpeg is installed: `ffmpeg -version`
- Make sure you're in a voice channel
- Check bot permissions

### Spotify doesn't work
- Leave .env blank (will use YouTube as fallback)
- Or configure Spotify Developer credentials

## Contributing 🤝

Feel free to suggest improvements or report bugs!

## License 📄

Personal project. Use freely.

---

**Bot Prefix:** `l!`  
**Version:** 1.0  
**Developed by:** Duarte Lacerda
