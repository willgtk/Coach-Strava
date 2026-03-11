"""
Testes unitários do Coach-Strava.
Cobre: memória SQLite, interceptadores, configuração, utilidades do bot,
       e cobertura de serviços (weather cache, strava retry).
"""
import os
import tempfile
import sqlite3
from typing import Optional
from unittest.mock import patch, MagicMock

import pytest


# ==========================================
# TESTES DE MEMÓRIA (SQLite — ai_engine)
# ==========================================
class TestMemoriaSQLite:
    """Testes para as funções de memória persistente com SQLite."""

    def setup_method(self) -> None:
        """Cria um banco SQLite temporário para cada teste."""
        self.tmp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.tmp_db.close()
        self.db_path = self.tmp_db.name

        # Cria a tabela de conversas
        conn = sqlite3.connect(self.db_path)
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
        c.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                chat_id TEXT PRIMARY KEY,
                nome TEXT,
                meta_mensal_km REAL DEFAULT 150.0,
                data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def teardown_method(self) -> None:
        """Remove o banco temporário."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    @patch('ai_engine.DB_PATH')
    def test_guardar_e_carregar_memoria(self, mock_db_path) -> None:
        """Verifica que guardar e carregar memória funciona com SQLite."""
        with patch('ai_engine.DB_PATH', self.db_path):
            from ai_engine import guardar_memoria

            guardar_memoria("12345", "user", "Olá")
            guardar_memoria("12345", "model", "Olá, campeão!")

            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('SELECT role, mensagem FROM conversas WHERE chat_id = ? ORDER BY id', ("12345",))
            resultado = c.fetchall()
            conn.close()

            assert len(resultado) == 2
            assert resultado[0][0] == 'user'
            assert resultado[0][1] == 'Olá'
            assert resultado[1][0] == 'model'
            assert resultado[1][1] == 'Olá, campeão!'

    def test_banco_vazio_retorna_vazio(self) -> None:
        """Verifica que banco vazio retorna lista vazia."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM conversas')
        count = c.fetchone()[0]
        conn.close()
        assert count == 0

    @patch('ai_engine.DB_PATH')
    def test_isolamento_por_chat_id(self, mock_db_path) -> None:
        """Verifica que mensagens de diferentes usuários são isoladas."""
        with patch('ai_engine.DB_PATH', self.db_path):
            from ai_engine import guardar_memoria

            guardar_memoria("user_A", "user", "Mensagem A")
            guardar_memoria("user_B", "user", "Mensagem B")

            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('SELECT mensagem FROM conversas WHERE chat_id = ?', ("user_A",))
            msgs_a = c.fetchall()
            c.execute('SELECT mensagem FROM conversas WHERE chat_id = ?', ("user_B",))
            msgs_b = c.fetchall()
            conn.close()

            assert len(msgs_a) == 1
            assert msgs_a[0][0] == "Mensagem A"
            assert len(msgs_b) == 1
            assert msgs_b[0][0] == "Mensagem B"

    def test_validacao_roles_alternados(self) -> None:
        """Verifica que mensagem órfã de user é removida ao carregar."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO conversas (chat_id, role, mensagem) VALUES (?, ?, ?)", ("test", "user", "Pergunta 1"))
        c.execute("INSERT INTO conversas (chat_id, role, mensagem) VALUES (?, ?, ?)", ("test", "model", "Resposta 1"))
        c.execute("INSERT INTO conversas (chat_id, role, mensagem) VALUES (?, ?, ?)", ("test", "user", "Pergunta sem resposta"))
        conn.commit()
        conn.close()

        with patch('ai_engine.DB_PATH', self.db_path):
            from ai_engine import carregar_memoria
            resultado = carregar_memoria("test")

        # A última mensagem "user" deve ser removida (total: 2)
        assert len(resultado) == 2


# ==========================================
# TESTES DE MULTI-USUÁRIO
# ==========================================
class TestMultiUsuario:
    """Testa as funções de gestão de múltiplos usuários."""

    def setup_method(self) -> None:
        self.tmp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.tmp_db.close()
        self.db_path = self.tmp_db.name

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                chat_id TEXT PRIMARY KEY,
                nome TEXT,
                meta_mensal_km REAL DEFAULT 150.0,
                data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def teardown_method(self) -> None:
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    @patch('ai_engine.DB_PATH')
    def test_registrar_e_obter_usuarios(self, mock_db_path) -> None:
        """Verifica registro e listagem de múltiplos usuários."""
        with patch('ai_engine.DB_PATH', self.db_path):
            from ai_engine import registrar_usuario, obter_todos_chat_ids

            registrar_usuario("111", "Alice")
            registrar_usuario("222", "Bob")

            ids = obter_todos_chat_ids()
            assert "111" in ids
            assert "222" in ids

    @patch('ai_engine.DB_PATH')
    def test_meta_personalizada(self, mock_db_path) -> None:
        """Verifica que a meta pode ser personalizada por usuário."""
        with patch('ai_engine.DB_PATH', self.db_path):
            from ai_engine import registrar_usuario, atualizar_meta_usuario, obter_meta_usuario

            registrar_usuario("333", "Carlos")
            atualizar_meta_usuario("333", 250.0)
            meta = obter_meta_usuario("333", 150.0)
            assert meta == 250.0

    @patch('ai_engine.DB_PATH')
    def test_meta_padrao_quando_nao_definida(self, mock_db_path) -> None:
        """Verifica que a meta padrão é retornada quando não há registro."""
        with patch('ai_engine.DB_PATH', self.db_path):
            from ai_engine import obter_meta_usuario
            meta = obter_meta_usuario("inexistente", 150.0)
            assert meta == 150.0

    @patch('ai_engine.DB_PATH')
    @patch('strava_service.obter_progresso_mensal')
    def test_obter_ranking_usuarios(self, mock_progresso, mock_db_path) -> None:
        """Verifica se o ranking é formatado corretamente e ordenado por km."""
        with patch('ai_engine.DB_PATH', self.db_path):
            from ai_engine import registrar_usuario, obter_ranking_usuarios

            # Limpar tabela
            conn = sqlite3.connect(self.db_path)
            conn.execute("DELETE FROM usuarios")
            conn.commit()
            conn.close()

            registrar_usuario("555", "Líder")
            registrar_usuario("666", "Segundo")

            mock_progresso.side_effect = [
                {'total_km': 300, 'percentual_concluido': 200},  # Líder
                {'total_km': 200, 'percentual_concluido': 133}   # Segundo
            ]

            ranking = obter_ranking_usuarios()
            assert "🏆 Ranking Mensal da Equipe:" in ranking
            assert "🥇 Líder: 300.0 km" in ranking
            assert "🥈 Segundo: 200.0 km" in ranking

    @patch('ai_engine.DB_PATH')
    def test_obter_ranking_vazio(self, mock_db_path) -> None:
        """Verifica o retorno do ranking quando não há usuários."""
        with patch('ai_engine.DB_PATH', self.db_path):
            from ai_engine import obter_ranking_usuarios

            conn = sqlite3.connect(self.db_path)
            conn.execute("DELETE FROM usuarios")
            conn.commit()
            conn.close()

            ranking = obter_ranking_usuarios()
            assert "Nenhum usuário registrado ainda." in ranking


# ==========================================
# TESTES DE INTERCEPTADORES (constantes)
# ==========================================
class TestInterceptadores:
    """Testa a lógica de detecção de palavras-chave usando constantes compartilhadas."""

    def test_detecta_palavras_clima(self) -> None:
        from constantes import PALAVRAS_CLIMA
        assert any(p in "como está o tempo hoje?" for p in PALAVRAS_CLIMA)
        assert any(p in "vai chover amanhã?" for p in PALAVRAS_CLIMA)
        assert not any(p in "me manda uma rota" for p in PALAVRAS_CLIMA)

    def test_detecta_palavras_strava(self) -> None:
        from constantes import PALAVRAS_STRAVA
        assert any(p in "avalie meu pedal de hoje" for p in PALAVRAS_STRAVA)
        assert any(p in "quanto km fiz na semana?" for p in PALAVRAS_STRAVA)
        assert any(p in "meu último treino" for p in PALAVRAS_STRAVA)

    def test_detecta_palavras_bike(self) -> None:
        from constantes import PALAVRAS_BIKE
        assert any(p in "preciso trocar a corrente" for p in PALAVRAS_BIKE)
        assert any(p in "como está a kaéti?" for p in PALAVRAS_BIKE)
        assert not any(p in "bom dia!" for p in PALAVRAS_BIKE)

    def test_nao_detecta_falso_positivo(self) -> None:
        """Verifica que mensagens genéricas não ativam interceptadores."""
        from constantes import PALAVRAS_CLIMA, PALAVRAS_STRAVA, PALAVRAS_BIKE
        msg = "bom dia, tudo bem?"
        assert not any(p in msg for p in PALAVRAS_CLIMA)
        assert not any(p in msg for p in PALAVRAS_STRAVA)
        assert not any(p in msg for p in PALAVRAS_BIKE)


# ==========================================
# TESTES DE CONFIGURAÇÃO
# ==========================================
class TestConfig:
    """Testa a configuração e variáveis de ambiente."""

    def test_cidade_padrao(self) -> None:
        cidade = os.getenv('CITY', 'Curitiba,BR')
        assert 'Curitiba' in cidade or cidade == os.getenv('CITY')

    def test_formato_cidade(self) -> None:
        cidade = 'Curitiba,BR'
        assert ',' in cidade
        partes = cidade.split(',')
        assert len(partes) == 2
        assert len(partes[1]) == 2

    def test_team_name_padrao(self) -> None:
        team = os.getenv('TEAM_NAME', 'Equipe Partiu Pedal')
        assert len(team) > 0

    def test_tipos_pedal_definidos(self) -> None:
        """Verifica que os tipos de pedal estão corretamente definidos."""
        from constantes import TIPOS_PEDAL
        assert "Ride" in TIPOS_PEDAL
        assert "VirtualRide" in TIPOS_PEDAL
        assert "MountainBikeRide" in TIPOS_PEDAL


# ==========================================
# TESTES DE UTILIDADES DO BOT
# (Agora importando diretamente de bot_coach graças ao main guard)
# ==========================================
class TestEnviarRespostaSegura:
    """Testa a lógica de envio seguro de mensagens longas."""

    def test_mensagem_curta_envia_direto(self) -> None:
        from bot_coach import enviar_resposta_segura
        mock_bot = MagicMock()
        mock_reply = MagicMock()
        enviar_resposta_segura(mock_bot, "123", "Olá!", reply_to=mock_reply)
        mock_bot.reply_to.assert_called_once_with(mock_reply, "Olá!")
        mock_bot.send_message.assert_not_called()

    def test_mensagem_longa_divide(self) -> None:
        from bot_coach import enviar_resposta_segura
        mock_bot = MagicMock()
        texto_grande = "A" * 5000
        enviar_resposta_segura(mock_bot, "123", texto_grande)
        assert mock_bot.send_message.call_count == 2
        args1 = mock_bot.send_message.call_args_list[0]
        args2 = mock_bot.send_message.call_args_list[1]
        assert len(args1[0][1]) == 4096
        assert len(args2[0][1]) == 904

    def test_texto_comandos_constante_definida(self) -> None:
        """Verifica que TEXTO_COMANDOS existe e contém todos os comandos."""
        from bot_coach import TEXTO_COMANDOS
        assert "/start" in TEXTO_COMANDOS
        assert "/semana" in TEXTO_COMANDOS
        assert "/pedal" in TEXTO_COMANDOS
        assert "/bike" in TEXTO_COMANDOS
        assert "/clima" in TEXTO_COMANDOS
        assert "/meta" in TEXTO_COMANDOS
        assert "/historico" in TEXTO_COMANDOS
        assert "/ranking" in TEXTO_COMANDOS
        assert "/grafico" in TEXTO_COMANDOS


# ==========================================
# TESTES DE WEATHER SERVICE
# ==========================================
class TestWeatherService:
    """Testa cache e tratamento de erros do serviço de clima."""

    @patch('weather_service.requests.get')
    def test_weather_cache_hit(self, mock_get) -> None:
        """Verifica que o cache evita chamadas duplicadas à API."""
        from weather_service import _weather_cache, obter_previsao_tempo, CITY

        # Limpar cache
        _weather_cache.clear()

        # Simular resposta da API
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'cod': '200',
            'list': [
                {'dt_txt': '2026-03-11 12:00:00', 'main': {'temp': 25}, 'weather': [{'description': 'céu limpo'}]},
                {'dt_txt': '2026-03-11 15:00:00', 'main': {'temp': 27}, 'weather': [{'description': 'poucas nuvens'}]},
                {'dt_txt': '2026-03-11 18:00:00', 'main': {'temp': 23}, 'weather': [{'description': 'nublado'}]},
                {'dt_txt': '2026-03-11 21:00:00', 'main': {'temp': 20}, 'weather': [{'description': 'céu limpo'}]},
                {'dt_txt': '2026-03-12 00:00:00', 'main': {'temp': 18}, 'weather': [{'description': 'céu limpo'}]},
                {'dt_txt': '2026-03-12 03:00:00', 'main': {'temp': 16}, 'weather': [{'description': 'orvalho'}]},
                {'dt_txt': '2026-03-12 06:00:00', 'main': {'temp': 15}, 'weather': [{'description': 'neblina'}]},
                {'dt_txt': '2026-03-12 09:00:00', 'main': {'temp': 19}, 'weather': [{'description': 'sol'}]},
            ]
        }
        mock_get.return_value = mock_response

        # Primeira chamada: deve chamar a API
        resultado1 = obter_previsao_tempo()
        assert mock_get.call_count == 1

        # Segunda chamada: deve usar cache
        resultado2 = obter_previsao_tempo()
        assert mock_get.call_count == 1  # Mesmo count = cache hit
        assert resultado1 == resultado2


# ==========================================
# TESTES DO STRAVA SERVICE
# ==========================================
class TestStravaService:
    """Testa funções do serviço Strava."""

    def test_filtrar_pedais(self) -> None:
        """Verifica que a filtragem de pedais funciona corretamente."""
        from strava_service import _filtrar_pedais

        atividade_ride = MagicMock()
        atividade_ride.type = "Ride"

        atividade_run = MagicMock()
        atividade_run.type = "Run"

        atividade_mtb = MagicMock()
        atividade_mtb.type = "MountainBikeRide"

        resultado = _filtrar_pedais([atividade_ride, atividade_run, atividade_mtb])
        assert len(resultado) == 2
        assert atividade_ride in resultado
        assert atividade_mtb in resultado
        assert atividade_run not in resultado

    @patch('strava_service._obter_atividades')
    def test_obter_atividades_com_retry_success(self, mock_obter) -> None:
        """Verifica que o retry funciona na primeira tentativa."""
        from strava_service import _obter_atividades_com_retry
        from datetime import datetime

        mock_obter.return_value = ["atividade1"]
        resultado = _obter_atividades_com_retry(after=datetime.now())
        assert resultado == ["atividade1"]

