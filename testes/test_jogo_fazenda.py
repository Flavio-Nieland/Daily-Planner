"""Jogo e Fazenda: trilhas em rotação, e toda indicação marcada como não conferida."""

from datetime import date

import pytest

from planner import conteudo, esqueleto, progressao
from planner.topicos import fazenda, jogo

SEXTA, DOMINGO, SABADO = date(2026, 8, 21), date(2026, 8, 23), date(2026, 8, 22)


@pytest.fixture(autouse=True)
def sem_rede(tmp_path, monkeypatch):
    monkeypatch.setattr(conteudo, "PASTA", tmp_path / "gerado")
    monkeypatch.setattr(esqueleto, "PASTA", tmp_path / "esqueletos")

    def falso(prompt, **k):
        # prompt de esqueleto é o que pede uma lista de itens; o resto é conteúdo do dia
        if '{"itens"' in prompt:
            return {"itens": [{"titulo": f"item {i}", "precisa": "nada"} for i in range(1, 61)]}
        return {"dica": "faça assim.", "material": "vídeo do canal X", "aplicar": "no seu jogo, faça Y.",
                "entrega": "a entrega fecha quando Z.", "primeiro_passo": "comece por W.",
                "risco": "escopo crescer", "recurso": "o recurso serve para K.",
                "no_jogo": "aplique em L.", "pegadinha": "cuidado com M.",
                "explicacao": "é assim que funciona.", "na_pratica": "na roça aparece assim.",
                "engano": "gente de cidade acha que N.", "porque": "porque resolve O.",
                "comece_por": "comece pelo capítulo 1"}

    monkeypatch.setattr(jogo.llm, "gerar_json", falso)
    monkeypatch.setattr(fazenda.llm, "gerar_json", falso)


def _feito(topico, *dias):
    return {progressao.SECAO: {progressao.chave(topico, d): True for d in dias}}


def test_jogo_rotaciona_as_tres_trilhas():
    assert "trilha dica" in "".join(jogo.blocos(SEXTA, {}))
    assert "trilha fatia" in "".join(jogo.blocos(DOMINGO, _feito("jogo", SEXTA)))
    assert "trilha godot" in "".join(jogo.blocos(date(2026, 8, 28), _feito("jogo", SEXTA, DOMINGO)))


def test_a_fatia_do_projeto_fala_do_roguelite():
    assert "roguelite" in jogo.JOGO
    assert "Mercenários" not in "".join(jogo.blocos(DOMINGO, _feito("jogo", SEXTA)))


def test_godot_tecnico_aplica_ao_jogo_dele():
    saida = "".join(jogo.blocos(date(2026, 8, 28), _feito("jogo", SEXTA, DOMINGO)))
    assert "No seu jogo" in saida


def test_o_material_do_jogo_vai_como_nao_conferido():
    saida = "".join(jogo.blocos(SEXTA, {}))
    assert "vídeo do canal X" in saida
    assert "não conferida" in saida


def test_fazenda_alterna_base_e_curadoria():
    assert "trilha base" in "".join(fazenda.blocos(SABADO, {}))
    assert "trilha curadoria" in "".join(fazenda.blocos(DOMINGO, _feito("fazenda", SABADO)))


def test_a_curadoria_da_fazenda_vai_como_nao_conferida():
    saida = "".join(fazenda.blocos(DOMINGO, _feito("fazenda", SABADO)))
    assert "não conferida" in saida
    assert "sem verificação" in saida


def test_os_ponteiros_das_trilhas_do_jogo_andam_separados():
    estado = _feito("jogo", SEXTA, DOMINGO)
    assert progressao.posicao_trilha(estado, "jogo", jogo.ORDEM, "dica", 1, 60) == 2
    assert progressao.posicao_trilha(estado, "jogo", jogo.ORDEM, "fatia", 1, 12) == 2
    assert progressao.posicao_trilha(estado, "jogo", jogo.ORDEM, "godot", 1, 30) == 1


def test_marcar_aparece_e_vira_feito():
    assert 'class="marcar"' in "".join(jogo.blocos(SEXTA, {}))
    assert "feito hoje" in "".join(jogo.blocos(SEXTA, _feito("jogo", SEXTA)))
