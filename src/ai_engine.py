import os
import threading
import sqlite3
from google import genai
from google.genai import types

from config import GOOGLE_API_KEY, DB_PATH, TEAM_NAME, logger

_memory_lock = threading.Lock()

# ==========================================
# MÓDULO DE MEMÓRIA PERSISTENTE (SQLite)
# ==========================================

def init_db():
    """Inicializa o banco de dados e cria a tabela se não existir."""
    with _memory_lock:
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS conversas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    mensagem TEXT NOT NULL,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Erro ao inicializar o banco SQLite: {e}")
        finally:
            if conn:
                conn.close()

# Inicializa o banco assim que o módulo for carregado
init_db()


def carregar_memoria(chat_id):
    """Carrega o histórico de conversa do banco de dados para um usuário específico."""
    chat_id = str(chat_id)
    with _memory_lock:
        conn = None
        historico = []
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # Buscar as últimas 40 mensagens do usuário, ordenadas pela mais antiga primeiro
            # A subquery pega as últimas 40 descendentes, e a query externa inverte para ascendente
            c.execute('''
                SELECT role, mensagem FROM (
                    SELECT role, mensagem, id FROM conversas 
                    WHERE chat_id = ? 
                    ORDER BY id DESC LIMIT 40
                ) ORDER BY id ASC
            ''', (chat_id,))
            
            linhas = c.fetchall()
            
            if not linhas:
                return []

            # Validação de integridade: a API exige que os papéis alternem (user -> model).
            dados = [{"role": row[0], "text": row[1]} for row in linhas]
            if len(dados) > 0 and dados[-1]['role'] == 'user':
                dados.pop()

            for msg in dados:
                historico.append(
                    types.Content(
                        role=msg['role'],
                        parts=[types.Part.from_text(text=msg['text'])]
                    )
                )
            
            logger.info(f"Memória restaurada: {len(historico)} interações para o chat {chat_id}.")
            return historico

        except sqlite3.Error as e:
            logger.error(f"Erro ao carregar memória do SQLite: {e}")
            return []
        finally:
            if conn:
                conn.close()


def guardar_memoria(chat_id, role, text):
    """Guarda uma nova mensagem no banco de dados para um usuário específico."""
    chat_id = str(chat_id)
    with _memory_lock:
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('INSERT INTO conversas (chat_id, role, mensagem) VALUES (?, ?, ?)', (chat_id, role, text))
            conn.commit()
            
            # (Opcional) Limpar mensagens muito antigas para não inflar o DB ad-eternum
            c.execute('''
                DELETE FROM conversas WHERE id NOT IN (
                    SELECT id FROM conversas WHERE chat_id = ? ORDER BY id DESC LIMIT 100
                ) AND chat_id = ?
            ''', (chat_id, chat_id))
            conn.commit()
            
        except sqlite3.Error as e:
            logger.error(f"Erro ao guardar memória no SQLite: {e}")
        finally:
            if conn:
                conn.close()


# ==========================================
# CÉREBRO DA IA E GERENCIAMENTO DE SESSÕES
# ==========================================
instrucoes_coach = f"""
Você é um parceiro e treinador de Mountain Bike focado em condicionamento e qualidade de vida. 
Seu aluno faz parte da {TEAM_NAME} e quer ser o melhor ciclista! Você receberá os dados da bicicleta principal dele.
Ele não treina para competições, o objetivo dele é construir uma base aeróbica forte ("ter motor") para estar sempre pronto para qualquer pedal com o grupo, sem sofrer nas subidas.
Analise os dados do Strava, sugira treinos focados em constância e resistência, e seja um motivador amigável.
Sempre responda de forma concisa, direta e com bom humor, ideal para leitura no Telegram.

IMPORTANTE: Quando dados do Strava forem injetados na conversa via [DADOS STRAVA: ...] ou [DADOS ÚLTIMO PEDAL: ...], 
USE esses dados para responder ao atleta. Nunca diga que não tem acesso aos dados se eles foram fornecidos.
"""

client_ai = genai.Client(api_key=GOOGLE_API_KEY)

# Dicionário para armazenar a sessão de chat de cada usuário (vários clientes)
_active_sessions = {}
_session_lock = threading.Lock()

def get_chat_session(chat_id):
    """Retorna uma sessão do Gemini inicializada com a memória específica do usuário."""
    chat_id = str(chat_id)
    with _session_lock:
        if chat_id not in _active_sessions:
            historico = carregar_memoria(chat_id)
            session = client_ai.chats.create(
                model='gemini-2.5-flash',
                config=types.GenerateContentConfig(system_instruction=instrucoes_coach),
                history=historico
            )
            _active_sessions[chat_id] = session
        return _active_sessions[chat_id]


def processar_mensagem_audio(chat_id, caminho_audio, prompt_adicional="Diga o que você entendeu do áudio e responda como o Coach."):
    """Faz o upload de um arquivo de áudio para o Gemini e processa a resposta amarrada a um usuário."""
    try:
        chat_id = str(chat_id)
        session = get_chat_session(chat_id)
        
        logger.info(f"Fazendo upload do áudio para o Gemini: {caminho_audio} (Chat ID: {chat_id})")
        arquivo_gemini = client_ai.files.upload(file=caminho_audio)
        
        conteudo = [arquivo_gemini]
        if prompt_adicional:
            conteudo.append(prompt_adicional)

        logger.info(f"Enviando áudio para a sessão de chat (ID: {chat_id})...")
        resposta = session.send_message(conteudo)
        
        # Como o banco guarda strings, nós salvamos pelo menos a instrução de envio de áudio para ter contexto na re-leitura
        guardar_memoria(chat_id, "user", f"[VOICE MESSAGE SENT] {prompt_adicional}")
        guardar_memoria(chat_id, "model", resposta.text)

        return resposta.text
    except Exception as e:
        logger.error(f"Erro ao processar áudio no Gemini (Chat ID: {chat_id}): {e}")
        return "Desculpe, tive um problema nos meus ouvidos digitais e não consegui processar o áudio. Pode escrever?"

