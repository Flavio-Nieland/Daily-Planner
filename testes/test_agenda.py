from datetime import date

from planner.agenda import FIXAS, topicos_do_dia

# Contagem de folhas por dia, conforme a tabela do AGENDA.md (revisão de 2026-09-07).
ESPERADO = {
    date(2026, 8, 17): 10,   # segunda
    date(2026, 8, 18): 11,   # terça
    date(2026, 8, 19): 10,   # quarta
    date(2026, 8, 20): 9,    # quinta — o dia do corpo
    date(2026, 8, 21): 11,   # sexta
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


def test_quinta_e_o_dia_do_corpo():
    """Pilates estreou na quinta e o estudo saiu de lá — revisão de 2026-09-07."""
    quinta = topicos_do_dia(date(2026, 8, 20))
    assert "pilates" in quinta
    for estudo in ("ingles", "xadrez", "livros", "programacao", "musica"):
        assert estudo not in quinta, estudo


def test_pilates_so_na_quinta_e_jogo_so_no_domingo():
    for dia in ESPERADO:
        tem_pilates = "pilates" in topicos_do_dia(dia)
        tem_jogo = "jogo" in topicos_do_dia(dia)
        assert tem_pilates == (dia.weekday() == 3), dia
        assert tem_jogo == (dia.weekday() == 6), dia


def test_todo_topico_da_agenda_tem_gerador():
    """A rede contra a folha que desaparece calada.

    `build.montar_topicos` pula tópico que não está em GERADORES sem erro nenhum — foi o que
    permitiria pôr `pilates` na agenda e a quinta simplesmente sair sem a folha.
    """
    from build import GERADORES

    for dia in ESPERADO:
        for topico in topicos_do_dia(dia):
            if topico == "resumo":
                continue                 # montado à parte, depois das outras folhas
            assert topico in GERADORES, topico
