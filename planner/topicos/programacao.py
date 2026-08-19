"""Folha de Programação — fundamentos de CC, num grafo de pré-requisitos.

Aqui o esqueleto **não é uma lista, é um grafo**: BST antes de AVL antes de B-tree. Sem
isso a aula do dia cai no vácuo. O ponteiro deixa de ser "próximo da fila" e passa a ser
**próximo tópico cujos pré-requisitos estão todos concluídos** — o que permite ordem
diferente sem quebrar dependência.

Descartado o `get_programming_plan()`, que sorteava tema por dia (RAG numa terça, Docker na
sexta): amplitude sem acúmulo era exatamente o problema.
"""

from datetime import date

from planner import conteudo, esqueleto, llm, progressao

TOPICO = "programacao"
SECAO = "dominio"
TOTAL = 40

PROMPT_ESQUELETO = """Monte um currículo de 40 tópicos de fundamentos de ciência da computação:
algoritmos, estruturas de dados, concorrência, redes e sistemas operacionais. Conhecimento que
não expira. Não inclua ferramentas, frameworks nem nada de nuvem.

Cada tópico declara de quais outros ele depende, pelo nome exato. Os primeiros não dependem de
nada. Respeite dependências reais: árvore binária de busca antes de AVL, AVL antes de B-tree.

Responda SÓ com JSON neste formato:
{"itens": [{"titulo": "nome do tópico", "depende": ["nome exato de outro tópico"]}]}"""

PROMPT_AULA = """Você escreve a folha de programação de um jornal pessoal, em português do Brasil.
O tópico de hoje é: "{titulo}".
{contexto}

Responda SÓ com JSON neste formato:
{{
  "porque": "string, 3 frases: o problema que isso resolve e por que foi inventado",
  "implemente": "string, 3 frases: um exercício de mão, do zero, em Python, sem biblioteca",
  "antes": "string, de onde isso vem — o conceito anterior e o que ele deixou pronto",
  "depois": "string, para onde isso leva — o que passa a ser possível depois",
  "gancho": "string, 1 frase: onde isso aparece na prática, tipo 'é por isso que índice de banco é B-tree e não hash'"
}}
Sem markdown e sem texto fora do JSON."""


def _esqueleto() -> list[dict]:
    def gerar():
        bruto = llm.gerar_json(PROMPT_ESQUELETO, max_tokens=8000)
        itens = []
        for i in llm.campo(bruto, "itens", "topicos", "tópicos", "lista"):
            depende = llm.campo(i, "depende", "prerequisitos", "pre_requisitos", "depends", padrao=[])
            if isinstance(depende, str):
                depende = [x.strip() for x in depende.split(",") if x.strip()]
            itens.append({"titulo": llm.texto(llm.campo(i, "titulo", "topico", "nome")),
                          "depende": [llm.texto(x) for x in depende]})
        return itens[:TOTAL]

    return esqueleto.obter("programacao-grafo", gerar)


def concluidos(estado: dict) -> set[str]:
    """Os títulos já concluídos, contados só quando marcados em dia com Programação na agenda."""
    feitos = set()
    for chave, registro in progressao.decisoes(estado, SECAO, TOPICO).items():
        if chave.startswith("cc:") and registro["veredito"] == "concluido":
            feitos.add(chave[3:])
    return feitos


def liberados(itens: list[dict], feitos: set[str]) -> list[dict]:
    """Tópicos cujos pré-requisitos estão todos concluídos — a fronteira do grafo."""
    conhecidos = {i["titulo"] for i in itens}
    return [i for i in itens
            if i["titulo"] not in feitos
            and all(d in feitos for d in i["depende"] if d in conhecidos)]


def _aula(titulo: str, feitos: set[str]) -> dict:
    def gerar():
        contexto = (f"Ele já concluiu: {', '.join(sorted(feitos)[:12])}. Apoie-se nisso."
                    if feitos else "É o primeiro tópico dele.")
        bruto = llm.gerar_json(PROMPT_AULA.format(titulo=titulo, contexto=contexto), max_tokens=4000)
        return {c: llm.texto(llm.campo(bruto, c, alt, padrao=""))
                for c, alt in [("porque", "por_que"), ("implemente", "exercicio"),
                               ("antes", "vem_de"), ("depois", "leva_a"), ("gancho", "pratica")]}

    # a chave do cache é a posição do tópico no esqueleto, então a aula é estável
    posicao = _posicao_no_esqueleto(titulo)
    return conteudo.obter("programacao", posicao, gerar)


def _posicao_no_esqueleto(titulo: str) -> int:
    for n, item in enumerate(_esqueleto(), start=1):
        if item["titulo"] == titulo:
            return n
    return 1


def blocos(dia: date, estado: dict) -> list[str]:
    itens = _esqueleto()
    feitos = concluidos(estado)
    fila = liberados(itens, feitos)

    if not fila:
        pendentes = [i for i in itens if i["titulo"] not in feitos]
        if not pendentes:
            return ['<div class="bloco"><h4>Currículo concluído</h4>'
                    f'<p>Os {len(itens)} tópicos foram fechados.</p></div>']
        faltando = sorted({d for i in pendentes for d in i["depende"] if d not in feitos})
        return ['<div class="bloco"><h4>Nenhum tópico liberado</h4>'
                '<p>Todo tópico pendente depende de algo que ainda não foi concluído.</p>'
                f'<p class="miudo">falta concluir: {", ".join(faltando[:6])}</p></div>']

    item = fila[0]
    aula = _aula(item["titulo"], feitos)
    vem_de = ", ".join(item["depende"]) if item["depende"] else "nada — é ponto de partida"

    partes = [
        f'<div class="bloco"><h4>Tópico {len(feitos) + 1} de {len(itens)}</h4>'
        f'<p class="destaque-texto">{item["titulo"]}</p>'
        f'<p class="miudo">pré-requisitos: {vem_de}</p></div>',
        f'<div class="bloco"><h4>Por que existe</h4><p>{aula["porque"]}</p></div>',
        f'<div class="bloco"><h4>Implemente</h4><p>{aula["implemente"]}</p></div>',
        f'<div class="bloco"><h4>Antes · depois</h4><p><b>Antes:</b> {aula["antes"]}</p>'
        f'<p><b>Depois:</b> {aula["depois"]}</p></div>',
    ]
    if aula["gancho"]:
        partes.append(f'<div class="bloco"><h4>Na prática</h4><p>{aula["gancho"]}</p></div>')

    liberou = [i["titulo"] for i in itens if item["titulo"] in i["depende"]]
    partes.append(
        '<div class="bloco"><h4>Concluiu?</h4><p class="campo">'
        f'<button type="button" class="veredito" data-veredito="concluido" '
        f'data-chave="cc:{item["titulo"]}" data-dia="{dia.isoformat()}">concluí</button></p>'
        + (f'<p class="miudo">libera: {", ".join(liberou[:3])}</p>' if liberou else "")
        + f'<p class="miudo" id="programacao-aviso">{len(fila) - 1} outro(s) tópico(s) já liberado(s).</p></div>')
    return partes
