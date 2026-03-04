# 🚵‍♂️ MTB AI Coach: Seu Treinador de Performance com Inteligência Artificial

O **Coach-Strava** é um bot de Telegram proativo projetado para atuar como seu treinador de Mountain Bike e parceiro de trilha. Ele cruza dados reais das suas pedaladas, analisa a previsão do tempo e usa a inteligência do Google Gemini para te manter motivado, consistente e com a manutenção da sua bicicleta em dia. Todas essa informações em seu Telegram! Converse com o bot e avance seu nível no pedal!

---

> 💡 **Primeira vez mexendo com código ou terminal?**
> Se você não é da área de tecnologia, nunca usou o GitHub ou não tem o costume de usar linhas de comando, preparei um passo a passo focado em você! 
> 👉 **[Clique aqui para ler o Guia Zero a Um: Preparando seu Computador](GUIA_INICIANTES.md)**. Leia este guia rápido antes de seguir com a instalação abaixo para deixar seu VS Code e Git prontos para o uso.

---

## ✨ Funcionalidades

* **📊 Análise de Dados (Strava):** Monitora seu volume de treinos (km, elevação, dias pedalados) e identifica automaticamente a sua **bicicleta principal** cadastrada no Strava para alertar sobre o desgaste acumulado.
* **🌤️ Inteligência Climática (OpenWeather):** Verifica a previsão do tempo local para te avisar se o pedal de fim de semana terá sol, chuva ou muita lama.
* **🧠 Cérebro de IA com Memória (Google Gemini):** Utiliza o modelo *Gemini 2.5 Flash* com memória persistente em banco de dados SQLite. O bot lembra das suas conversas anteriores, dores relatadas e manutenções feitas na bike.
* **⏰ Proatividade (Agendador):** Toda sexta-feira às 18:00, o bot te envia proativamente um planejamento para o fim de semana com base no seu cansaço e no clima — para **todos os usuários registrados**.
* **📷 Análise Visual de Fotos (Gemini Multimodal):** Envie fotos da trilha, bicicleta, equipamento ou paisagem e o coach analisa visualmente e responde com dicas!
* **🏆 Conquistas Automáticas:** O bot celebra marcos como bater a meta mensal, atingir 50%/75% da meta, ou marcos de quilometragem na bike (1000km, 3000km, 5000km).
* **🎯 Meta Personalizada:** Cada usuário pode definir sua própria meta mensal de quilometragem diretamente pelo chat.
* **📈 Histórico de Evolução:** Comparativo mês a mês para acompanhar sua evolução ao longo do tempo.
* **🔄 Resiliência:** Cache inteligente de dados Strava, retry automático com backoff exponencial em APIs externas, e renovação automática de tokens.
* **🐳 Pronto para Produção (Docker):** Totalmente conteinerizado com health check, garantindo monitoramento e auto-restart.

---

## 📋 Pré-requisitos

Antes de instalar, você precisará criar contas e gerar chaves (gratuitas) nas seguintes plataformas:

