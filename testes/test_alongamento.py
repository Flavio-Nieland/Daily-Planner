"""Rotina fixa: a mesma sequência todo dia, sem LLM e sem sortear nada."""

from datetime import date

import pytest

from planner.topicos import alongamento

SEGUNDA, TERCA, QUARTA, QUINTA, SEXTA = (date(2026, 8, d) for d in (17, 18, 19, 20, 21))


def test_pernas_na_segunda_quarta_e_sexta_quadril_na_terca_e_quinta():
    assert [alongamento.bloco_do_dia(d) for d in (SEGUNDA, QUARTA, SEXTA)] == [alongamento.BLOCO_A] * 3
    assert [alongamento.bloco_do_dia(d) for d in (TERCA, QUINTA)] == [alongamento.BLOCO_B] * 2


def test_o_nucleo_lombar_aparece_todos_os_dias():
    for dia in (SEGUNDA, TERCA, QUARTA, QUINTA, SEXTA):
        saida = "".join(alongamento.blocos(dia, {}))
        assert saida.count("N1 ·") == 1
        assert "N6 ·" in saida


def test_a_rotina_e_identica_de_uma_semana_para_a_outra():
    """Se isto mudar, o tópico voltou a gerar rotina nova — o defeito que o v2 conserta.

    Só o último bloco difere, porque é o de registro e carrega a data do dia.
    """
    assert alongamento.blocos(SEGUNDA, {})[:-1] == alongamento.blocos(date(2026, 8, 24), {})[:-1]


def test_cada_posicao_tem_ilustracao_dose_e_erro_comum():
    saida = "".join(alongamento.blocos(SEGUNDA, {}))
    assert saida.count("<svg") == 14          # 6 do núcleo + 8 do bloco A
    assert "Erro comum:" in saida
    assert "120s" in saida


def test_os_dois_alvos_travados_tem_pnf():
    pernas = "".join(alongamento.blocos(SEGUNDA, {}))
    quadril = "".join(alongamento.blocos(TERCA, {}))
    assert "Isquiotibiais — PNF" in pernas
    assert "Psoas — PNF" in quadril


def test_nenhuma_chamada_de_modelo_neste_topico(monkeypatch):
    from planner import llm

    def explode(*a, **k):
        raise AssertionError("este tópico não pode chamar LLM")

    monkeypatch.setattr(llm, "gerar_json", explode)
    monkeypatch.setattr(llm, "_cliente", explode)
    assert alongamento.blocos(SEGUNDA, {})


def test_campos_de_maochao_e_dor_aparecem():
    saida = "".join(alongamento.blocos(SEGUNDA, {}))
    assert 'id="maochao-gravar"' in saida and 'id="dor-gravar"' in saida


def test_variacao_contra_o_primeiro_registro():
    estado = {alongamento.SECAO: {"maochao:2026-07-01": 18, "maochao:2026-08-17": 12,
                                  "dor:2026-08-17": 3}}
    saida = "".join(alongamento.blocos(SEGUNDA, estado))
    assert "último: 12 cm em 17/08" in saida
    assert "-6 cm desde 01/07" in saida
    assert "último: 3 em 17/08" in saida


def test_registro_estragado_nao_derruba_a_folha():
    estado = {alongamento.SECAO: {"maochao:2026-08-17": "nada", "outra:coisa": 1}}
    assert "sem registro ainda" in "".join(alongamento.blocos(SEGUNDA, estado))
