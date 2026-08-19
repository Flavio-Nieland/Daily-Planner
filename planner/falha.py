"""A folha que aparece quando uma fonte falha.

O pior defeito do v1 era a seção sumir da página quando a chamada falhava: a dieta não
saía em produção há tempo indeterminado e ninguém percebeu. Aqui a folha continua na
edição dizendo o que faltou — e traz o dado de ontem quando existir.
"""

import re
from datetime import date

# O site é público: a mensagem de erro não pode levar chave nem token para a folha.
SEGREDOS = [
    re.compile(r"(?i)\b(sk|ghp|gho|xox[baprs])[-_][A-Za-z0-9_-]{8,}"),
    re.compile(r"(?i)\b(api[_-]?key|token|authorization|senha|password)\s*[=:]\s*\S+"),
    re.compile(r"(?i)([?&](?:key|token|api_key|access_token)=)[^&\s]+"),
]


def _motivo(erro: BaseException) -> str:
    texto = str(erro).strip() or erro.__class__.__name__
    for padrao in SEGREDOS:
        texto = padrao.sub("[oculto]", texto)
    return texto if len(texto) <= 200 else texto[:197] + "..."


def blocos(nome: str, erro: BaseException, anteriores: tuple[list[str], date] | None) -> list[str]:
    aviso = (
        f'<div class="bloco falhou"><h4>Esta folha não saiu hoje</h4>'
        f'<p>A fonte de {nome} falhou na geração desta edição.</p>'
        f'<p class="miudo">{erro.__class__.__name__}: {_motivo(erro)}</p></div>'
    )
    if not anteriores:
        return [aviso]

    blocos_antigos, quando = anteriores
    marca = (
        f'<div class="bloco falhou"><h4>Abaixo, o que saiu em {quando.strftime("%d/%m")}</h4>'
        f'<p class="miudo">Conteúdo repetido do acervo — não é o dado de hoje.</p></div>'
    )
    return [aviso, marca] + blocos_antigos
