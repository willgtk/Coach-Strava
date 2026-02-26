import os
import schedule
import time
import threading
from dotenv import set_key

import telebot

from config import TELEGRAM_TOKEN, TEAM_NAME, META_MENSAL_KM, env_path, logger
from strava_service import (
    obter_resumo_semana, obter_ultimo_pedal,
    obter_status_bike, obter_status_bike_texto,
    obter_progresso_mensal, gerar_grafico_progresso
)
from weather_service import obter_previsao_tempo
from ai_engine import get_chat_session, guardar_memoria, processar_mensagem_audio

# ==========================================
# INICIALIZAR O BOT DO TELEGRAM
# ==========================================
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Limite de caracteres por mensagem do Telegram
_MAX_MSG_LEN = 4096


def enviar_resposta_segura(bot, chat_id, texto, reply_to=None):
    """Envia mensagem dividindo em pedaços se exceder o limite do Telegram."""
    for i in range(0, len(texto), _MAX_MSG_LEN):
        pedaco = texto[i:i + _MAX_MSG_LEN]
        if reply_to and i == 0:
            bot.reply_to(reply_to, pedaco)
        else:
            bot.send_message(chat_id, pedaco)


# ==========================================
# 🚀 MOTOR PROATIVO: SUPER PROMPT DE SEXTA
# ==========================================
def mensagem_planeamento_fim_de_semana():
    """Envia mensagem proativa toda sexta-feira com análise completa."""
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not chat_id:
        logger.warning("TELEGRAM_CHAT_ID não configurado. Mensagem proativa ignorada.")
        return

    try:
        logger.info("Analisando dados completos para mensagem proativa...")
        dados_treino = obter_resumo_semana()
        clima = obter_previsao_tempo()
        bike = obter_status_bike_texto()
        
        # Gamificação: Progresso na meta mensal
        meta = obter_progresso_mensal(META_MENSAL_KM)
        texto_meta = meta if isinstance(meta, str) else meta.get('texto', 'Erro ao obter meta.')

        prompt = f"""
        Inicia a conversa de forma proativa. Hoje é sexta-feira. 
        Cruza estes 4 dados para criar a tua mensagem:
        1. Resumo da Semana: {dados_treino}
        2. Clima (Próx 24h): {clima}
        3. Status da Bicicleta: {bike}
        4. Meta do Mês: {texto_meta}
        
        Diretrizes:
        - Sugere um treino para o fim de semana com a {TEAM_NAME} adequado ao clima (se chover, avisa sobre a lama).
        - Avalia se o volume da semana foi bom para manter o "motor".
        - Celebre ou cobre (de forma amigável) o progresso em relação à meta do mês. Se faltar pouco, o motive muito! Se estiver longe, diga que o fim de semana é para tirar o atraso.
        - Se a quilometragem da bicicleta for alta, deixa um alerta amigável sobre lubrificar a relação ou verificar o desgaste.
        Sê um verdadeiro parceiro de treino!
        """

        session = get_chat_session(chat_id)
        
        guardar_memoria(chat_id, "user", prompt)
        resposta_ia = session.send_message(prompt)
        guardar_memoria(chat_id, "model", resposta_ia.text)

        enviar_resposta_segura(bot, chat_id, resposta_ia.text)
        logger.info("Mensagem proativa enviada com sucesso.")
    except Exception as e:
        logger.error(f"Erro na mensagem proativa de sexta: {e}")


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
        "/semana — Resumo semanal completo e andamento da meta\n"
        "/grafico —  Gráfico de evolução e treino\n"
        "/pedal — Dados do último pedal\n"
        "/bike — Status da bicicleta\n"
        "/clima — Previsão do tempo\n"
        "Ou simplesmente converse comigo! 💬",
        parse_mode='Markdown'
    )


@bot.message_handler(commands=['grafico'])
def enviar_grafico(message):
    """Comando /grafico: envia a imagem gerada com o volume de treino."""
    try:
        msg_wait = bot.reply_to(message, "A desenhar o teu gráfico de evolução dos últimos 30 dias... 📊⏳")
        caminho_grafico = gerar_grafico_progresso(30)
        
        if caminho_grafico and os.path.exists(caminho_grafico):
            with open(caminho_grafico, 'rb') as foto:
                bot.send_photo(message.chat.id, foto, caption="A tua evolução nos últimos 30 dias! 🚀")
            os.remove(caminho_grafico)  # Limpa o arquivo após o envio
            bot.delete_message(message.chat.id, msg_wait.message_id) # remove as reticencias
        else:
            bot.edit_message_text(
                "Não consegui gerar o teu gráfico neste momento. Tu tens pedalado nos últimos dias?",
                chat_id=message.chat.id,
                message_id=msg_wait.message_id
            )
            
    except Exception as e:
        logger.error(f"Erro no /grafico: {e}")
        bot.reply_to(message, "⚠️ Erro ao gerar o gráfico. Tente novamente em instantes.")


@bot.message_handler(commands=['semana'])
def analisar_semana(message):
    """Comando /semana: análise semanal com treino + clima + bike + meta."""
    try:
        bot.reply_to(message, "A procurar dados de treino, metas do mês, clima e equipamento... ⏳")
        
        meta = obter_progresso_mensal(META_MENSAL_KM)
        texto_meta = meta if isinstance(meta, str) else meta.get('texto', 'Erro ao obter meta.')
        
        prompt = (
            f"O atleta pediu um resumo manual agora. "
            f"Treino Semana: {obter_resumo_semana()}. "
            f"Meta Mês: {texto_meta}. "
            f"Clima: {obter_previsao_tempo()}. "
            f"Bike: {obter_status_bike_texto()}."
            f"\n\nInstruções: Faça um resumo engajador juntando todas as informações, motivando o atleta a bater a meta mensal."
        )

        chat_id = message.chat.id
        session = get_chat_session(chat_id)
        
        guardar_memoria(chat_id, "user", prompt)
        resposta_ia = session.send_message(prompt)
        guardar_memoria(chat_id, "model", resposta_ia.text)

        enviar_resposta_segura(bot, message.chat.id, resposta_ia.text, reply_to=message)
    except Exception as e:
        logger.error(f"Erro no /semana: {e}")
        bot.reply_to(message, "⚠️ Erro ao processar. Tente novamente em instantes.")


