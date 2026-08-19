"""Ritmo, retenção e o que ele escreve — o dado mais insubstituível do sistema."""

from datetime import date, timedelta

import pytest

from planner import conteudo, progressao
from planner.topicos import livros

TERCA, QUINTA, SABADO = date(2026, 8, 18), date(2026, 8, 20), date(2026, 8, 22)
TRECHO = {"onde": "ele está no meio da desilusão do protagonista.",
          "observe": "o narrador usa ironia para não julgar direto.",
          "pergunta": "O que a ironia do narrador esconde aqui?"}


@pytest.fixture(autouse=True)
def sem_rede(tmp_path, monkeypatch):
    monkeypatch.setattr(conteudo, "PASTA", tmp_path / "gerado")
    monkeypatch.setattr(livros.llm, "gerar_json", lambda p, **k: (
        {"sugestoes": [{"titulo": f"livro {i}", "autor": "autor", "motivo": "porque sim"}
                       for i in range(3)]} if "três próximos" in p else dict(TRECHO)))


def _feito(*dias):
    return {progressao.SECAO: {progressao.chave("livros", d): True for d in dias}}


def _nota(quando, texto):
    return {livros.SECAO_NOTA: {quando.isoformat(): texto}}


def test_a_primeira_sessao_traz_as_primeiras_paginas():
    saida = "".join(livros.blocos(TERCA, {}))
    assert "páginas 1 a 15" in saida
    assert "sessão 1 de 12" in saida


def test_ler_avanca_as_paginas():
    saida = "".join(livros.blocos(QUINTA, _feito(TERCA)))
    assert "páginas 16 a 30" in saida
    assert "sessão 2 de 12" in saida


def test_faltar_nao_avanca_a_leitura():
    assert "páginas 1 a 15" in "".join(livros.blocos(date(2026, 9, 1), {}))


def test_a_folha_pede_confirmacao_de_onde_ele_parou():
    """É a guarda contra o modelo inventar o que acontece na página."""
    assert "confirme onde você parou" in "".join(livros.blocos(TERCA, {}))


def test_o_prompt_proibe_afirmar_detalhe_de_pagina():
    assert "Nunca afirme detalhe de página específica" in livros.PROMPT_TRECHO
    assert "em vez de\ninventar cena" in livros.PROMPT_TRECHO


def test_a_pergunta_e_o_campo_de_resposta_aparecem():
    saida = "".join(livros.blocos(TERCA, {}))
    assert TRECHO["pergunta"] in saida
    assert 'id="nota-gravar"' in saida


def test_nota_recente_ainda_nao_volta():
    estado = _nota(TERCA, "achei irônico")
    assert "O que você escreveu antes" not in "".join(livros.blocos(QUINTA, estado))


def test_nota_de_tres_semanas_volta_para_revisao():
    estado = _nota(TERCA, "achei irônico")
    saida = "".join(livros.blocos(TERCA + timedelta(days=21), estado))
    assert "O que você escreveu antes" in saida
    assert "achei irônico" in saida


def test_notas_sobrevivem_no_estado_e_saem_em_ordem():
    estado = {livros.SECAO_NOTA: {"2026-08-01": "primeira", "2026-07-01": "anterior"}}
    assert [t for _, t in livros.notas(estado)] == ["anterior", "primeira"]


def test_na_ultima_sessao_aparecem_tres_sugestoes():
    from datetime import timedelta
    dias, dia = [], TERCA
    while len(dias) < 11:
        if progressao.na_edicao("livros", dia):
            dias.append(dia)
        dia += timedelta(days=1)
    saida = "".join(livros.blocos(dias[-1], _feito(*dias)))
    assert "O próximo livro" in saida
    assert saida.count('class="proximo"') == 3


def test_antes_da_ultima_sessao_nao_ha_sugestao():
    assert "O próximo livro" not in "".join(livros.blocos(TERCA, {}))
