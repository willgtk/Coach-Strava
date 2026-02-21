# Coach-Strava
🚵‍♂️ MTB AI Coach: Seu Treinador de Performance com Inteligência Artificial
Este projeto consiste em um Bot de Telegram proativo projetado para ciclistas de Mountain Bike que buscam constância e evolução (o famoso "ganhar motor"). O script integra dados reais do Strava, previsões meteorológicas e o poder de processamento do Google Gemini para atuar como um professor particular e parceiro de trilha.

🚀 Como o Script Funciona?
O bot opera em três frentes principais:

Análise de Dados (Strava API): O script monitora suas atividades semanais, calculando volume de quilometragem, ganho de elevação e tempo de movimento. Ele também rastreia o desgaste do seu equipamento (como a quilometragem da sua Oggi).

Inteligência Geográfica e Climática: Utilizando a API do OpenWeather, o bot verifica as condições para Curitiba e região, ajustando as sugestões de treino de acordo com a previsão de chuva ou sol.

Cérebro de IA (Google Gemini): Através de um "System Prompt" calibrado, a IA processa os dados brutos e gera feedbacks motivadores, sugestões técnicas para o uso do grupo SRAM GX e metas para os próximos pedais com a Equipe Partiu Pedal.

Memória Persistente: O bot possui um banco de dados em JSON que armazena o histórico de conversas, permitindo que ele aprenda sobre suas dores, trocas de componentes e evolução ao longo do tempo.

📋 Requisitos e Dependências
Para rodar este projeto, você precisará de:

Python 3.10 ou superior.

Tokens de API:

Telegram: Obtido via @BotFather.

Google Gemini: Chave de API gerada no Google AI Studio.

Strava: Client ID e Client Secret obtidos no Strava Developers.

OpenWeather: Chave de API gratuita para dados climáticos.

🛠️ Passo a Passo para Instalação
1. Clonar o Repositório
Bash
git clone https://github.com/SEU_USUARIO/Coach-Strava.git
cd Coach-Strava
2. Instalar Dependências
Bash
pip install requests python-dotenv telebot stravalib schedule
3. Configurar as Variáveis de Ambiente
Crie um arquivo .env na raiz do projeto com a seguinte estrutura:

Plaintext
STRAVA_CLIENT_ID=seu_id
STRAVA_CLIENT_SECRET=seu_secret
STRAVA_TOKEN=token_inicial
STRAVA_REFRESH_TOKEN=refresh_token_inicial
GOOGLE_API_KEY=sua_chave_gemini
TELEGRAM_TOKEN=seu_token_bot
OPENWEATHER_API_KEY=sua_chave_clima
TELEGRAM_CHAT_ID=seu_id_telegram
4. Autorização do Strava
Rode o script de autenticação para garantir que o bot tenha permissão de ler suas atividades e seu perfil (garagem):

Bash
python auth_strava_v2.py
5. Executar o Bot
Bash
python bot_coach.py
🤖 Comandos Disponíveis no Telegram
/start: Inicializa o bot e registra seu Chat ID para mensagens proativas.

/semana: Solicita um resumo manual e imediato do desempenho dos últimos 7 dias, incluindo clima e status da bike.

Conversa Livre: Você pode enviar mensagens como "Troquei os pneus por tubeless hoje" e o bot salvará isso na memória de longo prazo para feedbacks futuros.

📅 Rotina Proativa
O script possui um agendador (schedule) configurado para te chamar todas as sextas-feiras às 18:00. Ele analisará sua semana e sugerirá o melhor plano para o pedal de fim de semana com base no seu cansaço e na previsão do tempo.
