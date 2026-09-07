"""Quais folhas entram na edição de cada dia.

Fonte: AGENDA.md, decidida com o Flávio em 2026-08-18 e revista em 2026-09-07. Substitui o
WEEKLY_SCHEDULE do schedule.py, que divergia da rotina real dele. O jornal sai sete dias por
semana.

Revisão de 2026-09-07: Inglês trocou quinta por quarta; Xadrez e Livros trocaram quinta por
sexta; o Jogo saiu da sexta e ficou só no domingo; a quinta virou o dia do corpo, com Pilates
novo ao lado do Alongamento e da Corrida.
"""

# Folhas que aparecem todos os dias, na ordem em que entram na edição.
FIXAS = ["resumo", "tempo", "dieta", "biblia", "album", "peso"]

# Tópicos por dia da semana, no padrão do datetime: 0 = segunda ... 6 = domingo.
POR_DIA = {
    0: ["alongamento", "treino", "ingles", "musica"],
    1: ["alongamento", "treino", "programacao", "xadrez", "livros"],
    2: ["alongamento", "treino", "musica", "ingles"],
    3: ["alongamento", "pilates", "corrida"],
    4: ["alongamento", "treino", "programacao", "xadrez", "livros"],
    5: ["corrida", "livros", "comida", "fazenda"],
    6: ["jogo", "fazenda", "comida"],
}

# Nome de exibição de cada tópico. As bolinhas do rodapé usam isto no title.
NOMES = {
    "resumo": "Resumo", "tempo": "Tempo", "dieta": "Dieta", "biblia": "Bíblia",
    "album": "Álbum", "peso": "Peso", "alongamento": "Alongamento", "treino": "Treino",
    "corrida": "Corrida", "pilates": "Pilates", "ingles": "Inglês", "musica": "Música",
    "programacao": "Programação", "xadrez": "Xadrez", "livros": "Livros",
    "jogo": "Jogo", "comida": "Comida", "fazenda": "Fazenda",
}


def topicos_do_dia(data) -> list[str]:
    """Os tópicos da edição daquela data, fixos primeiro."""
    return FIXAS + POR_DIA[data.weekday()]
