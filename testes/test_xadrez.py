"""Rotação de trilhas: cada uma com ponteiro próprio, andando independente da outra."""

from datetime import date

import pytest

from planner import conteudo, esqueleto, progressao
from planner.topicos import xadrez

TERCA, QUINTA = date(2026, 8, 18), date(2026, 8, 20)

ABERTURA = {"lances": "1.e4 e5 2.Cf3 Cc6 3.Bb5", "ideia": "pressiona o cavalo que defende o peão.",
            "erro": "trocar em c6 cedo demais"}
FUNDAMENTO = {"conceito": "oposição decide finais de rei e peão.", "regra": "tome a oposição antes de avançar",
              "erro": "empurrar o peão antes do rei"}


@pytest.fixture(autouse=True)
def sem_rede(tmp_path, monkeypatch):
    monkeypatch.setattr(conteudo, "PASTA", tmp_path / "gerado")
    monkeypatch.setattr(esqueleto, "PASTA", tmp_path / "esqueletos")

    def falso_json(prompt, **k):
        if "Liste 16 linhas" in prompt:
            return {"itens": [{"titulo": f"linha {i}", "cor": "brancas"} for i in range(1, 17)]}
        if "Liste 20 fundamentos" in prompt:
            return {"itens": [{"titulo": f"fundamento {i}", "tipo": "final"} for i in range(1, 21)]}
        return dict(ABERTURA) if "abertura de xadrez" in prompt else dict(FUNDAMENTO)

    monkeypatch.setattr(xadrez.llm, "gerar_json", falso_json)


def _feito(*dias):
    return {progressao.SECAO: {progressao.chave("xadrez", d): True for d in dias}}


def test_comeca_pela_abertura_e_diz_qual_vem_depois():
    saida = "".join(xadrez.blocos(TERCA, {}, []))
    assert "Trilha de hoje: abertura" in saida
    assert "amanhã a vez é de fundamentos" in saida


def test_marcar_passa_a_vez_para_a_outra_trilha():
    saida = "".join(xadrez.blocos(QUINTA, _feito(TERCA), []))
    assert "Trilha de hoje: fundamentos" in saida


def test_o_ponteiro_de_uma_trilha_nao_mexe_no_da_outra():
    """Duas sessões: abertura anda uma, fundamentos anda uma — nenhuma anda duas."""
    estado = _feito(TERCA, QUINTA)
    assert xadrez.progressao.posicao_trilha(estado, "xadrez", xadrez.ORDEM, "abertura",
                                            xadrez.INICIAIS["abertura"], 16) == 5
    assert xadrez.progressao.posicao_trilha(estado, "xadrez", xadrez.ORDEM, "fundamentos",
                                            xadrez.INICIAIS["fundamentos"], 20) == 7


def test_tatica_e_analise_sao_prescritas_no_chesscom():
    saida = "".join(xadrez.blocos(TERCA, {}, []))
    assert "Chess.com" in saida
    assert "20 puzzles" in saida
    assert "analisador" in saida


def test_nenhuma_posicao_de_xadrez_e_inventada():
    """O prompt de fundamentos proíbe diagrama; o de abertura pede só notação da linha."""
    assert "sem diagrama" in xadrez.PROMPT_ESQUELETO["fundamentos"].lower().replace("nada que precise de diagrama", "sem diagrama")
    saida = "".join(xadrez.blocos(TERCA, {}, []))
    assert "1.e4 e5" in saida


def test_elo_aparece_com_campo_e_variacao():
    saida = "".join(xadrez.blocos(TERCA, {}, [("2026-08-10", 1200), ("2026-08-17", 1240)]))
    assert 'id="elo-gravar"' in saida
    assert "1240" in saida
    assert "+40 desde a última anotação" in saida


def test_sem_elo_anotado_a_folha_nao_quebra():
    saida = "".join(xadrez.blocos(TERCA, {}, []))
    assert 'id="elo-gravar"' in saida


def test_curva_do_elo_a_partir_de_duas_anotacoes():
    uma = "".join(xadrez.blocos(TERCA, {}, [("2026-08-17", 1240)]))
    assert "<svg" not in uma
    duas = "".join(xadrez.blocos(TERCA, {}, [("2026-08-10", 1200), ("2026-08-17", 1240)]))
    assert "<svg" in duas


def test_esqueleto_fica_editavel_a_mao():
    xadrez.blocos(TERCA, {}, [])
    assert esqueleto.caminho("xadrez-abertura").exists()
    assert len(esqueleto.obter("xadrez-abertura", lambda: [])) == 16
