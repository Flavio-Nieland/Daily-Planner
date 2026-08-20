"""Folha da Música — harmonia para tirar de ouvido e improvisar.

Não é repertório nem técnica de dedo: é compreensão. O esqueleto tem ~24 conceitos em ordem
de dependência (campo harmônico → cifragem → II-V-I → tensões → escalas sobre acorde), e a
lição do dia é escrita na hora com os conceitos já estudados no contexto.

A alternância violão/piano do plano antigo perdeu sentido — harmonia é a mesma nos dois, e o
bloco "no instrumento" traz a aplicação em cada um quando faz diferença. O `music_plan.json`
de técnica foi descartado.

Risco assumido (TOPICOS.md): teoria sem repertório é o caminho que mais frustra. Se o
interesse cair, o bloco "ouça" vira tarefa de tirar aquele trecho de ouvido.
"""

from datetime import date

from planner import conteudo, esqueleto, llm, progressao, referencia

TOPICO = "musica"
CONCEITO_INICIAL = 1
TOTAL = 24

PROMPT_ESQUELETO = """Liste 24 conceitos de harmonia musical em ordem de dependência, do mais
básico ao mais avançado, para alguém que quer entender harmonia o suficiente para tirar música
de ouvido e improvisar. Comece em campo harmônico e cifragem; termine em escalas sobre acorde.

Responda SÓ com JSON neste formato:
{"itens": [{"titulo": "nome do conceito", "depende": "o conceito anterior de que ele depende"}]}"""

PROMPT_LICAO = """Você escreve a folha de música de um jornal pessoal, em português do Brasil.
O conceito de hoje é: "{titulo}".
{contexto}

Responda SÓ com JSON neste formato:
{{
  "conceito": "string, 3 frases: o que é e por que funciona, com o mecanismo explícito",
  "instrumento": "string, 3 frases: como tocar isso no violão e no piano, com tonalidades e número de repetições",
  "ouca": "string, uma gravação onde o conceito aparece de forma óbvia, e o que ouvir nela"
}}
Sem markdown e sem texto fora do JSON."""


def _esqueleto() -> list[dict]:
    def gerar():
        bruto = llm.gerar_json(PROMPT_ESQUELETO, max_tokens=6000)
        return [{"titulo": llm.texto(llm.campo(i, "titulo", "conceito", "nome")),
                 "depende": llm.texto(llm.campo(i, "depende", "prerequisito", "depends", padrao=""))}
                for i in llm.campo(bruto, "itens", "conceitos", "lista")][:TOTAL]

    return esqueleto.obter("musica-conceitos", gerar)


def _licao(numero: int, item: dict, estudados: list[str]) -> dict:
    def gerar():
        contexto = (f"Ele já estudou: {', '.join(estudados)}. Pode apoiar-se nesses conceitos "
                    "sem reexplicar." if estudados else "É o primeiro conceito dele.")
        bruto = llm.gerar_json(PROMPT_LICAO.format(titulo=item["titulo"], contexto=contexto),
                               max_tokens=3500)
        return {"conceito": llm.texto(llm.campo(bruto, "conceito", "explicacao", "teoria")),
                "instrumento": llm.texto(llm.campo(bruto, "instrumento", "no_instrumento", "pratica")),
                "ouca": llm.texto(llm.campo(bruto, "ouca", "ouça", "gravacao", "referencia", padrao=""))}

    return conteudo.obter("musica", numero, gerar)


def blocos(dia: date, estado: dict) -> list[str]:
    itens = _esqueleto()
    numero = progressao.posicao(estado, TOPICO, CONCEITO_INICIAL, TOTAL)
    item = esqueleto.item(itens, numero)
    estudados = [esqueleto.item(itens, n)["titulo"] for n in range(1, numero)][-6:]
    licao = _licao(numero, item, estudados)

    partes = [
        f'<div class="bloco"><h4>Conceito {numero} de {TOTAL}</h4>'
        f'<p class="destaque-texto">{item["titulo"]}</p>'
        + (f'<p class="miudo">vem de: {item["depende"]}</p>' if item.get("depende") else "")
        + '</div>',
        f'<div class="bloco"><h4>O conceito</h4><p>{licao["conceito"]}</p></div>',
        f'<div class="bloco"><h4>No instrumento</h4><p>{licao["instrumento"]}</p></div>',
    ]
    if licao["ouca"]:
        partes.append(referencia.bloco("Ouça", licao["ouca"]))

    if progressao.feito_hoje(estado, TOPICO, dia):
        partes.append('<div class="bloco"><p class="feito">✓ estudado hoje</p></div>')
    else:
        partes.append(
            '<div class="bloco"><p class="campo">'
            f'<button type="button" class="marcar" data-topico="{TOPICO}" '
            f'data-dia="{dia.isoformat()}" id="musica-marca">estudei hoje</button></p>'
            '<p class="miudo" id="musica-aviso">O próximo conceito entra na edição de amanhã.</p></div>')
    return partes
