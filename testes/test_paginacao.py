"""A paginação é o coração da edição: mede no Chromium e distribui blocos em folhas.

O que estes testes protegem, do ADR 0001: multi-coluna transborda na horizontal, então
medir altura não detecta nada; e um bloco nunca é partido — ou cabe inteiro, ou vai para
a folha seguinte.
"""

from datetime import date

import pytest

from planner import render
from planner.paginacao import medir


def _topico(quantos: int, tid: str = "tempo") -> dict:
    blocos = [
        f'<div class="bloco"><h4>Bloco {i}</h4><p>{"palavra " * 40}</p></div>'
        for i in range(quantos)
    ]
    return {"id": tid, "nome": tid.title(), "chapeu": "teste", "blocos": blocos}


def _folhas(topicos: list[dict]) -> list[dict]:
    return medir(render.montar(date(2026, 8, 19), topicos))


def test_topico_grande_ocupa_varias_folhas():
    folhas = _folhas([_topico(30)])
    assert len(folhas) > 1
    assert [f["cont"] for f in folhas] == list(range(len(folhas)))


def test_nenhum_bloco_se_perde_nem_se_repete():
    topico = _topico(30)
    vistos = [i for f in _folhas([topico]) for i in f["blocos"]]
    assert vistos == list(range(len(topico["blocos"])))


def test_topico_pequeno_cabe_numa_folha_so():
    assert len(_folhas([_topico(2)])) == 1


def test_cada_topico_comeca_em_folha_propria():
    folhas = _folhas([_topico(20, "tempo"), _topico(20, "dieta")])
    primeiras = [f["topico"] for f in folhas if f["cont"] == 0]
    assert primeiras == [0, 1]


def test_bloco_gigante_sozinho_nao_trava_a_paginacao():
    """Bloco que não cabe nem sozinho fica na folha assim mesmo — o build não pode entrar em laço."""
    enorme = {"id": "tempo", "nome": "Tempo", "chapeu": "teste",
              "blocos": ['<div class="bloco"><p>' + "palavra " * 4000 + "</p></div>",
                         '<div class="bloco"><p>fim</p></div>']}
    folhas = _folhas([enorme])
    assert [i for f in folhas for i in f["blocos"]] == [0, 1]


def test_bloco_marcado_abre_folha_nova():
    """A Dieta depende disso: a lista de compras nunca divide folha com o jantar."""
    topico = _topico(4)
    topico["blocos"][2] = topico["blocos"][2].replace(
        '<div class="bloco">', '<div class="bloco" data-quebra="Compras">', 1)
    folhas = _folhas([topico])
    assert [f["blocos"] for f in folhas] == [[0, 1], [2, 3]]
    assert [f["cont"] for f in folhas] == [0, 0], "grupo novo recomeça a contagem"


# ------------------------------------------------- grill de 07/09/2026: a capa do Álbum

# PNG 64x64 opaco, inline: carrega na hora, sem rede.
QUADRADO = (
    "data:image/svg+xml;base64,"
    "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI2NCIgaGVpZ2h0PSI2NCI+"
    "PHJlY3Qgd2lkdGg9IjY0IiBoZWlnaHQ9IjY0IiBmaWxsPSIjODg4Ii8+PC9zdmc+"
)
QUEBRADA = "https://invalido.invalido/nao-existe.jpg"     # nunca carrega


def _album(src: str) -> dict:
    """O caderno do Álbum com um disco de texto longo, como o do dia a dia."""
    disco = {"album": "Album", "artista": "Artista", "ano": "1972", "faixa": "Faixa — ouça isso",
             "historia": "palavra " * 90, "capa": src, "id": "abc"}
    return {"id": "album", "nome": "Álbum", "chapeu": "teste", "blocos": [], "caderno": "album",
            "dados": {"hoje": "2026-11-04", "gosto": disco, "estilo": dict(disco), "sem_spotify": None,
                      "perfil_de": None, "vigente": "jazz", "pendente": None, "discoteca": [],
                      "planilha": "https://exemplo"}}


def _mede_album(html: str, largura: int, altura: int) -> dict:
    import tempfile
    from pathlib import Path

    from playwright.sync_api import sync_playwright

    with tempfile.TemporaryDirectory() as tmp:
        alvo = Path(tmp) / "edicao.html"
        alvo.write_text(html, encoding="utf-8")
        with sync_playwright() as p:
            navegador = p.chromium.launch()
            pagina = navegador.new_page(viewport={"width": largura, "height": altura})
            pagina.goto(alvo.as_uri() + "#album/1")
            pagina.wait_for_selector(".disco-pg img.capa")
            medido = pagina.evaluate("""() => {
                const corpo = document.querySelector('.corpo.pagina');
                const capa = corpo.querySelector('img.capa');
                return {alta: Math.round(capa.clientHeight), larga: Math.round(capa.clientWidth),
                        lado: corpo.scrollWidth - corpo.clientWidth,
                        rola: getComputedStyle(corpo).overflowY};
            }""")
            navegador.close()
    return medido


def test_a_capa_reserva_o_quadrado_sem_a_imagem_chegar():
    """Desde 07/09/2026: `aspect-ratio` dá altura à capa antes do carregamento. A imagem
    aqui aponta para um host que não existe — nunca carrega."""
    medido = _mede_album(render.montar(date(2026, 11, 4), [_album(QUEBRADA)]), 1366, 768)
    assert medido["alta"] == medido["larga"] > 0


def test_a_pagina_do_disco_nao_esconde_texto_em_tela_nenhuma():
    """O defeito de 07/09/2026 era texto cortado em silêncio. A página do caderno rola em vez
    de cortar, e nunca transborda para o lado."""
    for largura, altura in ((1366, 768), (1920, 1080), (390, 820)):
        medido = _mede_album(render.montar(date(2026, 11, 4), [_album(QUADRADO)]), largura, altura)
        assert medido["lado"] <= 0, f"{largura}x{altura}"
        assert medido["rola"] == "auto"
