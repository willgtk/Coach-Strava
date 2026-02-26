import os
import requests
from datetime import datetime, timedelta
from dotenv import set_key
from stravalib.client import Client

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from config import (
    STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_TOKEN,
    env_path, logger
)

# ==========================================
# SERVIÇO DO STRAVA
# ==========================================
client_strava = Client(access_token=STRAVA_TOKEN)


def gerar_grafico_progresso(dias_historico=30):
    """
    Gera um gráfico do volume de treinos (km) por dia nos últimos `dias_historico` dias.
    Salva temporariamente em 'grafico_progresso.png' e retorna o caminho.
    """
    data_inicio = datetime.now() - timedelta(days=dias_historico)
    
    try:
        atividades = _obter_atividades(after=data_inicio)
    except Exception as e:
        logger.error(f"Erro ao buscar atividades para o gráfico: {e}")
        return None

    # Filtrar apenas pedais
    pedais = [act for act in atividades if act.type in ["Ride", "VirtualRide", "MountainBikeRide"]]
    
    if not pedais:
        return None

    # Montar DataFrame
    dados = []
    for p in pedais:
        # Pega a data ignorando a hora (apenas a data do pedal)
        data_str = p.start_date_local.strftime('%Y-%m-%d')
        distancia_km = float(p.distance) / 1000
        dados.append({'data': data_str, 'km': distancia_km})

    df = pd.DataFrame(dados)
    
    # Se houver mais de um pedal no mesmo dia, soma os km
    df = df.groupby('data')['km'].sum().reset_index()
    
    # Converter string de data para objeto datetime
    df['data'] = pd.to_datetime(df['data'])
    
    # Criar um DataFrame com todos os dias do período (para dias sem pedal aparecerem como zero)
    todos_os_dias = pd.date_range(start=data_inicio.date(), end=datetime.now().date())
    df_completo = pd.DataFrame({'data': todos_os_dias})
    
    # Fazer um merge para juntar as datas
    df_completo = pd.merge(df_completo, df, on='data', how='left')
    df_completo['km'] = df_completo['km'].fillna(0)  # Preencher dias sem pedal com 0

    # Configuração do Gráfico usando estilo mais moderno
    plt.style.use('dark_background' if plt.style.available and 'dark_background' in plt.style.available else 'default')
    fig, ax = plt.subplots(figsize=(10, 5))
    
    # Plotar as barras
    barras = ax.bar(df_completo['data'], df_completo['km'], color='#fc4c02', alpha=0.8, edgecolor='white', width=0.8)

    # Formatação do eixo X
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    plt.xticks(rotation=45)
    
    # Títulos e labels
    plt.title(f'Volume de Treinos (Últimos {dias_historico} dias)', fontsize=14, pad=15, color='white')
    plt.ylabel('Distância (km)', fontsize=12, color='white')
    plt.xlabel('Data', fontsize=12, color='white')
    
    # Grid e remoção das bordas cima/direita
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#aaaaaa')
    ax.spines['bottom'].set_color('#aaaaaa')
    ax.tick_params(colors='#aaaaaa')

    # Adicionar o valor em km no topo de cada barra que não for zero
    for bar in barras:
        altura = bar.get_height()
        if altura > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, altura + 0.5, f'{altura:.1f}', 
                    ha='center', va='bottom', fontsize=9, color='white')

    plt.tight_layout()
    
    caminho_arquivo = 'grafico_progresso.png'
    plt.savefig(caminho_arquivo, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    
    return caminho_arquivo
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


def obter_progresso_mensal(meta_km):
    """Calcula o total de km rodados no mês atual e compara com a meta."""
    hoje = datetime.now()
    primeiro_dia_mes = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    try:
        atividades_lista = _obter_atividades(after=primeiro_dia_mes)
    except Exception as e:
        logger.error(f"Erro ao buscar atividades do mês: {e}")
        return f"Erro ao buscar dados do mês no Strava."

    total_km = 0
    for act in atividades_lista:
        if act.type in ["Ride", "VirtualRide", "MountainBikeRide"]:
            total_km += float(act.distance) / 1000

    percentual = (total_km / meta_km) * 100 if meta_km > 0 else 0
    
    return {
        "mes_atual": hoje.strftime('%m/%Y'),
        "total_km": total_km,
        "meta_km": meta_km,
        "percentual_concluido": percentual,
        "texto": f"Progresso do mês ({hoje.strftime('%m/%Y')}): {total_km:.1f} km de {meta_km:.0f} km ({percentual:.1f}%)."
    }


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
