"""Caderno do Álbum: dois discos por dia, a caixa de estilo que só vale amanhã, a nota
que ele dá em cada disco e o gosto que não depende do Spotify estar de pé (2026-11-03)."""

import json
from datetime import date

import pytest

from planner import conteudo
from planner.topicos import album

HOJE, ONTEM = date(2026, 8, 19), date(2026, 8, 18)

DISCO = {"album": "Kind of Blue", "artista": "Miles Davis", "ano": "1959",
         "historia": "Saiu em 1959. Mudou o jazz. Importa porque abriu o modal.",
         "faixa": "So What — ouça o baixo abrindo"}


@pytest.fixture(autouse=True)
def sem_rede(tmp_path, monkeypatch):
    monkeypatch.setattr(album, "HISTORICO", tmp_path / "album_history.json")
    monkeypatch.setattr(conteudo, "PASTA", tmp_path / "gerado")
    monkeypatch.setattr(album.llm, "gerar_json", lambda p, **k: dict(DISCO))
    monkeypatch.setattr(album, "PERFIL", tmp_path / "perfil-gosto.json")
    monkeypatch.setattr(album, "_capa", lambda d: {})
    import sys, types
    falso = types.ModuleType("spotify")
    falso.get_spotify_taste_profile = lambda: {"top_artists": ["Radiohead"], "top_genres": ["indie"],
                                               "saved_albums": [{"album": "OK Computer", "artist": "Radiohead"}]}
    falso.search_album = lambda a, b: {"cover_url": None, "spotify_id": None}
    monkeypatch.setitem(sys.modules, "planner.spotify", falso)


def _pedido(estilo, dia):
    return {album.SECAO: {album.CHAVE: {"dia": dia.isoformat(), "estilo": estilo}}}


def test_sem_pedido_algum_usa_o_estilo_padrao():
    vigente, pendente = album.estilo_vigente({}, HOJE)
    assert vigente == album.ESTILO_PADRAO
    assert pendente is None


def test_estilo_pedido_hoje_so_vale_amanha():
    vigente, pendente = album.estilo_vigente(_pedido("jazz modal", HOJE), HOJE)
    assert vigente == album.ESTILO_PADRAO, "a edição de hoje já está publicada"
    assert pendente == "jazz modal"


def test_estilo_pedido_ontem_esta_em_vigor_hoje():
    vigente, pendente = album.estilo_vigente(_pedido("jazz modal", ONTEM), HOJE)
    assert vigente == "jazz modal"
    assert pendente is None


def test_o_pedido_continua_valendo_indefinidamente():
    antigo = _pedido("jazz modal", date(2026, 1, 1))
    assert album.estilo_vigente(antigo, HOJE)[0] == "jazz modal"


def _dados(dia=HOJE, estado=None):
    return album.caderno(dia, estado or {})["dados"]


def test_a_pagina_avisa_que_o_pedido_de_hoje_vale_amanha():
    d = _dados(HOJE, _pedido("jazz modal", HOJE))
    assert d["pendente"] == "jazz modal"
    assert d["vigente"] == album.ESTILO_PADRAO


def test_os_dois_discos_saem_inteiros_com_o_link_da_planilha():
    d = _dados()
    for qual in ("gosto", "estilo"):
        assert d[qual]["album"] == "Kind of Blue" and d[qual]["faixa"].startswith("So What")
    assert d["planilha"].startswith("https://docs.google.com/spreadsheets/")


def test_o_que_ja_foi_sugerido_entra_no_prompt_para_nao_repetir(monkeypatch):
    prompts = []
    monkeypatch.setattr(album.llm, "gerar_json", lambda p, **k: prompts.append(p) or dict(DISCO))
    album.caderno(HOJE, {})                        # grava no histórico
    album.caderno(date(2026, 8, 20), {})
    assert any("Kind of Blue — Miles Davis" in p for p in prompts[2:])


def test_discos_salvos_na_biblioteca_nao_sao_sugeridos_como_novidade(monkeypatch):
    prompts = []
    monkeypatch.setattr(album.llm, "gerar_json", lambda p, **k: prompts.append(p) or dict(DISCO))
    album.caderno(HOJE, {})
    assert any("OK Computer — Radiohead" in p for p in prompts)


def test_historico_registra_os_dois_discos_com_a_origem_e_a_discoteca_mostra():
    d = _dados()
    assert [r["origem"] for r in album._historico()] == ["gosto", "estilo"]
    assert [r["origem"] for r in d["discoteca"]] == ["estilo", "gosto"], "mais novo primeiro"


