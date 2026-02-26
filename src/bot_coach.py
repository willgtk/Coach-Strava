import os
import schedule
import time
import threading
from dotenv import set_key

import telebot

from config import TELEGRAM_TOKEN, env_path, logger
from strava_service import (
    obter_resumo_semana, obter_ultimo_pedal,
    obter_status_bike, obter_status_bike_texto
)
from weather_service import obter_previsao_tempo
from ai_engine import chat_session, guardar_memoria

# ==========================================
# INICIALIZAR O BOT DO TELEGRAM
# ==========================================
bot = telebot.TeleBot(TELEGRAM_TOKEN)


# ==========================================
# 🚀 MOTOR PROATIVO: SUPER PROMPT DE SEXTA
# ==========================================
def mensagem_planeamento_fim_de_semana():
    """Envia mensagem proativa toda sexta-feira com análise completa."""
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not chat_id:
        logger.warning("TELEGRAM_CHAT_ID não configurado. Mensagem proativa ignorada.")
        return

    logger.info("Analisando dados completos para mensagem proativa...")
    dados_treino = obter_resumo_semana()
    clima = obter_previsao_tempo()
    bike = obter_status_bike_texto()

    prompt = f"""
    Inicia a conversa de forma proativa. Hoje é sexta-feira. 
    Cruza estes 3 dados para criar a tua mensagem:
    1. Resumo da Semana: {dados_treino}
    2. Clima (Próx 24h): {clima}
    3. Status da Bicicleta: {bike}
    
    Diretrizes:
    - Sugere um treino para o fim de semana com a Equipe Partiu Pedal adequado ao clima (se chover, avisa sobre a lama).
    - Avalia se o volume da semana foi bom para manter o "motor".
    - Se a quilometragem da bicicleta for alta, deixa um alerta amigável sobre lubrificar a relação ou verificar o desgaste.
    Sê um verdadeiro parceiro de treino!
    """

    guardar_memoria("user", prompt)
    resposta_ia = chat_session.send_message(prompt)
    guardar_memoria("model", resposta_ia.text)

    bot.send_message(chat_id, resposta_ia.text)
    logger.info("Mensagem proativa enviada com sucesso.")


def agendador_em_segundo_plano():
    """Loop do agendador que roda em background."""
    while True:
        schedule.run_pending()
        time.sleep(1)


# Agendamento: Sexta-feira às 18:00
schedule.every().friday.at("18:00").do(mensagem_planeamento_fim_de_semana)
threading.Thread(target=agendador_em_segundo_plano, daemon=True).start()


# ==========================================
# ROTAS DO TELEGRAM
# ==========================================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Registra o chat ID e dá as boas-vindas."""
    chat_id = str(message.chat.id)
    set_key(env_path, 'TELEGRAM_CHAT_ID', chat_id)
    os.environ['TELEGRAM_CHAT_ID'] = chat_id
    logger.info(f"Novo utilizador registado. Chat ID: {chat_id}")
    bot.reply_to(
        message,
        "Coach Inteligente ativado! 🚵‍♂️\n"
        "Já registrei o teu contato. Agora monitorizo o teu Strava, "
        "o desgaste da tua bicicleta e o clima! SIMBOOOORA!\n\n"
        "📋 *Comandos disponíveis:*\n"
        "/semana — Resumo semanal completo\n"
        "/pedal — Dados do último pedal\n"
        "/bike — Status da bicicleta\n"
        "/clima — Previsão do tempo\n"
        "Ou simplesmente converse comigo! 💬",
        parse_mode='Markdown'
    )


@bot.message_handler(commands=['semana'])
def analisar_semana(message):
    """Comando /semana: análise semanal com treino + clima + bike."""
    bot.reply_to(message, "A procurar dados de treino, clima e equipamento... ⏳")
    prompt = (
        f"O atleta pediu um resumo manual agora. "
        f"Treino: {obter_resumo_semana()}. "
        f"Clima: {obter_previsao_tempo()}. "
        f"Bike: {obter_status_bike_texto()}."
    )

    guardar_memoria("user", prompt)
    resposta_ia = chat_session.send_message(prompt)
    guardar_memoria("model", resposta_ia.text)

    bot.reply_to(message, resposta_ia.text)


@bot.message_handler(commands=['pedal'])
def ultimo_pedal(message):
    """Comando /pedal: mostra dados detalhados do último pedal."""
    bot.reply_to(message, "A buscar o teu último pedal no Strava... 🚴⏳")
    dados_pedal = obter_ultimo_pedal()
    prompt = (
        f"O atleta pediu os dados do último pedal. "
        f"[DADOS ÚLTIMO PEDAL: {dados_pedal}]. "
        f"Analise o pedal, elogie os pontos fortes e sugira melhorias "
        f"para construir o 'motor' aeróbico."
    )

    guardar_memoria("user", "/pedal")
    resposta_ia = chat_session.send_message(prompt)
    guardar_memoria("model", resposta_ia.text)

    bot.reply_to(message, resposta_ia.text)


