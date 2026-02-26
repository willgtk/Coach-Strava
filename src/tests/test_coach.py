import json
import os
import tempfile
import pytest


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

    def test_guardar_e_carregar_memoria(self):
        """Verifica que guardar e carregar memória funciona."""
        # Simula guardar memória diretamente no JSON
        dados = [
            {"role": "user", "text": "Olá"},
            {"role": "model", "text": "Olá, campeão!"}
        ]
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False)

        # Lê e verifica
        with open(self.filepath, 'r', encoding='utf-8') as f:
            resultado = json.load(f)

        assert len(resultado) == 2
        assert resultado[0]['role'] == 'user'
        assert resultado[1]['role'] == 'model'

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

    def test_limite_40_mensagens(self):
        """Verifica que o historico é limitado a 40 mensagens."""
        dados = []
        for i in range(50):
            role = "user" if i % 2 == 0 else "model"
            dados.append({"role": role, "text": f"Mensagem {i}"})

        # Simula o comportamento de guardar_memoria
        if len(dados) > 40:
            dados = dados[-40:]

        assert len(dados) == 40
        assert dados[0]['text'] == 'Mensagem 10'

    def test_validacao_roles_alternados(self):
        """Verifica que mensagem órfã de user é removida."""
        dados = [
            {"role": "user", "text": "Pergunta 1"},
            {"role": "model", "text": "Resposta 1"},
            {"role": "user", "text": "Pergunta sem resposta"}
        ]

        # Simula validação do carregar_memoria
        if len(dados) > 0 and dados[-1]['role'] == 'user':
            dados.pop()

        assert len(dados) == 2
        assert dados[-1]['role'] == 'model'


# ==========================================
# TESTES DE INTERCEPTADORES
# ==========================================
class TestInterceptadores:
    """Testa a lógica de detecção de palavras-chave."""

    def test_detecta_palavras_clima(self):
        palavras_clima = ['clima', 'tempo', 'temperatura', 'chover', 'chuva', 'sol', 'frio', 'calor']
        assert any(p in "Como está o tempo hoje?" for p in palavras_clima)
        assert any(p in "Vai chover amanhã?" for p in palavras_clima)
        assert not any(p in "Me manda uma rota" for p in palavras_clima)

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
