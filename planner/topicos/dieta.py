"""Dieta e Compras — o cardápio planejado por CICLO DE COMPRAS de três dias.

Decisão dele em 2026-11-03: compra a cada três dias ("um dia sim, dois não"). O cardápio
deixou de ser gerado dia a dia com "não repita o de ontem" — que trabalhava contra
aproveitar o que foi comprado — e passou a ser gerado por ciclo, numa chamada só, como uma
despensa: o frango assado do almoço vira o recheio do lanche de amanhã, a abóbora inteira
rende três preparos. Cada refeição diz o que aproveita no campo `aproveita`.

A lista de compras é SOMADA POR CÓDIGO a partir do cardápio (antes era um LLM por build,
sem cache: a lista da manhã e a da tarde saíam diferentes). Só a tradução do total para a
unidade de prateleira ("1 abóbora cabotiá pequena, ~1 kg") é do modelo, uma vez por ciclo,
cacheada em gerado/compras/<início>.json.

Regras de geração (o cache é diet_plan.json, versionado):
- dia já gerado nunca é regerado — o "amanhã" de hoje é o "hoje" de amanhã;
- ciclo que ainda não começou (início >= hoje) e não está inteiro no formato novo é
  gerado INTEIRO, para a compra fazer sentido;
- ciclo em andamento com dia faltando gera só os dias que faltam, dizendo ao modelo o que
  já está na despensa;
- dia passado que falta não é inventado.

O prompt repete o schema inteiro de propósito (ADR 0001).
"""

import json
import re
import unicodedata
from datetime import date, timedelta
from pathlib import Path

from planner import llm

RAIZ = Path(__file__).resolve().parent.parent.parent
CACHE = RAIZ / "diet_plan.json"
COMPRAS = RAIZ / "gerado" / "compras"
META_KCAL = 2800
CICLO = 3
# A primeira compra do regime de ciclos. Todo dia (d - ANCORA) % 3 == 0 é dia de compra.
ANCORA = date(2026, 11, 4)
SECOES = ["Hortifrúti", "Padaria", "Açougue e peixaria", "Laticínios e frios", "Mercearia"]
REFEICOES = ["Café da manhã", "Lanche da manhã", "Almoço", "Lanche da tarde", "Jantar"]

PROMPT_CICLO = """Monte o cardápio de um CICLO DE COMPRAS para um homem adulto, em português do Brasil.
Ele faz compras no primeiro dia do ciclo e só volta ao mercado três dias depois. Por isso o
cardápio é planejado JUNTO, como uma despensa só:

- Reaproveite ingredientes entre os dias: quem compra uma abóbora inteira, um pacote de aveia ou
  1 kg de frango usa ao longo do ciclo, em preparos diferentes. Variar o PREPARO, não a compra.
- Planeje sobras: cozinhar uma vez e comer duas (ex.: o frango assado do almoço vira o recheio do
  lanche de amanhã). Diga isso no campo "aproveita" da refeição que USA a sobra ou o ingrediente;
  deixe vazio quando não houver aproveitamento de verdade.
- Perecíveis (folhas, peixe fresco, frutas maduras) primeiro; o fim do ciclo fica com o que dura.
- Alimentos brasileiros, baratos e da estação ({estacao}, sul do Brasil).
- Cinco refeições por dia somando aproximadamente {meta} kcal.
{contexto}
Dias a planejar: {dias}.

Responda SÓ com JSON exatamente neste formato:
{
  "dias": [
    {
      "data": "AAAA-MM-DD",
      "refeicoes": [
        {
          "nome": "Café da manhã | Lanche da manhã | Almoço | Lanche da tarde | Jantar",
          "hora": "07:00",
          "prato": "nome curto do prato principal, ex: Omelete de espinafre",
          "kcal": 0, "proteina_g": 0, "carbo_g": 0, "gordura_g": 0,
          "preparo": "até 3 frases curtas de como fazer",
          "aproveita": "string; vazio se não reaproveita nada",
          "itens": [{"alimento": "como vai no prato, ex: Feijão carioca cozido",
                     "qtd": "medida caseira, ex: 1 concha média",
                     "gramas": 0,
                     "produto": "o que se COMPRA, cru e genérico, sempre com o MESMO nome no ciclo inteiro, ex: Feijão carioca",
                     "secao": "Hortifrúti | Padaria | Açougue e peixaria | Laticínios e frios | Mercearia"}]
        }
      ]
    }
  ]
}
"gramas" é número: o peso em gramas (ou ml para líquidos) da porção no prato.
Sem markdown e sem texto fora do JSON."""

