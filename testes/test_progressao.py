"""Os roteiros do protótipo de lógica, agora como teste.

Cada um deles existe porque é fácil errar no papel: são cinco regras que interagem quando
ele falta, pula dias ou muda de ideia.
"""

from datetime import date

import pytest

from planner import progressao

# quinta e sábado são os dias de corrida na agenda
QUINTA, SABADO = date(2026, 8, 20), date(2026, 8, 22)
SEXTA = date(2026, 8, 21)

INICIAL, TOTAL = 6, 32


def _feito(*dias, topico="corrida"):
    return {progressao.SECAO: {progressao.chave(topico, d): True for d in dias}}


def test_sem_nenhuma_marcacao_ele_esta_na_sessao_inicial():
    assert progressao.posicao({}, "corrida", INICIAL, TOTAL) == INICIAL


def test_faltar_nao_queima_sessao():
    """Passar dias sem marcar não avança nada — o plano espera por ele."""
    estado = {}
    for _ in range(10):
        assert progressao.posicao(estado, "corrida", INICIAL, TOTAL) == INICIAL


def test_marcar_como_feito_e_o_que_avanca():
    assert progressao.posicao(_feito(QUINTA), "corrida", INICIAL, TOTAL) == INICIAL + 1
    assert progressao.posicao(_feito(QUINTA, SABADO), "corrida", INICIAL, TOTAL) == INICIAL + 2


def test_marcar_duas_vezes_no_mesmo_dia_conta_uma():
    estado = _feito(QUINTA)
    estado[progressao.SECAO][progressao.chave("corrida", QUINTA)] = True   # de novo
    assert progressao.posicao(estado, "corrida", INICIAL, TOTAL) == INICIAL + 1


def test_marcacao_em_dia_fora_da_edicao_nao_vale():
    """Sexta não tem corrida na agenda. Se o ponteiro andar aqui, a regra está errada."""
    assert progressao.posicao(_feito(SEXTA), "corrida", INICIAL, TOTAL) == INICIAL
    assert progressao.conclusoes(_feito(SEXTA), "corrida") == []


def test_o_ponteiro_nao_passa_do_total():
    muitos = [date(2026, 8, 20) for _ in range(1)]
    estado = _feito(*[d for d in _dias_de_corrida(60)])
    assert progressao.posicao(estado, "corrida", INICIAL, TOTAL) == TOTAL


def _dias_de_corrida(quantos: int) -> list[date]:
    from datetime import timedelta
    dias, dia = [], date(2026, 8, 20)
    while len(dias) < quantos:
        if progressao.na_edicao("corrida", dia):
            dias.append(dia)
        dia += timedelta(days=1)
    return dias


def test_feito_hoje_so_vale_para_o_dia_de_hoje():
    estado = _feito(QUINTA)
    assert progressao.feito_hoje(estado, "corrida", QUINTA) is True
    assert progressao.feito_hoje(estado, "corrida", SABADO) is False


def test_um_topico_nao_mexe_no_ponteiro_do_outro():
    estado = _feito(QUINTA, topico="corrida")
    estado[progressao.SECAO].update(_feito(date(2026, 8, 18), topico="livros")[progressao.SECAO])
    assert progressao.posicao(estado, "corrida", INICIAL, TOTAL) == INICIAL + 1
    assert progressao.posicao(estado, "livros", 1, 12) == 2


def test_lixo_no_estado_nao_derruba_a_edicao():
    estado = {progressao.SECAO: {
        "corrida:não-é-data": True,
        "sem-dois-pontos": True,
        "corrida:2026-08-20": False,      # desmarcado
        "corrida:2026-08-22": True,
    }}
    assert progressao.conclusoes(estado, "corrida") == [SABADO]


def test_ultima_conclusao():
    assert progressao.ultima_conclusao({}, "corrida") is None
    assert progressao.ultima_conclusao(_feito(QUINTA, SABADO), "corrida") == SABADO
