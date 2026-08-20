"""Revisão espaçada: prato não dominado volta, e o esqueleto anda mesmo assim."""

from datetime import date

import pytest

from planner import conteudo, esqueleto
from planner.topicos import comida

SABADO, DOMINGO = date(2026, 8, 22), date(2026, 8, 23)
RECEITA = {"ingredientes": ["2 ovos", "sal"], "preparo": ["bata", "frite"],
           "ensina": "controle de fogo", "erro": "fogo alto demais"}


@pytest.fixture(autouse=True)
def sem_rede(tmp_path, monkeypatch):
    monkeypatch.setattr(conteudo, "PASTA", tmp_path / "gerado")
    monkeypatch.setattr(esqueleto, "PASTA", tmp_path / "esqueletos")
    monkeypatch.setattr(comida.llm, "gerar_json", lambda p, **k: (
        {"itens": [{"titulo": f"prato {i}", "tecnica": f"técnica {i}"} for i in range(1, 31)]}
        if "Liste 30 pratos" in p else dict(RECEITA)))


def _decidido(**pratos):
    """_decidido(**{'7': ('dominado', SABADO)}) -> estado."""
    return {comida.SECAO: {f"prato:{n}": {"dia": dia.isoformat(), "veredito": v}
                           for n, (v, dia) in pratos.items()}}


def test_comeca_no_primeiro_prato():
    assert "Prato 1 de 30" in comida.blocos(SABADO, {})[0]


def test_dominar_conta_e_avanca():
    saida = "".join(comida.blocos(DOMINGO, _decidido(**{"1": ("dominado", SABADO)})))
    assert "Prato 2 de 30" in saida
    assert "1 de 30 dominados" in saida


def test_nao_dominar_tambem_avanca_o_esqueleto():
    saida = "".join(comida.blocos(DOMINGO, _decidido(**{"1": ("revisar", SABADO)})))
    assert "Prato 2 de 30" in saida
    assert "0 de 30 dominados" in saida


def test_prato_nao_dominado_volta_depois_da_espera():
    estado = _decidido(**{"1": ("revisar", SABADO)})
    logo_depois = "".join(comida.blocos(DOMINGO, estado))
    assert "Prato 1 de 30" not in logo_depois          # ainda esperando

    passada_a_espera = "".join(comida.blocos(date(2026, 8, 29), estado))
    assert "Prato 1 de 30" in passada_a_espera
    assert "revisão" in passada_a_espera


def test_prato_dominado_nunca_volta():
    estado = _decidido(**{"1": ("dominado", SABADO)})
    assert "Prato 1 de 30" not in "".join(comida.blocos(date(2026, 8, 29), estado))


def test_veredito_gravado_em_dia_sem_comida_na_agenda_nao_vale():
    """Quarta não tem Comida. Marcar de fora não pode avançar nem contar."""
    estado = _decidido(**{"1": ("dominado", date(2026, 8, 19))})
    assert "Prato 1 de 30" in "".join(comida.blocos(SABADO, estado))


def test_a_folha_traz_ingredientes_preparo_e_o_que_ensina():
    saida = "".join(comida.blocos(SABADO, {}))
    assert "2 ovos" in saida and "bata" in saida
    assert "controle de fogo" in saida
    assert "fogo alto demais" in saida


def test_os_dois_botoes_de_veredito_aparecem():
    saida = "".join(comida.blocos(SABADO, {}))
    assert 'data-veredito="dominado"' in saida
    assert 'data-veredito="revisar"' in saida


def test_receita_e_gerada_com_os_dominados_no_contexto(monkeypatch):
    prompts = []
    monkeypatch.setattr(comida.llm, "gerar_json", lambda p, **k: prompts.append(p) or (
        {"itens": [{"titulo": f"prato {i}", "tecnica": "t"} for i in range(1, 31)]}
        if "Liste 30 pratos" in p else dict(RECEITA)))
    comida.blocos(DOMINGO, _decidido(**{"1": ("dominado", SABADO)}))
    assert any("Ele já domina: prato 1" in p for p in prompts)


def test_o_ponteiro_nao_passa_do_ultimo_prato():
    estado = _decidido(**{str(n): ("dominado", SABADO) for n in range(1, 41)})
    assert "Prato 30 de 30" in "".join(comida.blocos(DOMINGO, estado))
