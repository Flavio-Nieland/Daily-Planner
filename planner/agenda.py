"""Quais folhas entram na edição de cada dia.

Fonte: AGENDA.md, decidida com o Flávio em 2026-08-18. Substitui o WEEKLY_SCHEDULE
do schedule.py, que divergia da rotina real dele. O jornal sai sete dias por semana.
"""

# Folhas que aparecem todos os dias, na ordem em que entram na edição.
FIXAS = ["resumo", "tempo", "dieta", "biblia", "album", "peso"]

# Tópicos por dia da semana, no padrão do datetime: 0 = segunda ... 6 = domingo.
POR_DIA = {
    0: ["alongamento", "treino", "ingles", "musica"],
    1: ["alongamento", "treino", "programacao", "xadrez", "livros"],
    2: ["alongamento", "treino", "musica"],
    3: ["alongamento", "corrida", "ingles", "xadrez", "livros"],
    4: ["alongamento", "treino", "programacao", "jogo"],
    5: ["corrida", "livros", "comida", "fazenda"],
    6: ["jogo", "fazenda", "comida"],
}

# Nome de exibição de cada tópico. As bolinhas do rodapé usam isto no title.
NOMES = {
    "resumo": "Resumo", "tempo": "Tempo", "dieta": "Dieta", "biblia": "Bíblia",
    "album": "Álbum", "peso": "Peso", "alongamento": "Alongamento", "treino": "Treino",
    "corrida": "Corrida", "ingles": "Inglês", "musica": "Música",
    "programacao": "Programação", "xadrez": "Xadrez", "livros": "Livros",
    "jogo": "Jogo", "comida": "Comida", "fazenda": "Fazenda",
}


def topicos_do_dia(data) -> list[str]:
    """Os tópicos da edição daquela data, fixos primeiro."""
    return FIXAS + POR_DIA[data.weekday()]
