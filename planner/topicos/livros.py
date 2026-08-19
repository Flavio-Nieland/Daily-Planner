"""Folha dos Livros — duas folhas: antes de ler e depois de ler.

Quatro objetivos ao mesmo tempo: manter o ritmo até terminar, entender mais fundo, reter o
que leu, e ter o próximo livro escolhido antes de acabar o atual.

**As respostas dele são o dado mais valioso do sistema inteiro** e o mais insubstituível se
perder — por isso vão para o Worker, nunca só para o navegador. E este é o único tópico onde
o modelo fala de uma obra real, então é o único onde ele pode errar fato (inventar o que
acontece na página 118): a folha pede que ele confirme onde parou e o texto se apoia no que
é público sobre a obra.
"""

import json
from datetime import date, timedelta
from pathlib import Path

from planner import conteudo, llm, progressao

TOPICO = "livros"
SECAO_NOTA = "nota"
PLANO = Path(__file__).resolve().parent.parent.parent / "reading_plan.json"
REVISAO = timedelta(days=21)

PROMPT_TRECHO = """Você escreve a folha de leitura de um jornal pessoal, em português do Brasil.
O livro é "{titulo}", de {autor}. Hoje ele lê as páginas {inicio} a {fim} (sessão {sessao} de {total}).

Fale do trecho apenas no que é público e consagrado sobre a obra. Se não tiver certeza do que
acontece exatamente nessas páginas, fale do movimento geral dessa parte do livro em vez de
inventar cena. Nunca afirme detalhe de página específica.

Responda SÓ com JSON neste formato:
{{
  "onde": "string, 2 frases: onde ele está na narrativa, sem revelar o que vem depois",
  "observe": "string, 2 frases: o que o autor está fazendo nessa parte e que passa batido",
  "pergunta": "string, uma pergunta sobre o trecho, para responder em duas linhas"
}}
Sem markdown e sem texto fora do JSON."""

PROMPT_PROXIMOS = """Ele está terminando "{titulo}", de {autor}, e já leu: {lidos}.
Sugira três próximos livros, cada um com o motivo da escolha ligado ao que ele já leu.

Responda SÓ com JSON neste formato:
{{"sugestoes": [{{"titulo": "string", "autor": "string", "motivo": "string, 2 frases"}}]}}
Sem markdown e sem texto fora do JSON."""


def _plano() -> dict:
    return json.loads(PLANO.read_text(encoding="utf-8"))


def _sessao_atual(estado: dict, total: int) -> int:
    return progressao.posicao(estado, TOPICO, 1, total)


def notas(estado: dict) -> list[tuple[date, str]]:
    saida = []
    for chave, valor in (estado.get(SECAO_NOTA) or {}).items():
        try:
            quando = date.fromisoformat(chave)
        except ValueError:
            continue
        texto = llm.texto(valor) if not isinstance(valor, dict) else llm.texto(valor.get("texto", ""))
        if texto:
            saida.append((quando, texto))
    return sorted(saida)


def para_revisar(estado: dict, dia: date) -> list[tuple[date, str]]:
    """As notas que ele escreveu há três semanas ou mais — a revisão espaçada."""
    return [(quando, texto) for quando, texto in notas(estado) if quando + REVISAO <= dia]


def _trecho(sessao: int, plano: dict, inicio: int, fim: int) -> dict:
    def gerar():
        bruto = llm.gerar_json(PROMPT_TRECHO.format(
            titulo=plano["title"], autor=plano["author"], inicio=inicio, fim=fim,
            sessao=sessao, total=plano["total_sessions"]), max_tokens=3000)
        return {"onde": llm.texto(llm.campo(bruto, "onde", "narrativa", "contexto")),
                "observe": llm.texto(llm.campo(bruto, "observe", "observar", "atencao")),
                "pergunta": llm.texto(llm.campo(bruto, "pergunta", "questao", "question"))}

    return conteudo.obter("livros", sessao, gerar)


