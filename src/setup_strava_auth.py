import os
from dotenv import load_dotenv, set_key
from stravalib.client import Client
from urllib.parse import urlparse, parse_qs

# .env fica na raiz do projeto (pai de src/)
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if not os.path.exists(env_path):
    open(env_path, 'w').close()

load_dotenv(env_path)
client_id = os.getenv('STRAVA_CLIENT_ID')
client_secret = os.getenv('STRAVA_CLIENT_SECRET')

if not client_id or not client_secret:
    print("❌ ERROR: Por favor, insira STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET em seu .env primeiro!")
    print("Veja o arquivo .env.example para detalhes da configuração")
    exit()

client = Client()
# AJUSTE 1: Adição do escopo profile:read_all para ler a garagem de bicicletas
authorize_url = client.authorization_url(
    client_id=client_id, 
    redirect_uri='http://localhost', 
    scope=['read', 'activity:read_all', 'profile:read_all']
)

print("\n" + "="*60)
print("🚴 Configuração da autenticação Strava - Coach Strava")
print("="*60)
print("\n1. Clique no link e autorize o accesso no seu Strava:")
# AJUSTE 2: Remoção das chaves duplas para a variável aparecer corretamente no terminal
print(f"\n   {authorize_url}\n")
print("2. Voce será redirecionado para a pagina 'localhost' apresentando erro.")
print("   (Isso é NORMAL! O erro acontece apenas para voce capturar o token.)\n")
print("3. Copie a URL completa.\n")
print("4. Copia a URL abaixo:\n")

callback_url = input("URL: ").strip()

if not callback_url:
    print("❌ Erro: sem URL!")
    exit()

try:
    parsed_url = urlparse(callback_url)
    code = parse_qs(parsed_url.query)['code'][0]
    
    print("\n⏳ Trocando código por tokens...")
    token_response = client.exchange_code_for_token(
        client_id=client_id, 
        client_secret=client_secret, 
        code=code
    )
    
    # Save tokens permanently in the .env file
    set_key(env_path, 'STRAVA_TOKEN', token_response['access_token'])
    set_key(env_path, 'STRAVA_REFRESH_TOKEN', token_response['refresh_token'])
    
    print("\n" + "="*60)
    print("✅ SUCCESSO! Configuração da autenticação feita com louvor!")
    print("="*60)
    print("\n✓ Token de acesso e Refresh Token salvos em: .env")
    print("✓ Você pode agora executar: python bot_coach.py\n")
    
except KeyError:
    print("❌ Erro: A URL fornecida não contém o código de autorização.")
    print("Certifique-se de copiar a URL COMPLETA da página de erro.")
    exit()
except Exception as e:
    print(f"❌ Erro durante a autenticação: {e}")
    print("\nDicas de solução de problemas:")
    print("- Verifique se STRAVA_CLIENT_ID e STRAVA_CLIENT_SECRET estão corretos")
    print("- Tente novamente e copie a URL completa (incluindo http://localhost...)")
    exit()