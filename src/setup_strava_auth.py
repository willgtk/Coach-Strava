"""
Script de autenticação inicial do Strava.
Gera tokens de acesso e refresh, salvando-os diretamente no arquivo .env.
"""
from __future__ import annotations

import os
from dotenv import load_dotenv, set_key
from stravalib.client import Client
from urllib.parse import urlparse, parse_qs

# .env fica na raiz do projeto (pai de src/)
env_path: str = os.path.join(os.path.dirname(__file__), '..', '.env')
if not os.path.exists(env_path):
    open(env_path, 'w').close()

load_dotenv(env_path)
client_id: str | None = os.getenv('STRAVA_CLIENT_ID')
client_secret: str | None = os.getenv('STRAVA_CLIENT_SECRET')

if not client_id or not client_secret:
    print("❌ ERRO: Insira STRAVA_CLIENT_ID e STRAVA_CLIENT_SECRET no seu .env primeiro!")
    print("Veja o arquivo .env.example para detalhes da configuração.")
    exit()

client = Client()
# Escopo profile:read_all necessário para ler a garagem de bicicletas
authorize_url: str = client.authorization_url(
    client_id=client_id,
    redirect_uri='http://localhost',
    scope=['read', 'activity:read_all', 'profile:read_all']
)

print("\n" + "=" * 60)
print("🚴 Configuração da Autenticação Strava — Coach Strava")
print("=" * 60)
print("\n1. Clique no link abaixo e autorize o acesso no seu Strava:")
print(f"\n   {authorize_url}\n")
print("2. Você será redirecionado para uma página 'localhost' com erro.")
print("   (Isso é normal! O erro serve apenas para capturar o token.)\n")
print("3. Copie a URL completa da barra de endereço do navegador.\n")
print("4. Cole a URL abaixo:\n")

callback_url: str = input("URL: ").strip()

if not callback_url:
    print("❌ Erro: nenhuma URL fornecida!")
    exit()

try:
    parsed_url = urlparse(callback_url)
    code: str = parse_qs(parsed_url.query)['code'][0]

    print("\n⏳ Trocando código por tokens de acesso...")
    token_response = client.exchange_code_for_token(
        client_id=client_id,
        client_secret=client_secret,
        code=code
    )

    # Salva os tokens permanentemente no .env
    set_key(env_path, 'STRAVA_TOKEN', token_response['access_token'])
    set_key(env_path, 'STRAVA_REFRESH_TOKEN', token_response['refresh_token'])

    print("\n" + "=" * 60)
    print("✅ SUCESSO! Autenticação configurada com sucesso!")
    print("=" * 60)
    print("\n✓ Token de acesso e Refresh Token salvos em: .env")
    print("✓ Agora você pode executar: python src/bot_coach.py\n")

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