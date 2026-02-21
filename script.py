import os
from dotenv import load_dotenv
from google import genai # A NOVA biblioteca oficial do Google
from stravalib.client import Client

# 1. Carrega as chaves
load_dotenv()
STRAVA_TOKEN = os.getenv('STRAVA_TOKEN')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# 2. Inicializa a IA (Novo Padrão)
client_ai = genai.Client(api_key=GOOGLE_API_KEY)

# 3. Conecta ao Strava e Filtra por Pedal (Ride)
client_strava = Client(access_token=STRAVA_TOKEN)
athlete = client_strava.get_athlete()

print("Buscando seu último pedal no Strava...")
activities = client_strava.get_activities(limit=10) # Puxa as últimas 10 para garantir
last_ride = None

for activity in activities:
    if activity.type == "Ride" or activity.type == "VirtualRide":
        last_ride = activity
        break

if not last_ride:
    print("Nenhum pedal encontrado nas suas últimas 10 atividades!")
    exit()

# 4. Prepara os dados corrigidos
dados_pedal = {
    "nome": last_ride.name,
    "distancia": f"{float(last_ride.distance) / 1000:.2f} km",
    "elevacao": f"{float(last_ride.total_elevation_gain):.0f} m",
    "tempo": str(last_ride.moving_time),
    "data": last_ride.start_date.strftime("%d/%m/%Y")
}

# 5. O Prompt
prompt = f"""
Você é um treinador de Mountain Bike sarcástico e de alta performance. 
Analise os dados deste pedal de {athlete.firstname}, que pedala uma Oggi Agile Sport (SRAM GX):
Dados: {dados_pedal}

Responda em 3 tópicos curtos:
1. Avaliação de desempenho (O que foi bom?)
2. Sugestão técnica para melhorar o tempo em subidas, considerando tração e o uso correto do grupo SRAM GX.
3. Uma meta desafiadora para o próximo treino em estradão ou trilha.
Seja direto e motivador.
"""

# 6. Execução do Agente (Nova Sintaxe)
print("Enviando dados para o seu Agente de IA... Aguarde.\n")
response = client_ai.models.generate_content(
    model='gemini-2.5-flash',
    contents=prompt,
)

print(f"--- RELATÓRIO DO TREINADOR IA ---\n")
print(response.text)