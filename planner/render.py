"""Monta o HTML da edição a partir dos tópicos e das folhas medidas."""

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

RAIZ = Path(__file__).resolve().parent.parent
ESTATICO = Path(__file__).resolve().parent / "estatico"

JORNAL = "O Diário do Flávio"
DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
        "sexta-feira", "sábado", "domingo"]


def montar(data, topicos: list[dict], folhas: list[dict] | None = None) -> str:
    """topicos: [{'id','nome','chapeu','blocos':[html]}]. folhas: medidas pelo build."""
    env = Environment(
        loader=FileSystemLoader(RAIZ / "templates"),
        autoescape=select_autoescape(enabled_extensions=()),
    )
    dados = {
        "jornal": JORNAL,
        "data": data.strftime("%d/%m/%Y"),
        "dia": DIAS[data.weekday()],
        "numero": data.strftime("%Y%m%d"),
        "topicos": topicos,
        "folhas": folhas or [],
    }
    return env.get_template("edicao.html.j2").render(
        jornal=JORNAL,
        data=dados["data"],
        textura=(RAIZ / "assets" / "papel-textura.b64").read_text(encoding="utf-8").strip(),
        css=(ESTATICO / "edicao.css").read_text(encoding="utf-8"),
        script=(ESTATICO / "paginar.js").read_text(encoding="utf-8"),
        dados=json.dumps(dados, ensure_ascii=False),
    )