PROMPT_UNIDADES = """Você transforma o total de ingredientes de um ciclo de cardápio numa lista de COMPRAS de
supermercado brasileiro. Para cada produto, diga o que pegar na prateleira, na embalagem ou unidade
em que ele é vendido, arredondando para cima. Os gramas vieram do prato pronto: converta para o
produto cru quando for o caso (arroz cozido ~ 3x o cru; feijão cozido ~ 2,5x; massa cozida ~ 2,2x;
carnes perdem ~30% no preparo).

Produtos (chave | nome | total em gramas no prato | porções):
{lista}

Responda SÓ com JSON neste formato:
{"itens": [{"chave": "a chave exatamente como veio", "compra": "ex: 1 abóbora cabotiá pequena (~1 kg)"}]}
Sem markdown e sem texto fora do JSON."""

ESTADOS = re.compile(r"\s+(cozid|assad|cru|desfiad|grelhad|refogad|ralad|picad|fatiad|amassad)[a-z]*\b.*$",
                     re.IGNORECASE)


# ---------------- ciclos ----------------

def inicio_do_ciclo(dia: date) -> date:
    return dia - timedelta(days=(dia - ANCORA).days % CICLO)


def dias_do_ciclo(inicio: date) -> list[date]:
    return [inicio + timedelta(days=n) for n in range(CICLO)]


def _estacao(dia: date) -> str:
    return {12: "verão", 1: "verão", 2: "verão", 3: "outono", 4: "outono", 5: "outono",
            6: "inverno", 7: "inverno", 8: "inverno"}.get(dia.month, "primavera")


# ---------------- cache ----------------

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


def formato_novo(plano: dict | None) -> bool:
    """Dia gerado já no regime de ciclos: tem prato e gramas. Os de antes de 04/11/2026 não."""
    refeicoes = (plano or {}).get("refeicoes") or []
    return bool(refeicoes) and all("prato" in r for r in refeicoes)


# ---------------- normalização ----------------

def _numero(valor, padrao=0.0) -> float:
    try:
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return padrao


def _secao(valor: str) -> str:
    bruto = chave(valor)
    for secao in SECOES:
        if chave(secao)[:5] in bruto:
            return secao
    if "acougue" in bruto or "carne" in bruto or "peix" in bruto:
        return "Açougue e peixaria"
    if "latic" in bruto or "frios" in bruto:
        return "Laticínios e frios"
    return "Mercearia"


def chave(nome: str) -> str:
    """Chave de agrupamento: minúsculas, sem acento, sem espaço sobrando."""
    sem_acento = unicodedata.normalize("NFD", str(nome).lower())
    return "".join(c for c in sem_acento if not unicodedata.combining(c)).strip()


def _item(i: dict) -> dict:
    alimento = llm.texto(llm.campo(i, "alimento", "item", "food"))
    produto = llm.texto(llm.campo(i, "produto", "compra", "ingrediente", padrao="")) \
        or ESTADOS.sub("", alimento).strip()
    return {"alimento": alimento,
            "qtd": llm.texto(llm.campo(i, "qtd", "quantidade", "quantity", padrao="")),
            "gramas": _numero(llm.campo(i, "gramas", "g", "peso_g", padrao=0)),
            "produto": produto,
            "secao": _secao(llm.texto(llm.campo(i, "secao", "seção", "section", padrao="Mercearia")))}


def _refeicao(r: dict) -> dict:
    itens = [_item(i) for i in llm.campo(r, "itens", "items", "alimentos")]
    nome = llm.texto(llm.campo(r, "nome", "refeicao", "refeição", "name"))
    return {"nome": nome,
            "hora": llm.texto(llm.campo(r, "hora", "horario", "horário", "time", padrao="")),
            "prato": llm.texto(llm.campo(r, "prato", "titulo", "título", padrao="")) or itens[0]["alimento"],
            "kcal": round(_numero(llm.campo(r, "kcal", "calorias", "calories", padrao=0))),
            "proteina_g": round(_numero(llm.campo(r, "proteina_g", "proteína_g", "proteina", padrao=0))),
            "carbo_g": round(_numero(llm.campo(r, "carbo_g", "carboidrato_g", "carbo", padrao=0))),
            "gordura_g": round(_numero(llm.campo(r, "gordura_g", "gordura", padrao=0))),
            "preparo": llm.texto(llm.campo(r, "preparo", "modo_de_preparo", "como_fazer", padrao="")),
            "aproveita": llm.texto(llm.campo(r, "aproveita", "aproveitamento", "sobra", padrao="")),
            "itens": itens}


