"""Folha do Pilates — prescrição pura, sem LLM e sem rotina própria.

A aula é conduzida por instrutora, então a folha não tem o que inventar de exercício: quem
sabe o que fazer com a lombar dele está na sala, e um modelo de linguagem só teria como
contribuir contraindicação. Mesma decisão do Xadrez, que manda a tática para o Chess.com em
vez de gerar posição.

O que sobra é o que a folha faz bem: dizer que hoje é dia e contar a constância. A contagem
é **derivada** das conclusões (`progressao`), nunca armazenada — igual ao resto do sistema.
"""

from datetime import date

from planner import progressao

TOPICO = "pilates"


def _constancia(dia: date, feitas: list[date]) -> str:
    if not feitas:
        return ('<div class="bloco"><h4>Constância</h4>'
                '<p class="miudo">Nenhuma aula marcada ainda. A primeira marcação começa a contagem.</p>'
                '</div>')
    ultima = feitas[-1]
    faz = (dia - ultima).days
    quando = "hoje" if faz == 0 else ("ontem" if faz == 1 else f"há {faz} dias")
    linhas = "".join(
        f'<li><span>{d.strftime("%d/%m")}</span><span class="qtd">aula {i}</span></li>'
        for i, d in list(enumerate(feitas, start=1))[-4:])
    return (f'<div class="bloco"><h4>Constância</h4>'
            f'<p class="destaque">{len(feitas)}</p>'
            f'<p class="miudo">aulas marcadas · a última {quando}, em {ultima.strftime("%d/%m")}</p>'
            f'<ul>{linhas}</ul></div>')


def blocos(dia: date, estado: dict) -> list[str]:
    feitas = progressao.conclusoes(estado, TOPICO)
    fez_hoje = progressao.feito_hoje(estado, TOPICO, dia)
    numero = len(feitas) if fez_hoje else len(feitas) + 1

    partes = [
        f'<div class="bloco presc"><h4>Aula {numero}</h4>'
        f'<p class="destaque-texto">Hoje é dia de Pilates.</p>'
        f'<p class="miudo">a aula é da instrutora; esta folha não prescreve exercício — '
        f'só registra que o dia aconteceu</p></div>',
        _constancia(dia, feitas),
    ]

    if fez_hoje:
        partes.append('<div class="bloco"><p class="feito">✓ pilates feito hoje</p></div>')
    else:
        partes.append(
            '<div class="bloco"><p class="campo">'
            f'<button type="button" class="marcar" data-topico="{TOPICO}" '
            f'data-dia="{dia.isoformat()}" id="pilates-marca">fiz hoje</button></p>'
            '<p class="miudo" id="pilates-aviso">Marcar entra na contagem da edição de amanhã.'
            '</p></div>')
    return partes
