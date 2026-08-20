"""Folha do Inglês — duas trilhas em rotação: falar sem travar e entender áudio real.

**Fala** é prescritora, mesma lógica do Chess.com: a folha entrega a situação e as
expressões, e manda praticar onde a ferramenta faz melhor (ELSA Speak para pronúncia,
Gemini Live para conversa). O ouvir-e-repetir acontece na própria folha, com a voz do
navegador.

**Escuta** precisa de áudio real com o gabarito do que foi dito de verdade — e o modelo não
pode transcrever um áudio que não ouviu, inventaria a transcrição. Então o gabarito vem da
**legenda oficial**, extraída pela `youtube-transcript-api` (sem chave de API). O modelo só
escolhe o trecho e aponta o que provavelmente vai escapar. Vídeo cuja legenda não vem não
entra na folha.
"""

from datetime import date

from planner import conteudo, esqueleto, llm, progressao

TOPICO = "ingles"
ORDEM = ["fala", "escuta"]
INICIAIS = {"fala": 1, "escuta": 1}
TOTAIS = {"fala": 40, "escuta": 20}
TENTATIVAS = 5                 # vídeos a tentar antes de desistir
SEGUNDOS_TRECHO = 45

FERRAMENTAS = [
    ("ELSA Speak", "drills ilimitados de pronúncia, feedback fonema por fonema"),
    ("Gemini Live", "conversa livre por voz, sem limite curto — você já tem conta Google"),
]

PROMPT_FALA_ESQUELETO = """Liste 40 situações concretas de conversa em inglês que travam um
brasileiro que fala razoavelmente mas hesita, em ordem crescente de dificuldade. Situações de
trabalho e de vida social, específicas — não temas genéricos.

Responda SÓ com JSON neste formato:
{"itens": [{"titulo": "situação, ex: discordar numa reunião sem soar agressivo"}]}"""

PROMPT_FALA = """Você escreve a folha de inglês de um jornal pessoal, em português do Brasil.
A situação de hoje é: "{titulo}".

Responda SÓ com JSON neste formato:
{{
  "expressoes": [{{"frase": "a expressão em inglês", "quando": "quando usar, em português"}}],
  "exercicio": "string, 2 frases: o que dizer em voz alta agora, e como saber se saiu bem",
  "cuidado": "string, 1 frase: o que soa mal ou errado se ele traduzir do português"
}}
Entre 4 e 6 expressões. Sem markdown e sem texto fora do JSON."""

PROMPT_ESCUTA_ESQUELETO = """Liste 20 vídeos do YouTube com legenda oficial em inglês, bons para
treinar escuta de fala real: TED e TED-Ed, entrevistas e palestras conhecidas. Prefira vídeos
antigos e muito populares, cujo ID você tenha certeza.

Responda SÓ com JSON neste formato:
{"itens": [{"video": "o ID de 11 caracteres do YouTube", "titulo": "título do vídeo"}]}"""

PROMPT_ESCUTA = """Você escreve a folha de escuta de inglês de um jornal pessoal, em português do
Brasil. Este é o trecho REAL da legenda oficial do vídeo "{titulo}":

{transcricao}

Responda SÓ com JSON neste formato:
{{
  "escapa": "string, 3 frases em português: o que provavelmente não vai ser ouvido neste trecho — contrações, palavras ligadas, vogais reduzidas — citando as passagens exatas",
  "foco": "string, 1 frase: o que escutar antes de ler a transcrição"
}}
Não reescreva a transcrição. Sem markdown e sem texto fora do JSON."""


def _esqueleto(trilha: str) -> list[dict]:
    def gerar():
        if trilha == "fala":
            bruto = llm.gerar_json(PROMPT_FALA_ESQUELETO, max_tokens=10000)
            return [{"titulo": llm.texto(llm.campo(i, "titulo", "situacao", "situação"))}
                    for i in llm.campo(bruto, "itens", "situacoes", "lista")][: TOTAIS["fala"]]
        bruto = llm.gerar_json(PROMPT_ESCUTA_ESQUELETO, max_tokens=10000)
        return [{"video": llm.texto(llm.campo(i, "video", "video_id", "id")),
                 "titulo": llm.texto(llm.campo(i, "titulo", "title"))}
                for i in llm.campo(bruto, "itens", "videos", "lista")][: TOTAIS["escuta"]]

    return esqueleto.obter(f"ingles-{trilha}", gerar)


def transcricao(video: str, inicio_segundos: int = 0) -> list[dict]:
    """O trecho da legenda oficial, ou [] quando o vídeo não tem legenda acessível."""
    from youtube_transcript_api import YouTubeTranscriptApi

    try:
        buscada = YouTubeTranscriptApi().fetch(video, languages=["en"])
    except Exception:                                  # noqa: BLE001 — vídeo sumiu, sem legenda etc.
        return []
    linhas = [{"inicio": t.start, "texto": t.text.replace("\n", " ").strip()} for t in buscada]
    fim = inicio_segundos + SEGUNDOS_TRECHO
    trecho = [l for l in linhas if inicio_segundos <= l["inicio"] < fim]
    return trecho or linhas[:12]


