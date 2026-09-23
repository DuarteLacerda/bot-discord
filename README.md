# Bot Discord 🤖

Um bot Discord completo com sistema de música, níveis/XP, jogos de palavras, lembretes, sondagens, moderação automática e ferramentas de moderação.

## Funcionalidades ✨

### 🎵 Música

* Reprodução a partir do YouTube
* Sistema de fila
* Controlos: reproduzir, saltar, pausar, retomar e parar
* Suporte para playlists (máximo de 100 faixas)
* Abertura de caixas com recompensas ao jogar música

### 📊 Sistema de Níveis

* Progressão do nível 1 ao 500
* Ganho de XP por mensagem
* Tabela de classificação (top 10)
* Abertura automática de caixas ao subir de nível
* Várias recompensas (XP, bónus, etc.)

### 🌤️ Meteorologia e Hora

* Meteorologia atual para qualquer cidade do mundo
* Hora local de qualquer cidade
* Previsão meteorológica de 7 dias com informações detalhadas
* Dados de temperatura, precipitação e velocidade do vento

### 💬 Respostas Automáticas

* Deteção automática de calão português (de Portugal)
* Respostas relacionadas com terminologia de jogos
* Várias respostas aleatórias por palavra-chave
* Deteção sem distinção de acentos (funciona com "bué" ou "bue")
* Fácil de personalizar através de um ficheiro JSON

### 🎮 Jogos

* **Termo**: Wordle português com estatísticas e classificações
* **Jogos Rápidos**: Pedra-papel-tesoura, dado, moeda, 8-ball e adivinhação de números
* **Desafios de Código**: Desafios de programação para praticar programação

### ⏰ Lembretes

* Definir um lembrete com uma duração natural (`10m`, `2h`, `1d2h30m`)
* Enviado por mensagem privada (DM), utilizando o canal como alternativa caso as DMs estejam fechadas
* Listar e cancelar os seus próprios lembretes pendentes
* Mantém os dados após reinícios (`data/reminders.json`)

### 📊 Sondagens

* Sondagens rápidas de sim/não ou até 10 opções personalizadas, com votação através de reações
* Fecho automático após um período configurável (24h por predefinição, com a opção `--tempo` para personalizar)
* Fecho manual disponível para o autor da sondagem ou para um administrador
* Resultados publicados automaticamente quando uma sondagem é encerrada

### 🛡️ Moderação Automática

* **Anti-spam**: rajadas rápidas de mensagens são eliminadas e o remetente recebe um timeout
* **Anti-links**: mensagens que contenham links não incluídos na lista branca são eliminadas automaticamente
* Ativação/desativação por servidor para todo o sistema ou para cada verificação individualmente
* Lista branca de domínios, totalmente configurável
* Sistema de permissões próprio, independente dos cargos do Discord: permite atribuir/remover o estado de "moderador de automod", que isenta um utilizador das verificações e permite consultar as definições atuais
* Todas as definições são guardadas por servidor (`data/automod.json`)

### 🔨 Moderação

* Sistema de avisos com histórico persistente por utilizador (`data/warnings.json`)
* Expulsão e banimento (respeitando as permissões reais do Discord), com DM automática para o utilizador afetado
* Remoção de banimentos através do ID do utilizador
* Canal opcional de registo de moderação: cada aviso/expulsão/banimento/remoção de banimento é automaticamente registado nesse canal

### 🎫 Tickets

* Criar tickets privados com a equipa de suporte
* Gerir e resolver tickets de forma eficiente
* Registar todas as interações dos tickets

### 🚨 Anti-Raid

* Deteta entradas em massa e ativa automaticamente um bloqueio do servidor
* O bloqueio aumenta temporariamente o nível de verificação do servidor para o nível Máximo e expulsa contas com menos da idade mínima configurada
* Reverte automaticamente após uma duração configurável
* Ativação/desativação manual do bloqueio disponível para administradores
* Sensibilidade configurável (número de entradas, intervalo de tempo e idade mínima da conta)
* Predefinição: 5 entradas em 10 segundos ativam o bloqueio; contas com menos de 7 dias são expulsas durante o bloqueio; o bloqueio dura 15 minutos e é revertido automaticamente

