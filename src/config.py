"""
Módulo de configuração central do Coach-Strava.
Carrega variáveis de ambiente, configura logging e valida dependências.
"""
from __future__ import annotations
import os
import logging
from dotenv import load_dotenv

# ==========================================
# CONFIGURAÇÃO E LOGGING
# ==========================================

# Carregar variáveis de ambiente ANTES de ler LOG_LEVEL (o .env fica na raiz do projeto, pai de src/)
_project_root: str = os.path.join(os.path.dirname(__file__), '..')
env_path: str = os.path.join(_project_root, '.env')
load_dotenv(env_path)

_log_level_str: str = os.getenv('LOG_LEVEL', 'INFO').upper()
_log_level: int = getattr(logging, _log_level_str, logging.INFO)

logging.basicConfig(
    level=_log_level,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger: logging.Logger = logging.getLogger('CoachStrava')

# --- Variáveis de API ---
STRAVA_CLIENT_ID: str | None = os.getenv('STRAVA_CLIENT_ID')
STRAVA_CLIENT_SECRET: str | None = os.getenv('STRAVA_CLIENT_SECRET')
STRAVA_TOKEN: str | None = os.getenv('STRAVA_TOKEN')
STRAVA_REFRESH_TOKEN: str | None = os.getenv('STRAVA_REFRESH_TOKEN')
GOOGLE_API_KEY: str | None = os.getenv('GOOGLE_API_KEY')
TELEGRAM_TOKEN: str | None = os.getenv('TELEGRAM_TOKEN')
OPENWEATHER_API_KEY: str | None = os.getenv('OPENWEATHER_API_KEY')

# --- Configurações personalizáveis ---
CITY: str = os.getenv('CITY', 'Curitiba,BR')
TEAM_NAME: str = os.getenv('TEAM_NAME', 'Equipe Partiu Pedal')

# Meta de km mensal configurável (padrão: 150km)
try:
    META_MENSAL_KM: float = float(os.getenv('META_MENSAL_KM', '150'))
except ValueError:
    logger.warning("Valor inválido para META_MENSAL_KM. Usando o padrão de 150km.")
    META_MENSAL_KM = 150.0

# Caminho do banco de dados SQLite (no diretório data/)
_data_dir: str = os.path.join(_project_root, 'data')
os.makedirs(_data_dir, exist_ok=True)
DB_PATH: str = os.path.join(_data_dir, 'coach_database.db')

# ==========================================
# VALIDAÇÃO DE VARIÁVEIS OBRIGATÓRIAS
# ==========================================
required_vars: list[str] = [
    'STRAVA_CLIENT_ID',
    'STRAVA_CLIENT_SECRET',
    'GOOGLE_API_KEY',
    'TELEGRAM_TOKEN',
    'OPENWEATHER_API_KEY'
]
for var in required_vars:
    if not os.getenv(var):
        raise ValueError(f"Variável de ambiente faltando: {var}")
