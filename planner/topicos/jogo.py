"""Folha do Jogo — gamedev em geral mais o roguelite, em três trilhas.

Definido com ele: quando a folha falar de projeto concreto, é **o roguelite**. O Administrador
de Mercenários fica fora. Descartada a trilha de game design teórico.

Toda indicação de material vai marcada como não conferida — modelo de linguagem inventa vídeo
do YouTube e capítulo de livro que não existem (ADR 0004).
"""

from datetime import date

from planner import conteudo, esqueleto, llm, progressao, referencia

TOPICO = "jogo"
ORDEM = ["dica", "fatia", "godot"]
INICIAIS = {"dica": 1, "fatia": 1, "godot": 1}
TOTAIS = {"dica": 60, "fatia": 12, "godot": 30}
JOGO = "um roguelite de combate por turnos feito em Godot 4, em desenvolvimento solo"

PROMPTS_ESQUELETO = {
    "dica": """Liste 60 dicas práticas de desenvolvimento de jogos para quem faz um jogo solo em
Godot 4, em ordem de utilidade para quem está começando a fase de conteúdo. Cada dica é um tema,
não a explicação.

Responda SÓ com JSON neste formato:
{"itens": [{"titulo": "o tema da dica"}]}""",
    "fatia": """Liste 12 entregas concretas, em ordem, para levar {jogo} de um combate jogável até
o lançamento. Cada entrega é uma fatia vertical que dá para jogar quando termina.

Responda SÓ com JSON neste formato:
{"itens": [{"titulo": "a entrega", "precisa": "o que é preciso saber para fazê-la"}]}""",
    "godot": """Liste 30 recursos técnicos do Godot 4 que um desenvolvedor solo precisa dominar
(shader, tilemap, physics, save, export, sinais, cena instanciada...), em ordem de necessidade.

Responda SÓ com JSON neste formato:
{"itens": [{"titulo": "o recurso"}]}""",
}

PROMPTS_ITEM = {
    "dica": """Você escreve a folha de gamedev de um jornal pessoal, em português do Brasil.
A dica de hoje é sobre: "{titulo}". O jogo dele é {jogo}.

Responda SÓ com JSON neste formato:
{{
  "dica": "string, 3 frases: a dica prática, com o porquê",
  "material": "string, um artigo, vídeo ou livro sobre isso, com autor ou canal",
  "aplicar": "string, 1 frase: o que fazer no jogo dele hoje por causa dessa dica"
}}
Sem markdown e sem texto fora do JSON.""",
    "fatia": """Você escreve a folha de gamedev de um jornal pessoal, em português do Brasil.
A próxima entrega do jogo é: "{titulo}". Precisa saber: "{precisa}". O jogo é {jogo}.

Responda SÓ com JSON neste formato:
{{
  "entrega": "string, 3 frases: o que exatamente precisa estar funcionando para a entrega fechar",
  "primeiro_passo": "string, 2 frases: por onde começar hoje",
  "risco": "string, 1 frase: o que costuma dar errado nessa parte"
}}
Sem markdown e sem texto fora do JSON.""",
    "godot": """Você escreve a folha de gamedev de um jornal pessoal, em português do Brasil.
O recurso do Godot 4 de hoje é: "{titulo}". Aplique ao jogo dele: {jogo}.

Responda SÓ com JSON neste formato:
{{
  "recurso": "string, 3 frases: o que é e quando usar",
  "no_jogo": "string, 3 frases: como aplicar isso no jogo dele, concretamente",
  "pegadinha": "string, 1 frase: a pegadinha desse recurso no Godot 4"
}}
Sem markdown e sem texto fora do JSON.""",
}

TITULOS = {"dica": "Dica do dia", "fatia": "A próxima entrega", "godot": "Godot por dentro"}


