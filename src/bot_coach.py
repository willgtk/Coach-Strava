import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv, set_key
import telebot
from google import genai
from google.genai import types
from stravalib.client import Client
import schedule
import time
import threading 

# 1. Carregar as variáveis
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

STRAVA_CLIENT_ID = os.getenv('STRAVA_CLIENT_ID')
STRAVA_CLIENT_SECRET = os.getenv('STRAVA_CLIENT_SECRET')
STRAVA_TOKEN = os.getenv('STRAVA_TOKEN')
STRAVA_REFRESH_TOKEN = os.getenv('STRAVA_REFRESH_TOKEN')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')

# 1.1 Validar variaveis.
required_vars = ['STRAVA_CLIENT_ID', 'GOOGLE_API_KEY', 'TELEGRAM_TOKEN', 'OPENWEATHER_API_KEY']
for var in required_vars:
    if not os.getenv(var):
        raise ValueError(f"Variável de ambiente faltando: {var}")

# 2. Inicializar as APIs
bot = telebot.TeleBot(TELEGRAM_TOKEN)
client_ai = genai.Client(api_key=GOOGLE_API_KEY)
client_strava = Client(access_token=STRAVA_TOKEN)

# ==========================================
# 🧠 NOVO: MÓDULO DE MEMÓRIA PERSISTENTE
# ==========================================
FICHEIRO_MEMORIA = os.path.join(os.path.dirname(__file__), 'memoria_coach.json')

def carregar_memoria():
    if not os.path.exists(FICHEIRO_MEMORIA):
        return []
    try:
        with open(FICHEIRO_MEMORIA, 'r', encoding='utf-8') as f:
            dados = json.load(f)
            
            # Validação de integridade: a API da Google exige que os papéis alternem (user -> model).
            # Se o script tiver falhado a meio de um registo, removemos a mensagem órfã.
            if len(dados) > 0 and dados[-1]['role'] == 'user':
                dados.pop()
                
            historico = []
            for msg in dados:
                historico.append(
                    types.Content(
                        role=msg['role'],
                        parts=[types.Part.from_text(text=msg['text'])]
                    )
                )
            print(f"🧠 Memória restaurada: {len(historico)} interações carregadas.")
            return historico
    except Exception as e:
        print(f"⚠️ Erro ao carregar memória: {e}")
        return []

