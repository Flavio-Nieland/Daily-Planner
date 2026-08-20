"""Conceitos em ordem de dependência, e a indicação sempre marcada como não conferida."""

from datetime import date

import pytest

from planner import conteudo, esqueleto, progressao
from planner.topicos import musica

SEGUNDA, QUARTA = date(2026, 8, 17), date(2026, 8, 19)
LICAO = {"conceito": "o trítono entre 3ª e 7ª puxa a resolução.",
         "instrumento": "toque em dó e em sol, dez vezes cada.",
         "ouca": "Kind of Blue, faixa So What"}


@pytest.fixture(autouse=True)
def sem_rede(tmp_path, monkeypatch):
    monkeypatch.setattr(conteudo, "PASTA", tmp_path / "gerado")
    monkeypatch.setattr(esqueleto, "PASTA", tmp_path / "esqueletos")
    monkeypatch.setattr(musica.llm, "gerar_json", lambda p, **k: (
        {"itens": [{"titulo": f"conceito {i}", "depende": f"conceito {i-1}" if i > 1 else ""}
                   for i in range(1, 25)]} if "Liste 24 conceitos" in p else dict(LICAO)))


def _feito(*dias):
    return {progressao.SECAO: {progressao.chave("musica", d): True for d in dias}}


def test_comeca_no_primeiro_conceito_e_avanca_por_conclusao():
    assert "Conceito 1 de 24" in musica.blocos(SEGUNDA, {})[0]
    assert "Conceito 2 de 24" in musica.blocos(QUARTA, _feito(SEGUNDA))[0]


def test_faltar_mantem_o_conceito():
    assert "Conceito 1 de 24" in musica.blocos(date(2026, 9, 2), {})[0]


def test_a_folha_traz_conceito_e_no_instrumento():
    saida = "".join(musica.blocos(SEGUNDA, {}))
    assert "trítono entre 3ª e 7ª" in saida
    assert "toque em dó e em sol" in saida


def test_o_ouca_vai_marcado_como_nao_conferido():
    """Nenhum dos três modelos acertou indicação de gravação — a decisão foi avisar."""
    saida = "".join(musica.blocos(SEGUNDA, {}))
    assert "Kind of Blue" in saida
    assert "não conferida" in saida
    assert "sem verificação" in saida


def test_a_ordem_de_dependencia_aparece_na_folha():
    saida = musica.blocos(QUARTA, _feito(SEGUNDA))[0]
    assert "vem de: conceito 1" in saida


def test_a_licao_e_gerada_com_os_conceitos_estudados_no_contexto(monkeypatch):
    prompts = []
    monkeypatch.setattr(musica.llm, "gerar_json", lambda p, **k: prompts.append(p) or (
        {"itens": [{"titulo": f"conceito {i}", "depende": ""} for i in range(1, 25)]}
        if "Liste 24" in p else dict(LICAO)))
    musica.blocos(QUARTA, _feito(SEGUNDA))
    assert any("Ele já estudou: conceito 1" in p for p in prompts)


def test_o_ponteiro_nao_passa_do_ultimo_conceito():
    from datetime import timedelta
    dias, dia = [], SEGUNDA
    while len(dias) < 30:
        if progressao.na_edicao("musica", dia):
            dias.append(dia)
        dia += timedelta(days=1)
    assert "Conceito 24 de 24" in musica.blocos(dias[-1], _feito(*dias))[0]
