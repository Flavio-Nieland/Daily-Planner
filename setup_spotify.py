# setup_spotify.py
# Rode este script UMA vez para gerar o Refresh Token do Spotify.
# Pré-requisito: SPOTIFY_CLIENT_ID e SPOTIFY_CLIENT_SECRET já no .env
#
# Como usar:
#   python setup_spotify.py
#   → Abre URL no terminal, você acessa no browser e autoriza
#   → Cola a URL de callback aqui
#   → Script imprime o SPOTIFY_REFRESH_TOKEN para copiar ao .env

import os
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

client_id     = os.environ.get("SPOTIFY_CLIENT_ID")
client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")

if not client_id or not client_secret:
    print("❌ SPOTIFY_CLIENT_ID e SPOTIFY_CLIENT_SECRET precisam estar no .env")
    exit(1)

REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPES       = "user-top-read user-library-read"

auth_manager = SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=REDIRECT_URI,
    scope=SCOPES,
    open_browser=False,
)

print("=" * 60)
print("CONFIGURAÇÃO DO SPOTIFY — passo único")
print("=" * 60)
print()
print("1. Abra esta URL no seu navegador e autorize o acesso:")
print()
print(auth_manager.get_authorize_url())
print()
print("2. Após autorizar, você será redirecionado para uma URL")
print("   que começa com: http://localhost:8888/callback?code=...")
print("   (o browser vai dar erro — isso é normal)")
print()

callback_url = input("3. Cole aqui a URL completa de callback: ").strip()

code = auth_manager.parse_response_code(callback_url)
token_info = auth_manager.get_access_token(code, as_dict=True)

print()
print("=" * 60)
print("✅ Sucesso! Adicione esta linha ao seu .env:")
print()
print(f"SPOTIFY_REFRESH_TOKEN={token_info['refresh_token']}")
print("=" * 60)
