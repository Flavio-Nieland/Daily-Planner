"""Folha da Dieta — cinco refeições fechando 2.800 kcal, e a lista de compras da semana.

Mantida como era, com a janela de três dias que dá continuidade: o "amanhã" de hoje é o
"hoje" de amanhã, sem regenerar. O que entra de novo é a lista de compras — os ingredientes
dos próximos dias somados e agrupados por seção de mercado, que é o que torna o plano
executável.

O prompt repete o schema inteiro de propósito: dizer "JSON igual ao padrão" foi o que fez o
modelo devolver `horario` por `hora` e a lista sem seções (ADR 0001).
"""

import json
from datetime import date, timedelta
from pathlib import Path

from planner import llm

CACHE = Path(__file__).resolve().parent.parent.parent / "diet_plan.json"
META_KCAL = 2800
JANELA = 3          # hoje e os dois próximos dias
CHAPEU_COMPRAS = "Compras dos próximos 3 dias"

PROMPT_DIA = """Monte o plano alimentar de um dia para um homem adulto, em português do Brasil.
Cinco refeições somando aproximadamente {meta} kcal, com alimentos brasileiros, baratos e da
estação. Data: {data}.
{continuidade}

Responda SÓ com JSON exatamente neste formato:
{{
  "refeicoes": [
    {{
      "nome": "string, ex: Café da manhã",
      "hora": "string, ex: 07:00",
      "kcal": 0,
      "itens": [{{"alimento": "string", "qtd": "string com a quantidade"}}]
    }}
  ],
  "total_kcal": 0
}}
Sem markdown, sem comentários e sem texto fora do JSON."""

PROMPT_COMPRAS = """Some os ingredientes destes dias de cardápio numa lista de compras única,
em português do Brasil, agrupada por seção de mercado.

Cardápios:
{cardapios}

Responda SÓ com JSON exatamente neste formato:
{{
  "secoes": [
    {{
      "secao": "string, ex: Hortifrúti",
      "itens": [{{"item": "string", "qtd": "string com a quantidade total", "custo": "string, ex: R$ 8,00"}}]
    }}
  ],
  "custo_total": "string, ex: R$ 180,00"
}}
Sem markdown e sem texto fora do JSON."""


def _cache() -> dict:
    if not CACHE.exists():
        return {}
    try:
        dados = json.loads(CACHE.read_text(encoding="utf-8"))
        return dados if isinstance(dados, dict) else {}
    except json.JSONDecodeError:
        return {}


def _gravar(dados: dict) -> None:
    CACHE.write_text(json.dumps(dados, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                     encoding="utf-8")


def _normalizar(bruto: dict) -> dict:
    refeicoes = []
    for r in llm.campo(bruto, "refeicoes", "refeições", "meals"):
        itens = [
            {"alimento": llm.texto(llm.campo(i, "alimento", "item", "food")),
             "qtd": llm.texto(llm.campo(i, "qtd", "quantidade", "quantity", padrao=""))}
            for i in llm.campo(r, "itens", "items", "alimentos")
        ]
        refeicoes.append({
            "nome": llm.texto(llm.campo(r, "nome", "refeicao", "name")),
            "hora": llm.texto(llm.campo(r, "hora", "horario", "horário", "time", padrao="")),
            "kcal": llm.campo(r, "kcal", "calorias", "subtotal_kcal", "calories", padrao=0),
            "itens": itens,
        })
    return {"refeicoes": refeicoes,
            "total_kcal": llm.campo(bruto, "total_kcal", "total", "kcal_total", padrao=META_KCAL)}


def _dia(data: date, anterior: dict | None) -> dict:
    guardados = _cache()
    chave = data.isoformat()
    if chave in guardados:
        return guardados[chave]

    continuidade = ""
    if anterior:
        pratos = [i["alimento"] for r in anterior["refeicoes"] for i in r["itens"]]
        continuidade = ("Não repita estes alimentos do dia anterior como prato principal: "
                        + ", ".join(pratos[:12]) + ".")
    bruto = llm.gerar_json(
        PROMPT_DIA.format(meta=META_KCAL, data=data.strftime("%d/%m/%Y"), continuidade=continuidade),
        max_tokens=6000)
    guardados[chave] = _normalizar(bruto)
    _gravar(guardados)
    return guardados[chave]


def _compras(dias: list[dict]) -> dict:
    cardapios = "\n".join(
        f"Dia {n + 1}: " + ", ".join(f'{i["qtd"]} de {i["alimento"]}'
                                     for r in dia["refeicoes"] for i in r["itens"])
        for n, dia in enumerate(dias)
    )
    bruto = llm.gerar_json(PROMPT_COMPRAS.format(cardapios=cardapios), max_tokens=5000)
    secoes = []
    for s in llm.campo(bruto, "secoes", "seções", "sections", "lista"):
        secoes.append({
            "secao": llm.texto(llm.campo(s, "secao", "seção", "section", "nome")),
            "itens": [{"item": llm.texto(llm.campo(i, "item", "alimento", "produto")),
                       "qtd": llm.texto(llm.campo(i, "qtd", "quantidade", padrao="")),
                       "custo": llm.texto(llm.campo(i, "custo", "preco", "preço", padrao=""))}
                      for i in llm.campo(s, "itens", "items", "produtos")],
        })
    return {"secoes": secoes,
            "custo_total": llm.texto(llm.campo(bruto, "custo_total", "total", "custo", padrao=""))}


def blocos(dia: date) -> list[str]:
    ontem = _cache().get((dia - timedelta(days=1)).isoformat())
    plano = _dia(dia, ontem)

    partes = []
    for refeicao in plano["refeicoes"]:
        itens = "".join(
            f'<li><span>{i["alimento"]}</span><span class="qtd">{i["qtd"]}</span></li>'
            for i in refeicao["itens"]
        )
        partes.append(
            f'<div class="bloco refeicao"><h4>{refeicao["nome"]}'
            f'<span class="hora">{refeicao["hora"]}</span>'
            f'<span class="kcal">{refeicao["kcal"]} kcal</span></h4>'
            f'<ul>{itens}</ul></div>'
        )

    total = plano.get("total_kcal") or META_KCAL
    partes.append(f'<div class="bloco"><h4>O dia fecha em</h4>'
                  f'<p class="destaque">{total} kcal</p>'
                  f'<p class="miudo">meta de {META_KCAL} kcal</p></div>')

    # a janela dá continuidade e alimenta a lista de compras
    proximos = [plano]
    for n in range(1, JANELA):
        proximos.append(_dia(dia + timedelta(days=n), proximos[-1]))

    compras = _compras(proximos)
    for n, secao in enumerate(compras["secoes"]):
        itens = "".join(
            f'<li><span>{i["item"]}</span><span class="qtd">{i["qtd"]}'
            + (f' · {i["custo"]}' if i["custo"] else "") + "</span></li>"
            for i in secao["itens"]
        )
        # a primeira seção de compras abre folha nova: o dia e a feira são duas leituras
        # diferentes, e misturadas empurravam metade da lista para uma terceira folha
        quebra = f' data-quebra="{CHAPEU_COMPRAS}"' if n == 0 else ""
        partes.append(f'<div class="bloco"{quebra}><h4>Compras · {secao["secao"]}</h4>'
                      f'<ul>{itens}</ul></div>')
    if compras["custo_total"]:
        partes.append(f'<div class="bloco"><h4>A conta da semana</h4>'
                      f'<p class="destaque">{compras["custo_total"]}</p>'
                      f'<p class="miudo">estimativa para {JANELA} dias</p></div>')
    return partes