def _normalizar(bruto: dict, datas: list[date]) -> dict:
    """{iso: dia}. Casa pela data que o modelo devolveu e, se ela vier torta, pela ordem."""
    dias = llm.campo(bruto, "dias", "days", "cardapio", "cardápio")
    if len(dias) < len(datas):
        raise ValueError(f"o modelo devolveu {len(dias)} dia(s) para {len(datas)} pedidos")
    pedidas = [d.isoformat() for d in datas]
    por_data = {str(d.get("data", "")).strip(): d for d in dias}
    saida = {}
    for n, iso in enumerate(pedidas):
        dia = por_data.get(iso) or dias[n]
        refeicoes = [_refeicao(r) for r in llm.campo(dia, "refeicoes", "refeições", "meals")]
        saida[iso] = {"refeicoes": refeicoes, "total_kcal": sum(r["kcal"] for r in refeicoes)}
    return saida


# ---------------- geração ----------------

def _pratos(cache: dict, datas: list[date]) -> list[str]:
    return [r.get("prato") or r["itens"][0]["alimento"]
            for d in datas if formato_novo(cache.get(d.isoformat()))
            for r in cache[d.isoformat()]["refeicoes"]]


def _gerar(cache: dict, datas: list[date], ja_no_ciclo: list[date]) -> dict:
    anteriores = dias_do_ciclo(inicio_do_ciclo(datas[0]) - timedelta(days=CICLO))
    contexto = ""
    vistos = _pratos(cache, anteriores)
    if vistos:
        contexto += "O ciclo anterior teve estes pratos; varie em relação a eles: " + ", ".join(vistos) + ".\n"
    despensa = sorted({i["produto"] for d in ja_no_ciclo if formato_novo(cache.get(d.isoformat()))
                       for r in cache[d.isoformat()]["refeicoes"] for i in r["itens"]})
    if despensa:
        contexto += ("O ciclo já começou e a compra já foi feita: aproveite o que está na despensa — "
                     + ", ".join(despensa) + ".\n")
    prompt = (PROMPT_CICLO.replace("{meta}", str(META_KCAL)).replace("{estacao}", _estacao(datas[0]))
              .replace("{contexto}", contexto).replace("{dias}", ", ".join(d.isoformat() for d in datas)))
    return _normalizar(llm.gerar_json(prompt, max_tokens=24000), datas)


def ciclos_relevantes(dia: date) -> list[date]:
    """Os inícios de ciclo que a edição mostra: o de ontem, o de hoje e o próximo."""
    atual = inicio_do_ciclo(dia)
    return sorted({inicio_do_ciclo(dia - timedelta(days=1)), atual, atual + timedelta(days=CICLO)})


def garantir(dia: date) -> dict:
    """Garante no cache o ciclo em andamento e o próximo; devolve o cache inteiro."""
    cache = _cache()
    atual = inicio_do_ciclo(dia)
    mudou = False
    for inicio in (atual, atual + timedelta(days=CICLO)):
        datas = dias_do_ciclo(inicio)
        if inicio >= dia:
            if all(formato_novo(cache.get(d.isoformat())) for d in datas):
                continue
            cache.update(_gerar(cache, datas, []))
        else:
            faltam = [d for d in datas if d >= dia and d.isoformat() not in cache]
            if not faltam:
                continue
            cache.update(_gerar(cache, faltam, [d for d in datas if d not in faltam]))
        mudou = True
    if mudou:
        _gravar(cache)
    return cache


# ---------------- compras ----------------