@bot.message_handler(commands=['bike'])
def status_bike(message):
    """Comando /bike: mostra status e dicas de manutenção da bicicleta."""
    bot.reply_to(message, "A verificar a garagem... 🔧⏳")
    resultado = obter_status_bike()

    if isinstance(resultado, tuple):
        texto_bike, km, nome = resultado
    else:
        texto_bike, km, nome = resultado, 0, "Desconhecida"

    prompt = (
        f"O atleta pediu o status da bicicleta. "
        f"[DADOS BIKE: {texto_bike}]. "
        f"A bike tem {km:.0f} km acumulados. "
        f"Com base na quilometragem, dê dicas de manutenção: "
        f"lubrificação da corrente (a cada 300-500km), "
        f"verificação das pastilhas de freio (a cada 1000km), "
        f"troca de relação/cassete (a cada 3000-5000km). "
        f"Seja amigável e prático."
    )

    guardar_memoria("user", "/bike")
    resposta_ia = chat_session.send_message(prompt)
    guardar_memoria("model", resposta_ia.text)

    bot.reply_to(message, resposta_ia.text)


@bot.message_handler(commands=['clima'])
def comando_clima(message):
    """Comando /clima: previsão do tempo com contexto de pedal."""
    bot.reply_to(message, "A olhar para o céu... ☁️⏳")
    clima_atual = obter_previsao_tempo()
    prompt = (
        f"O atleta pediu a previsão do tempo. "
        f"Responda de forma parceira e motivadora usando estes dados: {clima_atual}"
    )

    guardar_memoria("user", "/clima")
    resposta_ia = chat_session.send_message(prompt)
    guardar_memoria("model", resposta_ia.text)

    bot.reply_to(message, resposta_ia.text)


@bot.message_handler(func=lambda message: True)
def conversa_livre(message):
    """Handler de conversa livre com interceptação inteligente de contexto."""
    bot.send_chat_action(message.chat.id, 'typing')
    texto_usuario = message.text.lower()

    prompt_final = message.text
    dados_extras = []

    # 🕵️ INTERCEPTADOR DE CLIMA: injeta dados se o usuário falar sobre o tempo
    palavras_clima = ['clima', 'tempo', 'temperatura', 'chover', 'chuva', 'sol', 'frio', 'calor']
    if any(palavra in texto_usuario for palavra in palavras_clima):
        clima_atual = obter_previsao_tempo()
        dados_extras.append(f"[DADOS DE CLIMA: {clima_atual}]")

    # 🚴 INTERCEPTADOR DE STRAVA: injeta dados se o usuário falar sobre treinos/pedais
    palavras_strava = [
        'pedal', 'pedais', 'treino', 'treinos', 'resultado', 'resultados',
        'hoje', 'ontem', 'semana', 'pedalei', 'andei', 'rodei',
        'km', 'quilometro', 'quilômetro', 'distância', 'distancia',
        'elevação', 'subida', 'subidas', 'desempenho', 'performance',
        'avalie', 'avaliar', 'análise', 'analise', 'último', 'ultimo',
        'strava'
    ]
    if any(palavra in texto_usuario for palavra in palavras_strava):
        dados_strava = obter_ultimo_pedal()
        resumo_semana = obter_resumo_semana()
        dados_extras.append(f"[DADOS ÚLTIMO PEDAL: {dados_strava}]")
        dados_extras.append(f"[DADOS SEMANA: {resumo_semana}]")

    # 🔧 INTERCEPTADOR DE BIKE: injeta dados sobre a bicicleta
    palavras_bike = [
        'bike', 'bicicleta', 'manutenção', 'manutencao', 'corrente',
        'freio', 'pastilha', 'relação', 'relacao', 'cassete',
        'pneu', 'câmbio', 'cambio', 'kaéti', 'kaeti'
    ]
    if any(palavra in texto_usuario for palavra in palavras_bike):
        bike_texto = obter_status_bike_texto()
        dados_extras.append(f"[DADOS BIKE: {bike_texto}]")

    if dados_extras:
        prompt_final = message.text + "\n\n" + "\n".join(dados_extras)

    guardar_memoria("user", message.text)
    resposta_ia = chat_session.send_message(prompt_final)
    guardar_memoria("model", resposta_ia.text)

    bot.reply_to(message, resposta_ia.text)


# ==========================================
# ARRANQUE DO BOT
# ==========================================
logger.info("Coach 4.0 (Modular + Interceptadores Inteligentes + Novos Comandos) ativo no Telegram!")
bot.infinity_polling()