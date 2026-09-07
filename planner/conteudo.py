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


def caminho_por_data(topico: str, dia) -> Path:
    return PASTA / topico / f"{dia.isoformat()}.json"


def obter_por_data(topico: str, dia, gerar) -> dict:
    """A exceção consciente à regra acima, para o Álbum.

    Cachear por sessão pressupõe que o tópico tenha sessão — e o Álbum é o único que não
    tem: ele não avança por conclusão, é um disco por data e pronto. Sem cache nenhum,
    cada build do dia sorteava outro disco: com dois crons, quem abria de manhã via um
    disco e quem abria de tarde via outro, e o histórico inflava quatro linhas por dia.
    """
    arquivo = caminho_por_data(topico, dia)
    if arquivo.exists():
        try:
            return json.loads(arquivo.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass                                   # arquivo corrompido: gera de novo
    dados = gerar()
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return dados


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
