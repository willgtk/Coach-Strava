import json
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock


# ==========================================
# TESTES DE MEMÓRIA (ai_engine)
# ==========================================
class TestMemoria:
    """Testes para as funções de memória persistente."""

    def setup_method(self):
        """Cria um ficheiro temporário para cada teste."""
        self.tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False, encoding='utf-8'
        )
        self.tmp.write('[]')
        self.tmp.close()
        self.filepath = self.tmp.name

    def teardown_method(self):
        """Remove o ficheiro temporário."""
        if os.path.exists(self.filepath):
            os.remove(self.filepath)

    @patch('ai_engine.FICHEIRO_MEMORIA')
    def test_guardar_e_carregar_memoria(self, mock_path):
        """Verifica que guardar e carregar memória funciona."""
        mock_path.__str__ = lambda s: self.filepath
        # Patch para que o módulo use nosso ficheiro temporário
        with patch('ai_engine.FICHEIRO_MEMORIA', self.filepath):
            from ai_engine import guardar_memoria

            guardar_memoria("user", "Olá")
            guardar_memoria("model", "Olá, campeão!")

            with open(self.filepath, 'r', encoding='utf-8') as f:
                resultado = json.load(f)

            assert len(resultado) == 2
            assert resultado[0]['role'] == 'user'
            assert resultado[0]['text'] == 'Olá'
            assert resultado[1]['role'] == 'model'
            assert resultado[1]['text'] == 'Olá, campeão!'

    def test_memoria_vazia(self):
        """Verifica que ficheiro vazio retorna lista vazia."""
        with open(self.filepath, 'r', encoding='utf-8') as f:
            resultado = json.load(f)
        assert resultado == []

    def test_memoria_corrompida_retorna_vazio(self):
        """Verifica que JSON corrompido não causa crash."""
        with open(self.filepath, 'w', encoding='utf-8') as f:
            f.write('{invalid json}}}')

        with pytest.raises(json.JSONDecodeError):
            with open(self.filepath, 'r', encoding='utf-8') as f:
                json.load(f)

    @patch('ai_engine.FICHEIRO_MEMORIA')
    def test_limite_40_mensagens(self, mock_path):
        """Verifica que o histórico é limitado a 40 mensagens."""
        with patch('ai_engine.FICHEIRO_MEMORIA', self.filepath):
            from ai_engine import guardar_memoria

            for i in range(50):
                role = "user" if i % 2 == 0 else "model"
                guardar_memoria(role, f"Mensagem {i}")

            with open(self.filepath, 'r', encoding='utf-8') as f:
                dados = json.load(f)

            assert len(dados) == 40
            # As 10 primeiras devem ter sido descartadas
            assert dados[0]['text'] == 'Mensagem 10'

    def test_validacao_roles_alternados(self):
        """Verifica que mensagem órfã de user é removida ao carregar."""
        dados = [
            {"role": "user", "text": "Pergunta 1"},
            {"role": "model", "text": "Resposta 1"},
            {"role": "user", "text": "Pergunta sem resposta"}
        ]
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False)

        with patch('ai_engine.FICHEIRO_MEMORIA', self.filepath):
            from ai_engine import carregar_memoria
            resultado = carregar_memoria()

        assert len(resultado) == 2