def test_spotify_fora_do_ar_e_sem_perfil_salvo_so_custa_o_disco_do_gosto(monkeypatch):
    monkeypatch.setattr(album, "_perfil", lambda dia: ({}, "o Spotify recusou o refresh token", None))
    d = _dados(HOJE, _pedido("jazz modal", ONTEM))
    assert d["gosto"] is None
    assert d["sem_spotify"] == "o Spotify recusou o refresh token"
    assert d["estilo"]["album"] == "Kind of Blue", "o disco do estilo pedido continua saindo"


def test_spotify_de_pe_salva_o_perfil_e_fora_do_ar_usa_o_salvo(monkeypatch):
    import sys
    _dados()
    assert json.loads(album.PERFIL.read_text())["top_artists"] == ["Radiohead"]

    def caiu():
        raise RuntimeError("invalid_grant")
    monkeypatch.setattr(sys.modules["planner.spotify"], "get_spotify_taste_profile", caiu)
    prompts = []
    monkeypatch.setattr(album.llm, "gerar_json", lambda p, **k: prompts.append(p) or dict(DISCO))
    d = _dados(date(2026, 8, 20))
    assert d["gosto"]["album"] == "Kind of Blue"
    assert d["sem_spotify"] == "invalid_grant" and d["perfil_de"] == "2026-08-19"
    assert any("Radiohead" in p for p in prompts), "o gosto sai pelo perfil salvo"


def test_a_nota_dele_entra_no_prompt_do_gosto(monkeypatch):
    _dados(ONTEM)                                  # o disco de ontem no histórico
    prompts = []
    monkeypatch.setattr(album.llm, "gerar_json", lambda p, **k: prompts.append(p) or dict(DISCO))
    album.caderno(HOJE, {"feito": {"disco:2026-08-18:gosto": "gostei",
                                   "disco:2026-08-18:estilo": "não curti"}})
    gosto = prompts[0]
    assert "GOSTOU: Kind of Blue — Miles Davis" in gosto
    assert "NÃO CURTIU" in gosto


def test_notas_so_le_as_marcas_de_disco_validas():
    est = {"feito": {"disco:2026-11-03:gosto": "gostei", "disco:2026-11-03:estilo": False,
                     "treino:2026-11-03": True, "disco:2026-11-02:gosto": "talvez"}}
    assert album.notas(est) == {"2026-11-03:gosto": "gostei"}


def test_a_capa_vem_da_busca_publica(monkeypatch):
    monkeypatch.undo()
    import sys, types
    falso = types.ModuleType("spotify")
    falso.search_album = lambda a, b: {"cover_url": "https://i.scdn.co/x.jpg", "spotify_id": "abc"}
    monkeypatch.setitem(sys.modules, "planner.spotify", falso)
    assert album._capa({"album": "Kind of Blue", "artista": "Miles Davis"}) == {
        "capa": "https://i.scdn.co/x.jpg", "id": "abc"}


# ---------------------------------------------------------------- grill de 07/09/2026

def _conta_chamadas(monkeypatch, disco=None):
    """Troca o gerador por um contador, para provar que o cache evita a segunda chamada."""
    chamadas = []

    def gerar(prompt, **k):
        chamadas.append(prompt)
        return dict(disco or DISCO)

    monkeypatch.setattr(album.llm, "gerar_json", gerar)
    return chamadas


def test_o_disco_do_dia_nao_muda_no_segundo_build(monkeypatch):
    """Com dois crons, o build roda 2x por dia: quem abre de manhã e de tarde vê o mesmo."""
    chamadas = _conta_chamadas(monkeypatch)
    primeiro = _dados()
    quantas = len(chamadas)
    assert _dados() == primeiro
    assert len(chamadas) == quantas, "o segundo build não pode chamar o modelo de novo"


def test_dia_diferente_gera_disco_novo(monkeypatch):
    chamadas = _conta_chamadas(monkeypatch)
    _dados(ONTEM)
    antes = len(chamadas)
    _dados(HOJE)
    assert len(chamadas) > antes


def test_o_historico_nao_acumula_no_mesmo_dia(monkeypatch):
    _conta_chamadas(monkeypatch)
    for _ in range(3):
        _dados()
    registros = [r for r in album._historico() if r["data"] == HOJE.isoformat()]
    assert len(registros) == 2, "um disco por origem, não um par por build"


def test_spotify_fora_do_ar_nao_congela_o_disco_do_gosto(monkeypatch):
    """Só o estilo fica cacheado: o gosto tenta de novo no build seguinte do mesmo dia."""
    _conta_chamadas(monkeypatch)
    monkeypatch.setattr(album, "_perfil", lambda dia: ({}, "credencial inválida", None))
    _dados()
    assert not conteudo.caminho_por_data("album-gosto", HOJE).exists()
    assert conteudo.caminho_por_data("album-estilo", HOJE).exists()
