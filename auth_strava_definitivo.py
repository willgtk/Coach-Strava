import os
from dotenv import load_dotenv, set_key
from stravalib.client import Client
from urllib.parse import urlparse, parse_qs

# Garante que o arquivo .env existe
env_path = os.path.join(os.path.dirname(__file__), '.env')
if not os.path.exists(env_path):
    open(env_path, 'w').close()

load_dotenv(env_path)
client_id = os.getenv('STRAVA_CLIENT_ID')
client_secret = os.getenv('STRAVA_CLIENT_SECRET')

if not client_id or not client_secret:
    print("❌ ERRO: Coloque STRAVA_CLIENT_ID e STRAVA_CLIENT_SECRET no seu .env primeiro!")
    exit()

client = Client()
authorize_url = client.authorization_url(
    client_id=client_id, 
    redirect_uri='http://localhost', 
    scope=['activity:read_all']
)

print("\n--- AUTORIZAÇÃO STRAVA DEFINITIVA ---")
print("1. Clique no link e autorize:")
print(authorize_url)
print("\n2. Copie a URL da página de erro (localhost) e cole abaixo.")

callback_url = input("\nURL: ")

try:
    parsed_url = urlparse(callback_url)
    code = parse_qs(parsed_url.query)['code'][0]
    
    token_response = client.exchange_code_for_token(
        client_id=client_id, 
        client_secret=client_secret, 
        code=code
    )
    
    # Salva os tokens permanentemente no arquivo .env
    set_key(env_path, 'STRAVA_TOKEN', token_response['access_token'])
    set_key(env_path, 'STRAVA_REFRESH_TOKEN', token_response['refresh_token'])
    
    print("\n✅ SUCESSO! Access Token e Refresh Token salvos no .env automaticamente.")
    
except Exception as e:
    print(f"\n❌ Erro: {e}")