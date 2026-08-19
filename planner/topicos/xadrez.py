"""Folha do Xadrez — duas trilhas geradas e duas prescritas.

Palavras dele: "não precisa fazer a análise por dentro de você, nem do jogo nem de tática,
somente me peça para fazer no chess.com, lá ele vai fazer muito melhor que você com uma LLM
fraca." Tática e Análise viraram prescrição; sobraram como conteúdo gerado apenas Abertura e
Fundamentos, que são texto e não exigem diagrama nem motor de xadrez — o que elimina de uma
vez o risco de posição ilegal e mate inexistente, que nenhum modelo evita.
"""

from datetime import date

from planner import conteudo, esqueleto, llm, progressao

TOPICO = "xadrez"
ORDEM = ["abertura", "fundamentos"]
INICIAIS = {"abertura": 4, "fundamentos": 6}
TOTAIS = {"abertura": 16, "fundamentos": 20}

PROMPT_ESQUELETO = {
    "abertura": """Liste 16 linhas de abertura de xadrez para um jogador que está subindo de Elo,
em ordem de prioridade de estudo, alternando brancas e pretas, sem repetir sistema.

Responda SÓ com JSON neste formato:
{"itens": [{"titulo": "nome da linha, ex: Ruy Lopez, variante Berlim", "cor": "brancas ou pretas"}]}""",
    "fundamentos": """Liste 20 fundamentos de xadrez em ordem de dependência: finais elementares,
mates básicos e estruturas de peões. Nada que precise de diagrama de posição específica.

Responda SÓ com JSON neste formato:
{"itens": [{"titulo": "nome do fundamento, ex: final de rei e peão contra rei", "tipo": "final, mate ou estrutura"}]}""",
}

PROMPT_ITEM = {
    "abertura": """Escreva a folha de abertura de xadrez de um jornal pessoal, em português do Brasil.
A linha de hoje é: "{titulo}" ({cor}).

Responda SÓ com JSON neste formato:
{{
  "lances": "string, a sequência principal em notação algébrica, ex: 1.e4 e5 2.Cf3 Cc6 3.Bb5",
  "ideia": "string, 2 frases, a ideia por trás dos lances — que estruturas e planos ela busca",
  "erro": "string, 1 frase, o erro mais comum de quem joga essa linha sem entender"
}}
Sem markdown e sem texto fora do JSON.""",
    "fundamentos": """Escreva a folha de fundamentos de xadrez de um jornal pessoal, em português do Brasil.
O fundamento de hoje é: "{titulo}".

Responda SÓ com JSON neste formato:
{{
  "conceito": "string, 2 frases, o que é e por que funciona",
  "regra": "string, 1 frase, a regra prática que se leva para a partida",
  "erro": "string, 1 frase, o erro comum de quem não domina isso"
}}
Sem markdown e sem texto fora do JSON.""",
}

PRESCRICOES = [
    ("Tática, no Chess.com", "Faça 20 puzzles no Chess.com puxando pelo tema de hoje. "
     "O treino de tática é lá — a folha só cobra."),
    ("Análise, no Chess.com", "Abra sua última partida no analisador do Chess.com e ache o lance "
     "onde a vantagem virou. Um lance só, o primeiro que escorregou."),
]


def _esqueleto(trilha: str) -> list[dict]:
    def gerar():
        bruto = llm.gerar_json(PROMPT_ESQUELETO[trilha], max_tokens=1400)
        itens = llm.campo(bruto, "itens", "lista", "linhas", "fundamentos")
        return [{"titulo": llm.texto(llm.campo(i, "titulo", "nome", "title")),
                 "extra": llm.texto(llm.campo(i, "cor", "tipo", padrao=""))}
                for i in itens][: TOTAIS[trilha]]

    return esqueleto.obter(f"xadrez-{trilha}", gerar)