### 🔧 Outros

* Ping/pong
* Informações do utilizador
* Informações do servidor
* Ajuda contextual (apresenta comandos diferentes aos administradores)

## Instalação 🚀

### Pré-requisitos

* Python 3.8+
* FFmpeg
* Node.js (para o yt-dlp)

### Passo a passo

```bash
# 1. Clonar o repositório
git clone git@github.com:DuarteLacerda/bot-discord.git
cd bot-discord

# 2. Criar o ficheiro .env
cp .env.example .env
# Editar o .env e adicionar:
# - DISCORD_BOT_TOKEN (obrigatório)
# - AUTO_ROLE_NAME (opcional)

# 3. Criar o ambiente virtual
python3 -m venv Venv
source Venv/bin/activate  # Linux/Mac
# ou
Venv\Scripts\activate  # Windows

# 4. Instalar as dependências
pip install -r requirements.txt

# 5. Executar o bot
python main.py
```

## Configuração ⚙️

### Variáveis de Ambiente (.env)

```env
# Token do Bot Discord
DISCORD_BOT_TOKEN=your_discord_bot_token_here

# Configuração dos Tickets
TICKET_CATEGORY_NAME=your_ticket_category_name_here
TICKET_STAFF_ROLE_NAME=your_staff_role_name_here
TICKET_LOG_CHANNEL_NAME=your_log_channel_name_here

```

Ao convidar a aplicação, inclui os scopes `bot` e `applications.commands`. Os comandos slash são sincronizados globalmente ao iniciar o bot e podem demorar algum tempo a aparecer no Discord.

### Balanceamento de XP

Edita o início de `cogs/levels.py`:

```python
XP_POR_CARACTERE = 0.5  # XP gained per character
XP_MIN_POR_MSG = 5      # Minimum XP per message
XP_MAX_POR_MSG = 50     # Maximum XP per message (cap to prevent spam)
COOLDOWN_SEGUNDOS = 10  # Cooldown between XP-giving messages
XP_BASE_NIVEL = 100     # XP needed to go from level 1 to 2
XP_MULTIPLICADOR = 1.15 # Multiplicador de XP per level (progression)
NIVEL_MAXIMO = 500      # Maximum level
LEVEL_ROLE_INTERVAL = 10  # A cada quantos níveis se ganha uma role nova
```

### Editar Regras

Edita `data/rules.json` para adicionar ou remover regras do servidor. Não é necessário reiniciar o bot!

O ficheiro utiliza esta estrutura:

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

### Respostas Automáticas

Edita `data/auto_responses.json` para personalizar as respostas ao calão:

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

O bot responde automaticamente quando deteta estas palavras-chave nas mensagens (sem distinção entre maiúsculas e minúsculas nem acentos).

Reinicia o bot depois de alterares este ficheiro para que as novas respostas sejam carregadas.

### Palavras do Termo

Edita `data/termo_palavras.json` para adicionar ou remover palavras válidas de cinco letras do Termo. O ficheiro deve conter um array JSON de palavras:

```json
[
    "carro",
    "porta",
    "ponte"
]
```

Utiliza palavras em minúsculas e sem acentos e reinicia o bot depois de alterares o ficheiro.

### Desafios de Código

Edita `data/code_challenges.json` para adicionar desafios. Organiza-os por linguagem e dificuldade (`facil`, `medio` ou `dificil`):

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

Cada desafio precisa de `titulo`, `descricao`, `exemplo` e `dica`. Reinicia o bot depois de alterares este ficheiro.

### Moderação Automática

Configurada por servidor através de comandos (ver abaixo), não através de um ficheiro que deva ser editado manualmente. Valores predefinidos:

* Anti-spam: 5 mensagens em 6 segundos ativam um timeout de 5 minutos
* Anti-links: qualquer link que não esteja na lista branca é eliminado

Ajusta os limites editando as constantes no início de `cogs/automod.py` (`SPAM_MSG_LIMIT`, `SPAM_WINDOW_SECONDS`, `SPAM_TIMEOUT_MINUTES`).

