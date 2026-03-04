"""
Serviço de integração com a API do Strava.
Gerencia autenticação, atividades, status da bike e geração de gráficos.
"""
from __future__ import annotations
import os
import tempfile
from typing import Optional
from datetime import datetime, timedelta

import requests
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Backend não-interativo para evitar erros em servidores
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from dotenv import set_key
from stravalib.client import Client
from cachetools import TTLCache
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import (
    STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_TOKEN,
    env_path, logger
)
from constantes import TIPOS_PEDAL

# ==========================================
# SERVIÇO DO STRAVA
# ==========================================
client_strava = Client(access_token=STRAVA_TOKEN)

# Cache de atividades com TTL de 5 minutos (evita chamadas repetidas à API)
_strava_cache: TTLCache = TTLCache(maxsize=20, ttl=300)


def renovar_token_strava() -> bool:
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


def _obter_atividades(after: datetime) -> list:
    """Busca atividades do Strava com cache e renovação automática de token."""
    cache_key = f"atividades_{after.strftime('%Y%m%d%H')}"

    if cache_key in _strava_cache:
        logger.debug(f"Cache hit para atividades: {cache_key}")
        return _strava_cache[cache_key]

    try:
        atividades = list(client_strava.get_activities(after=after))
        _strava_cache[cache_key] = atividades
        return atividades
    except Exception as e:
        if "401" in str(e) or "unauthorized" in str(e).lower():
            if renovar_token_strava():
                atividades = list(client_strava.get_activities(after=after))
                _strava_cache[cache_key] = atividades
                return atividades
            else:
                raise ConnectionError("Erro crítico na renovação de token do Strava.")
        raise


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.exceptions.Timeout, ConnectionError)),
    reraise=True
)
def _obter_atividades_com_retry(after: datetime) -> list:
    """Wrapper com retry automático para chamadas ao Strava."""
    return _obter_atividades(after)


def _filtrar_pedais(atividades: list) -> list:
    """Filtra apenas atividades do tipo pedal."""
    return [act for act in atividades if act.type in TIPOS_PEDAL]


# ==========================================
# FUNÇÕES PÚBLICAS
# ==========================================
def obter_progresso_mensal(meta_km: float) -> dict | str:
    """Calcula o total de km rodados no mês atual e compara com a meta."""
    hoje = datetime.now()
    primeiro_dia_mes = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    try:
        atividades_lista = _obter_atividades_com_retry(after=primeiro_dia_mes)
    except Exception as e:
        logger.error(f"Erro ao buscar atividades do mês: {e}")
        return "Erro ao buscar dados do mês no Strava."

    pedais = _filtrar_pedais(atividades_lista)
    total_km = sum(float(act.distance) / 1000 for act in pedais)
    percentual = (total_km / meta_km) * 100 if meta_km > 0 else 0

    return {
        "mes_atual": hoje.strftime('%m/%Y'),
        "total_km": total_km,
        "meta_km": meta_km,
        "percentual_concluido": percentual,
        "texto": f"Progresso do mês ({hoje.strftime('%m/%Y')}): {total_km:.1f} km de {meta_km:.0f} km ({percentual:.1f}%)."
    }


def obter_resumo_semana() -> str:
    """Retorna um resumo textual dos pedais dos últimos 7 dias."""
    uma_semana_atras = datetime.now() - timedelta(days=7)
    try:
        atividades_lista = _obter_atividades_com_retry(after=uma_semana_atras)
    except Exception as e:
        logger.error(f"Erro ao buscar resumo semanal: {e}")
        return f"Erro ao buscar dados do Strava: {e}"

    pedais = _filtrar_pedais(atividades_lista)
    total_km = sum(float(act.distance) / 1000 for act in pedais)
    total_elevacao = sum(float(act.total_elevation_gain) for act in pedais)
    qtd_pedais = len(pedais)

    if qtd_pedais == 0:
        return "Nenhum pedal registado nos últimos 7 dias."
    return f"{qtd_pedais} pedais, {total_km:.1f} km rodados, {total_elevacao:.0f}m de elevação."


def obter_ultimo_pedal() -> str:
    """Retorna dados detalhados do pedal mais recente."""
    um_mes_atras = datetime.now() - timedelta(days=30)
    try:
        atividades_lista = _obter_atividades_com_retry(after=um_mes_atras)
    except Exception as e:
        logger.error(f"Erro ao buscar último pedal: {e}")
        return "Erro ao buscar último pedal no Strava."

    pedais = _filtrar_pedais(atividades_lista)

    if not pedais:
        return "Nenhum pedal encontrado nos últimos 30 dias."

    # Ordena pelo mais recente primeiro
    pedais.sort(key=lambda x: x.start_date_local, reverse=True)
    ultimo = pedais[0]
    distancia_km = float(ultimo.distance) / 1000
    elevacao = float(ultimo.total_elevation_gain)
    tempo_seg = int(ultimo.moving_time)
    tempo_min = tempo_seg / 60
    velocidade_media = float(ultimo.average_speed) * 3.6  # m/s -> km/h
    data_pedal = ultimo.start_date_local.strftime('%d/%m/%Y às %H:%M')

    return (
        f"Último pedal ({data_pedal}): "
        f"{distancia_km:.1f} km, {elevacao:.0f}m de elevação, "
        f"{velocidade_media:.1f} km/h de média, {tempo_min:.0f} min pedalando. "
        f"Tipo: {ultimo.type}."
    )


