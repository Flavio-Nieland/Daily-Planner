"""Jogo e Fazenda: trilhas em rotação, e toda indicação marcada como não conferida."""

from datetime import date

import pytest

from planner import conteudo, esqueleto, progressao
from planner.topicos import fazenda, jogo

# O Jogo saiu da sexta na revisão de 2026-09-07 e ficou só no domingo: as três trilhas
# precisam de três domingos para rotacionar, porque marcação fora da agenda não vale.
DOMINGO, DOMINGO2, DOMINGO3 = date(2026, 8, 23), date(2026, 8, 30), date(2026, 9, 6)
SABADO = date(2026, 8, 22)


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
    assert "trilha dica" in "".join(jogo.blocos(DOMINGO, {}))
    assert "trilha fatia" in "".join(jogo.blocos(DOMINGO2, _feito("jogo", DOMINGO)))
    assert "trilha godot" in "".join(jogo.blocos(DOMINGO3, _feito("jogo", DOMINGO, DOMINGO2)))


def test_a_fatia_do_projeto_fala_do_roguelite():
    assert "roguelite" in jogo.JOGO
    assert "Mercenários" not in "".join(jogo.blocos(DOMINGO2, _feito("jogo", DOMINGO)))


def test_godot_tecnico_aplica_ao_jogo_dele():
    saida = "".join(jogo.blocos(DOMINGO3, _feito("jogo", DOMINGO, DOMINGO2)))
    assert "No seu jogo" in saida


def test_o_material_do_jogo_vai_como_nao_conferido():
    saida = "".join(jogo.blocos(DOMINGO, {}))
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
    estado = _feito("jogo", DOMINGO, DOMINGO2)
    assert progressao.posicao_trilha(estado, "jogo", jogo.ORDEM, "dica", 1, 60) == 2
    assert progressao.posicao_trilha(estado, "jogo", jogo.ORDEM, "fatia", 1, 12) == 2
    assert progressao.posicao_trilha(estado, "jogo", jogo.ORDEM, "godot", 1, 30) == 1


def test_marcar_aparece_e_vira_feito():
    assert 'class="marcar"' in "".join(jogo.blocos(DOMINGO, {}))
    assert "feito hoje" in "".join(jogo.blocos(DOMINGO, _feito("jogo", DOMINGO)))
