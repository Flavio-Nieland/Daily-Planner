"""Fala prescrita e escuta com gabarito real — o modelo nunca diz o que foi falado."""

from datetime import date

import pytest

from planner import conteudo, esqueleto, progressao
from planner.topicos import ingles

SEGUNDA, QUINTA = date(2026, 8, 17), date(2026, 8, 20)

FALA = {"expressoes": [{"frase": "I see it differently", "quando": "para discordar sem atrito"}],
        "exercicio": "diga em voz alta três vezes.", "cuidado": "não traduza 'com certeza'"}
ESCUTA = {"escapa": "'want to' vira 'wanna'.", "foco": "escute o ritmo antes de ler."}
LINHAS = [{"inicio": 37.0, "texto": "I've been blown away"}, {"inicio": 41.0, "texto": "by the whole thing"}]


@pytest.fixture(autouse=True)
def sem_rede(tmp_path, monkeypatch):
    monkeypatch.setattr(conteudo, "PASTA", tmp_path / "gerado")
    monkeypatch.setattr(esqueleto, "PASTA", tmp_path / "esqueletos")

    def falso(prompt, **k):
        if "40 situações" in prompt:
            return {"itens": [{"titulo": f"situação {i}"} for i in range(1, 41)]}
        if "40 vídeos" in prompt:
            return {"itens": [{"video": f"video{i:07d}", "titulo": f"vídeo {i}"} for i in range(1, 41)]}
        return dict(ESCUTA) if "legenda oficial do vídeo" in prompt else dict(FALA)

    monkeypatch.setattr(ingles.llm, "gerar_json", falso)
    monkeypatch.setattr(ingles, "transcricao", lambda video, inicio=0: list(LINHAS))


def _feito(*dias):
    return {progressao.SECAO: {progressao.chave("ingles", d): True for d in dias}}


def test_comeca_pela_fala_e_alterna_com_a_escuta():
    assert "trilha da fala" in "".join(ingles.blocos(SEGUNDA, {}))
    assert "trilha da escuta" in "".join(ingles.blocos(QUINTA, _feito(SEGUNDA)))


def test_a_fala_e_prescritora():
    saida = "".join(ingles.blocos(SEGUNDA, {}))
    assert "ELSA Speak" in saida and "Gemini Live" in saida
    assert "o treino de pronúncia é lá" in saida


def test_a_expressao_pode_ser_ouvida_no_proprio_navegador():
    saida = "".join(ingles.blocos(SEGUNDA, {}))
    assert 'data-falar="I see it differently"' in saida


def test_a_escuta_aponta_o_minuto_e_traz_o_gabarito_da_legenda():
    saida = "".join(ingles.blocos(QUINTA, _feito(SEGUNDA)))
    assert "youtube.com/watch?v=" in saida and "&t=37s" in saida
    assert "a partir de 0min37" in saida
    assert "I've been blown away by the whole thing" in saida
    assert "legenda oficial do vídeo — não é transcrição gerada" in saida


def test_o_gabarito_e_revelado_depois():
    saida = "".join(ingles.blocos(QUINTA, _feito(SEGUNDA)))
    assert "<details>" in saida and "revelar o que foi dito" in saida


def test_o_modelo_nao_reescreve_a_transcricao():
    assert "Não reescreva a transcrição" in ingles.PROMPT_ESCUTA


def test_video_sem_legenda_e_pulado(monkeypatch):
    tentativas = []

    def so_o_terceiro(video, inicio=0):
        tentativas.append(video)
        return list(LINHAS) if len(tentativas) >= 3 else []

    monkeypatch.setattr(ingles, "transcricao", so_o_terceiro)
    saida = "".join(ingles.blocos(QUINTA, _feito(SEGUNDA)))
    assert len(tentativas) == 3
    assert "I've been blown away" in saida


def test_sem_nenhuma_legenda_a_folha_falha_em_vez_de_inventar(monkeypatch):
    monkeypatch.setattr(ingles, "transcricao", lambda video, inicio=0: [])
    with pytest.raises(RuntimeError, match="nenhum vídeo da fila tinha legenda"):
        ingles.blocos(QUINTA, _feito(SEGUNDA))


def test_cada_trilha_tem_ponteiro_proprio():
    estado = _feito(SEGUNDA, QUINTA)
    assert progressao.posicao_trilha(estado, "ingles", ingles.ORDEM, "fala", 1, 40) == 2
    assert progressao.posicao_trilha(estado, "ingles", ingles.ORDEM, "escuta", 1, 40) == 2
