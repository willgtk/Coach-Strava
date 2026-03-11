"""
Bot principal do Coach-Strava para Telegram.
Gerencia comandos, conversas livres, áudio, fotos e mensagens proativas.
"""
from __future__ import annotations

import os
import signal
import sys
import tempfile
import schedule
import time
import threading
from typing import Optional

from dotenv import set_key
import telebot
from cachetools import TTLCache

from config import TELEGRAM_TOKEN, TEAM_NAME, META_MENSAL_KM, env_path, logger
from strava_service import (
    obter_resumo_semana, obter_ultimo_pedal,
    obter_status_bike, obter_status_bike_texto,
    obter_progresso_mensal, gerar_grafico_progresso,
    obter_historico_mensal
)
from weather_service import obter_previsao_tempo
from ai_engine import (
    get_chat_session, guardar_memoria, processar_mensagem_audio,
    processar_mensagem_foto, registrar_usuario, obter_todos_chat_ids,
    obter_meta_usuario, atualizar_meta_usuario, obter_ranking_usuarios
)
from constantes import PALAVRAS_CLIMA, PALAVRAS_STRAVA, PALAVRAS_BIKE

# ==========================================
# INICIALIZAR O BOT DO TELEGRAM
# ==========================================
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Limite de caracteres por mensagem do Telegram
_MAX_MSG_LEN: int = 4096

# Rate limiter com expiração automática (evita vazamento de memória)
_RATE_LIMIT_SECONDS: float = 3.0
_rate_limit: TTLCache = TTLCache(maxsize=1000, ttl=_RATE_LIMIT_SECONDS)

# Caminho do arquivo de heartbeat para o healthcheck do Docker
_HEALTH_FILE: str = '/tmp/bot_health'

# Texto reutilizável da lista de comandos
TEXTO_COMANDOS: str = (
    "📋 *Comandos disponíveis:*\n"
    "/start — Registrar e ativar o coach\n"
    "/semana — Resumo semanal completo e andamento da meta\n"
    "/grafico — Gráfico de evolução de treino\n"
    "/pedal — Dados do último pedal\n"
    "/bike — Status da bicicleta\n"
    "/clima — Previsão do tempo\n"
    "/meta — Definir sua meta mensal (ex: /meta 200)\n"
    "/historico — Evolução mensal comparativa\n"
    "/ranking — Ranking de km entre membros\n"
    "📷 Envie uma foto da trilha para análise!\n"
    "🎙️ Envie um áudio como Walkie-Talkie!\n"
    "Ou simplesmente converse comigo! 💬"
)


def _check_rate_limit(chat_id: int | str) -> bool:
    """Retorna True se o usuário pode enviar, False se está em cooldown."""
    key = str(chat_id)
    if key in _rate_limit:
        return False
    _rate_limit[key] = True
    return True


def _escrever_heartbeat() -> None:
    """Escreve timestamp para o healthcheck do Docker."""
    try:
        with open(_HEALTH_FILE, 'w') as f:
            f.write(str(time.time()))
    except OSError:
        pass


def enviar_resposta_segura(bot: telebot.TeleBot, chat_id: int | str, texto: str, reply_to=None) -> None:
    """Envia mensagem dividindo em pedaços se exceder o limite do Telegram."""
    for i in range(0, len(texto), _MAX_MSG_LEN):
        pedaco = texto[i:i + _MAX_MSG_LEN]
        if reply_to and i == 0:
            bot.reply_to(reply_to, pedaco)
        else:
            bot.send_message(chat_id, pedaco)


