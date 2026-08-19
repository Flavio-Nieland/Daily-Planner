"""Folha do Treino — a divisão continua fixa; o que muda é passar a medir.

A sugestão de carga **não usa LLM**: sai de regra sobre o histórico — bateu o topo da faixa
de reps na última sessão, sobe a carga. O esqueleto dos exercícios é gerado uma vez e fica
editável à mão, porque a divisão é dele, não do modelo.
"""

import re
import unicodedata
from datetime import date

from planner import esqueleto, llm

SECAO = "carga"
DIVISAO = {0: "peito e tríceps", 1: "costas e bíceps", 2: "pernas", 4: "ombro e braços"}
INCREMENTO = {"pernas": 5.0}          # kg a subir quando bate o topo da faixa
INCREMENTO_PADRAO = 2.5

PROMPT = """Monte a divisão de treino de hipertrofia de um homem que treina quatro dias por semana
em academia. Para cada dia, seis exercícios na ordem de execução, com faixa de repetições.

Dias: {dias}

Responda SÓ com JSON neste formato:
{{
  "dias": [
    {{
      "dia": "string, o nome do dia como listado acima",
      "exercicios": [{{"nome": "string", "series": "string, ex: 4", "reps": "string, ex: 8-12"}}]
    }}
  ]
}}
Sem markdown e sem texto fora do JSON."""


def _slug(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")


def _esqueleto() -> dict[str, list[dict]]:
    def gerar():
        bruto = llm.gerar_json(PROMPT.format(dias=", ".join(DIVISAO.values())), max_tokens=6000)
        saida = []
        for d in llm.campo(bruto, "dias", "divisao", "treinos"):
            saida.append({
                "dia": llm.texto(llm.campo(d, "dia", "nome", "grupo")),
                "exercicios": [
                    {"nome": llm.texto(llm.campo(e, "nome", "exercicio", "name")),
                     "series": llm.texto(llm.campo(e, "series", "séries", "sets", padrao="4")),
                     "reps": llm.texto(llm.campo(e, "reps", "repeticoes", "repetições", padrao="8-12"))}
                    for e in llm.campo(d, "exercicios", "exercícios", "exercises")
                ][:6],
            })
        return saida

    lista = esqueleto.obter("treino-divisao", gerar)
    return {item["dia"]: item["exercicios"] for item in lista}


def _faixa(reps: str) -> tuple[int, int]:
    numeros = [int(n) for n in re.findall(r"\d+", reps)]
    if not numeros:
        return 8, 12
    return (numeros[0], numeros[-1]) if len(numeros) > 1 else (numeros[0], numeros[0])


def _historico(estado: dict, slug: str) -> list[tuple[str, dict]]:
    registros = []
    for chave, valor in (estado.get(SECAO) or {}).items():
        nome, _, quando = chave.rpartition(":")
        if nome != slug or not isinstance(valor, dict):
            continue
        registros.append((quando, valor))
    return sorted(registros)


def sugerir(exercicio: dict, ultima: dict | None) -> tuple[str, str]:
    """(sugestão de hoje, motivo). Sem histórico, a folha pede a carga em vez de sugerir."""
    if not ultima:
        return "—", "primeira vez: anote a carga que você usou"
    try:
        kg = float(ultima.get("kg"))
        reps = int(ultima.get("reps"))
    except (TypeError, ValueError):
        return "—", "último registro ilegível: anote de novo"

    _, topo = _faixa(exercicio["reps"])
    if reps >= topo:
        passo = INCREMENTO.get(exercicio.get("grupo", ""), INCREMENTO_PADRAO)
        return f"{kg + passo:g} kg", f"bateu {reps} reps: sobe {passo:g} kg"
    return f"{kg:g} kg", f"fez {reps} reps: mantém a carga até chegar a {topo}"


def blocos(dia: date, estado: dict) -> list[str]:
    grupo = DIVISAO.get(dia.weekday())
    if not grupo:
        return ['<div class="bloco"><h4>Hoje não é dia de academia</h4>'
                '<p>A folha do Treino aparece nos quatro dias da divisão.</p></div>']

    exercicios = _esqueleto().get(grupo, [])
    partes = [f'<div class="bloco"><h4>Treino de hoje</h4>'
              f'<p class="destaque-texto">{grupo}</p>'
              f'<p class="miudo">{len(exercicios)} exercícios · anote as cargas conforme fizer</p></div>']

    volume = 0.0
    for exercicio in exercicios:
        exercicio = {**exercicio, "grupo": grupo}
        slug = _slug(exercicio["nome"])
        historico = _historico(estado, slug)
        ultima = historico[-1][1] if historico else None
        sugestao, motivo = sugerir(exercicio, ultima)

        if ultima:
            try:
                volume += float(ultima["kg"]) * int(ultima["reps"]) * float(_faixa(exercicio["series"])[0])
            except (TypeError, ValueError, KeyError):
                pass

        antes = (f'{ultima["kg"]:g} kg × {ultima["reps"]} em {historico[-1][0][8:]}/{historico[-1][0][5:7]}'
                 if ultima else "sem registro")
        partes.append(
            f'<div class="bloco exercicio"><h4>{exercicio["nome"]}</h4>'
            f'<p class="miudo">{exercicio["series"]} séries · {exercicio["reps"]} reps</p>'
            f'<p class="miudo">última vez: {antes}</p>'
            f'<p class="destaque-texto">{sugestao}</p>'
            f'<p class="miudo">{motivo}</p>'
            f'<p class="campo"><input type="text" inputmode="decimal" class="carga-kg" '
            f'placeholder="kg" aria-label="carga em quilos de {exercicio["nome"]}">'
            f'<input type="text" inputmode="numeric" class="carga-reps" placeholder="reps" '
            f'aria-label="repetições de {exercicio["nome"]}">'
            f'<button type="button" class="anotar-carga" data-exercicio="{slug}" '
            f'data-dia="{dia.isoformat()}">anotar</button></p>'
            f'<p class="miudo aviso-carga"></p></div>'
        )

    partes.append(_volume(estado, dia, exercicios, volume))
    return partes


def _volume(estado: dict, dia: date, exercicios: list[dict], volume_hoje: float) -> str:
    from datetime import timedelta

    def volume_semana(inicio: date, fim: date) -> float:
        total = 0.0
        for chave, valor in (estado.get(SECAO) or {}).items():
            _, _, quando = chave.rpartition(":")
            try:
                quando_dia = date.fromisoformat(quando)
                if inicio <= quando_dia <= fim:
                    total += float(valor["kg"]) * int(valor["reps"])
            except (TypeError, ValueError, KeyError):
                continue
        return total

    inicio_semana = dia - timedelta(days=dia.weekday())
    esta = volume_semana(inicio_semana, dia)
    anterior = volume_semana(inicio_semana - timedelta(days=7), inicio_semana - timedelta(days=1))
    if not esta and not anterior:
        comparacao = '<p class="miudo">o volume aparece quando você começar a anotar</p>'
    elif anterior:
        delta = (esta - anterior) / anterior * 100
        comparacao = (f'<p class="miudo">{"+" if delta > 0 else ""}{delta:.0f}% contra a semana '
                      f'anterior ({anterior:,.0f} kg)</p>'.replace(",", "."))
    else:
        comparacao = '<p class="miudo">primeira semana registrada</p>'

    return (f'<div class="bloco"><h4>Volume da semana</h4>'
            f'<p class="destaque">{esta:,.0f} kg</p>'.replace(",", ".") + comparacao + '</div>')
