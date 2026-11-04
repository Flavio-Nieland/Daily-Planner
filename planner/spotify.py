# spotify.py
# Integração com a Spotify Web API.
# Fornece o perfil musical do usuário (top artists, genres, tracks, saved albums)
# e busca capa de álbum por nome/artista.

import os
import re
import unicodedata
from collections import Counter

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth


CREDENCIAIS = ("SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "SPOTIFY_REFRESH_TOKEN")


def _get_client() -> spotipy.Spotify:
    """Cria cliente Spotify autenticado usando o Refresh Token.

    Credencial ausente vinha como KeyError cru, e a folha dizia que "o Spotify não
    respondeu" — que é outra coisa. Dizer qual variável falta economiza a investigação.
    """
    faltando = [nome for nome in CREDENCIAIS if not os.environ.get(nome)]
    if faltando:
        raise RuntimeError("falta a credencial do Spotify: " + ", ".join(faltando))

    auth_manager = SpotifyOAuth(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        redirect_uri="http://127.0.0.1:8888/callback",
        scope="user-top-read user-library-read",
    )
    token_info = auth_manager.refresh_access_token(os.environ["SPOTIFY_REFRESH_TOKEN"])
    if "access_token" not in token_info:
        raise RuntimeError("o Spotify recusou o refresh token — gere outro com setup_spotify.py")
    return spotipy.Spotify(auth=token_info["access_token"])


def get_spotify_taste_profile() -> dict:
    """
    Retorna o perfil musical do usuário a partir do Spotify:
    {
        "top_genres":  ["indie rock", "alternative", ...],  # top 5 gêneros
        "top_artists": ["Radiohead", "Arctic Monkeys", ...],# top 10 artistas
        "top_tracks":  ["Creep - Radiohead", ...],          # top 10 faixas
        "saved_albums": [
            {"album": "OK Computer", "artist": "Radiohead",
             "year": "1997", "cover_url": "https://..."},
            ...
        ]  # até 20 álbuns salvos na biblioteca
    }
    """
    sp = _get_client()

    # Top artistas (últimos ~6 meses)
    top_artists_result = sp.current_user_top_artists(limit=10, time_range="medium_term")
    top_artists = [a["name"] for a in top_artists_result["items"]]

    # Gêneros: extrai de todos os top artistas, pega os 5 mais frequentes
    all_genres = []
    for artist in top_artists_result["items"]:
        all_genres.extend(artist.get("genres", []))
    top_genres = [g for g, _ in Counter(all_genres).most_common(5)]

    # Top faixas (últimos ~6 meses)
    top_tracks_result = sp.current_user_top_tracks(limit=10, time_range="medium_term")
    top_tracks = [
        f'{t["name"]} - {t["artists"][0]["name"]}'
        for t in top_tracks_result["items"]
    ]

    # Álbuns salvos (biblioteca do usuário)
    saved_result = sp.current_user_saved_albums(limit=20)
    saved_albums = []
    for item in saved_result["items"]:
        album = item["album"]
        cover_url = album["images"][0]["url"] if album.get("images") else None
        saved_albums.append({
            "album":      album["name"],
            "artist":     album["artists"][0]["name"],
            "year":       album.get("release_date", "")[:4],
            "cover_url":  cover_url,
            "spotify_id": album.get("id"),
        })

    return {
        "top_genres":   top_genres,
        "top_artists":  top_artists,
        "top_tracks":   top_tracks,
        "saved_albums": saved_albums,
    }


def _cliente_publico() -> spotipy.Spotify:
    """Cliente sem o login dele (client credentials): basta para a busca de discos.

    As capas sumiram do site junto com o refresh token (invalid_grant, set/2026) só porque a
    busca usava o cliente do usuário — e busca é pública. Agora capa não depende do login.
    """
    faltando = [nome for nome in CREDENCIAIS[:2] if not os.environ.get(nome)]
    if faltando:
        raise RuntimeError("falta a credencial do Spotify: " + ", ".join(faltando))
    return spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"]))


def _consultas(album_name: str, artist_name: str) -> list[str]:
    """Do mais estrito ao mais solto. `artist:` casa um artista só: com dois no nome
    ("Lula Côrtes e Zé Ramalho") a busca estrita voltava vazia e o disco saía sem capa."""
    primeiro = re.split(r"\s+(?:e|&|and|com|feat\.?)\s+|,|/", artist_name, maxsplit=1)[0].strip()
    consultas = [f"album:{album_name} artist:{artist_name}"]
    if primeiro and primeiro != artist_name:
        consultas.append(f"album:{album_name} artist:{primeiro}")
    consultas.append(f"{album_name} {primeiro or artist_name}")
    consultas.append(album_name)          # "Vários artistas" e afins atrapalham até a busca solta
    return consultas


def _simples(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in sem_acento if c.isalnum())


def search_album(album_name: str, artist_name: str) -> dict:
    """
    Busca um álbum no Spotify por nome e artista, sem precisar do login dele.
    Retorna {"cover_url": ..., "spotify_id": ...} ou valores None se não encontrar.
    Nas buscas soltas, só aceita resultado cujo nome contenha o do disco.
    """
    try:
        sp = _cliente_publico()
        alvo = _simples(album_name)
        for consulta in _consultas(album_name, artist_name):
            items = sp.search(q=consulta, type="album", limit=5)["albums"]["items"]
            if not consulta.startswith("album:"):
                items = [a for a in items if alvo and alvo in _simples(a.get("name", ""))]
            if items:
                album = items[0]
                cover_url = album["images"][0]["url"] if album.get("images") else None
                return {"cover_url": cover_url, "spotify_id": album.get("id")}
    except Exception:
        pass
    return {"cover_url": None, "spotify_id": None}
