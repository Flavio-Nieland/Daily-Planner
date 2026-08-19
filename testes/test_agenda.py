from datetime import date

from planner.agenda import FIXAS, topicos_do_dia

# Contagem de folhas por dia, conforme a tabela do AGENDA.md.
ESPERADO = {
    date(2026, 8, 17): 10,   # segunda
    date(2026, 8, 18): 11,   # terça
    date(2026, 8, 19): 9,    # quarta
    date(2026, 8, 20): 11,   # quinta
    date(2026, 8, 21): 10,   # sexta
    date(2026, 8, 22): 10,   # sábado
    date(2026, 8, 23): 9,    # domingo
}


def test_contagem_por_dia_bate_com_a_agenda():
    for dia, quantos in ESPERADO.items():
        assert len(topicos_do_dia(dia)) == quantos, dia


def test_jornal_sai_todos_os_dias_com_as_folhas_fixas():
    for dia in ESPERADO:
        assert topicos_do_dia(dia)[: len(FIXAS)] == FIXAS


def test_tcc_saiu_da_agenda():
    for dia in ESPERADO:
        assert "tcc" not in topicos_do_dia(dia)