def _verificar_conquistas(chat_id: int | str, meta_km: float) -> Optional[str]:
    """Verifica se o atleta atingiu marcos e retorna mensagem de celebração."""
    resultado = obter_progresso_mensal(meta_km)
    if isinstance(resultado, str):
        return None

    percentual = resultado.get('percentual_concluido', 0)
    total_km = resultado.get('total_km', 0)

    conquistas = []
    if percentual >= 100:
        conquistas.append("🏆🎉 PARABÉNS! VOCÊ BATEU A META DO MÊS! 🎉🏆\nVocê é uma máquina!")
    elif percentual >= 75:
        conquistas.append("🔥 75% da meta atingida! Falta pouco, não para agora!")
    elif percentual >= 50:
        conquistas.append("⚡ Metade da meta já foi! O motor está quente!")

    # Marcos de quilometragem total na bike
    _, km_bike, nome_bike = obter_status_bike()
    if km_bike >= 5000 and km_bike < 5050:
        conquistas.append(f"🌟 WOW! A {nome_bike} passou dos 5.000 km! Lendária!")
    elif km_bike >= 3000 and km_bike < 3050:
        conquistas.append(f"⭐ A {nome_bike} chegou aos 3.000 km! Que parceria!")
    elif km_bike >= 1000 and km_bike < 1050:
        conquistas.append(f"🎯 A {nome_bike} passou dos 1.000 km! Marco importante!")

    return "\n\n".join(conquistas) if conquistas else None


