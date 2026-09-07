"""Pilates: prescrição pura — sem LLM, sem rede, contagem derivada das conclusões.

Não há fixture de `sem_rede` aqui de propósito: se um dia alguém puser chamada de modelo
nesta folha, estes testes falham por tentar sair para a internet — que é o aviso desejado.
"""

from datetime import date

from planner import progressao
from planner.topicos import pilates

QUINTA, QUINTA2, QUINTA3 = date(2026, 8, 20), date(2026, 8, 27), date(2026, 9, 3)
SEGUNDA = date(2026, 8, 17)


def _feito(*dias):
    return {progressao.SECAO: {progressao.chave("pilates", d): True for d in dias}}


def test_a_folha_diz_que_hoje_e_dia_e_nao_prescreve_exercicio():
    saida = "".join(pilates.blocos(QUINTA, {}))
    assert "Hoje é dia de Pilates" in saida
    assert "não prescreve exercício" in saida


def test_sem_marcacao_e_a_primeira_aula():
    saida = "".join(pilates.blocos(QUINTA, {}))
    assert "Aula 1" in saida
    assert "Nenhuma aula marcada ainda" in saida


def test_a_contagem_sai_das_conclusoes():
    saida = "".join(pilates.blocos(QUINTA3, _feito(QUINTA, QUINTA2)))
    assert "Aula 3" in saida
    assert "aulas marcadas" in saida
    assert "27/08" in saida


def test_marcacao_em_dia_sem_pilates_na_agenda_nao_conta():
    """Segunda não tem Pilates. O navegador pode mandar qualquer coisa; o build confere."""
    saida = "".join(pilates.blocos(QUINTA, _feito(SEGUNDA)))
    assert "Aula 1" in saida
    assert "Nenhuma aula marcada ainda" in saida


def test_marcar_aparece_e_vira_feito():
    assert 'class="marcar"' in "".join(pilates.blocos(QUINTA, {}))
    feito = "".join(pilates.blocos(QUINTA, _feito(QUINTA)))
    assert "pilates feito hoje" in feito
    assert 'class="marcar"' not in feito


def test_marcar_hoje_nao_infla_o_numero_da_aula():
    """Marcar não é começar outra aula: o número da aula de hoje continua o mesmo."""
    antes = "".join(pilates.blocos(QUINTA2, _feito(QUINTA)))
    depois = "".join(pilates.blocos(QUINTA2, _feito(QUINTA, QUINTA2)))
    assert "Aula 2" in antes
    assert "Aula 2" in depois