### Ficheiros de Dados

| Ficheiro                    | Finalidade                                                         | Edição manual                                                              |
| --------------------------- | ------------------------------------------------------------------ | -------------------------------------------------------------------------- |
| `data/rules.json`           | Regras do servidor apresentadas por `/rules`.                      | Sim                                                                        |
| `data/auto_responses.json`  | Palavras-chave e respostas automáticas.                            | Sim, depois reiniciar o bot                                                |
| `data/termo_palavras.json`  | Palavras válidas de cinco letras para o Termo.                     | Sim, depois reiniciar o bot                                                |
| `data/code_challenges.json` | Desafios de programação agrupados por linguagem e dificuldade.     | Sim, depois reiniciar o bot                                                |
| `data/automod.json`         | Definições de moderação automática por servidor.                   | Sim, mas é preferível utilizar os comandos `/automod_*`; reiniciar depois  |
| `data/antiraid.json`        | Definições de anti-raid por servidor e estado do bloqueio.         | Sim, mas é preferível utilizar os comandos `/antiraid_*`; reiniciar depois |
| `data/tickets.json`         | Registos e configuração dos tickets.                               | Sim, com cuidado; é preferível gerir os tickets através do Discord         |
| `data/modlog.json`          | Canais de registo de moderação configurados.                       | Sim, mas `/modlog_canal` é mais seguro; reiniciar depois                   |
| `data/reminders.json`       | Lembretes pendentes. Criado quando o primeiro lembrete é guardado. | Sim, com cuidado; é preferível utilizar `/lembrar` e `/lembrete_cancelar`  |
| `data/warnings.json`        | Histórico de avisos. Criado quando o primeiro aviso é guardado.    | Sim, com cuidado; é preferível utilizar os comandos de moderação           |

Todos os ficheiros JSON podem ser editados manualmente, mas os ficheiros de configuração e de execução devem manter a estrutura existente. Para os editar, para o bot, faz primeiro uma cópia de segurança e reinicia-o depois. As alterações feitas através dos comandos são mais seguras porque são validadas e guardadas automaticamente.

## Comandos 📝

Os comandos estão disponíveis através do menu de comandos slash do Discord. Escreve `/` num canal para os consultar e selecionar o comando necessário.

### ⚙️ Básicos

* `/ping` - Mostra a latência do bot
* `/sum <a> <b>` - Soma dois números

### ℹ️ Informações

* `/info @user` - Informações do utilizador
* `/server` - Informações do servidor
* `/rules` - Mostra as regras do servidor

### 🌤️ Meteorologia

* `/tempo <city>` - Mostra a meteorologia atual de uma cidade
* `/hora <city>` - Mostra a hora atual de uma cidade
* `/previsao <city>` - Previsão meteorológica de 7 dias

### 🎵 Música

* `/join` - Entra no teu canal de voz
* `/play <term|link>` - Reproduz conteúdo do YouTube ou Spotify
* `/skip` - Salta a faixa atual
* `/stop` - Para a reprodução e sai do canal
* `/pause` - Pausa a reprodução
* `/resume` - Retoma a reprodução
* `/queue` - Mostra a fila
* `/testtone` - Testa o áudio com um tom
* `/music` - Mostra os comandos de música

### 📊 Níveis

* `/level @user` - Mostra o nível e o XP
* `/rank` - Tabela de classificação dos 10 melhores do servidor
* `/syncroles @user`- Sincroniza os cargos de nível com o nível atual *(requer Gerir Servidor)*

### 🎮 Jogo Termo

* `/termo` - Inicia um novo jogo de Termo (Wordle português)
* `/termo_quit` - Sai do jogo atual
* `/termo_stats @user` - Mostra as estatísticas do Termo
* `/termo_rank` - Mostra a classificação do Termo

### 🎲 Jogos Rápidos