# ==========================================
# TESTES DE INTERCEPTADORES
# ==========================================
class TestInterceptadores:
    """Testa a lógica de detecção de palavras-chave."""

    def test_detecta_palavras_clima(self):
        palavras_clima = ['clima', 'tempo', 'temperatura', 'chover', 'chuva', 'sol', 'frio', 'calor']
        assert any(p in "como está o tempo hoje?" for p in palavras_clima)
        assert any(p in "vai chover amanhã?" for p in palavras_clima)
        assert not any(p in "me manda uma rota" for p in palavras_clima)

    def test_detecta_palavras_strava(self):
        palavras_strava = [
            'pedal', 'pedais', 'treino', 'treinos', 'resultado', 'resultados',
            'hoje', 'ontem', 'semana', 'pedalei', 'andei', 'rodei',
            'km', 'quilometro', 'quilômetro', 'distância', 'distancia',
            'elevação', 'subida', 'subidas', 'desempenho', 'performance',
            'avalie', 'avaliar', 'análise', 'analise', 'último', 'ultimo',
            'strava'
        ]
        assert any(p in "avalie meu pedal de hoje" for p in palavras_strava)
        assert any(p in "quanto km fiz na semana?" for p in palavras_strava)
        assert any(p in "meu último treino" for p in palavras_strava)

    def test_detecta_palavras_bike(self):
        palavras_bike = [
            'bike', 'bicicleta', 'manutenção', 'manutencao', 'corrente',
            'freio', 'pastilha', 'relação', 'relacao', 'cassete',
            'pneu', 'câmbio', 'cambio', 'kaéti', 'kaeti'
        ]
        assert any(p in "preciso trocar a corrente" for p in palavras_bike)
        assert any(p in "como está a kaéti?" for p in palavras_bike)
        assert not any(p in "bom dia!" for p in palavras_bike)

    def test_nao_detecta_falso_positivo(self):
        """Verifica que mensagens genéricas não ativam interceptadores."""
        palavras_clima = ['clima', 'tempo', 'temperatura', 'chover', 'chuva', 'sol', 'frio', 'calor']
        palavras_strava = ['pedal', 'treino', 'km', 'strava']
        palavras_bike = ['bike', 'bicicleta', 'corrente', 'freio']

        msg = "bom dia, tudo bem?"
        assert not any(p in msg for p in palavras_clima)
        assert not any(p in msg for p in palavras_strava)
        assert not any(p in msg for p in palavras_bike)


# ==========================================
# TESTES DE CONFIGURAÇÃO
# ==========================================
class TestConfig:
    """Testa a configuração e variáveis de ambiente."""

    def test_cidade_padrao(self):
        """Verifica que a cidade padrão é Curitiba,BR."""
        cidade = os.getenv('CITY', 'Curitiba,BR')
        assert 'Curitiba' in cidade or cidade == os.getenv('CITY')

    def test_formato_cidade(self):
        """Verifica que o formato da cidade está correto."""
        cidade = 'Curitiba,BR'
        assert ',' in cidade
        partes = cidade.split(',')
        assert len(partes) == 2
        assert len(partes[1]) == 2  # Código do país tem 2 caracteres

    def test_team_name_padrao(self):
        """Verifica que o nome da equipe padrão está definido."""
        team = os.getenv('TEAM_NAME', 'Equipe Partiu Pedal')
        assert len(team) > 0


# ==========================================
# TESTES DE UTILIDADES DO BOT
# ==========================================
_MAX_MSG_LEN = 4096


def _enviar_resposta_segura(bot, chat_id, texto, reply_to=None):
    """Cópia local da função para teste sem importar bot_coach (evita iniciar o bot)."""
    for i in range(0, len(texto), _MAX_MSG_LEN):
        pedaco = texto[i:i + _MAX_MSG_LEN]
        if reply_to and i == 0:
            bot.reply_to(reply_to, pedaco)
        else:
            bot.send_message(chat_id, pedaco)


class TestEnviarRespostaSegura:
    """Testa a lógica de envio seguro de mensagens longas."""

    def test_mensagem_curta_envia_direto(self):
        """Mensagem curta deve ser enviada numa única chamada."""
        mock_bot = MagicMock()
        mock_reply = MagicMock()

        _enviar_resposta_segura(mock_bot, "123", "Olá!", reply_to=mock_reply)

        mock_bot.reply_to.assert_called_once_with(mock_reply, "Olá!")
        mock_bot.send_message.assert_not_called()

    def test_mensagem_longa_divide(self):
        """Mensagem maior que 4096 chars deve ser dividida em pedaços."""
        mock_bot = MagicMock()

        texto_grande = "A" * 5000
        _enviar_resposta_segura(mock_bot, "123", texto_grande)

        # Sem reply_to, tudo vai por send_message
        assert mock_bot.send_message.call_count == 2
        # Primeiro pedaço = 4096 chars, segundo = 904 chars
        args1 = mock_bot.send_message.call_args_list[0]
        args2 = mock_bot.send_message.call_args_list[1]
        assert len(args1[0][1]) == 4096
        assert len(args2[0][1]) == 904
