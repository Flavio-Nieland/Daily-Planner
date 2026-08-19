"""O conteúdo gerado é cacheado por sessão, nunca por data.

É o que faz "não fez? amanhã é a mesma aula" acontecer de graça: a chave do arquivo é o
número da sessão. E economiza chamada — cada sessão é escrita uma vez só, e fica
versionada no git para ele poder corrigir à mão.
"""

import json
from pathlib import Path

PASTA = Path(__file__).resolve().parent.parent / "gerado"


def caminho(topico: str, sessao: int) -> Path:
    return PASTA / topico / f"{sessao:03d}.json"


def obter(topico: str, sessao: int, gerar) -> dict:
    arquivo = caminho(topico, sessao)
    if arquivo.exists():
        try:
            return json.loads(arquivo.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass                                   # arquivo corrompido: gera de novo
    dados = gerar()
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return dados
