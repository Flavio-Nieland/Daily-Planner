"""Caderno do Resumo — a edição de hoje, o que falta hoje e o balanço da semana.

Sem LLM. A primeira página é a abertura de sempre (a lista dos tópicos da edição); as outras
duas são desenhadas no navegador por caderno-resumo.js, a partir das marcações dele
(2026-11-03): o diário passa a saber o que ele fez, e não só o que prescreveu.
"""

from planner.agenda import NOMES

DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
        "sexta-feira", "sábado", "domingo"]


def caderno(data, na_edicao: list[str]) -> dict:
    """A abertura vai como blocos da primeira página; o resto o navegador monta."""
    return {"caderno": "resumo", "dados": {"hoje": data.isoformat()}, "blocos": blocos(data, na_edicao)}


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
