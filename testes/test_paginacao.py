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
