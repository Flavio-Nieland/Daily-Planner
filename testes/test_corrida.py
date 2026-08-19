"""A folha da Corrida: o esqueleto que já existe mais o detalhe do dia.

O que se protege aqui é a regra de progressão chegando na folha — e o cache por sessão,
que é o que faz "não fez? amanhã é a mesma sessão" valer também para o conteúdo.
"""

import json
from datetime import date

import pytest

from planner import conteudo, progressao
from planner.topicos import corrida

QUINTA, SABADO = date(2026, 8, 20), date(2026, 8, 22)

DETALHE = {"aquecimento": "cinco minutos de caminhada rápida",
           "esforco": "dá para falar frases curtas, não dá para cantar",
           "tecnica": "passada curta, pé caindo embaixo do quadril",
           "porque": "constrói base aeróbica sem castigar as canelas"}


@pytest.fixture(autouse=True)
def sem_rede(tmp_path, monkeypatch):
    monkeypatch.setattr(conteudo, "PASTA", tmp_path / "gerado")
    monkeypatch.setattr(corrida.llm, "gerar_json", lambda *a, **k: dict(DETALHE))


def _feito(*dias):
    return {progressao.SECAO: {progressao.chave("corrida", d): True for d in dias}}


def test_sem_marcacao_alguma_ele_esta_na_sessao_inicial():
    blocos = corrida.blocos(QUINTA, {})
    assert f"Sessão {corrida.SESSAO_INICIAL} de 32" in blocos[0]


def test_marcar_avanca_a_sessao_no_dia_seguinte():
    blocos = corrida.blocos(SABADO, _feito(QUINTA))
    assert f"Sessão {corrida.SESSAO_INICIAL + 1} de 32" in blocos[0]


def test_faltar_mantem_a_mesma_sessao():
    """Duas semanas sem correr: a folha tem que continuar na mesma sessão."""
    de_hoje = corrida.blocos(QUINTA, {})[0]
    duas_semanas_depois = corrida.blocos(date(2026, 9, 3), {})[0]
    assert de_hoje == duas_semanas_depois


def test_a_folha_traz_aquecimento_esforco_e_tecnica():
    blocos = "".join(corrida.blocos(QUINTA, {}))
    assert DETALHE["aquecimento"] in blocos
    assert DETALHE["esforco"] in blocos
    assert DETALHE["tecnica"] in blocos


def test_o_esforco_e_descrito_em_sensacao():
    prompt = corrida.PROMPT
    assert "SENSAÇÃO" in prompt
    assert "Nunca use pace" in prompt


def test_marcador_de_hoje_aparece_e_some_depois_de_marcado():
    antes = "".join(corrida.blocos(QUINTA, {}))
    assert 'class="marcar"' in antes and 'data-dia="2026-08-20"' in antes

    depois = "".join(corrida.blocos(QUINTA, _feito(QUINTA)))
    assert "corrida feita hoje" in depois
    assert 'class="marcar"' not in depois


def test_progresso_conta_as_sessoes_ja_feitas():
    blocos = "".join(corrida.blocos(SABADO, _feito(QUINTA)))
    assert "6 de 32 sessões" in blocos
    assert "faltam 26" in blocos


def test_conteudo_e_cacheado_por_sessao_nao_por_data(monkeypatch):
    chamadas = []
    monkeypatch.setattr(corrida.llm, "gerar_json",
                        lambda *a, **k: chamadas.append(1) or dict(DETALHE))

    corrida.blocos(QUINTA, {})
    corrida.blocos(SABADO, {})          # outro dia, mesma sessão
    assert len(chamadas) == 1, "gerou de novo a mesma sessão — o cache é por sessão"

    corrida.blocos(SABADO, _feito(QUINTA))   # sessão nova
    assert len(chamadas) == 2


def test_conteudo_gerado_fica_em_arquivo_editavel_a_mao():
    corrida.blocos(QUINTA, {})
    arquivo = conteudo.caminho("corrida", corrida.SESSAO_INICIAL)
    assert arquivo.exists()
    assert json.loads(arquivo.read_text(encoding="utf-8"))["esforco"] == DETALHE["esforco"]


def test_arquivo_corrompido_nao_derruba_a_folha():
    arquivo = conteudo.caminho("corrida", corrida.SESSAO_INICIAL)
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text("{isso não é json", encoding="utf-8")
    assert DETALHE["esforco"] in "".join(corrida.blocos(QUINTA, {}))


def test_o_ponteiro_nao_passa_da_ultima_sessao():
    from datetime import timedelta
    dias, dia = [], QUINTA
    while len(dias) < 40:
        if progressao.na_edicao("corrida", dia):
            dias.append(dia)
        dia += timedelta(days=1)
    assert "Sessão 32 de 32" in corrida.blocos(dias[-1], _feito(*dias))[0]


def test_campo_alternativo_do_modelo_nao_quebra_a_folha(monkeypatch):
    """O modelo varia o nome das chaves mesmo com o schema repetido."""
    monkeypatch.setattr(corrida.llm, "gerar_json", lambda *a, **k: {
        "aquecer": "caminhada leve", "esforço": "conversar sim, cantar não",
        "técnica": "olhar no horizonte", "motivo": "base aeróbica"})
    blocos = "".join(corrida.blocos(QUINTA, {}))
    assert "conversar sim, cantar não" in blocos
    assert "olhar no horizonte" in blocos