def guardar_memoria(role, text):
    dados = []
    if os.path.exists(FICHEIRO_MEMORIA):
        try:
            with open(FICHEIRO_MEMORIA, 'r', encoding='utf-8') as f:
                dados = json.load(f)
        except:
            pass
    
    dados.append({"role": role, "text": text})
    
    # Limita o histórico às últimas 40 mensagens para poupar tokens e não exceder a cota diária
    if len(dados) > 40:
        dados = dados[-40:]
        
    with open(FICHEIRO_MEMORIA, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

# ==========================================
# CÉREBRO DA IA
# ==========================================
instrucoes_coach = """
Você é um parceiro e treinador de Mountain Bike focado em condicionamento e qualidade de vida. 
Seu aluno faz parte da Equipe Partiu Pedal e quer ser o melhor ciclista! Você receberá os dados da bicicleta principal dele.
Ele não treina para competições, o objetivo dele é construir uma base aeróbica forte ("ter motor") para estar sempre pronto para qualquer pedal com o grupo, sem sofrer nas subidas.
Analise os dados do Strava, sugira treinos focados em constância e resistência, e seja um motivador amigável.
Sempre responda de forma concisa, direta e com bom humor, ideal para leitura no Telegram.
"""

# Inicializa o chat já com o histórico injetado
chat_session = client_ai.chats.create(
    model='gemini-2.5-flash',    
    config=types.GenerateContentConfig(system_instruction=instrucoes_coach),
    history=carregar_memoria()
)

# ==========================================
# FUNÇÕES DE RECOLHA DE DADOS (STRAVA & CLIMA)
# ==========================================
def renovar_token_strava():
    print("🔄 A tentar renovar o token do Strava...")
    url = "https://www.strava.com/oauth/token"
    payload = {
        'client_id': STRAVA_CLIENT_ID,
        'client_secret': STRAVA_CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': os.getenv('STRAVA_REFRESH_TOKEN')
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        dados = response.json()
        set_key(env_path, 'STRAVA_TOKEN', dados['access_token'])
        set_key(env_path, 'STRAVA_REFRESH_TOKEN', dados['refresh_token'])
        os.environ['STRAVA_TOKEN'] = dados['access_token']
        os.environ['STRAVA_REFRESH_TOKEN'] = dados['refresh_token']
        client_strava.access_token = dados['access_token']
        return True
    return False

def obter_resumo_semana():
    uma_semana_atras = datetime.now() - timedelta(days=7)
    try:
        atividades = client_strava.get_activities(after=uma_semana_atras)
        atividades_lista = list(atividades)
    except Exception as e:
        if "401" in str(e) or "unauthorized" in str(e).lower():
            if renovar_token_strava():
                atividades = client_strava.get_activities(after=uma_semana_atras)
                atividades_lista = list(atividades)
            else:
                return "Erro crítico na renovação de token."
        else:
            return f"Erro desconhecido: {e}"

    total_km = total_elevacao = qtd_pedais = 0
    for act in atividades_lista:
        if act.type in ["Ride", "VirtualRide", "MountainBikeRide"]:
            total_km += float(act.distance) / 1000
            total_elevacao += float(act.total_elevation_gain)
            qtd_pedais += 1
            
    if qtd_pedais == 0:
        return "Nenhum pedal registado nos últimos 7 dias."
    return f"{qtd_pedais} pedais, {total_km:.1f} km rodados, {total_elevacao:.0f}m de elevação."

def obter_previsao_tempo():
    if not OPENWEATHER_API_KEY:
        return "Clima: API Key não configurada."
    try:
        url = f"http://api.openweathermap.org/data/2.5/forecast?q=Curitiba,BR&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt"
        res = requests.get(url).json()
        previsoes = res['list'][:8] # Próximas 24h
        resumo = ""
        for p in previsoes[::2]: # Pula de 6 em 6 horas
            resumo += f" {p['dt_txt'][11:16]}h: {p['main']['temp']:.0f}°C, {p['weather'][0]['description']} |"
        return resumo
    except Exception as e:
        return f"Erro ao buscar previsão: {e}"

def obter_status_bike():
    try:
        athlete = client_strava.get_athlete()
        if not athlete.bikes:
            return "Nenhuma bicicleta registada no Strava."
            
        bike_principal = None
        for bike in athlete.bikes:
            if bike.primary:
                bike_principal = bike
                break
                
        if not bike_principal:
            bike_principal = athlete.bikes[0]
            
        distancia_km = float(bike_principal.distance) / 1000
        return f"A bicicleta '{bike_principal.name}' tem {distancia_km:.1f} km acumulados no Strava."
    except Exception as e:
        return "Erro ao verificar desgaste da bicicleta."

# ==========================================
# 🚀 MOTOR PROATIVO: O SUPER PROMPT
# ==========================================
def mensagem_planeamento_fim_de_semana():
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not chat_id: return

    print("A analisar dados completos para mensagem proativa...")
    dados_treino = obter_resumo_semana()
    clima = obter_previsao_tempo()
    bike = obter_status_bike()
    
    prompt = f"""
    Inicia a conversa de forma proativa. Hoje é sexta-feira. 
    Cruza estes 3 dados para criar a tua mensagem:
    1. Resumo da Semana: {dados_treino}
    2. Clima em Curitiba (Próx 24h): {clima}
    3. Status da Bicicleta: {bike}
    
    Diretrizes:
    - Sugere um treino para o fim de semana com a Equipe Partiu Pedal adequado ao clima (se chover, avisa sobre a lama).
    - Avalia se o volume da semana foi bom para manter o "motor".
    - Se a quilometragem da bicicleta for alta, deixa um alerta amigável sobre lubrificar a relação ou verificar o desgaste.
    Sê um verdadeiro parceiro de treino!
    """
    
    guardar_memoria("user", prompt)
    resposta_ia = chat_session.send_message(prompt)
    guardar_memoria("model", resposta_ia.text)
    
    bot.send_message(chat_id, resposta_ia.text)

def agendador_em_segundo_plano():
    while True:
        schedule.run_pending()
        time.sleep(1)

# Agendamento: Sexta-feira às 18:00
schedule.every().friday.at("18:00").do(mensagem_planeamento_fim_de_semana)

threading.Thread(target=agendador_em_segundo_plano, daemon=True).start()

# ==========================================
# ROTAS DO TELEGRAM
# ==========================================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    chat_id = str(message.chat.id)
    set_key(env_path, 'TELEGRAM_CHAT_ID', chat_id)
    os.environ['TELEGRAM_CHAT_ID'] = chat_id
    bot.reply_to(message, "Coach Inteligente ativado! 🚵‍♂️\nJá registei o teu contato. Agora monitorizo o teu Strava, o desgaste da tua bicicleta e o clima de Curitiba! SIMBOOOORA!")

@bot.message_handler(commands=['semana'])
def analisar_semana(message):
    bot.reply_to(message, "A procurar dados de treino, clima e equipamento... ⏳")
    prompt = f"O atleta pediu um resumo manual agora. Treino: {obter_resumo_semana()}. Clima: {obter_previsao_tempo()}. Bike: {obter_status_bike()}."
    
    guardar_memoria("user", prompt)
    resposta_ia = chat_session.send_message(prompt)
    guardar_memoria("model", resposta_ia.text)
    
    bot.reply_to(message, resposta_ia.text)

@bot.message_handler(commands=['clima'])
def comando_clima(message):
    bot.reply_to(message, "A olhar para o céu de Curitiba... ☁️⏳")
    clima_atual = obter_previsao_tempo()
    prompt = f"O atleta pediu a previsão do tempo. Responda de forma parceira e motivadora usando estes dados de Curitiba: {clima_atual}"
    
    guardar_memoria("user", "/clima")
    resposta_ia = chat_session.send_message(prompt)
    guardar_memoria("model", resposta_ia.text)
    
    bot.reply_to(message, resposta_ia.text)

@bot.message_handler(func=lambda message: True)
def conversa_livre(message):
    bot.send_chat_action(message.chat.id, 'typing')
    texto_usuario = message.text.lower()
    
    # 🕵️‍♂️ INTERCEPTADOR: Se o usuário falar de clima na conversa livre, injetamos os dados
    palavras_clima = ['clima', 'tempo', 'temperatura', 'chover', 'chuva', 'sol', 'frio', 'calor']
    if any(palavra in texto_usuario for palavra in palavras_clima):
        clima_atual = obter_previsao_tempo()
        # Colocamos o dado como uma tag de sistema para a IA ler, mas sem o usuário ver
        prompt_final = f"{message.text}\n\n[DADOS DE SISTEMA PARA SUA RESPOSTA: {clima_atual}]"
    else:
        prompt_final = message.text
        
    guardar_memoria("user", message.text)
    resposta_ia = chat_session.send_message(prompt_final)
    guardar_memoria("model", resposta_ia.text)
    
    bot.reply_to(message, resposta_ia.text)

print("🤖 Coach 3.0 (Memória Persistente + Clima Interativo + Mecânica) a correr no Telegram!")
bot.infinity_polling()