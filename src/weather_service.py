"""
Serviço de previsão do tempo via OpenWeather API.
"""
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import OPENWEATHER_API_KEY, CITY, logger


# ==========================================
# SERVIÇO DE CLIMA (OPENWEATHER)
# ==========================================
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(requests.exceptions.Timeout),
    reraise=True
)
def obter_previsao_tempo() -> str:
    """Retorna previsão do tempo das próximas 24h para a cidade configurada."""
    if not OPENWEATHER_API_KEY:
        return "Clima: API Key não configurada."
    try:
        url = (
            f"http://api.openweathermap.org/data/2.5/forecast"
            f"?q={CITY}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt"
        )
        res = requests.get(url, timeout=10).json()

        if res.get('cod') != '200':
            logger.error(f"Erro na API do clima: {res.get('message', 'desconhecido')}")
            return f"Erro ao buscar clima: {res.get('message', 'erro desconhecido')}"

        previsoes = res['list'][:8]  # Próximas 24h
        resumo = ""
        for p in previsoes[::2]:  # Pula de 6 em 6 horas
            resumo += f" {p['dt_txt'][11:16]}h: {p['main']['temp']:.0f}°C, {p['weather'][0]['description']} |"
        return resumo
    except requests.exceptions.Timeout:
        logger.error("Timeout ao buscar previsão do tempo.")
        raise  # Re-raise para o tenacity tentar novamente
    except Exception as e:
        logger.error(f"Erro ao buscar previsão: {e}")
        return f"Erro ao buscar previsão: {e}"
