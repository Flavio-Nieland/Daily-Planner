"""Folha da Comida — repertório de ~30 pratos que ele faz de cor.

O critério de sucesso é retenção, não variedade: prato não dominado volta a aparecer dias
depois, enquanto o esqueleto segue andando. Por isso a folha tem duas filas em paralelo —
a principal e a de revisão.
"""

from datetime import date, timedelta

from planner import conteudo, esqueleto, llm, progressao

TOPICO = "comida"
SECAO = "dominio"
PRATO_INICIAL = 1
TOTAL = 30
ESPERA = timedelta(days=3)          # quanto tempo um prato não dominado espera para voltar

PROMPT_ESQUELETO = """Liste 30 pratos brasileiros do dia a dia para alguém que está aprendendo a
cozinhar do zero, em ordem crescente de dificuldade. Cada prato deve ensinar uma técnica de
cozinha diferente da anterior.

Responda SÓ com JSON neste formato:
{"itens": [{"titulo": "nome do prato", "tecnica": "a técnica de cozinha que ele ensina"}]}"""

PROMPT_RECEITA = """Escreva a folha de cozinha de um jornal pessoal, em português do Brasil.
O prato de hoje é: "{titulo}". A técnica que ele ensina: "{tecnica}".
{dominados}

Responda SÓ com JSON neste formato:
{{
  "ingredientes": ["string, um ingrediente com quantidade por item"],
  "preparo": ["string, um passo por item, na ordem"],
  "ensina": "string, 2 frases, o que esse prato te ensina de técnica e onde mais isso serve",
  "erro": "string, 1 frase, o erro que estraga esse prato"
}}
Sem markdown e sem texto fora do JSON."""


def _esqueleto() -> list[dict]:
    def gerar():
        bruto = llm.gerar_json(PROMPT_ESQUELETO, max_tokens=6000)
        itens = llm.campo(bruto, "itens", "pratos", "lista")
        return [{"titulo": llm.texto(llm.campo(i, "titulo", "nome", "prato")),
                 "tecnica": llm.texto(llm.campo(i, "tecnica", "técnica", "technique", padrao=""))}
                for i in itens][:TOTAL]

    return esqueleto.obter("comida-pratos", gerar)


def _receita(numero: int, item: dict, dominados: list[str]) -> dict:
    def gerar():
        contexto = (f"Ele já domina: {', '.join(dominados)}. Não repita explicação dessas técnicas."
                    if dominados else "É um dos primeiros pratos dele.")
        bruto = llm.gerar_json(
            PROMPT_RECEITA.format(titulo=item["titulo"], tecnica=item.get("tecnica", ""),
                                  dominados=contexto),
            max_tokens=4000)
        return {
            "ingredientes": [llm.texto(x) for x in llm.campo(bruto, "ingredientes", "ingredients")],
            "preparo": [llm.texto(x) for x in llm.campo(bruto, "preparo", "modo_preparo", "passos", "steps")],
            "ensina": llm.texto(llm.campo(bruto, "ensina", "tecnica", "aprendizado", padrao="")),
            "erro": llm.texto(llm.campo(bruto, "erro", "erro_comum", padrao="")),
        }

    return conteudo.obter("comida", numero, gerar)


def _fila(estado: dict, dia: date) -> tuple[int, list[int], list[str]]:
    """(prato da vez, pratos devidos de revisão, nomes dos dominados)."""
    decisoes = progressao.decisoes(estado, SECAO, TOPICO)
    dominados, revisar = [], []
    for chave, registro in decisoes.items():
        numero = int(chave.split(":")[-1]) if chave.split(":")[-1].isdigit() else None
        if numero is None:
            continue
        if registro["veredito"] == "dominado":
            dominados.append(numero)
        else:
            revisar.append(numero)

    devidos = sorted(n for n in revisar
                     if decisoes[f"prato:{n}"]["dia"] + ESPERA <= dia)
    # prato devido de revisão tem prioridade: é o que faz a revisão espaçada acontecer
    proximo = min(PRATO_INICIAL + len(decisoes), TOTAL)
    return (devidos[0] if devidos else proximo), devidos, sorted(dominados)


def blocos(dia: date, estado: dict) -> list[str]:
    itens = _esqueleto()
    numero, devidos, dominados = _fila(estado, dia)
    item = esqueleto.item(itens, numero)
    nomes_dominados = [esqueleto.item(itens, n)["titulo"] for n in dominados]
    receita = _receita(numero, item, nomes_dominados)

    revisao = " · <b>revisão</b>" if numero in devidos else ""
    cabeca = (f'<div class="bloco"><h4>Prato {numero} de {TOTAL}{revisao}</h4>'
              f'<p class="destaque-texto">{item["titulo"]}</p>'
              f'<p class="miudo">{item.get("tecnica", "")}</p></div>')

    ingredientes = "".join(f"<li>{x}</li>" for x in receita["ingredientes"])
    preparo = "".join(f"<li>{x}</li>" for x in receita["preparo"])
    partes = [
        cabeca,
        f'<div class="bloco"><h4>Ingredientes</h4><ul class="lista">{ingredientes}</ul></div>',
        f'<div class="bloco"><h4>Preparo</h4><ol class="lista numerada">{preparo}</ol></div>',
    ]
    if receita["ensina"]:
        partes.append(f'<div class="bloco"><h4>O que esse prato te ensina</h4><p>{receita["ensina"]}</p></div>')
    if receita["erro"]:
        partes.append(f'<div class="bloco"><h4>O erro que estraga</h4><p>{receita["erro"]}</p></div>')

    partes.append(_veredito(dia, numero, len(dominados), devidos))
    return partes


def _veredito(dia: date, numero: int, dominados: int, devidos: list[int]) -> str:
    espera = (dia + ESPERA).strftime("%d/%m")
    fila = (f'<p class="miudo">{len(devidos)} prato(s) aguardando revisão</p>' if devidos else "")
    return (
        '<div class="bloco"><h4>Você domina esse prato?</h4>'
        '<p class="campo">'
        f'<button type="button" class="veredito" data-veredito="dominado" data-prato="{numero}" '
        f'data-dia="{dia.isoformat()}">já sei de cor</button>'
        f'<button type="button" class="veredito" data-veredito="revisar" data-prato="{numero}" '
        f'data-dia="{dia.isoformat()}">ainda não</button></p>'
        f'<p class="miudo" id="comida-aviso">"Ainda não" traz o prato de volta em {espera}. '
        'Nos dois casos o próximo prato entra amanhã.</p>'
        f'<p class="miudo">{dominados} de {TOTAL} dominados</p>{fila}</div>'
    )
