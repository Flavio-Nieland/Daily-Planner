"""Folha da Fazenda — vida de fazenda em nível iniciante, como estudo e não como tarefa.

Duas trilhas em rotação: currículo base (solo, plantio, água, criação, ferramenta — sair do
zero e entender do que as pessoas falam) e curadoria de material. Criação de animais entra
como assunto dentro do currículo, não como trilha própria; projetos de mão ficaram fora.

Mesma pendência de curadoria do Jogo, mesma decisão: indicação vai marcada como não conferida.
"""

from datetime import date

from planner import conteudo, esqueleto, llm, progressao, referencia

TOPICO = "fazenda"
ORDEM = ["base", "curadoria"]
INICIAIS = {"base": 1, "curadoria": 1}
TOTAIS = {"base": 36, "curadoria": 36}

PROMPTS_ESQUELETO = {
    "base": """Monte um currículo de 36 assuntos de vida no campo para um iniciante absoluto que
quer entender do que as pessoas falam: solo, plantio, água, criação de animais, ferramenta e
manejo. Em ordem, do mais básico ao mais avançado, cada assunto apoiando-se no anterior.

Responda SÓ com JSON neste formato:
{"itens": [{"titulo": "o assunto"}]}""",
    "curadoria": """Liste 36 temas de vida no campo sobre os quais existe material bom de estudo
em português — livro, canal, cartilha da Embrapa ou do SENAR. Em ordem de utilidade para
iniciante. Liste o tema, não o material.

Responda SÓ com JSON neste formato:
{"itens": [{"titulo": "o tema"}]}""",
}

PROMPTS_ITEM = {
    "base": """Você escreve a folha de vida no campo de um jornal pessoal, em português do Brasil,
para um iniciante absoluto. O assunto de hoje é: "{titulo}".

Responda SÓ com JSON neste formato:
{{
  "explicacao": "string, 3 frases: o que é, por que importa, e o vocabulário que as pessoas usam",
  "na_pratica": "string, 2 frases: como isso aparece numa propriedade pequena de verdade",
  "engano": "string, 1 frase: o engano comum de quem é de cidade"
}}
Sem markdown e sem texto fora do JSON.""",
    "curadoria": """Você escreve a folha de vida no campo de um jornal pessoal, em português do
Brasil. O tema de hoje é: "{titulo}".

Responda SÓ com JSON neste formato:
{{
  "material": "string, um livro, canal ou cartilha em português sobre o tema, com autor ou instituição",
  "porque": "string, 2 frases: por que esse material e o que ele resolve",
  "comece_por": "string, 1 frase: por onde começar dentro dele"
}}
Sem markdown e sem texto fora do JSON.""",
}


def _esqueleto(trilha: str) -> list[dict]:
    def gerar():
        bruto = llm.gerar_json(PROMPTS_ESQUELETO[trilha], max_tokens=10000)
        return [{"titulo": llm.texto(llm.campo(i, "titulo", "assunto", "tema", "nome"))}
                for i in llm.campo(bruto, "itens", "lista")][: TOTAIS[trilha]]

    return esqueleto.obter(f"fazenda-{trilha}", gerar)


def _conteudo(trilha: str, numero: int, item: dict) -> dict:
    def gerar():
        bruto = llm.gerar_json(PROMPTS_ITEM[trilha].format(titulo=item["titulo"]), max_tokens=3500)
        campos = {"base": [("explicacao", "explicação"), ("na_pratica", "pratica"), ("engano", "erro")],
                  "curadoria": [("material", "indicacao"), ("porque", "por_que"), ("comece_por", "inicio")]}[trilha]
        return {c: llm.texto(llm.campo(bruto, c, alt, padrao="")) for c, alt in campos}

    return conteudo.obter(f"fazenda-{trilha}", numero, gerar)


def blocos(dia: date, estado: dict) -> list[str]:
    trilha = progressao.trilha_da_vez(estado, TOPICO, ORDEM)
    numero = progressao.posicao_trilha(estado, TOPICO, ORDEM, trilha, INICIAIS[trilha], TOTAIS[trilha])
    item = esqueleto.item(_esqueleto(trilha), numero)
    texto = _conteudo(trilha, numero, item)

    seguinte = "curadoria" if trilha == "base" else "base"
    partes = [f'<div class="bloco"><h4>{"Currículo" if trilha == "base" else "Material"} · '
              f'{numero} de {TOTAIS[trilha]}</h4>'
              f'<p class="destaque-texto">{item["titulo"]}</p>'
              f'<p class="miudo">trilha {trilha} · amanhã é a vez de {seguinte}</p></div>']

    if trilha == "base":
        partes.append(f'<div class="bloco"><h4>O assunto</h4><p>{texto["explicacao"]}</p></div>')
        partes.append(f'<div class="bloco"><h4>Na prática</h4><p>{texto["na_pratica"]}</p></div>')
        if texto["engano"]:
            partes.append(f'<div class="bloco"><h4>O engano de quem é de cidade</h4>'
                          f'<p>{texto["engano"]}</p></div>')
    else:
        partes.append(referencia.bloco("Para estudar", texto["material"], texto["porque"]))
        if texto["comece_por"]:
            partes.append(f'<div class="bloco"><h4>Comece por</h4><p>{texto["comece_por"]}</p></div>')

    if progressao.feito_hoje(estado, TOPICO, dia):
        partes.append('<div class="bloco"><p class="feito">✓ feito hoje</p></div>')
    else:
        partes.append('<div class="bloco"><p class="campo">'
                      f'<button type="button" class="marcar" data-topico="{TOPICO}" '
                      f'data-dia="{dia.isoformat()}" id="fazenda-marca">estudei hoje</button></p>'
                      f'<p class="miudo" id="fazenda-aviso">Marcar passa a vez para a trilha {seguinte}.</p></div>')
    return partes
