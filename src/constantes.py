"""
Constantes compartilhadas do Coach-Strava.
Centraliza palavras-chave dos interceptadores e tipos de atividade.
"""
from typing import List

# Tipos de atividade do Strava considerados como pedal
TIPOS_PEDAL: List[str] = ["Ride", "VirtualRide", "MountainBikeRide"]

# Palavras-chave para interceptação inteligente na conversa livre
PALAVRAS_CLIMA: List[str] = [
    'clima', 'tempo', 'temperatura', 'chover', 'chuva', 'sol', 'frio', 'calor'
]

PALAVRAS_STRAVA: List[str] = [
    'pedal', 'pedais', 'treino', 'treinos', 'resultado', 'resultados',
    'hoje', 'ontem', 'semana', 'pedalei', 'andei', 'rodei',
    'km', 'quilometro', 'quilômetro', 'distância', 'distancia',
    'elevação', 'subida', 'subidas', 'desempenho', 'performance',
    'avalie', 'avaliar', 'análise', 'analise', 'último', 'ultimo',
    'strava'
]

PALAVRAS_BIKE: List[str] = [
    'bike', 'bicicleta', 'manutenção', 'manutencao', 'corrente',
    'freio', 'pastilha', 'relação', 'relacao', 'cassete',
    'pneu', 'câmbio', 'cambio', 'kaéti', 'kaeti'
]