def _blocos_fala(dia: date, numero: int, item: dict) -> list[str]:
    def gerar():
        bruto = llm.gerar_json(PROMPT_FALA.format(titulo=item["titulo"]), max_tokens=3500)
        return {
            "expressoes": [{"frase": llm.texto(llm.campo(e, "frase", "expressao", "phrase")),
                            "quando": llm.texto(llm.campo(e, "quando", "uso", "when", padrao=""))}
                           for e in llm.campo(bruto, "expressoes", "expressões", "frases")],
            "exercicio": llm.texto(llm.campo(bruto, "exercicio", "exercício", "pratica")),
            "cuidado": llm.texto(llm.campo(bruto, "cuidado", "erro", "armadilha", padrao="")),
        }

    conteudo_dia = conteudo.obter("ingles-fala", numero, gerar)
    expressoes = "".join(
        f'<li><span class="frase" data-falar="{e["frase"]}">{e["frase"]}</span>'
        f'<span class="qtd">{e["quando"]}</span></li>'
        for e in conteudo_dia["expressoes"])
    prescricao = "".join(f'<li><span>{nome}</span><span class="qtd">{para}</span></li>'
                         for nome, para in FERRAMENTAS)

    partes = [
        f'<div class="bloco"><h4>Situação {numero} de {TOTAIS["fala"]}</h4>'
        f'<p class="destaque-texto">{item["titulo"]}</p>'
        f'<p class="miudo">trilha da fala · toque numa frase para ouvir</p></div>',
        f'<div class="bloco"><h4>As expressões</h4><ul>{expressoes}</ul>'
        f'<p class="miudo">o navegador lê em voz alta; repita até sair sem pensar</p></div>',
        f'<div class="bloco"><h4>Em voz alta agora</h4><p>{conteudo_dia["exercicio"]}</p></div>',
    ]
    if conteudo_dia["cuidado"]:
        partes.append(f'<div class="bloco"><h4>Não traduza do português</h4>'
                      f'<p>{conteudo_dia["cuidado"]}</p></div>')
    partes.append(f'<div class="bloco presc"><h4>Onde praticar de verdade</h4><ul>{prescricao}</ul>'
                  f'<p class="miudo">a folha entrega a situação; o treino de pronúncia é lá</p></div>')
    return partes


def _blocos_escuta(dia: date, numero: int, itens: list[dict]) -> list[str]:
    """Tenta os vídeos da vez até um deles ter legenda oficial acessível."""
    inicio = (numero * 37) % 240          # offset determinístico dentro do vídeo
    tentados = []
    for salto in range(TENTATIVAS):
        item = esqueleto.item(itens, min(numero + salto, len(itens)))
        tentados.append(item["titulo"])
        linhas = transcricao(item["video"], inicio)
        if linhas:
            break
    else:
        raise RuntimeError("nenhum vídeo da fila tinha legenda oficial acessível: "
                           + "; ".join(tentados))

    texto = " ".join(l["texto"] for l in linhas)
    segundos = int(linhas[0]["inicio"])

    def gerar():
        bruto = llm.gerar_json(PROMPT_ESCUTA.format(titulo=item["titulo"], transcricao=texto),
                               max_tokens=3000)
        return {"escapa": llm.texto(llm.campo(bruto, "escapa", "escape", "dificil")),
                "foco": llm.texto(llm.campo(bruto, "foco", "atencao", "focus", padrao=""))}

    analise = conteudo.obter("ingles-escuta", numero, gerar)
    link = f"https://www.youtube.com/watch?v={item['video']}&t={segundos}s"

    return [
        f'<div class="bloco"><h4>Trecho {numero} de {TOTAIS["escuta"]}</h4>'
        f'<p class="destaque-texto">{item["titulo"]}</p>'
        f'<p class="miudo">trilha da escuta · a partir de {segundos // 60}min{segundos % 60:02d}</p>'
        f'<p><a class="ouvir" href="{link}">abrir no minuto certo</a></p></div>',
        f'<div class="bloco"><h4>Escute antes de ler</h4><p>{analise["foco"]}</p></div>',
        f'<div class="bloco"><h4>O que vai escapar</h4><p>{analise["escapa"]}</p></div>',
        f'<div class="bloco"><h4>O gabarito</h4>'
        f'<p class="miudo">legenda oficial do vídeo — não é transcrição gerada</p>'
        f'<details><summary>revelar o que foi dito</summary>'
        f'<p class="gabarito">{texto}</p></details></div>',
    ]


def blocos(dia: date, estado: dict) -> list[str]:
    trilha = progressao.trilha_da_vez(estado, TOPICO, ORDEM)
    numero = progressao.posicao_trilha(estado, TOPICO, ORDEM, trilha,
                                       INICIAIS[trilha], TOTAIS[trilha])
    itens = _esqueleto(trilha)

    if trilha == "fala":
        partes = _blocos_fala(dia, numero, esqueleto.item(itens, numero))
    else:
        partes = _blocos_escuta(dia, numero, itens)

    seguinte = ORDEM[(ORDEM.index(trilha) + 1) % len(ORDEM)]
    if progressao.feito_hoje(estado, TOPICO, dia):
        partes.append('<div class="bloco"><p class="feito">✓ inglês feito hoje</p></div>')
    else:
        partes.append(
            '<div class="bloco"><p class="campo">'
            f'<button type="button" class="marcar" data-topico="{TOPICO}" '
            f'data-dia="{dia.isoformat()}" id="ingles-marca">fiz hoje</button></p>'
            f'<p class="miudo" id="ingles-aviso">Marcar passa a vez para a trilha da {seguinte}.</p></div>')
    return partes
