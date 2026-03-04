"""
Motor de IA do Coach-Strava.
Gerencia memória persistente (SQLite), sessões de chat do Gemini e processamento de áudio.
"""
import os
import threading
import sqlite3
from typing import Optional
from contextlib import contextmanager

from google import genai
from google.genai import types
from cachetools import TTLCache

from config import GOOGLE_API_KEY, DB_PATH, TEAM_NAME, logger

_memory_lock = threading.Lock()


# ==========================================
# CONTEXT MANAGER PARA CONEXÃO SQLITE
# ==========================================
@contextmanager
def get_db_connection():
    """Abre e fecha uma conexão SQLite de forma segura."""
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


# ==========================================
# MÓDULO DE MEMÓRIA PERSISTENTE (SQLite)
# ==========================================
def init_db() -> None:
    """Inicializa o banco de dados e cria as tabelas se não existirem."""
    with _memory_lock:
        try:
            with get_db_connection() as conn:
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
                # Tabela para armazenar múltiplos chat IDs (multi-usuário proativo)
                c.execute('''
                    CREATE TABLE IF NOT EXISTS usuarios (
                        chat_id TEXT PRIMARY KEY,
                        nome TEXT,
                        meta_mensal_km REAL DEFAULT 150.0,
                        data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Erro ao inicializar o banco SQLite: {e}")


# Inicializa o banco assim que o módulo for carregado
init_db()


def carregar_memoria(chat_id: str) -> list[types.Content]:
    """Carrega o histórico de conversa do banco de dados para um usuário específico."""
    chat_id = str(chat_id)
    with _memory_lock:
        historico: list[types.Content] = []
        try:
            with get_db_connection() as conn:
                c = conn.cursor()

                # Buscar as últimas 40 mensagens, ordenadas da mais antiga para a mais recente
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

                # Validação: a API exige que os papéis alternem (user -> model).
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


def guardar_memoria(chat_id: str, role: str, text: str) -> None:
    """Guarda uma nova mensagem no banco de dados para um usuário específico."""
    chat_id = str(chat_id)
    with _memory_lock:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute('INSERT INTO conversas (chat_id, role, mensagem) VALUES (?, ?, ?)', (chat_id, role, text))
                conn.commit()

                # Limpar mensagens muito antigas para não inflar o DB
                c.execute('''
                    DELETE FROM conversas WHERE id NOT IN (
                        SELECT id FROM conversas WHERE chat_id = ? ORDER BY id DESC LIMIT 100
                    ) AND chat_id = ?
                ''', (chat_id, chat_id))
                conn.commit()

        except sqlite3.Error as e:
            logger.error(f"Erro ao guardar memória no SQLite: {e}")


# ==========================================
# FUNÇÕES MULTI-USUÁRIO
# ==========================================
def registrar_usuario(chat_id: str, nome: Optional[str] = None) -> None:
    """Registra ou atualiza um usuário no banco para mensagens proativas.
    Usa INSERT OR IGNORE para não sobrescrever meta_mensal_km existente."""
    chat_id = str(chat_id)
    with _memory_lock:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                # INSERT OR IGNORE preserva os dados se o usuário já existir
                c.execute('''
                    INSERT OR IGNORE INTO usuarios (chat_id, nome)
                    VALUES (?, ?)
                ''', (chat_id, nome))
                # Atualiza apenas o nome (não altera meta_mensal_km)
                if nome:
                    c.execute('UPDATE usuarios SET nome = ? WHERE chat_id = ?', (nome, chat_id))
                conn.commit()
                logger.info(f"Usuário registrado/atualizado: {chat_id} ({nome})")
        except sqlite3.Error as e:
            logger.error(f"Erro ao registrar usuário: {e}")


def obter_todos_chat_ids() -> list[str]:
    """Retorna todos os chat IDs registrados para mensagens proativas."""
    with _memory_lock:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute('SELECT chat_id FROM usuarios')
                return [row[0] for row in c.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Erro ao obter chat IDs: {e}")
            return []


def obter_meta_usuario(chat_id: str, meta_padrao: float) -> float:
    """Retorna a meta mensal personalizada do usuário ou a padrão."""
    chat_id = str(chat_id)
    with _memory_lock:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute('SELECT meta_mensal_km FROM usuarios WHERE chat_id = ?', (chat_id,))
                row = c.fetchone()
                if row and row[0] is not None:
                    return float(row[0])
                return meta_padrao
        except sqlite3.Error as e:
            logger.error(f"Erro ao obter meta do usuário: {e}")
            return meta_padrao


def atualizar_meta_usuario(chat_id: str, nova_meta: float) -> bool:
    """Atualiza a meta mensal de um usuário específico."""
    chat_id = str(chat_id)
    with _memory_lock:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute('UPDATE usuarios SET meta_mensal_km = ? WHERE chat_id = ?', (nova_meta, chat_id))
                conn.commit()
                return c.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Erro ao atualizar meta do usuário: {e}")
            return False


# ==========================================
# CÉREBRO DA IA E GERENCIAMENTO DE SESSÕES
# ==========================================
instrucoes_coach: str = f"""
Você é um parceiro e treinador de Mountain Bike focado em condicionamento e qualidade de vida. 
Seu aluno faz parte da {TEAM_NAME} e quer ser o melhor ciclista! Você receberá os dados da bicicleta principal dele.
Ele não treina para competições, o objetivo dele é construir uma base aeróbica forte ("ter motor") para estar sempre pronto para qualquer pedal com o grupo, sem sofrer nas subidas.
Analise os dados do Strava, sugira treinos focados em constância e resistência, e seja um motivador amigável.
Sempre responda de forma concisa, direta e com bom humor, ideal para leitura no Telegram.

IMPORTANTE: Quando dados do Strava forem injetados na conversa via [DADOS STRAVA: ...] ou [DADOS ÚLTIMO PEDAL: ...], 
USE esses dados para responder ao atleta. Nunca diga que não tem acesso aos dados se eles foram fornecidos.
"""

client_ai = genai.Client(api_key=GOOGLE_API_KEY)

# Sessões de chat com expiração por inatividade (TTL de 30 minutos)
_active_sessions: TTLCache = TTLCache(maxsize=100, ttl=1800)
_session_lock = threading.Lock()


def get_chat_session(chat_id: str):
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


def processar_mensagem_audio(chat_id: str, caminho_audio: str, prompt_adicional: str = "Diga o que você entendeu do áudio e responda como o Coach.") -> str:
    """Faz o upload de um arquivo de áudio para o Gemini e processa a resposta."""
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

        # Como o banco guarda strings, salvamos a instrução de envio para ter contexto na re-leitura
        guardar_memoria(chat_id, "user", f"[VOICE MESSAGE SENT] {prompt_adicional}")
        guardar_memoria(chat_id, "model", resposta.text)

        return resposta.text
    except Exception as e:
        logger.error(f"Erro ao processar áudio no Gemini (Chat ID: {chat_id}): {e}")
        return "Desculpe, tive um problema nos meus ouvidos digitais e não consegui processar o áudio. Pode escrever?"


def processar_mensagem_foto(chat_id: str, caminho_foto: str, prompt_adicional: str = "O atleta enviou esta foto. Analise a imagem e responda como o Coach.") -> str:
    """Faz o upload de uma foto para o Gemini e processa a resposta com análise visual."""
    try:
        chat_id = str(chat_id)
        session = get_chat_session(chat_id)

        logger.info(f"Fazendo upload da foto para o Gemini: {caminho_foto} (Chat ID: {chat_id})")
        arquivo_gemini = client_ai.files.upload(file=caminho_foto)

        conteudo = [arquivo_gemini]
        if prompt_adicional:
            conteudo.append(prompt_adicional)

        logger.info(f"Enviando foto para a sessão de chat (ID: {chat_id})...")
        resposta = session.send_message(conteudo)

        guardar_memoria(chat_id, "user", f"[PHOTO SENT] {prompt_adicional}")
        guardar_memoria(chat_id, "model", resposta.text)

        return resposta.text
    except Exception as e:
        logger.error(f"Erro ao processar foto no Gemini (Chat ID: {chat_id}): {e}")
        return "Desculpe, não consegui analisar a foto. Pode enviar novamente ou descrever por texto?"