@bot.message_handler(commands=['pedal'])
def ultimo_pedal(message):
    """Comando /pedal: mostra dados detalhados do último pedal."""
    try:
        bot.reply_to(message, "A buscar o teu último pedal no Strava... 🚴⏳")
        dados_pedal = obter_ultimo_pedal()
        prompt = (
            f"O atleta pediu os dados do último pedal. "
            f"[DADOS ÚLTIMO PEDAL: {dados_pedal}]. "
            f"Analise o pedal, elogie os pontos fortes e sugira melhorias "
            f"para construir o 'motor' aeróbico."
        )

        chat_id = message.chat.id
        session = get_chat_session(chat_id)
        
        guardar_memoria(chat_id, "user", "/pedal")
        resposta_ia = session.send_message(prompt)
        guardar_memoria(chat_id, "model", resposta_ia.text)

        enviar_resposta_segura(bot, message.chat.id, resposta_ia.text, reply_to=message)
    except Exception as e:
        logger.error(f"Erro no /pedal: {e}")
        bot.reply_to(message, "⚠️ Erro ao processar. Tente novamente em instantes.")


@bot.message_handler(commands=['bike'])
def status_bike(message):
    """Comando /bike: mostra status e dicas de manutenção da bicicleta."""
    try:
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

        chat_id = message.chat.id
        session = get_chat_session(chat_id)
        
        guardar_memoria(chat_id, "user", "/bike")
        resposta_ia = session.send_message(prompt)
        guardar_memoria(chat_id, "model", resposta_ia.text)

        enviar_resposta_segura(bot, message.chat.id, resposta_ia.text, reply_to=message)
    except Exception as e:
        logger.error(f"Erro no /bike: {e}")
        bot.reply_to(message, "⚠️ Erro ao processar. Tente novamente em instantes.")


@bot.message_handler(commands=['clima'])
def comando_clima(message):
    """Comando /clima: previsão do tempo com contexto de pedal."""
    try:
        bot.reply_to(message, "A olhar para o céu... ☁️⏳")
        clima_atual = obter_previsao_tempo()
        prompt = (
            f"O atleta pediu a previsão do tempo. "
            f"Responda de forma parceira e motivadora usando estes dados: {clima_atual}"
        )

        chat_id = message.chat.id
        session = get_chat_session(chat_id)
        
        guardar_memoria(chat_id, "user", "/clima")
        resposta_ia = session.send_message(prompt)
        guardar_memoria(chat_id, "model", resposta_ia.text)

        enviar_resposta_segura(bot, message.chat.id, resposta_ia.text, reply_to=message)
    except Exception as e:
        logger.error(f"Erro no /clima: {e}")
        bot.reply_to(message, "⚠️ Erro ao processar. Tente novamente em instantes.")


@bot.message_handler(content_types=['voice'])
def receber_audio(message):
    """Handler para receber e processar mensagens de áudio (Walkie-Talkie)."""
    try:
        msg_wait = bot.reply_to(message, "A ouvir o teu áudio... 🎧⏳")
        bot.send_chat_action(message.chat.id, 'record_voice')
        
        # Obter informações do arquivo de áudio no Telegram
        file_info = bot.get_file(message.voice.file_id)
        
        # Fazer o download
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Salvar num arquivo temporário (.ogg)
        caminho_temporario = f"temp_audio_{message.chat.id}_{message.message_id}.ogg"
        with open(caminho_temporario, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        prompt = "O atleta enviou esta mensagem de áudio (Walkie-Talkie) possivelmente durante ou após o seu pedal. Escute, faça um breve resumo do que ele falou e responda como seu Coach parceiro de treino."
        
        resposta = processar_mensagem_audio(message.chat.id, caminho_temporario, prompt_adicional=prompt)
        
        # Limpar o arquivo temporário
        if os.path.exists(caminho_temporario):
            os.remove(caminho_temporario)
            
        bot.delete_message(message.chat.id, msg_wait.message_id)
        enviar_resposta_segura(bot, message.chat.id, resposta, reply_to=message)
        
    except Exception as e:
        logger.error(f"Erro no processamento de áudio: {e}")
        bot.reply_to(message, "⚠️ Erro ao processar o seu áudio. Os meus ouvidos digitais falharam, pode gravar de novo ou enviar por texto?")


@bot.message_handler(func=lambda message: True)
def conversa_livre(message):
    """Handler de conversa livre com interceptação inteligente de contexto."""
    try:
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

        chat_id = message.chat.id
        session = get_chat_session(chat_id)
        
        guardar_memoria(chat_id, "user", message.text)
        resposta_ia = session.send_message(prompt_final)
        guardar_memoria(chat_id, "model", resposta_ia.text)

        enviar_resposta_segura(bot, message.chat.id, resposta_ia.text, reply_to=message)
    except Exception as e:
        logger.error(f"Erro na conversa livre: {e}")
        bot.reply_to(message, "⚠️ Erro ao processar. Tente novamente em instantes.")


# ==========================================
# ARRANQUE DO BOT
# ==========================================
logger.info("Coach 4.0 (Modular + Interceptadores Inteligentes + Novos Comandos) ativo no Telegram!")
bot.infinity_polling()