# 🚵‍♂️ MTB AI Coach: Seu Treinador de Performance com Inteligência Artificial

O **Coach-Strava** é um bot de Telegram proativo projetado para atuar como seu treinador de Mountain Bike e parceiro de trilha. Ele cruza dados reais das suas pedaladas, analisa a previsão do tempo e usa a inteligência do Google Gemini para te manter motivado, consistente e com a manutenção da sua bicicleta em dia. Todas essa informações em seu Telegram! Converse com o bot e avence seu nivel no pedal!

---

> 💡 **Primeira vez mexendo com código ou terminal?**
> Se você não é da área de tecnologia, nunca usou o GitHub ou não tem o costume de usar linhas de comando, preparei um passo a passo focado em você! 
> 👉 **[Clique aqui para ler o Guia Zero a Um: Preparando seu Computador](GUIA_INICIANTES.md)**. Leia este guia rápido antes de seguir com a instalação abaixo para deixar seu VS Code e Git prontos para o uso.

---

## ✨ Funcionalidades

* **📊 Análise de Dados (Strava):** Monitora seu volume de treinos (km, elevação, dias pedalados) e identifica automaticamente a sua **bicicleta principal** cadastrada no Strava para alertar sobre o desgaste acumulado.
* **🌤️ Inteligência Climática (OpenWeather):** Verifica a previsão do tempo local para te avisar se o pedal de fim de semana terá sol, chuva ou muita lama.
* **🧠 Cérebro de IA com Memória (Google Gemini):** Utiliza o modelo *Gemini 2.5 Flash* com memória persistente. O bot lembra das suas conversas anteriores, dores relatadas e manutenções feitas na bike.
* **⏰ Proatividade (Agendador):** Toda sexta-feira às 18:00, o bot te envia proativamente um planejamento para o fim de semana com base no seu cansaço e no clima.
* **🐳 Pronto para Produção (Docker):** Totalmente conteinerizado, garantindo que rode perfeitamente em qualquer sistema operacional sem conflito de bibliotecas.

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
cd Coach-Strav
```

### Passo 2: Configurar as Variáveis de Ambiente
Na raiz do projeto, crie um arquivo chamado .env (você pode se basear no arquivo .env.example, se houver) e preencha com as suas chaves:


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
python setup_strava_auth.py
```

4. O terminal vai gerar um link. Clique nele, faça login no seu Strava e clique em Autorizar.

5. Você será redirecionado para uma página com erro (http://localhost...). Isso é normal! Copie a URL inteira dessa página de erro e cole de volta no seu terminal.

6. Pronto! O script salvará os tokens de acesso direto no seu arquivo .env.


### Passo 4: Criar o arquivo de memória
Crie um arquivo de texto vazio chamado memoria_coach.json na raiz do projeto. Ele será usado pelo Docker para salvar as conversas:

# No Linux/Mac:
```bash
touch memoria_coach.json
```

# No Windows (PowerShell):
```bash
if (!(Test-Path memoria_coach.json)) { Set-Content memoria_coach.json "[]" }
```

### Passo 5: Subir o Bot com Docker
Com as chaves configuradas, deixe a infraestrutura fazer o trabalho pesado. No terminal, rode:
```bash
docker compose up -d --build
```

O Docker vai baixar as dependências, compilar o que for necessário e subir o bot. Para acompanhar se deu tudo certo, veja os logs com docker compose logs -f.

---

### 🤖 Como Usar
Vá até o Telegram, busque pelo seu bot e envie os comandos:

/start: Inicia o bot. Importante: Isso registra o seu Chat ID no sistema, permitindo que o bot te envie mensagens proativas na sexta-feira.

/semana: Força o bot a ler o seu Strava, o clima e o desgaste da sua bicicleta naquele exato momento, gerando um resumo detalhado e uma dica de treino.

Mensagem Livre: Converse naturalmente. Ex: "Hoje o pedal teve muita lama, precisei trocar as pastilhas de freio". O bot vai guardar isso na memória para as próximas conversas.

---

### 🛠️ Personalização (Para Devs)
Se você quiser adaptar o bot para a sua realidade, abra o arquivo bot_coach.py e altere:

Sua Cidade: Na função obter_previsao_tempo(), altere q=Curitiba,BR para a sua cidade.

Sua Equipe: Na variável instrucoes_coach (o "System Prompt"), mude o nome da "Equipe Partiu Pedal" para o seu grupo de ciclismo para respostas mais imersivas.

Horário do Alerta: Na linha do schedule.every().friday.at("18:00"), mude para o dia e hora que preferir.

---

### 🤝 Contribuições
Sinta-se à vontade para abrir Issues relatando bugs ou Pull Requests com melhorias no código! Toda ajuda para otimizar o projeto é bem-vinda.

```bash
***

### O que eu destaco nessa nova versão:
1. **Foco na Fluidez:** O "Passo 3" (Autenticação do Strava) explica exatamente o comportamento do redirecionamento do `localhost`, evitando que o usuário comum ache que algo quebrou.
2. **Aviso do `/start`:** Deixei explícito que o usuário *precisa* dar `/start` no bot primeiro. Como o ID do chat é salvo na hora, se ele não der `/start`, a função de mensagem proativa da sexta-feira falha por não saber para quem mandar.
3. **Sessão de Personalização:** Como o seu código tem raízes na sua rotina (Curitiba, Equipe Partiu Pedal), deixei uma seção específica ensinando o usuário comum a ir no código e alterar para a cidade e equipe dele.

Pode copiar, colar no seu repositório e comitar. A apresentação do projeto agora está no nível da engenharia que aplicamos nele!
```
