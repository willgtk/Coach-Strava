import os
from dotenv import load_dotenv
from stravalib.client import Client
from urllib.parse import urlparse, parse_qs

# Carrega as credenciais
load_dotenv()
client_id = os.getenv('STRAVA_CLIENT_ID')
client_secret = os.getenv('STRAVA_CLIENT_SECRET')

client = Client()

# 1. Gera o link de autorização pedindo acesso TOTAL às atividades
authorize_url = client.authorization_url(
    client_id=client_id, 
    redirect_uri='http://localhost', 
    scope=['activity:read_all']
)

print("\n--- AUTORIZAÇÃO STRAVA ---")
print("1. Clique neste link e faça login (se necessário):")
print(authorize_url)
print("\n2. Clique em 'Autorizar'. O navegador vai tentar carregar uma página 'localhost' e vai dar erro (Isso é normal!).")
print("3. Copie a URL INTEIRA dessa página de erro e cole aqui embaixo.")

# 2. Recebe a URL que o usuário copiou
callback_url = input("\nCole a URL do localhost aqui: ")

try:
    # 3. Extrai o código de autorização da URL
    parsed_url = urlparse(callback_url)
    code = parse_qs(parsed_url.query)['code'][0]
    
    # 4. Troca o código pelo Token final
    token_response = client.exchange_code_for_token(
        client_id=client_id, 
        client_secret=client_secret, 
        code=code
    )
    
    print("\n✅ SUCESSO! Substitua a linha STRAVA_TOKEN no seu arquivo .env por:")
    print(f"STRAVA_TOKEN={token_response['access_token']}")
    
except Exception as e:
    print(f"\n❌ Erro ao gerar o token. Verifique se copiou a URL corretamente. Detalhes: {e}")