"""Dieta por ciclo de compras de três dias, e a lista de Compras somada por código.

O que se protege (decisões de 2026-11-03):
- o "amanhã" de hoje é o "hoje" de amanhã: dia gerado nunca é regerado;
- ciclo que ainda não começou é gerado inteiro, para a compra fazer sentido;
- ciclo em andamento gera só o que falta, sabendo o que já está na despensa;
- a lista de compras é a soma exata do cardápio, sem LLM — igual nos dois builds do dia;
- a tradução para unidade de prateleira é uma chamada por ciclo, cacheada, e falhar nela
  não derruba a Compras.
"""

import json
import re
from datetime import date

import pytest

from planner.topicos import dieta

D = date


@pytest.fixture(autouse=True)
def isolado(tmp_path, monkeypatch):
    monkeypatch.setattr(dieta, "CACHE", tmp_path / "diet_plan.json")
    monkeypatch.setattr(dieta, "COMPRAS", tmp_path / "compras")


def _refeicao(nome, n):
    return {"nome": nome, "hora": f"{7 + n * 3:02d}:00", "prato": f"Prato {n}", "kcal": 560,
            "proteina_g": 30, "carbo_g": 70, "gordura_g": 15, "preparo": "Faça.", "aproveita": "",
            "itens": [{"alimento": "Peito de frango assado", "qtd": "1 filé", "gramas": 120,
                       "produto": "Peito de frango", "secao": "Açougue e peixaria"},
                      {"alimento": "Arroz branco cozido", "qtd": "4 colheres", "gramas": 100,
                       "produto": "Arroz branco", "secao": "Mercearia"}]}


class Modelo:
    def __init__(self, monkeypatch, unidades=None, falhar_unidades=False):
        self.prompts = []
        self.unidades, self.falhar = unidades, falhar_unidades
        monkeypatch.setattr(dieta.llm, "gerar_json", self)

    def __call__(self, prompt, **_):
        self.prompts.append(prompt)
        if "lista de COMPRAS" in prompt:
            if self.falhar:
                raise RuntimeError("hub fora")
            chaves = re.findall(r"^(\S[^|]*?) \|", prompt.split("Produtos")[1], re.M)
            return {"itens": [{"chave": k, "compra": f"1 pacote de {k}"} for k in chaves]}
        datas = prompt.split("Dias a planejar: ")[1].split(".")[0].split(", ")
        return {"dias": [{"data": d, "refeicoes": [_refeicao(n, i) for i, n in enumerate(dieta.REFEICOES)]}
                         for d in datas]}

    def ciclos(self):
        return [p for p in self.prompts if "Dias a planejar" in p]


def test_dia_de_compra_a_cada_tres_dias_a_partir_da_ancora():
    assert dieta.inicio_do_ciclo(D(2026, 11, 4)) == D(2026, 11, 4)
    assert dieta.inicio_do_ciclo(D(2026, 11, 6)) == D(2026, 11, 4)
    assert dieta.inicio_do_ciclo(D(2026, 11, 7)) == D(2026, 11, 7)
    assert dieta.inicio_do_ciclo(D(2026, 11, 3)) == D(2026, 11, 1)     # antes da âncora também


def test_gera_o_ciclo_de_hoje_e_o_proximo_inteiros_numa_chamada_cada(monkeypatch):
    m = Modelo(monkeypatch)
    cache = dieta.garantir(D(2026, 11, 4))
    assert len(m.ciclos()) == 2
    assert "Dias a planejar: 2026-11-04, 2026-11-05, 2026-11-06" in m.ciclos()[0]
    assert "Dias a planejar: 2026-11-07, 2026-11-08, 2026-11-09" in m.ciclos()[1]
    assert all(dieta.formato_novo(cache[f"2026-11-0{d}"]) for d in range(4, 10))


def test_o_amanha_de_hoje_e_o_hoje_de_amanha(monkeypatch):
    m = Modelo(monkeypatch)
    dieta.garantir(D(2026, 11, 4))
    antes = json.loads(dieta.CACHE.read_text())["2026-11-05"]
    dieta.garantir(D(2026, 11, 5))
    assert len(m.ciclos()) == 2, "nada novo para gerar: os dois ciclos já estão no cache"
    assert json.loads(dieta.CACHE.read_text())["2026-11-05"] == antes


def test_ciclo_futuro_com_dia_no_formato_antigo_e_gerado_inteiro(monkeypatch):
    dieta.CACHE.write_text(json.dumps({"2026-11-08": {"refeicoes": [
        {"nome": "Almoço", "hora": "13:00", "kcal": 800, "itens": [{"alimento": "x", "qtd": "1"}]}]}}))
    m = Modelo(monkeypatch)
    cache = dieta.garantir(D(2026, 11, 4))
    assert any("2026-11-07, 2026-11-08, 2026-11-09" in p for p in m.ciclos())
    assert dieta.formato_novo(cache["2026-11-08"])


