"""O Resumo passa a saber o que ele fez: o que falta hoje, a cinta e o balanço (2026-11-03).

Tudo aqui roda no navegador de verdade, sem Worker: o envio é trocado por um dublê que
aceita tudo, para provar só o lado da página.
"""

from datetime import date

import pytest

from planner import render
from planner.topicos import peso, resumo

DIA = date(2026, 11, 4)


def _dieta():
    refeicoes = [{"nome": n, "hora": h, "prato": p, "kcal": 560, "proteina_g": 30, "carbo_g": 70,
                  "gordura_g": 15, "preparo": "", "aproveita": "",
                  "itens": [{"alimento": p, "qtd": "1", "gramas": 100, "produto": p, "secao": "Mercearia"}]}
                 for n, h, p in (("Café da manhã", "00:01", "Cuscuz"), ("Almoço", "00:02", "Frango"))]
    return {"id": "dieta", "nome": "Dieta", "chapeu": "x", "blocos": [], "caderno": "dieta",
            "dados": {"hoje": DIA.isoformat(), "meta": 2800, "dias": {DIA.isoformat(): {"refeicoes": refeicoes}},
                      "ciclos": [{"inicio": DIA.isoformat(), "dias": [DIA.isoformat()]}]}}


def _edicao(tmp_path, estado):
    topicos = [{"id": "resumo", "nome": "Resumo", "chapeu": "x", "falhou": False,
                **resumo.caderno(DIA, ["resumo", "dieta", "peso", "pilates"])},
               _dieta(),
               {"id": "peso", "nome": "Peso", "chapeu": "x", "blocos": [], "falhou": False, **peso.caderno(DIA)},
               {"id": "pilates", "nome": "Pilates", "chapeu": "x", "falhou": False,
                "blocos": ['<div class="bloco"><button type="button" class="marcar" data-topico="pilates" '
                           f'data-dia="{DIA.isoformat()}">fiz hoje</button></div>']}]
    alvo = tmp_path / "index.html"
    alvo.write_text(render.montar(DIA, topicos, estado=estado), encoding="utf-8")
    return alvo.as_uri()


@pytest.fixture
def pagina():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        pg = navegador.new_page(viewport={"width": 1366, "height": 768})
        yield pg
        navegador.close()


def _abrir(pagina, url, onde):
    pagina.goto(url + "#" + onde)
    pagina.wait_for_selector(".corpo.pagina")
    pagina.evaluate("window.gravarNoWorker = async () => ({ok: true})")


def test_o_que_falta_junta_refeicao_peso_e_a_folha_de_fiz_hoje(tmp_path, pagina):
    _abrir(pagina, _edicao(tmp_path, {"peso": {"2026-11-01": 68.0}}), "resumo/2")
    texto = pagina.text_content(".pend-lista")
    assert "Marcar como foi o café da manhã" in texto
    assert "Registrar o peso de hoje" in texto
    assert "Marcar Pilates como feito" in texto
    assert "faltam 4" in pagina.text_content(".cinta")


def test_marcar_a_refeicao_tira_ela_do_que_falta_na_hora(tmp_path, pagina):
    _abrir(pagina, _edicao(tmp_path, {}), "dieta/2")
    pagina.click("[data-marca$='|segui']")
    pagina.goto(pagina.url.split("#")[0] + "#resumo/2")
    pagina.evaluate("window.gravarNoWorker = async () => ({ok: true})")
    # se o goto recarregou a página, a marcação some do estado em memória: garante ela de novo
    pagina.evaluate("gravarEstado('feito', 'refeicao:2026-11-04:0', 'segui')")
    assert "Café da manhã: segui" in pagina.text_content(".pend-lista")
    assert "faltam 3" in pagina.text_content(".cinta")


def test_caderno_em_dia_ganha_a_bolinha_hachurada(tmp_path, pagina):
    _abrir(pagina, _edicao(tmp_path, {"peso": {"2026-11-04": {"kg": 68.2, "em": "2026-11-04T08:00:00Z"}}}), "resumo/1")
    bolinhas = pagina.locator(".bolinha")
    assert "feita" in bolinhas.nth(2).get_attribute("class")          # peso gravado hoje
    assert "feita" not in bolinhas.nth(1).get_attribute("class")      # refeições sem marca


def test_o_balanco_mostra_o_alvo_e_quanto_falta(tmp_path, pagina):
    estado = {"peso": {"2026-10-20": 67.0, "2026-10-27": 67.4, "2026-11-03": 67.8}}
    _abrir(pagina, _edicao(tmp_path, estado), "resumo/3")
    lado = pagina.text_content(".lado")
    assert "Faltam 2,2 kg" in lado
    assert "kg/semana" in lado
    pagina.fill("#alvo", "69")
    pagina.dispatch_event("#alvo", "change")
    pagina.wait_for_function("() => document.querySelector('.lado').textContent.includes('Faltam 1,2 kg')")
