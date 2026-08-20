"""O acervo guarda cada edição em HTML e também os blocos que a formaram.

Guardar os blocos é o que permite a folha do dia seguinte mostrar o dado de ontem quando
uma fonte falha, em vez de a folha simplesmente sumir da edição (ADR 0005).
"""

import json
from datetime import date, timedelta
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"


def pasta(dia: date) -> Path:
    return DOCS / dia.strftime("%Y") / dia.strftime("%m") / dia.strftime("%d")


def gravar(dia: date, topicos: list[dict], falhas: list[dict]) -> Path:
    destino = pasta(dia) / "edicao.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps({"data": dia.isoformat(), "topicos": topicos, "falhas": falhas},
                   ensure_ascii=False),
        encoding="utf-8",
    )
    return destino


def carregar(dia: date) -> dict | None:
    arquivo = pasta(dia) / "edicao.json"
    if not arquivo.exists():
        return None
    try:
        return json.loads(arquivo.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def blocos_de_ontem(dia: date, tid: str, dias_atras: int = 7) -> tuple[list[str], date] | None:
    """Os blocos mais recentes que aquele tópico teve, olhando alguns dias para trás."""
    for n in range(1, dias_atras + 1):
        anterior = dia - timedelta(days=n)
        edicao = carregar(anterior)
        if not edicao:
            continue
        for topico in edicao["topicos"]:
            if topico["id"] == tid and topico.get("blocos") and not topico.get("falhou"):
                return topico["blocos"], anterior
    return None
