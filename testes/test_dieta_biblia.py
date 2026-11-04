"""Bíblia determinística por data. A Dieta saiu para test_dieta.py em 2026-11-03."""

import json
from datetime import date

import pytest
import requests

from planner.topicos import biblia

HOJE = date(2026, 8, 19)

def test_o_mesmo_dia_cai_sempre_no_mesmo_salmo():
    assert biblia._numero_do_dia(HOJE) == biblia._numero_do_dia(date(2026, 8, 19))
    assert 1 <= biblia._numero_do_dia(HOJE) <= 150


def test_dias_diferentes_caem_em_salmos_diferentes():
    salmos = {biblia._numero_do_dia(date(2026, 8, d)) for d in range(1, 29)}
    assert len(salmos) > 20


def test_a_folha_traz_o_salmo_e_a_reflexao(monkeypatch):
    class _Resposta:
        def raise_for_status(self): pass
        def json(self): return {"text": "Louvai ao Senhor.\nCantai a ele."}

    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resposta())
    monkeypatch.setattr(biblia.llm, "gerar_json",
                        lambda p, **k: {"reflexao": "uma reflexão curta", "versiculo": "Salmo 105:4"})
    saida = "".join(biblia.blocos(HOJE))
    assert "Louvai ao Senhor." in saida
    assert "uma reflexão curta" in saida
    assert "Salmo 105:4" in saida


def test_api_sem_texto_vira_falha_visivel(monkeypatch):
    class _Vazio:
        def raise_for_status(self): pass
        def json(self): return {"text": ""}

    monkeypatch.setattr(requests, "get", lambda *a, **k: _Vazio())
    with pytest.raises(ValueError, match="não devolveu o texto"):
        biblia.blocos(HOJE)