* `/ppt <rock|paper|scissors>` - Pedra, papel e tesoura
* `/dado [sides]` - Lança um dado com N lados
* `/moeda` - Lança uma moeda
* `/escolher <option1 | option2>` - Deixa o bot escolher por ti
* `/adivinhar <number>` - Adivinha o número entre 1 e 10
* `/8ball <question>` - Faz uma pergunta à bola 8 mágica
* `/jogos` - Mostra todos os jogos disponíveis

### 💻 Desafios de Código

* `/code` - Inicia um desafio de programação
* `/stats_code` - Mostra as estatísticas dos desafios de código

### ⏰ Lembretes

* `/lembrar <tempo> <mensagem>` - Cria um lembrete (por exemplo, `10m`, `2h`, `1d`, `1d2h30m`)
* `/lembretes` - Lista os teus lembretes pendentes
* `/lembrete_cancelar <id>` - Cancela um lembrete

### 📊 Sondagens

* `/poll <question>` - Sondagem de sim/não (👍/👎), expira por predefinição após 24h
* `/poll <question> | opt1 | opt2 | ...` - Sondagem de escolha múltipla (até 10 opções)
* `/poll <question> | opt1 | opt2 | --tempo 2h` - Expiração personalizada (de 5 minutos a 7 dias)
* `/poll_fechar <message_id>` - Fecha uma sondagem antecipadamente e mostra os resultados (autor ou administrador)

### 🛡️ Moderação Automática

* `/automod` - Mostra o estado atual da moderação automática
* `/automod_whitelist` - Lista os domínios autorizados
* `/automod_perms` - Lista os utilizadores com permissão de moderador de automod
* `/automod_on` / `/automod_off` - Ativa/desativa todo o sistema *(admin)*
* `/automod_antispam <on|off>` - Ativa/desativa apenas o anti-spam *(admin)*
* `/automod_antilinks <on|off>` - Ativa/desativa apenas o anti-links *(admin)*
* `/automod_whitelist_add <domain>` - Permite um domínio (por exemplo, `youtube.com`) *(admin)*
* `/automod_whitelist_remove <domain>` - Remove um domínio da lista branca *(admin)*
* `/automod_addperm @user` - Concede permissão de moderador de automod *(admin)*
* `/automod_removeperm @user` - Remove essa permissão *(admin)*

### 🚨 Anti-Raid

* `/antiraid` - Mostra o estado atual do anti-raid
* `/antiraid_on` / `/antiraid_off` - Ativa/desativa o sistema *(admin)*
* `/antiraid_config <entradas> <segundos> <dias_conta>` - Configura a sensibilidade (limite de entradas, intervalo de tempo e idade mínima da conta) *(admin)*
* `/antiraid_lockdown_on` / `/antiraid_lockdown_off` - Ativa/desativa manualmente o bloqueio *(admin)*

### 🔨 Moderação

* `/warn @user <reason>` - Avisa um membro *(admin ou moderador de automod)*
* `/warnings @user` - Mostra o histórico de avisos (omitir = os teus próprios avisos)
* `/warn_remove @user <id>` - Remove um aviso específico *(admin)*
* `/kick @user [reason]` - Expulsa um membro *(requer a permissão Expulsar Membros)*
* `/ban @user [reason]` - Bane um membro *(requer a permissão Banir Membros)*
* `/unban <user_id>` - Remove um banimento *(requer a permissão Banir Membros)*
* `/modlog_canal [#channel]` - Define ou mostra o canal de registo de moderação *(admin)*

### 🎫 Tickets

* `/ticket <reason>` - Abre um ticket privado com a equipa
* `/ticketpanel` - Publica o painel de abertura de tickets *(requer Gerir Servidor)*

### 👑 Comandos de Administrador

* `/write <message>` - Reenvia a mensagem
* `/clear [amount]` - Elimina mensagens do canal
* `/addxp @user <value>` - Adiciona XP a um utilizador

## Executar em Segundo Plano (Linux)

### Com systemd

```bash
# O serviço já está configurado no discord-bot.service

# Iniciar
systemctl --user start discord-bot

# Verificar estado
systemctl --user status discord-bot

# Consultar os registos
journalctl --user -u discord-bot -f

# Iniciar automaticamente no arranque
systemctl --user enable discord-bot
```

### Com screen

