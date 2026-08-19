# spotify.py
# Integração com a Spotify Web API.
# Fornece o perfil musical do usuário (top artists, genres, tracks, saved albums)
# e busca capa de álbum por nome/artista.

import os
from collections import Counter

import spotipy
from spotipy.oauth2 import SpotifyOAuth


def _get_client() -> spotipy.Spotify:
    """Cria cliente Spotify autenticado usando o Refresh Token do .env."""
    auth_manager = SpotifyOAuth(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        redirect_uri="http://127.0.0.1:8888/callback",
        scope="user-top-read user-library-read",
    )
    token_info = auth_manager.refresh_access_token(os.environ["SPOTIFY_REFRESH_TOKEN"])
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


def search_album(album_name: str, artist_name: str) -> dict:
    """
    Busca um álbum no Spotify por nome e artista.
    Retorna {"cover_url": ..., "spotify_id": ...} ou valores None se não encontrar.
    """
    try:
        sp = _get_client()
        results = sp.search(
            q=f"album:{album_name} artist:{artist_name}",
            type="album",
            limit=1,
        )
        items = results["albums"]["items"]
        if items:
            album = items[0]
            cover_url  = album["images"][0]["url"] if album.get("images") else None
            spotify_id = album.get("id")
            return {"cover_url": cover_url, "spotify_id": spotify_id}
    except Exception:
        pass
    return {"cover_url": None, "spotify_id": None}
