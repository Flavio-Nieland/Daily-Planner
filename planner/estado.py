"""O estado consolidado: o que ele escreveu na edição, versionado no git.

O caminho é Worker → KV → estado.json (ADR 0003). A escrita dele é instantânea; a leitura
acontece no build do dia seguinte. O KV é buffer: se sumir, o estado.json do último dia
sobrevive no git e perde-se no máximo um dia de marcações.
"""

import json
import os
from pathlib import Path

import requests

ARQUIVO = Path(__file__).resolve().parent.parent / "estado.json"
TEMPO_LIMITE = 20


def ler_do_git() -> dict:
    if not ARQUIVO.exists():
        return {}
    try:
        return json.loads(ARQUIVO.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def buscar_no_worker() -> dict | None:
    """O estado no KV, ou None quando não há Worker configurado ou ele não respondeu."""
    url, token = os.environ.get("WORKER_URL"), os.environ.get("WORKER_TOKEN")
    if not url or not token:
        return None
    try:
        resposta = requests.get(
            url.rstrip("/") + "/estado",
            headers={"Authorization": f"Bearer {token}"},
            timeout=TEMPO_LIMITE,
        )
        resposta.raise_for_status()
        dados = resposta.json()
        return dados if isinstance(dados, dict) else None
    except (requests.RequestException, ValueError) as erro:
        print(f"  KV indisponível ({erro.__class__.__name__}) — seguindo com o estado.json do git")
        return None


def consolidar() -> dict:
    """Junta o que veio do KV ao que já estava no git e grava o estado.json."""
    do_git = ler_do_git()
    do_kv = buscar_no_worker()
    if do_kv is None:
        return do_git

    juntos = dict(do_git)
    for secao, registros in do_kv.items():
        if isinstance(registros, dict):
            juntos[secao] = {**juntos.get(secao, {}), **registros}
        else:
            juntos[secao] = registros

    if juntos != do_git:
        ARQUIVO.write_text(json.dumps(juntos, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
        print(f"  estado consolidado: {sum(len(v) for v in juntos.values() if isinstance(v, dict))} registros")
    return juntos


def serie(estado: dict, secao: str) -> list[tuple[str, float]]:
    """Uma seção com data na chave, em ordem cronológica."""
    registros = estado.get(secao) or {}
    return sorted(((data, valor) for data, valor in registros.items()), key=lambda x: x[0])
