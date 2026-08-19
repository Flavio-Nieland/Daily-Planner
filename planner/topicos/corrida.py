"""Folha da Corrida — 10 km contínuos, sem prazo.

O `running_plan.json` já é o esqueleto: 32 sessões com a instrução objetiva de cada uma.
Ele entra como está; o modelo só escreve o detalhe do dia a partir do título da sessão da
vez. A progressão é por conclusão — faltar não queima sessão (ADR 0001, TOPICOS.md).
"""

import json
from datetime import date
from pathlib import Path

from planner import conteudo, llm, progressao

PLANO = Path(__file__).resolve().parent.parent.parent / "running_plan.json"
SESSAO_INICIAL = 6          # onde ele estava quando o v2 começou; editável à mão

PROMPT = """Você escreve a folha de corrida de um jornal pessoal, em português do Brasil.

A sessão de hoje é a número {numero} de {total} de um plano para chegar a 10 km contínuos.
A instrução objetiva dela é: "{instrucao}"

Escreva o detalhe do dia. Responda SÓ com um objeto JSON exatamente neste formato:

{{
  "aquecimento": "string, 1 frase, o que fazer antes de começar a correr",
  "esforco": "string, 1 frase, o esforço-alvo descrito em SENSAÇÃO (por exemplo: falar frases curtas, não cantar). Nunca use pace, batimento ou ritmo em números",
  "tecnica": "string, 1 frase, um único ponto de técnica para observar durante a corrida",
  "porque": "string, 1 frase, por que esta sessão existe dentro do plano"
}}

Sem markdown, sem comentários, sem texto fora do JSON."""


def _esqueleto() -> dict:
    return json.loads(PLANO.read_text(encoding="utf-8"))


def _sessao(plano: dict, numero: int) -> dict:
    for sessao in plano["sessions"]:
        if sessao["session"] == numero:
            return sessao
    return plano["sessions"][-1]


def _detalhe(numero: int, total: int, instrucao: str) -> dict:
    def gerar():
        bruto = llm.gerar_json(
            PROMPT.format(numero=numero, total=total, instrucao=instrucao), max_tokens=700
        )
        return {
            "aquecimento": llm.texto(llm.campo(bruto, "aquecimento", "warmup", "aquecer")),
            "esforco": llm.texto(llm.campo(bruto, "esforco", "esforço", "effort", "intensidade")),
            "tecnica": llm.texto(llm.campo(bruto, "tecnica", "técnica", "technique", "forma")),
            "porque": llm.texto(llm.campo(bruto, "porque", "por_que", "porquê", "motivo", padrao="")),
        }

    return conteudo.obter("corrida", numero, gerar)


def blocos(dia: date, estado: dict) -> list[str]:
    plano = _esqueleto()
    total = plano.get("total_sessions") or len(plano["sessions"])
    numero = progressao.posicao(estado, "corrida", SESSAO_INICIAL, total)
    sessao = _sessao(plano, numero)
    instrucao = sessao.get("goal_description", "")
    detalhe = _detalhe(numero, total, instrucao)

    feito = progressao.feito_hoje(estado, "corrida", dia)
    ultima = progressao.ultima_conclusao(estado, "corrida")
    desde = (f'<p class="miudo">última corrida em {ultima.strftime("%d/%m")}</p>'
             if ultima else '<p class="miudo">primeira sessão registrada</p>')

    duracao = (f'<p class="miudo">{sessao["duration_minutes"]} minutos</p>'
               if sessao.get("duration_minutes") else "")
    porque = f'<p class="miudo">{detalhe["porque"]}</p>' if detalhe["porque"] else ""
    hoje = (f'<div class="bloco"><h4>Sessão {numero} de {total}</h4>'
            f'<p class="destaque-texto">{instrucao}</p>{duracao}{porque}</div>')

    partes = [
        hoje,
        f'<div class="bloco"><h4>Antes de sair</h4><p>{detalhe["aquecimento"]}</p></div>',
        f'<div class="bloco"><h4>O esforço de hoje</h4><p>{detalhe["esforco"]}</p></div>',
        f'<div class="bloco"><h4>Observe na corrida</h4><p>{detalhe["tecnica"]}</p></div>',
    ]

    feitas = numero - 1
    proporcao = max(0, min(100, round(feitas / total * 100)))
    partes.append(
        f'<div class="bloco"><h4>O plano</h4>'
        f'<div class="barra"><i style="width:{proporcao}%"></i></div>'
        f'<p class="miudo">{feitas} de {total} sessões · faltam {total - feitas}</p>{desde}'
        + _marcador(dia, feito) + '</div>'
    )
    return partes


def _marcador(dia: date, feito: bool) -> str:
    if feito:
        return ('<p class="feito" id="corrida-marca" data-topico="corrida" '
                f'data-dia="{dia.isoformat()}">✓ corrida feita hoje</p>')
    return (
        '<p class="campo"><button type="button" class="marcar" data-topico="corrida" '
        f'data-dia="{dia.isoformat()}" id="corrida-marca">fiz hoje</button></p>'
        '<p class="miudo" id="corrida-aviso">Marcar avança para a próxima sessão na edição de amanhã.</p>'
    )
