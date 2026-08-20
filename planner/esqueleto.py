"""Esqueletos: a lista de itens de um plano, gerada uma vez e editável à mão.

O esqueleto é estável — só o item da vez é escrito no dia. Fica em `esqueletos/`,
versionado, para ele poder reordenar, cortar ou reescrever sem tocar em código.
"""

import json
from pathlib import Path

PASTA = Path(__file__).resolve().parent.parent / "esqueletos"


def caminho(nome: str) -> Path:
    return PASTA / f"{nome}.json"


def obter(nome: str, gerar) -> list[dict]:
    arquivo = caminho(nome)
    if arquivo.exists():
        try:
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
            if dados:
                return dados
        except json.JSONDecodeError:
            pass
    dados = gerar()
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return dados


def item(lista: list[dict], numero: int) -> dict:
    """O item `numero` (1-based), sem estourar no fim da lista."""
    if not lista:
        raise ValueError("esqueleto vazio")
    return lista[min(numero, len(lista)) - 1]
