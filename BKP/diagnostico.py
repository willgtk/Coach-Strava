import os
import requests
from dotenv import load_dotenv

# Carrega a sua chave
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)
chave = os.getenv('GOOGLE_API_KEY')

print("Consultando os servidores do Google...\n")
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={chave}"
resposta = requests.get(url)

if resposta.status_code == 200:
    dados = resposta.json()
    print("✅ MODELOS DISPONÍVEIS PARA A SUA CHAVE:\n")
    for modelo in dados.get('models', []):
        # Mostra apenas os modelos que servem para o nosso bot (generateContent)
        if 'generateContent' in modelo.get('supportedGenerationMethods', []):
            # Limpa o texto para mostrar apenas o nome exato
            nome_exato = modelo['name'].replace('models/', '')
            print(f"👉 {nome_exato}")
else:
    print(f"❌ Erro ao consultar a API: {resposta.text}")