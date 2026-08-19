"""O esqueleto é grafo: a próxima aula é o próximo tópico com pré-requisitos concluídos."""

from datetime import date

import pytest

from planner import conteudo, esqueleto
from planner.topicos import programacao

TERCA, SEXTA = date(2026, 8, 18), date(2026, 8, 21)

GRAFO = [
    {"titulo": "arrays", "depende": []},
    {"titulo": "árvore binária de busca", "depende": ["arrays"]},
    {"titulo": "AVL", "depende": ["árvore binária de busca"]},
    {"titulo": "B-tree", "depende": ["AVL"]},
    {"titulo": "hash", "depende": ["arrays"]},
]
AULA = {"porque": "resolve busca ordenada.", "implemente": "escreva a inserção.",
        "antes": "arrays", "depois": "AVL", "gancho": "é por isso que índice é B-tree"}


@pytest.fixture(autouse=True)
def sem_rede(tmp_path, monkeypatch):
    monkeypatch.setattr(conteudo, "PASTA", tmp_path / "gerado")
    monkeypatch.setattr(esqueleto, "PASTA", tmp_path / "esqueletos")
    monkeypatch.setattr(programacao.llm, "gerar_json", lambda p, **k: (
        {"itens": GRAFO} if "currículo de 40 tópicos" in p else dict(AULA)))


def _concluido(*titulos, dia=TERCA):
    return {programacao.SECAO: {f"cc:{t}": {"dia": dia.isoformat(), "veredito": "concluido"}
                                for t in titulos}}


def test_comeca_pelo_topico_sem_pre_requisito():
    assert "arrays" in programacao.blocos(TERCA, {})[0]


def test_concluir_libera_quem_dependia():
    saida = programacao.blocos(SEXTA, _concluido("arrays"))[0]
    assert "árvore binária de busca" in saida


def test_topico_com_pre_requisito_pendente_nao_e_proposto():
    fila = programacao.liberados(GRAFO, {"arrays"})
    titulos = [i["titulo"] for i in fila]
    assert "árvore binária de busca" in titulos and "hash" in titulos
    assert "AVL" not in titulos and "B-tree" not in titulos


def test_a_ordem_pode_variar_sem_quebrar_dependencia():
    """Fazer hash antes da árvore é permitido; B-tree antes de AVL, não."""
    fila = [i["titulo"] for i in programacao.liberados(GRAFO, {"arrays", "hash"})]
    assert fila == ["árvore binária de busca"]


def test_a_folha_mostra_pre_requisitos_e_o_que_libera():
    saida = "".join(programacao.blocos(SEXTA, _concluido("arrays")))
    assert "pré-requisitos: arrays" in saida
    assert "libera: AVL" in saida


def test_a_folha_traz_porque_implemente_e_a_cadeia():
    saida = "".join(programacao.blocos(TERCA, {}))
    assert "resolve busca ordenada" in saida
    assert "escreva a inserção" in saida
    assert "<b>Antes:</b>" in saida and "<b>Depois:</b>" in saida
    assert "é por isso que índice é B-tree" in saida


def test_ciclo_no_grafo_nao_trava_o_build_e_a_folha_diz_o_que_falta(monkeypatch):
    """O modelo pode gerar dependência circular. A folha precisa dizer isso, não quebrar."""
    monkeypatch.setattr(programacao.llm, "gerar_json", lambda p, **k: (
        {"itens": [{"titulo": "A", "depende": ["B"]}, {"titulo": "B", "depende": ["A"]}]}
        if "currículo" in p else dict(AULA)))
    saida = "".join(programacao.blocos(TERCA, {}))
    assert "Nenhum tópico liberado" in saida
    assert "falta concluir" in saida


def test_pre_requisito_com_nome_inexistente_e_ignorado(monkeypatch):
    """Se o modelo inventa um nome fora do currículo, travar tudo seria pior que ignorar."""
    monkeypatch.setattr(programacao.llm, "gerar_json", lambda p, **k: (
        {"itens": [{"titulo": "AVL", "depende": ["conceito que não está no currículo"]}]}
        if "currículo" in p else dict(AULA)))
    assert "AVL" in programacao.blocos(TERCA, {})[0]


def test_curriculo_concluido():
    estado = _concluido(*[i["titulo"] for i in GRAFO])
    assert "Currículo concluído" in "".join(programacao.blocos(TERCA, estado))


def test_conclusao_em_dia_sem_programacao_na_agenda_nao_vale():
    """Quinta não tem Programação. O build descarta."""
    assert programacao.concluidos(_concluido("arrays", dia=date(2026, 8, 20))) == set()


def test_a_aula_e_cacheada_pela_posicao_no_esqueleto(monkeypatch):
    chamadas = []
    monkeypatch.setattr(programacao.llm, "gerar_json", lambda p, **k: (
        {"itens": GRAFO} if "currículo" in p else (chamadas.append(1) or dict(AULA))))
    programacao.blocos(TERCA, {})
    programacao.blocos(SEXTA, {})
    assert len(chamadas) == 1, "regerou a mesma aula em outro dia"
