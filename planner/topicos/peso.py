"""Caderno do Peso — a curva interativa e o registro, sem LLM e sem API externa.

Desde 2026-11-03 é um caderno de duas páginas (A curva · Registrar) desenhado no
navegador por caderno-peso.js. A série vem do estado embutido no HTML e, quando o
navegador tem o token, do Worker ao vivo: o peso gravado agora entra na curva agora.

Continua sendo o caso de teste do caminho de escrita (Worker → KV → estado.json).
"""

from datetime import date

# Alvo dele, decidido em 2026-11-03. A página do Balanço deixa trocar; a troca vai para
# `medida["meta:peso"]` e vale sobre este padrão.
META_KG = 70.0


def caderno(dia: date) -> dict:
    return {"caderno": "peso", "dados": {"hoje": dia.isoformat(), "meta": META_KG}}
