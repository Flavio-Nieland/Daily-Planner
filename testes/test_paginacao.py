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


def _discos(quantos: int, src: str) -> dict:
    blocos = [
        f'<div class="bloco disco"><h4>Disco {i}</h4>'
        f'<img class="capa" src="{src}" alt="capa" loading="eager">'
        f'<p class="destaque-texto">Album {i}</p><p>{"palavra " * 60}</p></div>'
        for i in range(quantos)
    ]
    return {"id": "album", "nome": "Álbum", "chapeu": "teste", "blocos": blocos}


def test_a_capa_ocupa_espaco_mesmo_sem_carregar():
    """O bug de 07/09/2026: a folha do Álbum saía sem o texto do disco.

    A paginação mede num medidor `visibility:hidden;left:-9999px`, onde imagem nenhuma
    carrega. Sem altura reservada no CSS a capa media 0px, cabia bloco demais na folha, e
    o texto ia para uma coluna fora da caixa — invisível, por causa do `overflow:hidden`.

    Se a reserva funciona, medir com a capa carregando e com a capa quebrada tem que dar
    exatamente a mesma paginação.
    """
    carregando = _folhas([_discos(6, QUADRADO)])
    quebrada = _folhas([_discos(6, QUEBRADA)])
    assert [f["blocos"] for f in quebrada] == [f["blocos"] for f in carregando]


def test_a_capa_nao_e_medida_como_altura_zero():
    """Trava direta: um disco com capa tem que ocupar mais folha que o mesmo texto sem capa."""
    com_capa = _folhas([_discos(6, QUADRADO)])
    sem_capa = _folhas([_topico(6, "album")])
    assert len(com_capa) > len(sem_capa)