def _conteudo(trilha: str, numero: int, item: dict) -> dict:
    def gerar():
        bruto = llm.gerar_json(
            PROMPT_ITEM[trilha].format(titulo=item["titulo"], cor=item.get("extra", "")),
            max_tokens=800)
        if trilha == "abertura":
            return {"lances": llm.texto(llm.campo(bruto, "lances", "sequencia", "moves")),
                    "ideia": llm.texto(llm.campo(bruto, "ideia", "idea", "plano")),
                    "erro": llm.texto(llm.campo(bruto, "erro", "erro_comum", "armadilha", padrao=""))}
        return {"conceito": llm.texto(llm.campo(bruto, "conceito", "concept", "explicacao")),
                "regra": llm.texto(llm.campo(bruto, "regra", "rule", "pratica")),
                "erro": llm.texto(llm.campo(bruto, "erro", "erro_comum", padrao=""))}

    return conteudo.obter(f"xadrez-{trilha}", numero, gerar)


def blocos(dia: date, estado: dict, serie_elo: list[tuple[str, float]]) -> list[str]:
    trilha = progressao.trilha_da_vez(estado, TOPICO, ORDEM)
    numero = progressao.posicao_trilha(estado, TOPICO, ORDEM, trilha,
                                       INICIAIS[trilha], TOTAIS[trilha])
    itens = _esqueleto(trilha)
    item = esqueleto.item(itens, numero)
    texto = _conteudo(trilha, numero, item)

    seguinte = ORDEM[(ORDEM.index(trilha) + 1) % len(ORDEM)]
    cabeca = (
        f'<div class="bloco"><h4>Trilha de hoje: {trilha}</h4>'
        f'<p class="destaque-texto">{item["titulo"]}</p>'
        f'<p class="miudo">item {numero} de {TOTAIS[trilha]} · amanhã a vez é de {seguinte}</p></div>'
    )

    if trilha == "abertura":
        corpo = [
            f'<div class="bloco"><h4>Os lances</h4><p class="lances">{texto["lances"]}</p></div>',
            f'<div class="bloco"><h4>A ideia</h4><p>{texto["ideia"]}</p></div>',
        ]
    else:
        corpo = [
            f'<div class="bloco"><h4>O conceito</h4><p>{texto["conceito"]}</p></div>',
            f'<div class="bloco"><h4>Na partida</h4><p>{texto["regra"]}</p></div>',
        ]
    if texto.get("erro"):
        corpo.append(f'<div class="bloco"><h4>O erro comum</h4><p>{texto["erro"]}</p></div>')

    prescritos = [
        f'<div class="bloco presc"><h4>{titulo}</h4><p>{instrucao}</p></div>'
        for titulo, instrucao in PRESCRICOES
    ]

    return [cabeca] + corpo + prescritos + [_elo(dia, serie_elo),
                                            _marcador(dia, estado)]


def _elo(dia: date, serie: list[tuple[str, float]]) -> str:
    from planner.topicos.peso import _grafico

    atual = f'{serie[-1][1]:.0f}' if serie else "—"
    variacao = ""
    if len(serie) > 1:
        delta = serie[-1][1] - serie[-2][1]
        variacao = f'<p class="miudo">{"+" if delta > 0 else ""}{delta:.0f} desde a última anotação</p>'
    return (
        '<div class="bloco" id="elo-registro"><h4>Seu Elo</h4>'
        f'<p class="destaque">{atual}</p>{variacao}'
        '<p class="campo"><input type="text" inputmode="numeric" id="elo-valor" placeholder="1240" '
        f'aria-label="Elo de hoje" data-dia="{dia.isoformat()}">'
        '<button type="button" id="elo-gravar">anotar</button></p>'
        '<p class="miudo" id="elo-aviso">Anote depois de jogar; a curva entra na edição de amanhã.</p>'
        + (_curva(serie) if len(serie) > 1 else "") + '</div>'
    )


def _curva(serie: list[tuple[str, float]]) -> str:
    from planner.topicos.peso import _grafico
    return _grafico(serie)


def _marcador(dia: date, estado: dict) -> str:
    if progressao.feito_hoje(estado, TOPICO, dia):
        return '<div class="bloco"><p class="feito">✓ xadrez feito hoje</p></div>'
    return (
        '<div class="bloco"><p class="campo">'
        f'<button type="button" class="marcar" data-topico="{TOPICO}" '
        f'data-dia="{dia.isoformat()}" id="xadrez-marca">fiz hoje</button></p>'
        '<p class="miudo" id="xadrez-aviso">Marcar passa a vez para a outra trilha.</p></div>'
    )
