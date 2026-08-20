"""O caminho de escrita: Worker → KV → estado.json → folha.

Se o peso não persistir, nada persiste — é o caso de teste do estado inteiro (ADR 0003).
"""

import json
from datetime import date

import pytest
import requests

from planner import estado
from planner.topicos import peso


@pytest.fixture
def arquivo(tmp_path, monkeypatch):
    alvo = tmp_path / "estado.json"
    monkeypatch.setattr(estado, "ARQUIVO", alvo)
    monkeypatch.delenv("WORKER_URL", raising=False)
    monkeypatch.delenv("WORKER_TOKEN", raising=False)
    return alvo


class _Resposta:
    def __init__(self, dados): self._dados = dados
    def raise_for_status(self): pass
    def json(self): return self._dados


def _worker(monkeypatch, dados=None, erro=None):
    monkeypatch.setenv("WORKER_URL", "https://exemplo.workers.dev")
    monkeypatch.setenv("WORKER_TOKEN", "segredo")

    def falso(url, headers, timeout):
        assert headers["Authorization"] == "Bearer segredo"
        if erro:
            raise erro
        return _Resposta(dados)

    monkeypatch.setattr(requests, "get", falso)


def test_sem_worker_configurado_usa_o_que_esta_no_git(arquivo):
    arquivo.write_text(json.dumps({"peso": {"2026-08-18": 78.9}}), encoding="utf-8")
    assert estado.consolidar() == {"peso": {"2026-08-18": 78.9}}


def test_kv_fora_do_ar_nao_derruba_a_edicao(arquivo, monkeypatch, capsys):
    arquivo.write_text(json.dumps({"peso": {"2026-08-18": 78.9}}), encoding="utf-8")
    _worker(monkeypatch, erro=requests.ConnectionError("timeout"))

    assert estado.consolidar() == {"peso": {"2026-08-18": 78.9}}
    assert "KV indisponível" in capsys.readouterr().out


def test_o_que_veio_do_kv_e_gravado_no_estado_json(arquivo, monkeypatch):
    arquivo.write_text(json.dumps({"peso": {"2026-08-18": 78.9}}), encoding="utf-8")
    _worker(monkeypatch, dados={"peso": {"2026-08-19": 78.4}})

    juntos = estado.consolidar()
    assert juntos["peso"] == {"2026-08-18": 78.9, "2026-08-19": 78.4}
    assert json.loads(arquivo.read_text(encoding="utf-8"))["peso"]["2026-08-19"] == 78.4


def test_kv_vazio_preserva_o_historico_do_git(arquivo, monkeypatch):
    arquivo.write_text(json.dumps({"peso": {"2026-08-18": 78.9}}), encoding="utf-8")
    _worker(monkeypatch, dados={})
    assert estado.consolidar()["peso"] == {"2026-08-18": 78.9}


def test_serie_sai_em_ordem_cronologica(arquivo):
    est = {"peso": {"2026-08-19": 78.4, "2026-08-01": 79.9, "2026-08-10": 79.0}}
    assert [d for d, _ in estado.serie(est, "peso")] == ["2026-08-01", "2026-08-10", "2026-08-19"]


# ---- a folha ----

def test_a_folha_sempre_traz_o_campo_de_registro():
    for serie in ([], [("2026-08-19", 78.4)]):
        assert 'id="peso-gravar"' in peso.blocos(date(2026, 8, 19), serie)[0]


def test_folha_sem_medida_alguma_nao_quebra():
    blocos = peso.blocos(date(2026, 8, 19), [])
    assert "Sem medidas ainda" in blocos[1]


def test_mostra_ultima_medida_e_variacao():
    blocos = peso.blocos(date(2026, 8, 19), [("2026-08-17", 79.0), ("2026-08-19", 78.4)])
    assert "78.4 kg" in blocos[1]
    assert "-0.6 kg desde 17/08" in blocos[1]


def test_curva_aparece_a_partir_de_duas_medidas():
    uma = peso.blocos(date(2026, 8, 19), [("2026-08-19", 78.4)])
    assert all("<svg" not in b for b in uma)

    varias = peso.blocos(date(2026, 8, 19),
                         [("2026-08-01", 79.9), ("2026-08-10", 79.0), ("2026-08-19", 78.4)])
    assert "<svg" in varias[2]
    assert "3 registros" in varias[2]


def test_a_curva_e_diaria_e_nao_perde_ponto():
    serie = [(f"2026-08-{d:02d}", 79.0 - d * 0.05) for d in range(1, 20)]
    svg = peso.blocos(date(2026, 8, 19), serie)[2]
    assert svg.count(",") >= len(serie)          # um par x,y por medida
    assert "19 registros" in svg
