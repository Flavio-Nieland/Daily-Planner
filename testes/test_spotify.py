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
