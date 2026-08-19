"""Falha nunca é silenciosa: a folha continua na edição dizendo o que faltou.

O pior defeito do v1 era o contrário — a seção sumia da página e o job terminava verde.
"""

from datetime import date, timedelta

import pytest

import build
from planner import acervo


@pytest.fixture
def hoje(tmp_path, monkeypatch):
    monkeypatch.setattr(acervo, "DOCS", tmp_path)
    monkeypatch.setattr(build, "DOCS", tmp_path)
    return date(2026, 8, 19)


def _quebrado(_dia):
    raise ConnectionError("Open-Meteo fora do ar")


def test_folha_que_falha_continua_na_edicao(hoje, monkeypatch):
    monkeypatch.setitem(build.GERADORES, "tempo", _quebrado)
    topicos, falhas = build.montar_topicos(hoje)

    ids = [t["id"] for t in topicos]
    assert "tempo" in ids, "a folha sumiu da edição — é exatamente o defeito do v1"
    assert [f["topico"] for f in falhas] == ["tempo"]

    folha = next(t for t in topicos if t["id"] == "tempo")
    assert folha["falhou"] is True
    assert "não saiu hoje" in folha["blocos"][0]
    assert "ConnectionError" in folha["blocos"][0]
    assert "Open-Meteo fora do ar" in folha["blocos"][0]


def test_falha_reaproveita_o_dado_de_ontem(hoje, monkeypatch):
    ontem = hoje - timedelta(days=1)
    acervo.gravar(ontem, [{"id": "tempo", "nome": "Tempo", "blocos": ["<div>previsão de ontem</div>"],
                           "falhou": False}], [])

    monkeypatch.setitem(build.GERADORES, "tempo", _quebrado)
    topicos, _ = build.montar_topicos(hoje)
    blocos = next(t for t in topicos if t["id"] == "tempo")["blocos"]

    assert "18/08" in blocos[1]
    assert "não é o dado de hoje" in blocos[1]
    assert "<div>previsão de ontem</div>" in blocos


def test_sem_acervo_a_folha_diz_so_o_que_faltou(hoje, monkeypatch):
    monkeypatch.setitem(build.GERADORES, "tempo", _quebrado)
    topicos, _ = build.montar_topicos(hoje)
    assert len(next(t for t in topicos if t["id"] == "tempo")["blocos"]) == 1


def test_dado_de_ontem_nao_vem_de_uma_edicao_que_tambem_falhou(hoje, monkeypatch):
    ontem = hoje - timedelta(days=1)
    acervo.gravar(ontem, [{"id": "tempo", "nome": "Tempo", "blocos": ["<div>aviso de falha</div>"],
                           "falhou": True}], [{"topico": "tempo", "erro": "x"}])

    monkeypatch.setitem(build.GERADORES, "tempo", _quebrado)
    topicos, _ = build.montar_topicos(hoje)
    assert len(next(t for t in topicos if t["id"] == "tempo")["blocos"]) == 1


def test_o_resumo_conta_a_folha_que_falhou(hoje, monkeypatch):
    monkeypatch.setitem(build.GERADORES, "tempo", _quebrado)
    topicos, _ = build.montar_topicos(hoje)
    assert "Tempo" in topicos[0]["blocos"][1]


def test_build_sai_com_erro_quando_alguma_folha_falha(hoje, monkeypatch, capsys):
    monkeypatch.setitem(build.GERADORES, "tempo", _quebrado)
    monkeypatch.setattr("sys.argv", ["build.py", "--data", hoje.isoformat(), "--sem-medir"])

    assert build.main() == 2, "o job precisa terminar vermelho, não verde"
    assert "FALHARAM" in capsys.readouterr().err
    assert (build.DOCS / "index.html").exists(), "a edição precisa sair mesmo com falha"


@pytest.mark.parametrize("texto,proibido", [
    ("erro em https://hub.seazone.dev/v1?api_key=abc123secreto", "abc123secreto"),
    ("401: token=ghp_aaaaaaaaaaaaaaaaaaaa", "ghp_aaaaaaaaaaaaaaaaaaaa"),
    ("recusado: Authorization: Bearer sk-proj-xyz987", "sk-proj-xyz987"),
])
def test_a_folha_publica_nao_leva_segredo(texto, proibido):
    """O site é público: mensagem de erro não pode vazar chave para dentro da folha."""
    from planner.falha import blocos
    saida = "".join(blocos("Tempo", RuntimeError(texto), None))
    assert proibido not in saida
    assert "[oculto]" in saida