# ==========================================
# 🚀 MOTOR PROATIVO: SUPER PROMPT DE SEXTA
# ==========================================
def mensagem_planeamento_fim_de_semana() -> None:
    """Envia mensagem proativa toda sexta-feira para TODOS os usuários registrados."""
    chat_ids = obter_todos_chat_ids()
    if not chat_ids:
        # Fallback para o chat ID do .env (compatibilidade)
        chat_id_env = os.getenv('TELEGRAM_CHAT_ID')
        if chat_id_env:
            chat_ids = [chat_id_env]
        else:
            logger.warning("Nenhum usuário registrado. Mensagem proativa ignorada.")
            return

    for chat_id in chat_ids:
        try:
            logger.info(f"Enviando mensagem proativa para chat {chat_id}...")
            meta_usuario = obter_meta_usuario(chat_id, META_MENSAL_KM)
            dados_treino = obter_resumo_semana()
            clima = obter_previsao_tempo()
            bike = obter_status_bike_texto()

            meta = obter_progresso_mensal(meta_usuario)
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
            - Celebre ou cobre (de forma amigável) o progresso em relação à meta do mês.
            - Se a quilometragem da bicicleta for alta, deixa um alerta amigável sobre manutenção.
            Sê um verdadeiro parceiro de treino!
            """

            session = get_chat_session(chat_id)
            guardar_memoria(chat_id, "user", "[AUTO] Resumo proativo de sexta-feira solicitado")
            resposta_ia = session.send_message(prompt)
            guardar_memoria(chat_id, "model", resposta_ia.text)

            enviar_resposta_segura(bot, chat_id, resposta_ia.text)

            # Verificar conquistas e enviar se houver
            conquista = _verificar_conquistas(chat_id, meta_usuario)
            if conquista:
                bot.send_message(chat_id, conquista)

            logger.info(f"Mensagem proativa enviada para chat {chat_id}.")
        except Exception as e:
            logger.error(f"Erro na mensagem proativa para {chat_id}: {e}")


def agendador_em_segundo_plano() -> None:
    """Loop do agendador que roda em background, com heartbeat para healthcheck."""
    while True:
        schedule.run_pending()
        _escrever_heartbeat()
        time.sleep(1)


# ==========================================
# ROTAS DO TELEGRAM
# ==========================================
@bot.message_handler(commands=['start'])
def send_welcome(message) -> None:
    """Registra o chat ID e dá as boas-vindas."""
    chat_id = str(message.chat.id)
    nome = message.from_user.first_name or "Atleta"

    # Registra no banco SQLite (multi-usuário) e no .env (compatibilidade)
    registrar_usuario(chat_id, nome)
    set_key(env_path, 'TELEGRAM_CHAT_ID', chat_id)
    os.environ['TELEGRAM_CHAT_ID'] = chat_id
    logger.info(f"Novo utilizador registado: {nome} (Chat ID: {chat_id})")

    bot.reply_to(
        message,
        f"Coach Inteligente ativado, {nome}! 🚵‍♂️\n"
        "Já registrei o teu contato. Agora monitorizo o teu Strava, "
        "o desgaste da tua bicicleta e o clima! SIMBOOOORA!\n\n"
        f"{TEXTO_COMANDOS}",
        parse_mode='Markdown'
    )


@bot.message_handler(commands=['help'])
def send_help(message) -> None:
    """Exibe apenas a lista de comandos disponíveis."""
    bot.reply_to(message, TEXTO_COMANDOS, parse_mode='Markdown')


@bot.message_handler(commands=['grafico'])
def enviar_grafico(message) -> None:
    """Comando /grafico: envia a imagem gerada com o volume de treino."""
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        msg_wait = bot.reply_to(message, "A desenhar o teu gráfico de evolução dos últimos 30 dias... 📊⏳")
        caminho_grafico = gerar_grafico_progresso(30)

        if caminho_grafico and os.path.exists(caminho_grafico):
            with open(caminho_grafico, 'rb') as foto:
                bot.send_photo(message.chat.id, foto, caption="A tua evolução nos últimos 30 dias! 🚀")
            os.remove(caminho_grafico)  # Limpa o arquivo temporário após o envio
            bot.delete_message(message.chat.id, msg_wait.message_id)
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
def analisar_semana(message) -> None:
    """Comando /semana: análise semanal com treino + clima + bike + meta."""
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        bot.reply_to(message, "A procurar dados de treino, metas do mês, clima e equipamento... ⏳")

        chat_id = str(message.chat.id)
        meta_usuario = obter_meta_usuario(chat_id, META_MENSAL_KM)
        meta = obter_progresso_mensal(meta_usuario)
        texto_meta = meta if isinstance(meta, str) else meta.get('texto', 'Erro ao obter meta.')

        prompt = (
            f"O atleta pediu um resumo manual agora. "
            f"Treino Semana: {obter_resumo_semana()}. "
            f"Meta Mês: {texto_meta}. "
            f"Clima: {obter_previsao_tempo()}. "
            f"Bike: {obter_status_bike_texto()}."
            f"\n\nInstruções: Faça um resumo engajador juntando todas as informações, motivando o atleta a bater a meta mensal."
        )

        session = get_chat_session(chat_id)
        guardar_memoria(chat_id, "user", "[AUTO] Resumo semanal solicitado via /semana")
        resposta_ia = session.send_message(prompt)
        guardar_memoria(chat_id, "model", resposta_ia.text)

        enviar_resposta_segura(bot, message.chat.id, resposta_ia.text, reply_to=message)

        # Verificar conquistas
        conquista = _verificar_conquistas(chat_id, meta_usuario)
        if conquista:
            bot.send_message(message.chat.id, conquista)

    except Exception as e:
        logger.error(f"Erro no /semana: {e}")
        bot.reply_to(message, "⚠️ Erro ao processar. Tente novamente em instantes.")


@bot.message_handler(commands=['pedal'])
def ultimo_pedal(message) -> None:
    """Comando /pedal: mostra dados detalhados do último pedal."""
    try:
        bot.send_chat_action(message.chat.id, 'typing')
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
def status_bike(message) -> None:
    """Comando /bike: mostra status e dicas de manutenção da bicicleta."""
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        bot.reply_to(message, "A verificar a garagem... 🔧⏳")
        resultado = obter_status_bike()
        texto_bike, km, nome = resultado

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
def comando_clima(message) -> None:
    """Comando /clima: previsão do tempo com contexto de pedal."""
    try:
        bot.send_chat_action(message.chat.id, 'typing')
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


@bot.message_handler(commands=['meta'])
def comando_meta(message) -> None:
    """Comando /meta: permite ao atleta definir sua meta mensal de km."""
    try:
        chat_id = str(message.chat.id)
        partes = message.text.strip().split()

        if len(partes) < 2:
            meta_atual = obter_meta_usuario(chat_id, META_MENSAL_KM)
            bot.reply_to(
                message,
                f"🎯 Sua meta mensal atual é de *{meta_atual:.0f} km*.\n\n"
                f"Para alterar, use: `/meta 200` (exemplo para 200km)",
                parse_mode='Markdown'
            )
            return

        try:
            nova_meta = float(partes[1])
        except ValueError:
            bot.reply_to(message, "⚠️ Valor inválido. Use um número, ex: `/meta 200`", parse_mode='Markdown')
            return

        if nova_meta <= 0 or nova_meta > 10000:
            bot.reply_to(message, "⚠️ A meta deve ser entre 1 e 10.000 km.")
            return

        # Garante que o usuário existe na tabela
        registrar_usuario(chat_id, message.from_user.first_name or "Atleta")
        sucesso = atualizar_meta_usuario(chat_id, nova_meta)

        if sucesso:
            bot.send_chat_action(message.chat.id, 'typing')
            session = get_chat_session(chat_id)
            prompt = f"O atleta acabou de atualizar sua meta mensal para {nova_meta:.0f} km. Parabenize e motive!"
            guardar_memoria(chat_id, "user", f"/meta {nova_meta:.0f}")
            resposta_ia = session.send_message(prompt)
            guardar_memoria(chat_id, "model", resposta_ia.text)
            enviar_resposta_segura(bot, message.chat.id, resposta_ia.text, reply_to=message)
        else:
            bot.reply_to(message, "⚠️ Erro ao salvar a meta. Tente novamente.")

    except Exception as e:
        logger.error(f"Erro no /meta: {e}")
        bot.reply_to(message, "⚠️ Erro ao processar. Tente novamente em instantes.")


@bot.message_handler(commands=['historico'])
def comando_historico(message) -> None:
    """Comando /historico: mostra evolução mensal comparativa."""
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        bot.reply_to(message, "A compilar o teu histórico de evolução... 📈⏳")

        historico = obter_historico_mensal(meses=3)

        chat_id = str(message.chat.id)
        meta_usuario = obter_meta_usuario(chat_id, META_MENSAL_KM)

        prompt = (
            f"O atleta pediu seu histórico de evolução mensal. "
            f"[DADOS HISTÓRICO: {historico}]. "
            f"Meta mensal atual: {meta_usuario:.0f} km. "
            f"Analise a evolução, identifique tendências (subindo, descendo, estável), "
            f"parabenize os meses bons e motive para os próximos. "
            f"Se houve queda, encoraje a retomar com dicas práticas."
        )

        session = get_chat_session(chat_id)
        guardar_memoria(chat_id, "user", "/historico")
        resposta_ia = session.send_message(prompt)
        guardar_memoria(chat_id, "model", resposta_ia.text)

        enviar_resposta_segura(bot, message.chat.id, resposta_ia.text, reply_to=message)
    except Exception as e:
        logger.error(f"Erro no /historico: {e}")
        bot.reply_to(message, "⚠️ Erro ao processar. Tente novamente em instantes.")


@bot.message_handler(commands=['ranking'])
def comando_ranking(message) -> None:
    """Comando /ranking: mostra ranking de km entre membros registrados."""
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        bot.reply_to(message, "A montar o ranking da equipe... 🏆⏳")

        ranking = obter_ranking_usuarios()

        chat_id = str(message.chat.id)
        prompt = (
            f"O atleta pediu o ranking da equipe. "
            f"[DADOS RANKING: {ranking}]. "
            f"Monte uma apresentação divertida e motivadora do ranking, "
            f"parabenize o líder, encoraje os demais, e use emojis de pódio "
            f"(🥇🥈🥉) para os 3 primeiros."
        )

        session = get_chat_session(chat_id)
        guardar_memoria(chat_id, "user", "/ranking")
        resposta_ia = session.send_message(prompt)
        guardar_memoria(chat_id, "model", resposta_ia.text)

        enviar_resposta_segura(bot, message.chat.id, resposta_ia.text, reply_to=message)
    except Exception as e:
        logger.error(f"Erro no /ranking: {e}")
        bot.reply_to(message, "⚠️ Erro ao processar. Tente novamente em instantes.")


@bot.message_handler(content_types=['voice'])
def receber_audio(message) -> None:
    """Handler para receber e processar mensagens de áudio (Walkie-Talkie)."""
    try:
        msg_wait = bot.reply_to(message, "A ouvir o teu áudio... 🎧⏳")
        bot.send_chat_action(message.chat.id, 'record_voice')

        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # Arquivo temporário seguro
        tmp_file = tempfile.NamedTemporaryFile(
            suffix='.ogg', prefix=f'audio_{message.chat.id}_', delete=False
        )
        tmp_file.write(downloaded_file)
        tmp_file.close()
        caminho_temporario = tmp_file.name

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


@bot.message_handler(content_types=['photo'])
def receber_foto(message) -> None:
    """Handler para receber e analisar fotos enviadas pelo atleta."""
    try:
        msg_wait = bot.reply_to(message, "A analisar a tua foto... 📸⏳")
        bot.send_chat_action(message.chat.id, 'typing')

        # Pegar a foto de maior resolução (último item da lista)
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # Arquivo temporário seguro
        tmp_file = tempfile.NamedTemporaryFile(
            suffix='.jpg', prefix=f'foto_{message.chat.id}_', delete=False
        )
        tmp_file.write(downloaded_file)
        tmp_file.close()
        caminho_temporario = tmp_file.name

        # Usar a legenda da foto como contexto adicional, se houver
        legenda = message.caption or ""
        prompt = (
            f"O atleta enviou esta foto{' com a legenda: ' + legenda if legenda else ''}. "
            f"Analise a imagem (pode ser da trilha, bicicleta, paisagem, equipamento, lesão, etc.) "
            f"e responda como o Coach parceiro de treino. Se for uma foto da bike ou equipamento, "
            f"dê dicas relevantes. Se for da trilha, comente sobre o terreno e motivação."
        )

        resposta = processar_mensagem_foto(message.chat.id, caminho_temporario, prompt_adicional=prompt)

        # Limpar o arquivo temporário
        if os.path.exists(caminho_temporario):
            os.remove(caminho_temporario)

        bot.delete_message(message.chat.id, msg_wait.message_id)
        enviar_resposta_segura(bot, message.chat.id, resposta, reply_to=message)

    except Exception as e:
        logger.error(f"Erro no processamento de foto: {e}")
        bot.reply_to(message, "⚠️ Erro ao analisar a foto. Pode enviar novamente ou descrever por texto?")


@bot.message_handler(func=lambda message: True)
def conversa_livre(message) -> None:
    """Handler de conversa livre com interceptação inteligente de contexto."""
    try:
        # Guard: ignora mensagens sem texto (stickers, GIFs, documentos, etc.)
        if not message.text:
            return

        # Rate limiting: evita spam de chamadas ao Gemini
        if not _check_rate_limit(message.chat.id):
            return

        bot.send_chat_action(message.chat.id, 'typing')
        texto_usuario = message.text.lower()

        prompt_final = message.text
        dados_extras: list[str] = []

        # 🕵️ INTERCEPTADOR DE CLIMA
        if any(palavra in texto_usuario for palavra in PALAVRAS_CLIMA):
            clima_atual = obter_previsao_tempo()
            dados_extras.append(f"[DADOS DE CLIMA: {clima_atual}]")

        # 🚴 INTERCEPTADOR DE STRAVA
        if any(palavra in texto_usuario for palavra in PALAVRAS_STRAVA):
            dados_strava = obter_ultimo_pedal()
            resumo_semana = obter_resumo_semana()
            dados_extras.append(f"[DADOS ÚLTIMO PEDAL: {dados_strava}]")
            dados_extras.append(f"[DADOS SEMANA: {resumo_semana}]")

        # 🔧 INTERCEPTADOR DE BIKE
        if any(palavra in texto_usuario for palavra in PALAVRAS_BIKE):
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
# GRACEFUL SHUTDOWN
# ==========================================
def _graceful_shutdown(signum, frame) -> None:
    """Encerra o bot de forma limpa ao receber SIGTERM ou SIGINT."""
    logger.info(f"Sinal {signum} recebido. Encerrando o bot de forma segura...")
    bot.stop_polling()
    logger.info("Bot encerrado com sucesso.")
    sys.exit(0)


# ==========================================
# ARRANQUE DO BOT
# ==========================================
def main() -> None:
    """Inicializa o agendador, sinais e inicia o polling do bot."""
    signal.signal(signal.SIGINT, _graceful_shutdown)
    signal.signal(signal.SIGTERM, _graceful_shutdown)

    # Agendamento: Sexta-feira às 18:00
    schedule.every().friday.at("18:00").do(mensagem_planeamento_fim_de_semana)
    threading.Thread(target=agendador_em_segundo_plano, daemon=True).start()

    # Heartbeat inicial
    _escrever_heartbeat()

    logger.info("Coach 7.0 (WAL + Healthcheck + TTLCache + main guard) ativo no Telegram!")
    bot.infinity_polling()


if __name__ == '__main__':
    main()