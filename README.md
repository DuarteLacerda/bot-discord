# Discord Bot 🤖

Um bot Discord completo com sistema de música, níveis/XP, e ferramentas de moderação.

## Funcionalidades ✨

### 🎵 Música
- Reprodução de YouTube e Spotify
- Fila de reprodução
- Controles: play, skip, pause, resume, stop
- Suporte a playlists (máximo 20 faixas)
- Case opening com prémios ao tocar música

### 📊 Sistema de Níveis
- Progressão de 1 a 500 níveis
- Ganho de XP por mensagens
- Leaderboard (top 10)
- Case opening automático ao subir de nível
- Prémios variados (XP, bônus, etc.)

### 🛡️ Moderação
- Comando para limpar mensagens
- Comando echo (apenas admins)
- Sistema de regras em JSON (fácil de editar)

### 🔧 Outros
- Ping/pong
- Informações de utilizador
- Informações do servidor
- Help context-aware (mostra diferentes comandos a admins)

## Instalação 🚀

### Pré-requisitos
- Python 3.8+
- FFmpeg
- Node.js (para yt-dlp)

### Passo a passo

```bash
# 1. Clone o repositório
git clone git@github.com:DuarteLacerda/bot-discord.git
cd bot-discord

# 2. Crie o ficheiro .env
cp .env.example .env
# Edite .env e adicione:
# - DISCORD_BOT_TOKEN (obrigatório)
# - SPOTIPY_CLIENT_ID (opcional)
# - SPOTIPY_CLIENT_SECRET (opcional)

# 3. Crie a virtual environment
python3 -m venv Venv
source Venv/bin/activate  # Linux/Mac
# ou
Venv\Scripts\activate  # Windows

# 4. Instale as dependências
pip install -r requirements.txt

# 5. Corra o bot
python main.py
```

## Configuração ⚙️

### Variáveis de Ambiente (.env)
```
DISCORD_BOT_TOKEN=seu_token_aqui
SPOTIPY_CLIENT_ID=seu_id_spotify (opcional)
SPOTIPY_CLIENT_SECRET=seu_secret_spotify (opcional)
```

### Balanceamento de XP
Edite o topo de `levels.py`:
```python
XP_POR_CARACTERE = 0.5      # XP por caractere
NIVEL_MAXIMO = 500           # Nível máximo
XP_MULTIPLICADOR = 1.15      # Crescimento exponencial
```

### Editar Regras
Edite `rules.json` para adicionar/remover regras do servidor. Não precisa reiniciar o bot!

## Comandos 📝

### Gerais
- `l!ping` / `l!pong` - Responde Pong!
- `l!info` / `l!user [@user]` - Informações do utilizador
- `l!servidor` / `l!server` - Informações do servidor
- `l!rules` / `l!regras` - Mostra as regras do servidor
- `l!help` / `l!ajuda` - Mostra todos os comandos (context-aware)

### Música
- `l!join` / `l!entrar` / `l!j` - Entra no seu canal de voz
- `l!play` / `l!tocar` / `l!p <termo|link>` - Busca no YouTube ou Spotify
- `l!ytplay` / `l!ytp <termo>` - Força busca no YouTube
- `l!splay` / `l!sp <link>` - Toca link de Spotify
- `l!skip` / `l!pular` / `l!sk` - Pula a faixa atual
- `l!stop` / `l!parar` / `l!s` - Limpa fila e sai
- `l!pause` / `l!pausar` / `l!pz` - Pausa
- `l!resume` / `l!retomar` / `l!r` - Retoma
- `l!fila` / `l!queue` / `l!q` - Mostra a fila
- `l!music_cmds` / `l!mc` - Lista comandos de música

### Níveis
- `l!nivel` / `l!level [@user]` - Mostra nível e XP
- `l!rank` / `l!ranking` - Top 10 do servidor
- `l!addxp` / `l!adicionarxp @user <valor>` - Adiciona XP (apenas admins)

### Admins
- `l!limpar` / `l!clear [quantidade]` - Apaga mensagens do canal
- `l!escrever` / `l!write <mensagem>` - Eco da mensagem

## Executar em Background (Linux)

### Com systemd
```bash
# O serviço já está configurado em discord-bot.service

# Iniciar
systemctl --user start discord-bot

# Ver status
systemctl --user status discord-bot

# Ver logs
journalctl --user -u discord-bot -f

# Auto-start no boot
systemctl --user enable discord-bot
```

### Com screen
```bash
screen -S discordbot
source Venv/bin/activate
python main.py
# Pressione Ctrl+A depois D para desligar

# Reconectar
screen -r discordbot
```

## Estrutura do Projeto 📂

```
discord-bot/
├── main.py              # Inicialização do bot
├── bot_commands.py      # Comandos gerais e help
├── music.py             # Cog de música
├── levels.py            # Cog de níveis
├── events.py            # Event listeners
├── levels_data.json     # Dados de utilizadores (auto-gerado)
├── rules.json           # Regras do servidor
├── .env                 # Variáveis de ambiente (NÃO commitar!)
├── .env.example         # Template do .env
├── requirements.txt     # Dependências Python
└── README.md            # Este ficheiro
```

## Dependências 📦

- `discord.py` - Bot framework
- `python-dotenv` - Gestão de variáveis de ambiente
- `yt-dlp` - Download de vídeos do YouTube
- `spotipy` - API do Spotify
- `PyNaCl` - Suporte de voz

## Troubleshooting 🔧

### "ModuleNotFoundError: No module named 'discord'"
```bash
source Venv/bin/activate
pip install -r requirements.txt
```

### Bot não toca música
- Verifique se FFmpeg está instalado: `ffmpeg -version`
- Certifique-se que está no canal de voz
- Verifique as permissões do bot

### Spotify não funciona
- Deixe o .env em branco (usará YouTube como fallback)
- Ou configure as credenciais do Spotify Developer

## Contribuição 🤝

Sinta-se à vontade para sugerir melhorias ou reportar bugs!

## Licença 📄

Projeto pessoal. Use livremente.

---

**Bot Prefix:** `l!`  
**Versão:** 1.0  
**Desenvolvido por:** Duarte Lacerda
