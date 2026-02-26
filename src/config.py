import os
import logging
from dotenv import load_dotenv

# ==========================================
# CONFIGURAÇÃO E LOGGING
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('CoachStrava')

# Carregar variáveis de ambiente (o .env fica na raiz do projeto, pai de src/)
_project_root = os.path.join(os.path.dirname(__file__), '..')
env_path = os.path.join(_project_root, '.env')
load_dotenv(env_path)

# Variáveis de configuração
STRAVA_CLIENT_ID = os.getenv('STRAVA_CLIENT_ID')
STRAVA_CLIENT_SECRET = os.getenv('STRAVA_CLIENT_SECRET')
STRAVA_TOKEN = os.getenv('STRAVA_TOKEN')
STRAVA_REFRESH_TOKEN = os.getenv('STRAVA_REFRESH_TOKEN')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')

# Cidade configurável (padrão: Curitiba)
CITY = os.getenv('CITY', 'Curitiba,BR')

# Nome da equipe configurável
TEAM_NAME = os.getenv('TEAM_NAME', 'Equipe Partiu Pedal')

# Caminho do arquivo de memória (na raiz do projeto)
FICHEIRO_MEMORIA = os.path.join(_project_root, 'memoria_coach.json')

# Validação de variáveis obrigatórias
required_vars = ['STRAVA_CLIENT_ID', 'GOOGLE_API_KEY', 'TELEGRAM_TOKEN', 'OPENWEATHER_API_KEY']
for var in required_vars:
    if not os.getenv(var):
        raise ValueError(f"Variável de ambiente faltando: {var}")
