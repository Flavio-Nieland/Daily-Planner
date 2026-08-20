"""Folha de abertura — o que tem na edição de hoje.

Sem LLM: é a lista das folhas que a edição realmente traz, para ele saber o que vem antes
de virar a primeira folha.
"""

from planner.agenda import NOMES

DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
        "sexta-feira", "sábado", "domingo"]


def blocos(data, na_edicao: list[str]) -> list[str]:
    """na_edicao: os ids dos tópicos que ganharam folha nesta edição, o Resumo incluído."""
    demais = [t for t in na_edicao if t != "resumo"]
    dia = DIAS[data.weekday()]
    plural = "tópico" if len(demais) == 1 else "tópicos"
    abertura = (
        f'<div class="bloco"><p class="lede"><span class="capitular">{dia[0].upper()}</span>'
        f'{dia[1:]}, {data.strftime("%d/%m/%Y")}. '
        f'A edição de hoje tem {len(demais)} {plural}.</p></div>'
    )
    itens = "".join(f'<li><b>{i}</b> {NOMES[t]}</li>' for i, t in enumerate(demais, start=1))
    sumario = f'<div class="bloco"><h4>Nesta edição</h4><ol class="sumario">{itens}</ol></div>'
    return [abertura, sumario]
