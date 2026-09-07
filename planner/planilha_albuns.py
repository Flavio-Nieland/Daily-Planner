"""Manda a tabela de álbuns para a planilha do Google, via Apps Script preso a ela.

Decisões do grill de 07/09/2026:

- **Manda a tabela inteira, não a linha do dia.** É o que dá backfill, idempotência e
  auto-recuperação de graça: a primeira chamada preenche todas as datas do histórico, rodar
  três vezes no mesmo dia não duplica nada, e um dia que falhou entra sozinho na chamada
  seguinte. Um ano de diário são ~20 KB de payload, contra o limite de 50 MB do Apps Script.
- **Falha em silêncio, só no log.** Escolha explícita dele. Só é tolerável por causa da
  auto-recuperação acima — a planilha nunca fica com buraco permanente.
- **Sem `PLANILHA_URL`/`PLANILHA_TOKEN` é no-op**, sem erro e sem log de falha: é o que
  permite o código viver em produção antes de a planilha existir.

O token vive em secret do repositório e nunca é impresso — nem em mensagem de erro.
"""

import json
import os

TEMPO_LIMITE = 25          # s; o Apps Script costuma responder em 2-4


def consolidar(historico: list[dict]) -> list[dict]:
    """Uma linha por data: o disco de cada origem, no formato "Álbum — Artista".

    Data com mais de um disco da mesma origem é resquício da época do append cego, quando
    cada build do dia acrescentava um par. Vence o **último**, que é o que ficou no site
    naquele dia. Coluna vazia é legítima: nos primeiros dias o perfil do Spotify não vinha,
    então não houve disco do gosto.
    """
    campo = {"gosto": "gosto", "estilo": "pedido"}
    por_data: dict[str, dict] = {}
    for registro in historico:
        data = str(registro.get("data") or "").strip()
        qual = campo.get(registro.get("origem"))
        if not data or not qual:
            continue
        linha = por_data.setdefault(data, {"data": data, "gosto": "", "pedido": ""})
        album = str(registro.get("album") or "").strip()
        artista = str(registro.get("artista") or "").strip()
        if not album:
            continue
        linha[qual] = f"{album} — {artista}" if artista else album
    return [por_data[data] for data in sorted(por_data)]


def enviar(historico: list[dict]) -> dict | None:
    """Devolve a resposta do script, ou None quando não há para onde mandar."""
    url = os.environ.get("PLANILHA_URL", "").strip()
    token = os.environ.get("PLANILHA_TOKEN", "").strip()
    if not url or not token:
        return None                            # planilha não configurada: nada a fazer

    import requests

    linhas = consolidar(historico)
    corpo = json.dumps({"token": token, "linhas": linhas}, ensure_ascii=False)
    # text/plain é o que o Apps Script aceita sem preflight, e é o padrão já usado nos
    # outros scripts dele. O redirect 302 para googleusercontent é seguido como GET pelo
    # requests, que é justamente o comportamento correto aqui.
    resposta = requests.post(url, data=corpo.encode("utf-8"), timeout=TEMPO_LIMITE,
                             headers={"Content-Type": "text/plain; charset=utf-8"})
    resposta.raise_for_status()
    devolvido = resposta.json()
    if not devolvido.get("ok"):
        # o erro do script entra na mensagem; a URL e o token, nunca
        raise RuntimeError(f'a planilha recusou: {devolvido.get("erro", "motivo não dito")}')
    return devolvido
