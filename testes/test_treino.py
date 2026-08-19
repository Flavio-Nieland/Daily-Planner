"""A sugestão de carga sai de regra sobre o histórico, não de modelo de linguagem."""

from datetime import date

import pytest

from planner import esqueleto
from planner.topicos import treino

SEGUNDA, TERCA, QUARTA, SEXTA = (date(2026, 8, d) for d in (17, 18, 19, 21))
QUINTA = date(2026, 8, 20)

DIVISAO = {"dias": [
    {"dia": g, "exercicios": [{"nome": f"exercício {i} de {g}", "series": "4", "reps": "8-12"}
                              for i in range(1, 7)]}
    for g in treino.DIVISAO.values()]}


@pytest.fixture(autouse=True)
def sem_rede(tmp_path, monkeypatch):
    monkeypatch.setattr(esqueleto, "PASTA", tmp_path / "esqueletos")
    monkeypatch.setattr(treino.llm, "gerar_json", lambda p, **k: DIVISAO)


def _carga(slug, dia, kg, reps):
    return {treino.SECAO: {f"{slug}:{dia.isoformat()}": {"kg": kg, "reps": reps}}}


def test_a_divisao_segue_o_dia_da_semana():
    assert "peito e tríceps" in treino.blocos(SEGUNDA, {})[0]
    assert "costas e bíceps" in treino.blocos(TERCA, {})[0]
    assert "pernas" in treino.blocos(QUARTA, {})[0]
    assert "ombro e braços" in treino.blocos(SEXTA, {})[0]


def test_quinta_nao_e_dia_de_academia():
    assert "não é dia de academia" in treino.blocos(QUINTA, {})[0]


def test_seis_exercicios_com_campo_de_carga():
    blocos = treino.blocos(SEGUNDA, {})
    assert sum(1 for b in blocos if 'class="bloco exercicio"' in b) == 6
    assert 'class="anotar-carga"' in "".join(blocos)


def test_sem_historico_a_folha_pede_a_carga_em_vez_de_sugerir():
    exercicio = {"nome": "supino", "series": "4", "reps": "8-12"}
    assert treino.sugerir(exercicio, None) == ("—", "primeira vez: anote a carga que você usou")


def test_bateu_o_topo_da_faixa_sobe_a_carga():
    exercicio = {"nome": "supino", "series": "4", "reps": "8-12"}
    sugestao, motivo = treino.sugerir(exercicio, {"kg": 60, "reps": 12})
    assert sugestao == "62.5 kg"
    assert "sobe 2.5 kg" in motivo


def test_nao_bateu_o_topo_mantem_a_carga():
    exercicio = {"nome": "supino", "series": "4", "reps": "8-12"}
    sugestao, motivo = treino.sugerir(exercicio, {"kg": 60, "reps": 10})
    assert sugestao == "60 kg"
    assert "mantém a carga até chegar a 12" in motivo


def test_perna_sobe_mais_que_braco():
    exercicio = {"nome": "agachamento", "series": "4", "reps": "8-12", "grupo": "pernas"}
    assert treino.sugerir(exercicio, {"kg": 100, "reps": 12})[0] == "105 kg"


def test_registro_ilegivel_nao_derruba_a_folha():
    exercicio = {"nome": "supino", "series": "4", "reps": "8-12"}
    assert treino.sugerir(exercicio, {"kg": "muito", "reps": None})[0] == "—"


def test_a_ultima_vez_aparece_na_folha():
    slug = treino._slug("exercício 1 de peito e tríceps")
    saida = "".join(treino.blocos(SEGUNDA, _carga(slug, date(2026, 8, 10), 60, 12)))
    assert "última vez: 60 kg × 12 em 10/08" in saida
    assert "62.5 kg" in saida


def test_volume_da_semana_compara_com_a_anterior():
    slug = treino._slug("exercício 1 de peito e tríceps")
    estado = {treino.SECAO: {
        f"{slug}:2026-08-10": {"kg": 50, "reps": 10},     # semana anterior
        f"{slug}:2026-08-17": {"kg": 60, "reps": 10},     # esta semana
    }}
    saida = "".join(treino.blocos(SEGUNDA, estado))
    assert "+20% contra a semana anterior" in saida


def test_nenhuma_sugestao_de_carga_vem_de_modelo(monkeypatch):
    """O modelo só monta a divisão, uma vez. A carga é aritmética."""
    treino.blocos(SEGUNDA, {})                     # cria o esqueleto
    monkeypatch.setattr(treino.llm, "gerar_json",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("não pode chamar")))
    assert treino.blocos(SEGUNDA, _carga(treino._slug("exercício 1 de peito e tríceps"),
                                         date(2026, 8, 10), 60, 12))