```bash
screen -S discordbot
source Venv/bin/activate
python main.py
# Pressiona Ctrl+A e depois D para sair sem terminar a sessão

# Voltar a ligar
screen -r discordbot
```

## Estrutura do Projeto 📂

```text
discord-bot/
├── main.py                  # Inicialização do bot
├── cogs/
│   ├── bot_commands.py      # Comandos gerais e ajuda
│   ├── music.py             # Módulo de música
│   ├── levels.py            # Módulo de níveis
│   ├── events.py            # Eventos e respostas automáticas
│   ├── termo.py             # Jogo Termo
│   ├── code_challenges.py   # Desafios de programação
│   ├── games.py             # Jogos
│   ├── reminders.py         # Lembretes
│   ├── polls.py             # Sondagens
│   ├── automod.py           # Anti-spam / anti-links + sistema de permissões
│   ├── antiraid.py          # Deteção de entradas em massa e bloqueio
│   ├── moderation.py        # Avisos, expulsões, banimentos e registo de moderação
│   └── tickets.py           # Tickets privados de suporte
├── data/
│   ├── antiraid.json         # Definições de anti-raid por servidor
│   ├── auto_responses.json  # Respostas automáticas ao calão
│   ├── automod.json          # Definições de automod por servidor
│   ├── code_challenges.json  # Dados dos desafios
│   ├── modlog.json           # Canais de registo de moderação
│   ├── reminders.json        # Criado durante a execução para lembretes pendentes
│   ├── rules.json            # Regras do servidor
│   ├── termo_palavras.json  # Palavras do Termo
│   ├── tickets.json          # Registos dos tickets
│   └── warnings.json         # Criado durante a execução para o histórico de avisos
├── database/                # Módulo da base de dados
├── utils/                   # Componentes utilitários
├── .env.example              # Modelo do .env
├── requirements.txt          # Dependências Python
└── README.md                 # Este ficheiro
```

## Dependências 📦

* `discord.py` - Framework para bots Discord
* `python-dotenv` - Gestão de variáveis de ambiente
* `yt-dlp` - Descarregador de vídeos do YouTube
* `PyNaCl` - Suporte de voz para o Discord
* `davey` - Suporte para encriptação de voz do Discord
* `aiohttp` - Cliente HTTP assíncrono
* `audioop-lts` - Processamento de áudio

> Os lembretes, sondagens, moderação automática e moderação utilizam apenas a biblioteca padrão e `discord.py` — não são necessárias dependências adicionais.

## Resolução de Problemas 🔧

### "ModuleNotFoundError: No module named 'discord'"

```bash
source Venv/bin/activate
pip install -r requirements.txt
```

### O bot não reproduz música

* Verifica se o FFmpeg está instalado: `ffmpeg -version`
* Certifica-te de que estás num canal de voz
* Verifica as permissões do bot nos canais de voz

### Erros da base de dados

* Certifica-te de que o diretório `database/` tem permissões de escrita
* Verifica se o bot Discord possui as permissões necessárias no servidor

### O bot não responde automaticamente

* Verifica se `data/auto_responses.json` está corretamente formatado
* Verifica se o bot tem permissões para enviar mensagens no canal
* Certifica-te de que as palavras-chave estão presentes no ficheiro JSON

### O timeout do automod não está a funcionar

* Confirma que o bot tem a permissão **Moderar Membros** (Timeout Members) no servidor
* A eliminação das mensagens de spam continuará a funcionar mesmo que o timeout falhe silenciosamente

### Os comandos de expulsão/banimento indicam "permissões insuficientes"

* Confirma que o bot tem as permissões **Expulsar Membros** / **Banir Membros**, respetivamente
* Confirma que o cargo do bot está acima do cargo do membro-alvo na lista de cargos

## Contribuição 🤝

Sente-te à vontade para sugerir melhorias ou comunicar erros!

## Licença 📄

Este projeto está licenciado ao abrigo da [PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/). Consulta o ficheiro [LICENSE](LICENSE) para obter os detalhes.

---

**Versão:** 2.1
**Desenvolvido por:** Duarte Lacerda