def _esqueleto(trilha: str) -> list[dict]:
    def gerar():
        # replace e não format: o schema JSON dentro do prompt tem chaves, e o format
        # tentaria interpretá-las como campo
        bruto = llm.gerar_json(PROMPTS_ESQUELETO[trilha].replace("{jogo}", JOGO),
                               max_tokens=10000)
        return [{"titulo": llm.texto(llm.campo(i, "titulo", "tema", "nome", "recurso")),
                 "precisa": llm.texto(llm.campo(i, "precisa", "requisito", padrao=""))}
                for i in llm.campo(bruto, "itens", "lista")][: TOTAIS[trilha]]

    return esqueleto.obter(f"jogo-{trilha}", gerar)


def _conteudo(trilha: str, numero: int, item: dict) -> dict:
    def gerar():
        bruto = llm.gerar_json(PROMPTS_ITEM[trilha].format(
            titulo=item["titulo"], precisa=item.get("precisa", ""), jogo=JOGO), max_tokens=3500)
        campos = {"dica": [("dica", "texto"), ("material", "referencia"), ("aplicar", "acao")],
                  "fatia": [("entrega", "escopo"), ("primeiro_passo", "comeco"), ("risco", "perigo")],
                  "godot": [("recurso", "explicacao"), ("no_jogo", "aplicacao"), ("pegadinha", "cuidado")]}[trilha]
        return {c: llm.texto(llm.campo(bruto, c, alt, padrao="")) for c, alt in campos}

    return conteudo.obter(f"jogo-{trilha}", numero, gerar)


def blocos(dia: date, estado: dict) -> list[str]:
    trilha = progressao.trilha_da_vez(estado, TOPICO, ORDEM)
    numero = progressao.posicao_trilha(estado, TOPICO, ORDEM, trilha, INICIAIS[trilha], TOTAIS[trilha])
    item = esqueleto.item(_esqueleto(trilha), numero)
    texto = _conteudo(trilha, numero, item)

    seguinte = ORDEM[(ORDEM.index(trilha) + 1) % len(ORDEM)]
    partes = [f'<div class="bloco"><h4>{TITULOS[trilha]} · {numero} de {TOTAIS[trilha]}</h4>'
              f'<p class="destaque-texto">{item["titulo"]}</p>'
              f'<p class="miudo">trilha {trilha} · amanhã é a vez de {seguinte}</p></div>']

    if trilha == "dica":
        partes.append(f'<div class="bloco"><h4>A dica</h4><p>{texto["dica"]}</p></div>')
        partes.append(f'<div class="bloco"><h4>No seu jogo</h4><p>{texto["aplicar"]}</p></div>')
        if texto["material"]:
            partes.append(referencia.bloco("Material", texto["material"]))
    elif trilha == "fatia":
        partes.append(f'<div class="bloco"><h4>O que fecha a entrega</h4><p>{texto["entrega"]}</p></div>')
        partes.append(f'<div class="bloco"><h4>Comece por aqui</h4><p>{texto["primeiro_passo"]}</p></div>')
        if texto["risco"]:
            partes.append(f'<div class="bloco"><h4>O que costuma dar errado</h4><p>{texto["risco"]}</p></div>')
    else:
        partes.append(f'<div class="bloco"><h4>O recurso</h4><p>{texto["recurso"]}</p></div>')
        partes.append(f'<div class="bloco"><h4>No seu jogo</h4><p>{texto["no_jogo"]}</p></div>')
        if texto["pegadinha"]:
            partes.append(f'<div class="bloco"><h4>A pegadinha</h4><p>{texto["pegadinha"]}</p></div>')

    if progressao.feito_hoje(estado, TOPICO, dia):
        partes.append('<div class="bloco"><p class="feito">✓ feito hoje</p></div>')
    else:
        partes.append('<div class="bloco"><p class="campo">'
                      f'<button type="button" class="marcar" data-topico="{TOPICO}" '
                      f'data-dia="{dia.isoformat()}" id="jogo-marca">fiz hoje</button></p>'
                      f'<p class="miudo" id="jogo-aviso">Marcar passa a vez para a trilha {seguinte}.</p></div>')
    return partes
