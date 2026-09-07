"""Dois discos por dia e a caixa de estilo que só vale amanhã."""

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
    monkeypatch.setattr(album, "_capa", lambda d: "")
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


def test_a_folha_avisa_que_o_pedido_de_hoje_vale_amanha():
    saida = "".join(album.blocos(HOJE, _pedido("jazz modal", HOJE)))
    assert "entra na edição de amanhã" in saida


def test_cada_disco_e_um_bloco_so():
    """Capa, história e faixa juntos: separados, a paginação quebra o que é uma coisa só."""
    blocos = album.blocos(HOJE, {})
    assert len(blocos) == 3                      # gosto, estilo, caixa
    assert "Kind of Blue" in blocos[0] and "história" not in blocos[1].split("Kind")[0].lower()
    assert "Miles Davis" in blocos[0]
    assert "So What" in blocos[0]


def test_a_caixa_de_estilo_aparece_sempre():
    assert 'id="estilo-gravar"' in "".join(album.blocos(HOJE, {}))


def test_o_que_ja_foi_sugerido_entra_no_prompt_para_nao_repetir(monkeypatch):
    prompts = []
    monkeypatch.setattr(album.llm, "gerar_json", lambda p, **k: prompts.append(p) or dict(DISCO))
    album.blocos(HOJE, {})                        # grava no histórico
    album.blocos(date(2026, 8, 20), {})
    assert any("Kind of Blue — Miles Davis" in p for p in prompts[2:])


def test_discos_salvos_na_biblioteca_nao_sao_sugeridos_como_novidade(monkeypatch):
    prompts = []
    monkeypatch.setattr(album.llm, "gerar_json", lambda p, **k: prompts.append(p) or dict(DISCO))
    album.blocos(HOJE, {})
    assert any("OK Computer — Radiohead" in p for p in prompts)


def test_historico_registra_os_dois_discos_com_a_origem():
    album.blocos(HOJE, {})
    registros = album._historico()
    assert [r["origem"] for r in registros] == ["gosto", "estilo"]


def test_spotify_fora_do_ar_nao_custa_a_folha_inteira(monkeypatch):
    """O disco do estilo pedido não depende do Spotify — ele tem que sair mesmo assim."""
    monkeypatch.setattr(album, "_perfil", lambda: ({}, "o Spotify recusou o refresh token"))
    blocos = album.blocos(HOJE, _pedido("jazz modal", ONTEM))
    assert "Sem o disco do seu gosto hoje" in blocos[0]
    assert "o Spotify recusou o refresh token" in blocos[0]
    assert "Kind of Blue" in blocos[1], "o disco do estilo pedido continua saindo"
    assert 'id="estilo-gravar"' in blocos[2]



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
    primeiro = "".join(album.blocos(HOJE, {}))
    quantas = len(chamadas)
    segundo = "".join(album.blocos(HOJE, {}))
    assert primeiro == segundo
    assert len(chamadas) == quantas, "o segundo build não pode chamar o modelo de novo"


def test_dia_diferente_gera_disco_novo(monkeypatch):
    chamadas = _conta_chamadas(monkeypatch)
    album.blocos(ONTEM, {})
    antes = len(chamadas)
    album.blocos(HOJE, {})
    assert len(chamadas) > antes


def test_o_historico_nao_acumula_no_mesmo_dia(monkeypatch):
    _conta_chamadas(monkeypatch)
    album.blocos(HOJE, {})
    album.blocos(HOJE, {})
    album.blocos(HOJE, {})
    registros = [r for r in album._historico() if r["data"] == HOJE.isoformat()]
    assert len(registros) == 2, "um disco por origem, não um par por build"
    assert {r["origem"] for r in registros} == {"gosto", "estilo"}


def test_a_capa_carrega_cedo(monkeypatch):
    """`lazy` fazia a capa chegar depois de a paginação já ter decidido as colunas."""
    monkeypatch.undo()
    import sys, types
    falso = types.ModuleType("spotify")
    falso.search_album = lambda a, b: {"cover_url": "https://i.scdn.co/x.jpg", "spotify_id": "abc"}
    monkeypatch.setitem(sys.modules, "planner.spotify", falso)
    saida = album._capa({"album": "Kind of Blue", "artista": "Miles Davis"})
    assert 'loading="eager"' in saida
    assert "lazy" not in saida


def test_spotify_fora_do_ar_nao_congela_o_disco_do_gosto(monkeypatch):
    """Só o estilo fica cacheado: o gosto tenta de novo no build seguinte do mesmo dia."""
    _conta_chamadas(monkeypatch)
    monkeypatch.setattr(album, "_perfil", lambda: ({}, "credencial inválida"))
    album.blocos(HOJE, {})
    assert not conteudo.caminho_por_data("album-gosto", HOJE).exists()
    assert conteudo.caminho_por_data("album-estilo", HOJE).exists()