def test_ciclo_em_andamento_gera_so_o_que_falta_lembrando_da_despensa(monkeypatch):
    m = Modelo(monkeypatch)
    dieta.garantir(D(2026, 11, 4))
    cache = json.loads(dieta.CACHE.read_text())
    del cache["2026-11-06"]
    dieta.CACHE.write_text(json.dumps(cache))
    m.prompts.clear()
    dieta.garantir(D(2026, 11, 5))
    [prompt] = m.ciclos()
    assert "Dias a planejar: 2026-11-06." in prompt
    assert "despensa" in prompt and "Peito de frango" in prompt


def test_dia_passado_que_falta_nao_e_inventado(monkeypatch):
    Modelo(monkeypatch)
    cache = dieta.garantir(D(2026, 11, 5))           # o ciclo 04–06 começou ontem
    assert "2026-11-04" not in cache
    assert "2026-11-05" in cache and "2026-11-06" in cache


def test_o_prompt_repete_o_schema_inteiro():
    for campo in ('"prato"', '"aproveita"', '"gramas"', '"produto"', '"secao"', '"proteina_g"'):
        assert campo in dieta.PROMPT_CICLO


def test_nomes_alternativos_do_modelo_nao_derrubam_a_dieta(monkeypatch):
    def torto(prompt, **_):
        return {"days": [{"refeições": [{"name": "Almoço", "horário": "13:00", "calorias": "780",
                                         "items": [{"food": "Feijão carioca cozido", "quantidade": "1 concha",
                                                    "g": "150", "seção": "mercearia"}]}]}] * 3}
    monkeypatch.setattr(dieta.llm, "gerar_json", torto)
    cache = dieta.garantir(D(2026, 11, 7))
    almoco = cache["2026-11-07"]["refeicoes"][0]
    assert (almoco["hora"], almoco["kcal"], almoco["prato"]) == ("13:00", 780, "Feijão carioca cozido")
    assert almoco["itens"][0]["produto"] == "Feijão carioca"          # o estado do prato sai do nome
    assert almoco["itens"][0]["gramas"] == 150


def test_a_lista_e_a_soma_exata_por_produto_com_onde_e_usado(monkeypatch):
    Modelo(monkeypatch)
    cache = dieta.garantir(D(2026, 11, 4))
    itens = {i["nome"]: i for i in dieta.agregar(cache, D(2026, 11, 4))}
    frango = itens["Peito de frango"]
    assert frango["g"] == 120 * 5 * 3
    assert len(frango["usos"]) == 15
    assert frango["usos"][0] == {"dia": "2026-11-04", "ref": "Café da manhã", "qtd": "1 filé"}
    assert [i["secao"] for i in dieta.agregar(cache, D(2026, 11, 4))] == ["Açougue e peixaria", "Mercearia"]


def test_unidade_de_prateleira_e_uma_chamada_por_ciclo(monkeypatch):
    m = Modelo(monkeypatch)
    dieta.caderno_compras(D(2026, 11, 4))
    dieta.caderno_compras(D(2026, 11, 4))
    pedidos = [p for p in m.prompts if "lista de COMPRAS" in p]
    assert len(pedidos) == 2, "uma por ciclo (o de hoje e o próximo), e não de novo no segundo build"


def test_sem_unidades_a_compras_sai_com_os_gramas(monkeypatch):
    Modelo(monkeypatch, falhar_unidades=True)
    d = dieta.caderno_compras(D(2026, 11, 4))["dados"]
    assert d["ciclos"][0]["itens"][0]["compra"] == ""
    assert d["ciclos"][0]["itens"][0]["g"] == 1800
    assert not dieta.COMPRAS.exists() or not any(dieta.COMPRAS.iterdir()), "falha não é cacheada"


def test_a_compras_abre_na_compra_de_amanha_na_vespera(monkeypatch):
    Modelo(monkeypatch)
    assert dieta.caderno_compras(D(2026, 11, 6))["dados"]["padrao"] == 1     # 07/11 é dia de compra
    assert dieta.caderno_compras(D(2026, 11, 4))["dados"]["padrao"] == 0     # hoje é dia de compra
    assert dieta.caderno_compras(D(2026, 11, 5))["dados"]["padrao"] == 0     # meio do ciclo


def test_o_caderno_leva_ontem_hoje_amanha_e_os_ciclos(monkeypatch):
    Modelo(monkeypatch)
    d = dieta.caderno(D(2026, 11, 5))["dados"]
    assert d["hoje"] == "2026-11-05" and d["meta"] == 2800
    assert {"2026-11-05", "2026-11-06", "2026-11-07"} <= set(d["dias"])
    assert [c["inicio"] for c in d["ciclos"]] == ["2026-11-04", "2026-11-07"]
