"""Dieta com continuidade e lista de compras; Bíblia determinística por data."""

import json
from datetime import date

import pytest
import requests

from planner.topicos import biblia, dieta

HOJE = date(2026, 8, 19)

DIA = {"refeicoes": [{"nome": "Café da manhã", "hora": "07:00", "kcal": 600,
                      "itens": [{"alimento": "ovos", "qtd": "3 unidades"}]}],
       "total_kcal": 2800}
COMPRAS = {"secoes": [{"secao": "Hortifrúti",
                       "itens": [{"item": "banana", "qtd": "1 dúzia", "custo": "R$ 8,00"}]}],
           "custo_total": "R$ 180,00"}


@pytest.fixture(autouse=True)
def cache(tmp_path, monkeypatch):
    monkeypatch.setattr(dieta, "CACHE", tmp_path / "diet_plan.json")


def _modelo(monkeypatch, registro=None):
    def falso(prompt, **k):
        if registro is not None:
            registro.append(prompt)
        return dict(COMPRAS) if "lista de compras" in prompt else json.loads(json.dumps(DIA))
    monkeypatch.setattr(dieta.llm, "gerar_json", falso)


def test_as_cinco_refeicoes_e_a_meta_aparecem(monkeypatch):
    _modelo(monkeypatch)
    saida = "".join(dieta.blocos(HOJE))
    assert "Café da manhã" in saida and "3 unidades" in saida
    assert "2800 kcal" in saida
    assert "meta de 2800 kcal" in saida


def test_o_dia_ja_gerado_nao_e_gerado_de_novo(monkeypatch):
    prompts = []
    _modelo(monkeypatch, prompts)
    dieta.blocos(HOJE)
    quantos_dias = sum(1 for p in prompts if "plano alimentar" in p)
    prompts.clear()
    dieta.blocos(HOJE)
    assert not any("plano alimentar" in p for p in prompts), "regerou um dia que já existia"
    assert quantos_dias == dieta.JANELA


def test_a_lista_de_compras_abre_folha_nova(monkeypatch):
    """Duas leituras diferentes: o que comer hoje e o que comprar para três dias."""
    _modelo(monkeypatch)
    partes = dieta.blocos(HOJE)
    marcados = [b for b in partes if "data-quebra" in b]
    assert len(marcados) == 1, "a quebra é uma só, na primeira seção de compras"
    assert dieta.CHAPEU_COMPRAS in marcados[0]
    assert "Compras · Hortifrúti" in marcados[0]


def test_o_amanha_de_hoje_e_o_hoje_de_amanha(monkeypatch):
    """A janela é o que dá continuidade — o dia seguinte já está escrito."""
    _modelo(monkeypatch)
    dieta.blocos(HOJE)
    guardados = json.loads(dieta.CACHE.read_text(encoding="utf-8"))
    assert "2026-08-20" in guardados and "2026-08-21" in guardados


def test_a_lista_de_compras_soma_os_dias_por_secao(monkeypatch):
    _modelo(monkeypatch)
    saida = "".join(dieta.blocos(HOJE))
    assert "Compras · Hortifrúti" in saida
    assert "1 dúzia" in saida and "R$ 8,00" in saida
    assert "R$ 180,00" in saida


def test_o_prompt_repete_o_schema_inteiro():
    """Dizer 'JSON igual ao padrão' foi o que quebrou a dieta de domingo no teste real."""
    assert '"hora"' in dieta.PROMPT_DIA and '"qtd"' in dieta.PROMPT_DIA and '"kcal"' in dieta.PROMPT_DIA
    assert '"secoes"' in dieta.PROMPT_COMPRAS and '"custo"' in dieta.PROMPT_COMPRAS


def test_nomes_alternativos_do_modelo_nao_derrubam_a_folha(monkeypatch):
    torto = {"refeições": [{"refeicao": "Almoço", "horario": "12:00", "subtotal_kcal": 900,
                            "alimentos": [{"item": "arroz", "quantidade": "4 colheres"}]}],
             "kcal_total": 2800}
    monkeypatch.setattr(dieta.llm, "gerar_json",
                        lambda p, **k: dict(COMPRAS) if "lista de compras" in p else json.loads(json.dumps(torto)))
    saida = "".join(dieta.blocos(HOJE))
    assert "Almoço" in saida and "12:00" in saida and "4 colheres" in saida


# ---- Bíblia ----

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
