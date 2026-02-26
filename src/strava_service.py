import os
import requests
from datetime import datetime, timedelta
from dotenv import set_key
from stravalib.client import Client

from config import (
    STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_TOKEN,
    env_path, logger
)

# ==========================================
# SERVIÇO DO STRAVA
# ==========================================
client_strava = Client(access_token=STRAVA_TOKEN)


def renovar_token_strava():
    """Renova o token de acesso do Strava usando o refresh token."""
    logger.info("Tentando renovar o token do Strava...")
    url = "https://www.strava.com/oauth/token"
    payload = {
        'client_id': STRAVA_CLIENT_ID,
        'client_secret': STRAVA_CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': os.getenv('STRAVA_REFRESH_TOKEN')
    }
    try:
        response = requests.post(url, data=payload, timeout=15)
        if response.status_code == 200:
            dados = response.json()
            set_key(env_path, 'STRAVA_TOKEN', dados['access_token'])
            set_key(env_path, 'STRAVA_REFRESH_TOKEN', dados['refresh_token'])
            os.environ['STRAVA_TOKEN'] = dados['access_token']
            os.environ['STRAVA_REFRESH_TOKEN'] = dados['refresh_token']
            client_strava.access_token = dados['access_token']
            logger.info("Token do Strava renovado com sucesso.")
            return True
        else:
            logger.error(f"Falha ao renovar token. Status: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Erro ao renovar token do Strava: {e}")
        return False


def _obter_atividades(after):
    """Busca atividades do Strava, renovando token se necessário."""
    try:
        atividades = client_strava.get_activities(after=after)
        return list(atividades)
    except Exception as e:
        if "401" in str(e) or "unauthorized" in str(e).lower():
            if renovar_token_strava():
                atividades = client_strava.get_activities(after=after)
                return list(atividades)
            else:
                raise ConnectionError("Erro crítico na renovação de token do Strava.")
        raise


def obter_resumo_semana():
    """Retorna um resumo textual dos pedais dos últimos 7 dias."""
    uma_semana_atras = datetime.now() - timedelta(days=7)
    try:
        atividades_lista = _obter_atividades(after=uma_semana_atras)
    except Exception as e:
        logger.error(f"Erro ao buscar resumo semanal: {e}")
        return f"Erro ao buscar dados do Strava: {e}"

    total_km = total_elevacao = qtd_pedais = 0
    for act in atividades_lista:
        if act.type in ["Ride", "VirtualRide", "MountainBikeRide"]:
            total_km += float(act.distance) / 1000
            total_elevacao += float(act.total_elevation_gain)
            qtd_pedais += 1

    if qtd_pedais == 0:
        return "Nenhum pedal registado nos últimos 7 dias."
    return f"{qtd_pedais} pedais, {total_km:.1f} km rodados, {total_elevacao:.0f}m de elevação."


def obter_ultimo_pedal():
    """Retorna dados detalhados do pedal mais recente."""
    um_mes_atras = datetime.now() - timedelta(days=30)
    try:
        atividades_lista = _obter_atividades(after=um_mes_atras)
    except Exception as e:
        logger.error(f"Erro ao buscar último pedal: {e}")
        return "Erro ao buscar último pedal no Strava."

    # Filtra apenas pedais (Ride, VirtualRide, MountainBikeRide)
    pedais = [act for act in atividades_lista
              if act.type in ["Ride", "VirtualRide", "MountainBikeRide"]]

    if not pedais:
        return "Nenhum pedal encontrado nos últimos 30 dias."

    # A API não garante a ordem quando usamos 'after', então ordenamos explicitamente
    pedais.sort(key=lambda x: x.start_date_local, reverse=True)
    ultimo = pedais[0]
    distancia_km = float(ultimo.distance) / 1000
    elevacao = float(ultimo.total_elevation_gain)
    # stravalib retorna Duration, não timedelta — usar int() para obter segundos
    tempo_seg = int(ultimo.moving_time)
    tempo_min = tempo_seg / 60
    velocidade_media = float(ultimo.average_speed) * 3.6  # m/s para km/h
    data_pedal = ultimo.start_date_local.strftime('%d/%m/%Y às %H:%M')

    return (
        f"Último pedal ({data_pedal}): "
        f"{distancia_km:.1f} km, {elevacao:.0f}m de elevação, "
        f"{velocidade_media:.1f} km/h de média, {tempo_min:.0f} min pedalando. "
        f"Tipo: {ultimo.type}."
    )


def obter_status_bike():
    """Retorna informações da bicicleta principal do atleta."""
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
        return (
            f"A bicicleta '{bike_principal.name}' tem {distancia_km:.1f} km acumulados no Strava.",
            distancia_km,
            bike_principal.name
        )
    except Exception as e:
        logger.error(f"Erro ao verificar status da bicicleta: {e}")
        return "Erro ao verificar desgaste da bicicleta.", 0, "Desconhecida"


def obter_status_bike_texto():
    """Retorna apenas o texto do status da bike (compatibilidade)."""
    resultado = obter_status_bike()
    if isinstance(resultado, tuple):
        return resultado[0]
    return resultado
