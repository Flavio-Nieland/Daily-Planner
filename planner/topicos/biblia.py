"""Folha da Bíblia — um salmo do dia com uma reflexão curta.

É o único tópico que hoje funciona exatamente como deveria: vem sem alteração do v1. O
salmo é sorteado de forma determinística por hash da data, então o mesmo dia sempre cai no
mesmo salmo, sem guardar semente.
"""

import hashlib
from datetime import date

import requests

from planner import llm

TOTAL_SALMOS = 150
API = "https://bible-api.com/salmos+{numero}?translation=almeida"

PROMPT = """Leia este salmo e escreva uma reflexão curta para um jornal pessoal, em português do Brasil.

Salmo {numero}:
{texto}

Responda SÓ com JSON neste formato:
{{
  "reflexao": "string, 3 frases sobre o que este salmo diz e o que fazer com isso hoje",
  "versiculo": "string, o versículo do salmo que resume a passagem, com o número"
}}
Sem markdown e sem texto fora do JSON."""


def _numero_do_dia(dia: date) -> int:
    digest = hashlib.md5(dia.isoformat().encode("utf-8")).hexdigest()
    return int(digest, 16) % TOTAL_SALMOS + 1


def blocos(dia: date) -> list[str]:
    numero = _numero_do_dia(dia)
    resposta = requests.get(API.format(numero=numero), timeout=20)
    resposta.raise_for_status()
    dados = resposta.json()
    texto = (dados.get("text") or "").strip()
    if not texto:
        raise ValueError(f"a API não devolveu o texto do salmo {numero}")

    bruto = llm.gerar_json(PROMPT.format(numero=numero, texto=texto[:4000]), max_tokens=2500)
    reflexao = llm.texto(llm.campo(bruto, "reflexao", "reflexão", "reflection"))
    versiculo = llm.texto(llm.campo(bruto, "versiculo", "versículo", "verse", padrao=""))

    versos = [v.strip() for v in texto.split("\n") if v.strip()]
    corpo = "".join(f'<p class="verso">{v}</p>' for v in versos)

    partes = [f'<div class="bloco"><h4>Salmo {numero}</h4>{corpo}</div>',
              f'<div class="bloco"><h4>A reflexão de hoje</h4><p>{reflexao}</p></div>']
    if versiculo:
        partes.insert(1, f'<div class="bloco"><p class="citacao">{versiculo}</p></div>')
    return partes