1.  **Telegram:** Fale com o [@BotFather](https://t.me/botfather) para criar um bot e obter o `TELEGRAM_TOKEN`.
2.  **Google AI Studio:** Crie uma API Key gratuita para o Gemini em [Google AI Studio](https://aistudio.google.com/).
3.  **Strava Developers:** Acesse [Strava API](https://developers.strava.com/), crie uma aplicação e anote seu `Client ID` e `Client Secret`.
4.  **OpenWeather:** Crie uma conta no [OpenWeatherMap](https://openweathermap.org/api) e gere sua API Key.
5.  **Docker e Docker Compose:** Essenciais para rodar a aplicação de forma isolada e limpa.

---

## 🚀 Guia de Instalação Passo a Passo

### Passo 1: Clonar o Repositório
Abra o seu terminal e clone o projeto para a sua máquina:
```bash
git clone https://github.com/willgtk/Coach-Strava.git
cd Coach-Strava
```

### Passo 2: Configurar as Variáveis de Ambiente
Na raiz do projeto, copie o arquivo de exemplo e preencha com as suas chaves:

```bash
# Linux / macOS:
cp .env.example .env

# Windows (PowerShell):
copy .env.example .env
```

Edite o `.env` e preencha:

```bash
STRAVA_CLIENT_ID=seu_client_id_aqui
STRAVA_CLIENT_SECRET=seu_client_secret_aqui
GOOGLE_API_KEY=sua_chave_do_gemini
TELEGRAM_TOKEN=seu_token_do_telegram
OPENWEATHER_API_KEY=sua_chave_do_clima

# As variáveis abaixo serão preenchidas automaticamente nos próximos passos:
STRAVA_TOKEN=
STRAVA_REFRESH_TOKEN=
TELEGRAM_CHAT_ID=
```

### Passo 3: Autenticação do Strava (Obrigatório)
O bot precisa de permissão para ler seus treinos e equipamentos. Para gerar os tokens de acesso:

1. Tenha o Python instalado na sua máquina para rodar este script de configuração.

2. Instale a biblioteca do Strava e o dotenv:

```bash
pip install stravalib python-dotenv
```

3. Rode o script de autorização:

```bash
python src/setup_strava_auth.py
```

4. O terminal vai gerar um link. Clique nele, faça login no seu Strava e clique em Autorizar.

5. Você será redirecionado para uma página com erro (http://localhost...). Isso é normal! Copie a URL inteira dessa página de erro e cole de volta no seu terminal.

6. Pronto! O script salvará os tokens de acesso direto no seu arquivo .env.


### Passo 4: O Banco de Dados de Memória
O bot utiliza um banco de dados SQLite para se lembrar de você e dos seus amigos separadamente!
Você não precisa se preocupar em criá-lo: assim que o bot iniciar pela primeira vez, ele criará automaticamente um arquivo seguro chamado `coach_database.db` na raiz do seu projeto. É lá que o "cérebro" dele ficará guardado.

### Passo 5: Subir o Bot com Docker
Com as chaves configuradas, deixe a infraestrutura fazer o trabalho pesado. No terminal, rode:
```bash
docker compose up -d --build
```

O Docker vai baixar as dependências, compilar o que for necessário e subir o bot. Para acompanhar se deu tudo certo, veja os logs com `docker compose logs -f`.

---

## 🤖 Como Usar
Vá até o Telegram, busque pelo seu bot e envie os comandos:

- `/start` ou `/help`: Inicia o bot, exibe os comandos e registra o seu Chat ID no sistema, permitindo que o bot te envie mensagens proativas na sexta-feira.
- `/semana`: Força o bot a ler o seu Strava, o clima, o desgaste da sua bicicleta e o andamento da sua meta mensal naquele exato momento, gerando um resumo detalhado e uma dica de treino.
- `/grafico`: Gera e envia uma imagem com o gráfico do seu saldo de quilometragem por dia nos últimos 30 dias. Excelente para ver a constância visualmente!
- `/pedal`: Busca e analisa os dados detalhados do seu último pedal no Strava, indicando pontos fortes e o que melhorar.
- `/bike`: Verifica a sua bicicleta principal no Strava, mostra a quilometragem atual e dá dicas de manutenção precisas (freios, corrente, relação).
- `/clima`: Obtém a previsão do tempo detalhada e envia uma mensagem motivadora já adaptada às condições climáticas para o seu próximo pedal.
- `/meta`: Sem argumento mostra a meta atual. Com argumento (ex: `/meta 200`) define sua meta mensal personalizada de quilometragem.
- `/historico`: Mostra a evolução comparativa dos últimos 3 meses (km rodados e quantidade de pedais), com análise de tendências e motivação.

**📷 Envio de Fotos**: Envie uma foto da trilha, bike, equipamento ou paisagem. O coach usa o Gemini multimodal para analisar a imagem e responder com dicas, elogios ou motivação!

**🎙️ Walkie-Talkie (Mensagem de Voz)**: Está no meio da trilha e não quer digitar? Basta gravar um áudio natural (ex: *"Coach, acabei de virar um single track insano, me dá uma dica de recuperação"*). O bot usa o motor multimodal da IA para escutar a sua voz, entender o contexto, e te responder!

**Mensagem Livre**: Converse naturalmente por texto. Ex: "Hoje o pedal teve muita lama, precisei trocar as pastilhas de freio". O bot vai guardar isso na memória para as próximas conversas e até interceptar o clima e dados do Strava automaticamente dependendo das palavras!

**🏆 Conquistas**: O bot celebra automaticamente quando você atinge marcos na meta mensal (50%, 75%, 100%) ou quando sua bike atinge marcos de quilometragem (1.000km, 3.000km, 5.000km).

---

## 🛠️ Personalização (Para Devs)
Se você quiser adaptar o bot para a sua realidade, edite as variáveis no `.env`:

| Variável | Descrição | Padrão |
|:---|:---|:---|
| `CITY` | Cidade para previsão do tempo | `Curitiba,BR` |
| `TEAM_NAME` | Nome do seu grupo de ciclismo | `Equipe Partiu Pedal` |
| `META_MENSAL_KM` | Meta padrão de km mensal | `150` |
| `LOG_LEVEL` | Nível de log (DEBUG, INFO, WARNING, ERROR) | `INFO` |

O horário do alerta proativo pode ser alterado no arquivo `bot_coach.py`, na linha do `schedule.every().friday.at("18:00")`.

> ⏰ **Nota sobre fuso horário:** O agendador usa o fuso do sistema. No Docker, o fuso é configurado pela variável `TZ=America/Sao_Paulo` no `docker-compose.yml`. Ao rodar localmente, o horário segue o fuso do seu sistema operacional.

---

## 📁 Arquitetura do Projeto

```
Coach-Strava/
├── src/
│   ├── bot_coach.py        # Bot principal (Telegram, comandos, interceptadores)
│   ├── ai_engine.py         # Motor de IA (Gemini, memória SQLite, multi-usuário)
│   ├── strava_service.py    # Integração Strava (atividades, bike, gráficos)
│   ├── weather_service.py   # Integração OpenWeather (previsão do tempo)
│   ├── config.py            # Configuração central e logging
│   ├── constantes.py        # Constantes compartilhadas (palavras-chave, tipos)
│   ├── setup_strava_auth.py # Script de autenticação inicial do Strava
│   └── tests/
│       └── test_coach.py    # Testes unitários
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── GUIA_INICIANTES.md
```

---

## 🤝 Contribuições
Sinta-se à vontade para abrir Issues relatando bugs ou Pull Requests com melhorias no código! Toda ajuda para otimizar o projeto é bem-vinda.


## 📜 Licença

Este projeto é open-source. Contribuições são bem-vindas!
