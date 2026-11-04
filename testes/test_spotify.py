"""A porta do Spotify: credencial ausente tem que dizer o próprio nome.

Faltava passar os secrets ao build no Actions, e o erro chegava como KeyError cru — a folha
do Álbum então culpava o Spotify, que não tinha culpa nenhuma.
"""

import pytest

from planner import spotify


def test_credencial_faltando_diz_qual(monkeypatch):
    for nome in spotify.CREDENCIAIS:
        monkeypatch.delenv(nome, raising=False)
    with pytest.raises(RuntimeError, match="falta a credencial do Spotify: SPOTIFY_CLIENT_ID"):
        spotify._get_client()


def test_lista_todas_as_que_faltam(monkeypatch):
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "x")
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("SPOTIFY_REFRESH_TOKEN", raising=False)
    with pytest.raises(RuntimeError) as erro:
        spotify._get_client()
    assert "SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN" in str(erro.value)
    assert "SPOTIFY_CLIENT_ID" not in str(erro.value)


def test_refresh_recusado_diz_o_que_fazer(monkeypatch):
    for nome in spotify.CREDENCIAIS:
        monkeypatch.setenv(nome, "valor")

    class _Auth:
        def __init__(self, **k): pass
        def refresh_access_token(self, _): return {"error": "invalid_grant"}

    monkeypatch.setattr(spotify, "SpotifyOAuth", _Auth)
    with pytest.raises(RuntimeError, match="recusou o refresh token"):
        spotify._get_client()


def test_a_busca_de_capa_nao_precisa_do_login(monkeypatch):
    """O refresh token caiu (invalid_grant) e as capas sumiram junto: busca é pública."""
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "id")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "segredo")
    monkeypatch.delenv("SPOTIFY_REFRESH_TOKEN", raising=False)

    class _Sp:
        def __init__(self, auth_manager): self.auth = auth_manager
        def search(self, **k):
            return {"albums": {"items": [{"id": "x1", "images": [{"url": "https://capa"}]}]}}

    monkeypatch.setattr(spotify.spotipy, "Spotify", _Sp)
    assert spotify.search_album("Gita", "Raul Seixas") == {"cover_url": "https://capa", "spotify_id": "x1"}


def test_capa_de_disco_com_dois_artistas_cai_para_o_primeiro(monkeypatch):
    """"Lula Côrtes e Zé Ramalho" não casa com `artist:` — o Paêbirú saía sem capa (03/11)."""
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "id")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "segredo")
    consultas = []

    class _Sp:
        def __init__(self, auth_manager): pass
        def search(self, q, **k):
            consultas.append(q)
            achou = "artist:Lula Côrtes" in q and "Zé" not in q
            itens = [{"id": "pb", "name": "Paêbirú", "images": [{"url": "https://capa"}]}] if achou else []
            return {"albums": {"items": itens}}

    monkeypatch.setattr(spotify.spotipy, "Spotify", _Sp)
    assert spotify.search_album("Paêbirú", "Lula Côrtes e Zé Ramalho")["spotify_id"] == "pb"
    assert consultas[:2] == ["album:Paêbirú artist:Lula Côrtes e Zé Ramalho", "album:Paêbirú artist:Lula Côrtes"]


def test_busca_solta_nao_aceita_disco_de_outro_nome(monkeypatch):
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "id")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "segredo")

    class _Sp:
        def __init__(self, auth_manager): pass
        def search(self, q, **k):
            solta = not q.startswith("album:")
            return {"albums": {"items": [{"id": "x", "name": "Outro Disco", "images": [],
                                          "artists": [{"name": "Lula Côrtes"}]}] if solta else []}}

    monkeypatch.setattr(spotify.spotipy, "Spotify", _Sp)
    assert spotify.search_album("Paêbirú", "Lula Côrtes") == {"cover_url": None, "spotify_id": None}


def test_busca_solta_nao_aceita_disco_de_mesmo_nome_de_outro_artista(monkeypatch):
    """04/11: "Quem Não Vive Tem Medo da Morte — Ave Sangria" pegou a capa do Ney Matogrosso."""
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "id")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "segredo")

    class _Sp:
        def __init__(self, auth_manager): pass
        def search(self, q, **k):
            if q.startswith("album:"):
                return {"albums": {"items": []}}
            return {"albums": {"items": [{"id": "ney", "name": "Quem Não Vive Tem Medo da Morte",
                                          "images": [{"url": "u"}], "artists": [{"name": "Ney Matogrosso"}]}]}}

    monkeypatch.setattr(spotify.spotipy, "Spotify", _Sp)
    assert spotify.search_album("Quem Não Vive Tem Medo da Morte", "Ave Sangria")["spotify_id"] is None
    assert spotify.search_album("Quem Não Vive Tem Medo da Morte", "Ney Matogrosso")["spotify_id"] == "ney"
    assert spotify.search_album("Quem Não Vive Tem Medo da Morte", "Vários artistas")["spotify_id"] == "ney"
