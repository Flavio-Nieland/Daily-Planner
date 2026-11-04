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


# ---- o caderno e o recorte público ----

def test_peso_com_hora_entra_na_serie_pelo_kg():
    """Desde 2026-11-03 o registro é {kg, em}; os antigos continuam número."""
    est = {"peso": {"2026-09-07": 67.9, "2026-11-04": {"kg": 68.1, "em": "2026-11-04T09:12:00Z"}}}
    assert estado.serie(est, "peso") == [("2026-09-07", 67.9), ("2026-11-04", 68.1)]


def test_valor_estranho_na_serie_e_ignorado_sem_derrubar():
    est = {"peso": {"2026-09-07": "abc", "2026-09-08": {"em": "x"}, "2026-09-09": 67.0}}
    assert estado.serie(est, "peso") == [("2026-09-09", 67.0)]


def test_o_caderno_leva_o_dia_e_a_meta():
    c = peso.caderno(date(2026, 11, 4))
    assert c == {"caderno": "peso", "dados": {"hoje": "2026-11-04", "meta": peso.META_KG}}


def test_o_html_publico_nao_leva_as_notas_dos_livros():
    est = {"peso": {"2026-11-03": 68.1}, "nota": {"2026-11-01": "o que eu penso do livro"},
           "dominio": {"prato:3": {"veredito": "revisar"}},
           "feito": {"treino:2026-11-02": True, "treino:2026-08-01": True,
                     "refeicao:2026-11-03:2": "segui", "compra:2026-11-04:ovos": True},
           "medida": {"maochao:2026-11-01": 12, "meta:peso": 70}}
    pub = estado.publico(est, date(2026, 11, 4))
    assert set(pub) == {"peso", "feito", "medida"}
    assert "o que eu penso" not in json.dumps(pub)
    assert pub["feito"] == {"treino:2026-11-02": True, "refeicao:2026-11-03:2": "segui",
                            "compra:2026-11-04:ovos": True}
    assert pub["medida"] == {"meta:peso": 70}


def test_o_estado_json_e_criado_mesmo_sem_worker(arquivo):
    """O passo de publicação conta com o arquivo existindo."""
    assert not arquivo.exists()
    estado.consolidar()
    assert arquivo.exists()
    assert json.loads(arquivo.read_text(encoding="utf-8")) == {}
