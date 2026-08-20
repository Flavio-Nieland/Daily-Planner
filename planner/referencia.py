"""Indicação de material de fora — sempre marcada como não conferida.

No teste dos três modelos, todos erraram a indicação musical: o Luna atribuiu "Satin Doll"
ao disco Ellington/Coltrane, onde a faixa não está. A progressão harmônica todos acertaram;
apontar gravação com precisão, nenhum. A decisão registrada (ADR 0004) foi **avisar em vez
de verificar** — descartadas a busca de verificação e a lista curada.

Vale para todo bloco de indicação: o "ouça" da Música, o material de Jogo e de Fazenda.
"""

MARCA = '<span class="naoconferida">não conferida</span>'


def bloco(titulo: str, texto: str, detalhe: str = "") -> str:
    extra = f'<p class="miudo">{detalhe}</p>' if detalhe else ""
    return (f'<div class="bloco indicacao"><h4>{titulo} {MARCA}</h4>'
            f'<p>{texto}</p>{extra}'
            f'<p class="miudo">Indicação do modelo, sem verificação — pode não existir '
            f'ou estar trocada.</p></div>')
