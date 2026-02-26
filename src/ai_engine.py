import os
import json
import threading
from google import genai
from google.genai import types

from config import GOOGLE_API_KEY, FICHEIRO_MEMORIA, TEAM_NAME, logger

_memory_lock = threading.Lock()

# ==========================================
# MÓDULO DE MEMÓRIA PERSISTENTE
# ==========================================


def carregar_memoria():
    """Carrega o histórico de conversa do ficheiro JSON."""
    with _memory_lock:
        return _carregar_memoria_interno()


def _carregar_memoria_interno():
    if not os.path.exists(FICHEIRO_MEMORIA):
        return []
    try:
        with open(FICHEIRO_MEMORIA, 'r', encoding='utf-8') as f:
            dados = json.load(f)

            # Validação de integridade: a API exige que os papéis alternem (user -> model).
            if len(dados) > 0 and dados[-1]['role'] == 'user':
                dados.pop()

            historico = []
            for msg in dados:
                historico.append(
                    types.Content(
                        role=msg['role'],
                        parts=[types.Part.from_text(text=msg['text'])]
                    )
                )
            logger.info(f"Memória restaurada: {len(historico)} interações carregadas.")
            return historico
    except json.JSONDecodeError as e:
        logger.error(f"Ficheiro de memória corrompido: {e}")
        return []
    except Exception as e:
        logger.error(f"Erro ao carregar memória: {e}")
        return []


def guardar_memoria(role, text):
    """Guarda uma nova mensagem no histórico persistente."""
    with _memory_lock:
        dados = []
        if os.path.exists(FICHEIRO_MEMORIA):
            try:
                with open(FICHEIRO_MEMORIA, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Memória corrompida ao guardar, reiniciando: {e}")
                dados = []
            except Exception as e:
                logger.error(f"Erro ao ler memória existente: {e}")
                dados = []

        dados.append({"role": role, "text": text})

        # Limita o histórico às últimas 40 mensagens para poupar tokens
        if len(dados) > 40:
            dados = dados[-40:]

        try:
            with open(FICHEIRO_MEMORIA, 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Erro ao escrever memória: {e}")


# ==========================================
# CÉREBRO DA IA (GOOGLE GEMINI)
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

chat_session = client_ai.chats.create(
    model='gemini-2.5-flash',
    config=types.GenerateContentConfig(system_instruction=instrucoes_coach),
    history=carregar_memoria()
)