def agregar(cache: dict, inicio: date) -> list[dict]:
    """A lista do ciclo: soma exata das porções por produto, com onde cada um é usado."""
    itens: dict[str, dict] = {}
    for d in dias_do_ciclo(inicio):
        plano = cache.get(d.isoformat())
        if not formato_novo(plano):
            continue
        for r in plano["refeicoes"]:
            for i in r["itens"]:
                produto = i.get("produto") or ESTADOS.sub("", i["alimento"]).strip()
                k = chave(produto)
                item = itens.setdefault(k, {"chave": k, "nome": produto, "secao": i.get("secao") or "Mercearia",
                                            "g": 0.0, "compra": "", "usos": []})
                item["g"] += _numero(i.get("gramas"))
                item["usos"].append({"dia": d.isoformat(), "ref": r["nome"], "qtd": i.get("qtd", "")})
    return sorted(itens.values(), key=lambda x: (SECOES.index(x["secao"]) if x["secao"] in SECOES else 9, -x["g"]))


def unidades(inicio: date, itens: list[dict]) -> dict:
    """{chave: "o que pegar na prateleira"}, uma chamada por ciclo, cacheada.

    Falhar aqui não derruba a Compras: a lista sai com os gramas do cardápio.
    """
    if not itens:
        return {}
    arquivo = COMPRAS / f"{inicio.isoformat()}.json"
    chaves = sorted(i["chave"] for i in itens)
    if arquivo.exists():
        try:
            guardado = json.loads(arquivo.read_text(encoding="utf-8"))
            if sorted(guardado.get("chaves", [])) == chaves:
                return guardado["compra"]
        except (json.JSONDecodeError, KeyError):
            pass
    lista = "\n".join(f'{i["chave"]} | {i["nome"]} | {round(i["g"])} | '
                      + "; ".join(f'{u["qtd"]} ({u["ref"]})' for u in i["usos"]) for i in itens)
    try:
        bruto = llm.gerar_json(PROMPT_UNIDADES.replace("{lista}", lista), max_tokens=12000)
        compra = {chave(str(x.get("chave", ""))): llm.texto(x.get("compra", ""))
                  for x in llm.campo(bruto, "itens", "items") if x.get("compra")}
    except Exception as erro:                       # noqa: BLE001 — a lista vive sem isso
        print(f"  compras: unidades de prateleira não vieram ({erro.__class__.__name__}: {erro})")
        return {}
    compra = {k: v for k, v in compra.items() if k in chaves}
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(json.dumps({"chaves": chaves, "compra": compra}, ensure_ascii=False, indent=1) + "\n",
                       encoding="utf-8")
    return compra


# ---------------- os cadernos ----------------

def caderno(dia: date) -> dict:
    """Dieta: ontem, hoje e amanhã (e os vizinhos de cada um, para a coluna lateral)."""
    cache = garantir(dia)
    janela = [(dia + timedelta(days=n)).isoformat() for n in range(-2, 3)]
    if (dia.isoformat() not in cache):
        raise RuntimeError("o cardápio de hoje não está no cache")
    return {"caderno": "dieta", "dados": {
        "hoje": dia.isoformat(), "meta": META_KCAL,
        "dias": {iso: cache[iso] for iso in janela if iso in cache},
        "ciclos": [{"inicio": i.isoformat(), "dias": [d.isoformat() for d in dias_do_ciclo(i)]}
                   for i in ciclos_relevantes(dia)],
    }}


def caderno_compras(dia: date) -> dict:
    """Compras: o ciclo em andamento e o próximo, cada um com a lista somada e as unidades."""
    cache = garantir(dia)
    atual = inicio_do_ciclo(dia)
    ciclos = []
    for inicio in (atual, atual + timedelta(days=CICLO)):
        itens = agregar(cache, inicio)
        compra = unidades(inicio, itens)
        for i in itens:
            i["compra"] = compra.get(i["chave"], "")
            i["g"] = round(i["g"])
        ciclos.append({"inicio": inicio.isoformat(), "dias": [d.isoformat() for d in dias_do_ciclo(inicio)],
                       "itens": itens})
    # dia de compra mostra a de hoje; véspera, a de amanhã; no meio do ciclo, a em andamento
    amanha = dia + timedelta(days=1)
    padrao = 1 if inicio_do_ciclo(amanha) == amanha and ciclos[1]["itens"] else 0
    if not ciclos[0]["itens"]:
        padrao = 1
    return {"caderno": "compras", "dados": {"hoje": dia.isoformat(), "ciclos": ciclos, "padrao": padrao}}
