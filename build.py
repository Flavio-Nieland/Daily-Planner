"""Gera a edição do dia e publica.

Sem e-mail: a edição se refaz sozinha todo dia e fica esperando ele abrir a URL (ADR 0005).
Grava docs/index.html e o acervo docs/AAAA/MM/DD/index.html.
"""

import argparse
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from planner import acervo, estado, falha, render
from planner.agenda import NOMES, topicos_do_dia
from planner.paginacao import medir
from planner.topicos import (album, alongamento, biblia, comida, corrida, dieta, peso,
                             livros, musica, programacao, resumo, tempo,
                             treino, xadrez)

BRT = timezone(timedelta(hours=-3))
DOCS = Path(__file__).resolve().parent / "docs"

# Chapéu (kicker) de cada folha. Tópico sem gerador ainda não entra na edição.
CHAPEUS = {"resumo": "Edição de hoje", "tempo": "Previsão para São José",
           "peso": "Sua curva", "corrida": "Rumo aos 10 km",
           "xadrez": "Subindo de Elo", "comida": "Repertório de 30 pratos",
           "album": "Dois discos por dia", "dieta": "2.800 kcal do dia",
           "biblia": "Salmo do dia", "alongamento": "Amplitude e lombar",
           "treino": "Carga que sobe", "musica": "Entendendo harmonia",
           "programacao": "Fundamentos que não expiram",
           "livros": "Ritmo e retenção"}

# O Resumo fica de fora: ele fala das outras folhas, então é montado depois delas.
GERADORES = {
    "tempo": lambda dia, est: tempo.blocos(),
    "peso": lambda dia, est: peso.blocos(dia, estado.serie(est, "peso")),
    "corrida": lambda dia, est: corrida.blocos(dia, est),
    "xadrez": lambda dia, est: xadrez.blocos(dia, est, estado.serie(est, "elo")),
    "comida": lambda dia, est: comida.blocos(dia, est),
    "album": lambda dia, est: album.blocos(dia, est),
    "dieta": lambda dia, est: dieta.blocos(dia),
    "biblia": lambda dia, est: biblia.blocos(dia),
    "alongamento": lambda dia, est: alongamento.blocos(dia, est),
    "treino": lambda dia, est: treino.blocos(dia, est),
    "musica": lambda dia, est: musica.blocos(dia, est),
    "programacao": lambda dia, est: programacao.blocos(dia, est),
    "livros": lambda dia, est: livros.blocos(dia, est),
}


def _folha(tid: str, blocos: list[str], falhou: bool = False) -> dict:
    return {"id": tid, "nome": NOMES[tid], "chapeu": CHAPEUS.get(tid, NOMES[tid]),
            "blocos": blocos, "falhou": falhou}


def montar_topicos(dia: date, est: dict | None = None) -> tuple[list[dict], list[dict]]:
    """As folhas da edição, na ordem da agenda, mais a lista do que falhou.

    Folha que falha continua na edição dizendo o que faltou — nunca desaparece.
    """
    est = {} if est is None else est
    folhas, falhas = [], []
    for tid in topicos_do_dia(dia):
        if tid not in GERADORES:
            continue                     # tópico ainda não implementado nesta fatia
        try:
            folhas.append(_folha(tid, GERADORES[tid](dia, est)))
        except Exception as erro:        # noqa: BLE001 — qualquer fonte pode falhar
            print(f"  falhou: {tid} — {erro.__class__.__name__}: {erro}", file=sys.stderr)
            falhas.append({"topico": tid, "erro": f"{erro.__class__.__name__}: {erro}"})
            folhas.append(_folha(tid, falha.blocos(NOMES[tid], erro,
                                                  acervo.blocos_de_ontem(dia, tid)), falhou=True))
    na_edicao = ["resumo"] + [f["id"] for f in folhas]
    return [_folha("resumo", resumo.blocos(dia, na_edicao))] + folhas, falhas


def publicar(dia: date, html: str) -> list[Path]:
    destinos = [DOCS / "index.html",
                DOCS / dia.strftime("%Y") / dia.strftime("%m") / dia.strftime("%d") / "index.html"]
    for destino in destinos:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(html, encoding="utf-8")
    return destinos


def main() -> int:
    ap = argparse.ArgumentParser(description="Gera a edição do dia")
    ap.add_argument("--data", help="AAAA-MM-DD; padrão é hoje no fuso de Brasília")
    ap.add_argument("--sem-medir", action="store_true",
                    help="pula o Chromium; a paginação fica só do lado do navegador")
    args = ap.parse_args()

    dia = date.fromisoformat(args.data) if args.data else datetime.now(BRT).date()
    est = estado.consolidar()
    topicos, falhas = montar_topicos(dia, est)
    print(f"edição de {dia:%d/%m/%Y}: {len(topicos)} tópicos "
          f"({sum(len(t['blocos']) for t in topicos)} blocos)")

    html = render.montar(dia, topicos)
    folhas = [] if args.sem_medir else medir(html)
    if folhas:
        print(f"paginação medida: {len(folhas)} folhas")
        html = render.montar(dia, topicos, folhas)

    for destino in publicar(dia, html):
        print(f"publicado: {destino.relative_to(Path.cwd()) if destino.is_relative_to(Path.cwd()) else destino}")
    acervo.gravar(dia, topicos, falhas)

    _resumir(dia, topicos, falhas)

    # A edição sai de qualquer jeito; a falha é ruidosa depois de publicar, nunca silenciosa.
    if falhas:
        quais = ", ".join(f["topico"] for f in falhas)
        print(f"\nFALHARAM {len(falhas)} folha(s): {quais}", file=sys.stderr)
        return 2
    return 0


def _resumir(dia: date, topicos: list[dict], falhas: list[dict]) -> None:
    """Resumo da execução no painel do Actions, dizendo quais tópicos falharam."""
    caminho = os.environ.get("GITHUB_STEP_SUMMARY")
    if not caminho:
        return
    linhas = [f"## Edição de {dia:%d/%m/%Y}", "",
              f"{len(topicos)} folhas geradas."]
    if falhas:
        linhas += ["", f"### {len(falhas)} folha(s) falharam", ""]
        linhas += [f"- **{NOMES[f['topico']]}** — {f['erro']}" for f in falhas]
    else:
        linhas += ["", "Nenhuma falha."]
    with open(caminho, "a", encoding="utf-8") as saida:
        saida.write("\n".join(linhas) + "\n")


if __name__ == "__main__":
    sys.exit(main())