def _proximos(plano: dict) -> list[dict]:
    def gerar():
        bruto = llm.gerar_json(PROMPT_PROXIMOS.format(
            titulo=plano["title"], autor=plano["author"], lidos=plano["title"]), max_tokens=3000)
        return [{"titulo": llm.texto(llm.campo(s, "titulo", "title")),
                 "autor": llm.texto(llm.campo(s, "autor", "author")),
                 "motivo": llm.texto(llm.campo(s, "motivo", "porque", "razao"))}
                for s in llm.campo(bruto, "sugestoes", "sugestões", "livros")][:3]

    return conteudo.obter("livros-proximos", 1, gerar)


def blocos(dia: date, estado: dict) -> list[str]:
    plano = _plano()
    total_sessoes = plano["total_sessions"]
    por_sessao = plano["units_per_session"]
    sessao = _sessao_atual(estado, total_sessoes)

    inicio = (sessao - 1) * por_sessao + 1
    fim = min(sessao * por_sessao, plano["total_units"])
    trecho = _trecho(sessao, plano, inicio, fim)
    proporcao = round((inicio - 1) / plano["total_units"] * 100)

    antes = [
        f'<div class="bloco"><h4>{plano["title"]}</h4>'
        f'<p class="artista">{plano["author"]} · {plano.get("edition", "")}</p>'
        f'<p class="destaque-texto">páginas {inicio} a {fim}</p>'
        f'<p class="miudo">sessão {sessao} de {total_sessoes}</p>'
        f'<div class="barra"><i style="width:{proporcao}%"></i></div>'
        f'<p class="miudo">confirme onde você parou antes de seguir a folha — se a página '
        f'não bate, o texto abaixo fala da parte errada</p></div>',
        f'<div class="bloco"><h4>Onde você está</h4><p>{trecho["onde"]}</p></div>',
        f'<div class="bloco"><h4>Observe</h4><p>{trecho["observe"]}</p></div>',
    ]

    depois = [
        f'<div class="bloco"><h4>Depois de ler</h4>'
        f'<p class="destaque-texto">{trecho["pergunta"]}</p>'
        f'<p class="campo"><input type="text" id="nota-valor" placeholder="responda em duas linhas" '
        f'aria-label="sua resposta" data-dia="{dia.isoformat()}">'
        f'<button type="button" id="nota-gravar">anotar</button></p>'
        f'<p class="miudo" id="nota-aviso">O que você escreve aqui volta para revisão em três semanas.</p></div>'
    ]

    revisar = para_revisar(estado, dia)
    if revisar:
        itens = "".join(
            f'<li><span>{texto}</span><span class="qtd">{quando.strftime("%d/%m")}</span></li>'
            for quando, texto in revisar[-3:])
        depois.append(f'<div class="bloco"><h4>O que você escreveu antes</h4><ul>{itens}</ul>'
                      f'<p class="miudo">revisão espaçada · {len(revisar)} nota(s) na fila</p></div>')

    if sessao >= total_sessoes:
        sugestoes = "".join(
            f'<div class="proximo"><p class="destaque-texto">{s["titulo"]}</p>'
            f'<p class="artista">{s["autor"]}</p><p>{s["motivo"]}</p></div>'
            for s in _proximos(plano))
        depois.append(f'<div class="bloco"><h4>O próximo livro</h4>{sugestoes}</div>')

    if progressao.feito_hoje(estado, TOPICO, dia):
        depois.append('<div class="bloco"><p class="feito">✓ leitura feita hoje</p></div>')
    else:
        depois.append(
            '<div class="bloco"><p class="campo">'
            f'<button type="button" class="marcar" data-topico="{TOPICO}" '
            f'data-dia="{dia.isoformat()}" id="livros-marca">li hoje</button></p>'
            '<p class="miudo" id="livros-aviso">A próxima sessão entra na edição de amanhã.</p></div>')

    return antes + depois
