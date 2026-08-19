"""Mede a edição num Chromium headless e devolve as folhas já fechadas.

A paginação é responsabilidade do gerador, não do CSS (ADR 0001). Medir aqui é o que faz
a numeração `3 / 11` sair correta no HTML publicado; o mesmo JS re-mede no navegador dele.
"""

import json
import tempfile
from pathlib import Path

LARGURA, ALTURA = 1440, 900          # tela de referência do build


def medir(html: str) -> list[dict]:
    from playwright.sync_api import sync_playwright

    with tempfile.TemporaryDirectory() as tmp:
        alvo = Path(tmp) / "edicao.html"
        alvo.write_text(html, encoding="utf-8")
        with sync_playwright() as p:
            navegador = p.chromium.launch()
            pagina = navegador.new_page(viewport={"width": LARGURA, "height": ALTURA})
            pagina.goto(alvo.as_uri())
            pagina.wait_for_function("typeof window.__paginar === 'function'")
            folhas = pagina.evaluate("window.__paginar()")
            navegador.close()
    return folhas
