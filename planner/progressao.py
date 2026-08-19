"""As regras de progressão — porte do módulo PROGRESSAO do protótipo de lógica.

A regra central: **a sessão avança por conclusão, não por data**. Faltar não queima
sessão, o plano espera. Daí decorrem as outras:

- não fez? amanhã é a mesma sessão, com o mesmo conteúdo (a geração é cacheada por
  sessão, nunca por data);
- marcar duas vezes no mesmo dia conta uma só, porque a chave da conclusão é o dia;
- marcar um tópico que não está na edição daquele dia não avança nada.

O ponteiro não é armazenado: é **derivado** das conclusões. O navegador só registra que
o dia foi feito — quem decide em que sessão ele está é o build, olhando a agenda.
"""

from datetime import date

from planner.agenda import topicos_do_dia

SECAO = "feito"


def chave(topico: str, dia: date) -> str:
    return f"{topico}:{dia.isoformat()}"


def na_edicao(topico: str, dia: date) -> bool:
    return topico in topicos_do_dia(dia)


def conclusoes(estado: dict, topico: str) -> list[date]:
    """Os dias em que ele marcou o tópico como feito — só os que valem.

    Uma marcação num dia em que o tópico não estava na edição é descartada aqui: o
    navegador pode mandar qualquer coisa, o build é quem confere.
    """
    registros = (estado.get(SECAO) or {})
    dias = []
    for k, valor in registros.items():
        if not valor or ":" not in k:
            continue
        nome, _, quando = k.partition(":")
        if nome != topico:
            continue
        try:
            dia = date.fromisoformat(quando)
        except ValueError:
            continue
        if na_edicao(topico, dia):
            dias.append(dia)
    return sorted(dias)


def posicao(estado: dict, topico: str, inicial: int, total: int) -> int:
    """A sessão da vez: a seguinte à última marcada como feita, sem passar do total."""
    return min(inicial + len(conclusoes(estado, topico)), total)


def feito_hoje(estado: dict, topico: str, dia: date) -> bool:
    return bool((estado.get(SECAO) or {}).get(chave(topico, dia)))


def ultima_conclusao(estado: dict, topico: str) -> date | None:
    feitos = conclusoes(estado, topico)
    return feitos[-1] if feitos else None
