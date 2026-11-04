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


def _gravar(dados: dict) -> None:
    ARQUIVO.write_text(json.dumps(dados, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8")


def consolidar() -> dict:
    """Junta o que veio do KV ao que já estava no git e grava o estado.json.

    O arquivo é criado mesmo vazio: ele é o histórico versionado do que ele escreve, e o
    passo de publicação conta com a existência dele.
    """
    do_git = ler_do_git()
    if not ARQUIVO.exists():
        _gravar(do_git)

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
        _gravar(juntos)
        print(f"  estado consolidado: {sum(len(v) for v in juntos.values() if isinstance(v, dict))} registros")
    return juntos


def serie(estado: dict, secao: str) -> list[tuple[str, float]]:
    """Uma seção com data na chave, em ordem cronológica."""
    registros = estado.get(secao) or {}
    saida = []
    for data, valor in registros.items():
        # desde 2026-11-03 o peso grava {kg, em} para a curva saber a hora do registro
        if isinstance(valor, dict):
            valor = valor.get("kg")
        try:
            saida.append((data, float(valor)))
        except (TypeError, ValueError):
            continue
    return sorted(saida, key=lambda x: x[0])


def publico(estado: dict, dia, dias: int = 21) -> dict:
    """O pedaço do estado que vai embutido no HTML público da edição.

    Só o que as páginas leem: o peso inteiro (a curva), as marcações de `feito` recentes
    (o "o que falta hoje" e os "como foi?") e a meta do peso. As notas dos livros e os
    vereditos ficam de fora — o site é público.
    """
    from datetime import timedelta

    desde = (dia - timedelta(days=dias)).isoformat()
    feito = {}
    for chave, valor in (estado.get("feito") or {}).items():
        datas = [parte for parte in chave.split(":") if len(parte) == 10 and parte[4] == "-"]
        if datas and datas[0] >= desde:
            feito[chave] = valor
    medida = {k: v for k, v in (estado.get("medida") or {}).items() if k.startswith("meta:")}
    return {"peso": dict(estado.get("peso") or {}), "feito": feito, "medida": medida}
