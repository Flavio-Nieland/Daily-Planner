# schedule.py
# Define as atividades de cada dia da semana e suas prioridades.
#
# Conceito: separamos os "dados" (o que fazer em cada dia) do "código" (a lógica
# de como exibir). Assim, se quiser mudar uma atividade, edita só este arquivo.

# Prioridade 1 = alta (fazer primeiro), Prioridade 2 = baixa (complementares)
PRIORITY = {
    "trabalhar": 1,
    "TCC": 1,
    "treinar": 1,
    "ler": 2,
    "alongar": 2,
    "musica": 2,
    "programação": 2,
    "Inglês": 2,
    "xadrez": 2,
    "programar": 2,
    "correr": 2,
    "PFC": 2,
    "ingles": 2,
}

# Atividades de cada dia. Chave = número do dia (0=segunda, 6=domingo),
# igual ao retorno de datetime.weekday() do Python.
WEEKLY_SCHEDULE = {
    0: ["trabalhar", "ler", "treinar", "alongar"],        # Segunda
    1: ["trabalhar", "TCC", "treinar", "musica"],          # Terça
    2: ["trabalhar", "PFC", "treinar", "programação"],     # Quarta
    3: ["trabalhar", "PFC", "treinar", "Inglês"],          # Quinta
    4: ["trabalhar", "xadrez", "programar", "correr"],     # Sexta
    5: ["alongar", "musica", "ler", "correr"],             # Sábado
    6: ["ler", "alongar", "ingles", "xadrez"],             # Domingo
}

DAY_NAMES = {
    0: "Segunda-feira",
    1: "Terça-feira",
    2: "Quarta-feira",
    3: "Quinta-feira",
    4: "Sexta-feira",
    5: "Sábado",
    6: "Domingo",
}


def get_today_schedule(weekday: int) -> list:
    """
    Retorna a lista de atividades do dia com suas prioridades.

    weekday: número do dia (0=segunda, 6=domingo)
    Retorna: lista de dicionários com 'name', 'priority' e 'priority_label'

    Exemplo de retorno:
    [
        {"name": "trabalhar", "priority": 1, "priority_label": "Alta"},
        {"name": "ler",       "priority": 2, "priority_label": "Baixa"},
    ]
    """
    activities = WEEKLY_SCHEDULE.get(weekday, [])
    return [
        {
            "name": activity,
            "priority": PRIORITY.get(activity, 2),
            "priority_label": "Alta" if PRIORITY.get(activity, 2) == 1 else "Baixa",
        }
        for activity in activities
    ]