def obter_status_bike() -> tuple[str, float, str]:
    """Retorna informações da bicicleta principal do atleta."""
    try:
        athlete = client_strava.get_athlete()
        if not athlete.bikes:
            return ("Nenhuma bicicleta registada no Strava.", 0.0, "Desconhecida")

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
        return ("Erro ao verificar desgaste da bicicleta.", 0.0, "Desconhecida")


def obter_status_bike_texto() -> str:
    """Retorna apenas o texto do status da bike."""
    resultado = obter_status_bike()
    return resultado[0]


def obter_historico_mensal(meses: int = 3) -> str:
    """Retorna comparativo de quilometragem dos últimos N meses para evolução."""
    hoje = datetime.now()
    resumos: list[str] = []

    for i in range(meses):
        # Calcula o primeiro e último dia de cada mês
        if i == 0:
            primeiro_dia = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            ultimo_dia = hoje
        else:
            # Volta i meses
            mes_alvo = hoje.month - i
            ano_alvo = hoje.year
            while mes_alvo <= 0:
                mes_alvo += 12
                ano_alvo -= 1
            primeiro_dia = hoje.replace(year=ano_alvo, month=mes_alvo, day=1, hour=0, minute=0, second=0, microsecond=0)

            # Último dia do mês
            proximo_mes = mes_alvo + 1
            proximo_ano = ano_alvo
            if proximo_mes > 12:
                proximo_mes = 1
                proximo_ano += 1
            ultimo_dia = datetime(proximo_ano, proximo_mes, 1) - timedelta(seconds=1)

        try:
            atividades = _obter_atividades_com_retry(after=primeiro_dia)
            pedais = [act for act in _filtrar_pedais(atividades)
                      if act.start_date_local <= ultimo_dia]
            total_km = sum(float(act.distance) / 1000 for act in pedais)
            qtd = len(pedais)
            nome_mes = primeiro_dia.strftime('%B/%Y').capitalize()
            resumos.append(f"{nome_mes}: {total_km:.1f} km em {qtd} pedais")
        except Exception as e:
            logger.error(f"Erro ao buscar histórico do mês {i}: {e}")
            nome_mes = primeiro_dia.strftime('%B/%Y').capitalize()
            resumos.append(f"{nome_mes}: erro ao buscar dados")

    # Calcular evolução entre meses
    resultado = "📊 Evolução Mensal:\n" + "\n".join(f"  • {r}" for r in resumos)
    return resultado


def gerar_grafico_progresso(dias_historico: int = 30) -> Optional[str]:
    """
    Gera um gráfico do volume de treinos (km) por dia nos últimos N dias.
    Salva em arquivo temporário e retorna o caminho.
    """
    data_inicio = datetime.now() - timedelta(days=dias_historico)

    try:
        atividades = _obter_atividades_com_retry(after=data_inicio)
    except Exception as e:
        logger.error(f"Erro ao buscar atividades para o gráfico: {e}")
        return None

    pedais = _filtrar_pedais(atividades)

    if not pedais:
        return None

    # Montar DataFrame
    dados = []
    for p in pedais:
        data_str = p.start_date_local.strftime('%Y-%m-%d')
        distancia_km = float(p.distance) / 1000
        dados.append({'data': data_str, 'km': distancia_km})

    df = pd.DataFrame(dados)
    df = df.groupby('data')['km'].sum().reset_index()
    df['data'] = pd.to_datetime(df['data'])

    # DataFrame completo com todos os dias do período
    todos_os_dias = pd.date_range(start=data_inicio.date(), end=datetime.now().date())
    df_completo = pd.DataFrame({'data': todos_os_dias})
    df_completo = pd.merge(df_completo, df, on='data', how='left')
    df_completo['km'] = df_completo['km'].fillna(0)

    # Gráfico com estilo escuro
    plt.style.use('dark_background' if 'dark_background' in plt.style.available else 'default')
    fig, ax = plt.subplots(figsize=(10, 5))

    barras = ax.bar(df_completo['data'], df_completo['km'], color='#fc4c02', alpha=0.8, edgecolor='white', width=0.8)

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    plt.xticks(rotation=45)
    plt.title(f'Volume de Treinos (Últimos {dias_historico} dias)', fontsize=14, pad=15, color='white')
    plt.ylabel('Distância (km)', fontsize=12, color='white')
    plt.xlabel('Data', fontsize=12, color='white')

    ax.grid(axis='y', linestyle='--', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#aaaaaa')
    ax.spines['bottom'].set_color('#aaaaaa')
    ax.tick_params(colors='#aaaaaa')

    for bar in barras:
        altura = bar.get_height()
        if altura > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, altura + 0.5, f'{altura:.1f}',
                    ha='center', va='bottom', fontsize=9, color='white')

    plt.tight_layout()

    # Salva em arquivo temporário seguro
    tmp_file = tempfile.NamedTemporaryFile(suffix='.png', prefix='grafico_', delete=False)
    caminho_arquivo = tmp_file.name
    tmp_file.close()

    plt.savefig(caminho_arquivo, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()

    return caminho_arquivo
