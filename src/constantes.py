"""
Constantes compartilhadas do Coach-Strava.
Centraliza palavras-chave dos interceptadores e tipos de atividade.
"""
from __future__ import annotations

# Tipos de atividade do Strava considerados como pedal
TIPOS_PEDAL: list[str] = ["Ride", "VirtualRide", "MountainBikeRide"]

# Palavras-chave para interceptação inteligente na conversa livre
PALAVRAS_CLIMA: list[str] = [
    'clima', 'tempo', 'temperatura', 'chover', 'chuva', 'sol', 'frio', 'calor'
]

PALAVRAS_STRAVA: list[str] = [
    'pedal', 'pedais', 'treino', 'treinos', 'resultado', 'resultados',
    'hoje', 'ontem', 'semana', 'pedalei', 'andei', 'rodei',
    'km', 'quilometro', 'quilômetro', 'distância', 'distancia',
    'elevação', 'subida', 'subidas', 'desempenho', 'performance',
    'avalie', 'avaliar', 'análise', 'analise', 'último', 'ultimo',
    'strava'
]

PALAVRAS_BIKE: list[str] = [
    'bike', 'bicicleta', 'manutenção', 'manutencao', 'corrente',
    'freio', 'pastilha', 'relação', 'relacao', 'cassete',
    'pneu', 'câmbio', 'cambio', 'kaéti', 'kaeti'
]
