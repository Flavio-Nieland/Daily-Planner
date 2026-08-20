"""Folha do Alongamento — rotina fixa, sem LLM.

Ganho de amplitude vem de repetir a mesma coisa por semanas, não de rotina nova todo dia.
Por isso `get_stretching_plan()` saiu: era a única fonte do tópico e gerava sequência nova
a cada dia, o oposto do que produz resultado.

O conteúdo é a rotina aprovada em 2026-08-18, com as ilustrações que ele desenhou à mão —
extraídas para `esqueletos/alongamento-rotina.json` e versionadas.
"""

import json
from datetime import date
from pathlib import Path

ROTINA = Path(__file__).resolve().parent.parent.parent / "esqueletos" / "alongamento-rotina.json"
SECAO = "medida"
DIAS_BLOCO_A = {0, 2, 4}          # segunda, quarta, sexta — pernas
NUCLEO, BLOCO_A, BLOCO_B = 0, 1, 2


def _rotina() -> list[dict]:
    return json.loads(ROTINA.read_text(encoding="utf-8"))


def bloco_do_dia(dia: date) -> int:
    return BLOCO_A if dia.weekday() in DIAS_BLOCO_A else BLOCO_B


def _posicao(item: dict) -> str:
    erro = f'<p class="miudo"><b>Erro comum:</b> {item["erro"].replace("Erro comum:", "").strip()}</p>' if item["erro"] else ""
    return (
        f'<div class="bloco posicao"><h4>{item["id"]}</h4>'
        f'<div class="desenho">{item["svg"]}</div>'
        f'<p class="destaque-texto">{item["nome"]}</p>'
        f'<p class="dose">{item["dose"]}</p>'
        f'<p>{item["como"]}</p>{erro}</div>'
    )


def _serie(estado: dict, prefixo: str) -> list[tuple[str, float]]:
    registros = (estado.get(SECAO) or {})
    saida = []
    for chave, valor in registros.items():
        nome, _, quando = chave.partition(":")
        if nome != prefixo:
            continue
        try:
            saida.append((quando, float(valor)))
        except (TypeError, ValueError):
            continue
    return sorted(saida)


def _medidas(dia: date, estado: dict) -> str:
    maochao = _serie(estado, "maochao")
    dor = _serie(estado, "dor")

    def resumo(serie: list[tuple[str, float]], unidade: str) -> str:
        if not serie:
            return '<p class="miudo">sem registro ainda</p>'
        ultimo = serie[-1]
        linha = f'<p class="miudo">último: {ultimo[1]:g}{unidade} em {ultimo[0][8:]}/{ultimo[0][5:7]}</p>'
        if len(serie) > 1:
            delta = ultimo[1] - serie[0][1]
            desde = serie[0][0]
            linha += (f'<p class="miudo">{"+" if delta > 0 else ""}{delta:g}{unidade} desde '
                      f'{desde[8:]}/{desde[5:7]}</p>')
        return linha

    return (
        '<div class="bloco"><h4>Onde você está</h4>'
        '<p class="campo"><input type="text" inputmode="decimal" id="maochao-valor" placeholder="12" '
        f'aria-label="distância mão-chão em centímetros" data-dia="{dia.isoformat()}">'
        '<button type="button" class="medir" data-medida="maochao" id="maochao-gravar">mão–chão (cm)</button></p>'
        + resumo(maochao, " cm") +
        '<p class="campo"><input type="text" inputmode="numeric" id="dor-valor" placeholder="3" '
        f'aria-label="dor lombar de 0 a 10" data-dia="{dia.isoformat()}">'
        '<button type="button" class="medir" data-medida="dor" id="dor-gravar">dor (0–10)</button></p>'
        + resumo(dor, "") +
        '<p class="miudo" id="medida-aviso">Entra na comparação a partir de amanhã.</p></div>'
    )


def blocos(dia: date, estado: dict) -> list[str]:
    rotina = _rotina()
    nucleo, bloco = rotina[NUCLEO], rotina[bloco_do_dia(dia)]

    abertura = (f'<div class="bloco"><h4>A sessão de hoje</h4>'
                f'<p class="destaque-texto">{nucleo["titulo"].split("—")[0].strip()} + '
                f'{bloco["titulo"].split("—")[-1].strip()}</p>'
                f'<p class="miudo">{nucleo["meta"]} · {bloco["meta"]}</p>'
                f'<p class="miudo">A rotina é sempre a mesma: amplitude vem de repetição, '
                f'não de variedade.</p></div>')

    return ([abertura]
            + [_posicao(i) for i in nucleo["itens"]]
            + [_posicao(i) for i in bloco["itens"]]
            + [_medidas(dia, estado)])
