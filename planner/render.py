"""Monta o HTML da edição a partir dos tópicos e das folhas medidas."""

import json
import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

RAIZ = Path(__file__).resolve().parent.parent
ESTATICO = Path(__file__).resolve().parent / "estatico"

JORNAL = "O Diário do Flávio"
DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
        "sexta-feira", "sábado", "domingo"]


# A ordem importa só para a leitura: tudo roda no DOMContentLoaded.
SCRIPTS = ("estado.js", "paginar.js", "interacoes.js", "cadernos.js", "caderno-peso.js")


def montar(data, topicos: list[dict], folhas: list[dict] | None = None,
           estado: dict | None = None) -> str:
    """topicos: [{'id','nome','chapeu','blocos':[html]}] ou, nos cadernos, com 'caderno' e
    'dados'. folhas: medidas pelo build. estado: as fatias que as páginas leem (ver
    `estado.publico`) — nunca o estado inteiro, que tem as notas dele."""
    env = Environment(
        loader=FileSystemLoader(RAIZ / "templates"),
        autoescape=select_autoescape(enabled_extensions=()),
    )
    dados = {
        "jornal": JORNAL,
        "worker": (os.environ.get("WORKER_URL") or "").rstrip("/"),
        "data": data.strftime("%d/%m/%Y"),
        "dia": DIAS[data.weekday()],
        "numero": data.strftime("%Y%m%d"),
        "iso": data.isoformat(),
        "estado": estado or {},
        "topicos": topicos,
        "folhas": folhas or [],
    }
    return env.get_template("edicao.html.j2").render(
        jornal=JORNAL,
        data=dados["data"],
        textura=(RAIZ / "assets" / "papel-textura.b64").read_text(encoding="utf-8").strip(),
        css=(ESTATICO / "edicao.css").read_text(encoding="utf-8"),
        script="\n".join((ESTATICO / nome).read_text(encoding="utf-8")
                         for nome in SCRIPTS),
        dados=json.dumps(dados, ensure_ascii=False),
    )
