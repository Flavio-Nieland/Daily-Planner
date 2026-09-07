"""A planilha de backtracking dos discos: consolidação e as três garantias do desenho.

Nenhum teste sai para a rede: o que importa aqui é a tabela que o build monta e a regra de
não escrever quando não há para onde. A conversa com o Apps Script foi validada à mão em
07/09/2026 (token errado recusado, backfill de 22 linhas, duas chamadas seguintes intactas).
"""

import pytest

from planner import planilha_albuns


def _r(data, album, artista, origem):
    return {"data": data, "album": album, "artista": artista, "origem": origem}


def test_uma_linha_por_data_com_as_duas_origens():
    linhas = planilha_albuns.consolidar([
        _r("2026-09-06", "Maggot Brain", "Funkadelic", "gosto"),
        _r("2026-09-06", "Pérola Negra", "Luiz Melodia", "estilo"),
    ])
    assert linhas == [{"data": "2026-09-06",
                       "gosto": "Maggot Brain — Funkadelic",
                       "pedido": "Pérola Negra — Luiz Melodia"}]


def test_o_ultimo_disco_da_origem_vence():
    """Resquício do append cego: build que rodava 2x no dia deixava dois pares na data."""
    linhas = planilha_albuns.consolidar([
        _r("2026-09-07", "Bicho", "Caetano Veloso", "estilo"),
        _r("2026-09-07", "Jardim Elétrico", "Os Mutantes", "estilo"),
    ])
    assert linhas[0]["pedido"] == "Jardim Elétrico — Os Mutantes"


def test_coluna_do_gosto_vazia_e_legitima():
    """Nos primeiros dias o perfil do Spotify não vinha — a linha existe sem o disco."""
    linhas = planilha_albuns.consolidar([_r("2026-08-17", "Alucinação", "Belchior", "estilo")])
    assert linhas[0]["gosto"] == ""
    assert linhas[0]["pedido"] == "Alucinação — Belchior"


def test_sai_ordenado_por_data():
    linhas = planilha_albuns.consolidar([
        _r("2026-09-07", "b", "x", "estilo"),
        _r("2026-08-17", "a", "y", "estilo"),
        _r("2026-09-01", "c", "z", "estilo"),
    ])
    assert [l["data"] for l in linhas] == ["2026-08-17", "2026-09-01", "2026-09-07"]


def test_registro_estragado_e_ignorado_sem_explodir():
    linhas = planilha_albuns.consolidar([
        {"data": "", "album": "sem data", "artista": "x", "origem": "estilo"},
        {"data": "2026-09-01", "album": "sem origem", "artista": "x"},
        {"data": "2026-09-01", "album": "", "artista": "x", "origem": "estilo"},
        _r("2026-09-01", "vale", "y", "estilo"),
    ])
    assert linhas == [{"data": "2026-09-01", "gosto": "", "pedido": "vale — y"}]


def test_sem_os_secrets_nao_tenta_escrever(monkeypatch):
    """É o que permite o código viver em produção antes de a planilha existir."""
    monkeypatch.delenv("PLANILHA_URL", raising=False)
    monkeypatch.delenv("PLANILHA_TOKEN", raising=False)
    assert planilha_albuns.enviar([_r("2026-09-01", "a", "b", "estilo")]) is None


def test_url_sem_token_tambem_e_no_op(monkeypatch):
    monkeypatch.setenv("PLANILHA_URL", "https://exemplo/exec")
    monkeypatch.delenv("PLANILHA_TOKEN", raising=False)
    assert planilha_albuns.enviar([]) is None


def test_recusa_do_script_virou_erro_sem_vazar_o_token(monkeypatch):
    monkeypatch.setenv("PLANILHA_URL", "https://exemplo/exec")
    monkeypatch.setenv("PLANILHA_TOKEN", "segredo-que-nao-pode-aparecer")

    class Resposta:
        def raise_for_status(self):
            pass

        def json(self):
            return {"ok": False, "erro": "token"}

    import sys, types
    falso = types.ModuleType("requests")
    falso.post = lambda *a, **k: Resposta()
    monkeypatch.setitem(sys.modules, "requests", falso)

    with pytest.raises(RuntimeError) as erro:
        planilha_albuns.enviar([])
    assert "token" in str(erro.value)
    assert "segredo-que-nao-pode-aparecer" not in str(erro.value)
    assert "exemplo" not in str(erro.value)
