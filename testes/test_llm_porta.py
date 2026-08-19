"""A porta do modelo: as três lições do ADR 0001 viradas em código."""

import pytest

from planner import llm


def _cliente_falso(conteudo, finish_reason="stop"):
    class _Escolha:
        message = type("m", (), {"content": conteudo})()

    _Escolha.finish_reason = finish_reason

    class _Cliente:
        class chat:
            class completions:
                @staticmethod
                def create(**k):
                    return type("r", (), {"choices": [_Escolha()]})()

    return _Cliente()


def test_resposta_truncada_vira_erro_com_pista(monkeypatch):
    """Sem isto o truncamento chega como JSONDecodeError e não se acha a causa."""
    monkeypatch.setattr(llm, "_cliente", lambda: _cliente_falso('{"a": "cami', "length"))
    with pytest.raises(RuntimeError, match="truncada no limite de 10 tokens"):
        llm.gerar_json("qualquer", max_tokens=10)


def test_resposta_vazia_vira_erro(monkeypatch):
    monkeypatch.setattr(llm, "_cliente", lambda: _cliente_falso(""))
    with pytest.raises(ValueError, match="vazia"):
        llm.gerar_json("qualquer")


def test_cerca_de_markdown_e_removida(monkeypatch):
    monkeypatch.setattr(llm, "_cliente", lambda: _cliente_falso('```json\n{"a": 1}\n```'))
    assert llm.gerar_json("qualquer") == {"a": 1}


def test_campo_aceita_os_nomes_que_o_modelo_inventa():
    assert llm.campo({"esforço": "x"}, "esforco", "esforço") == "x"
    assert llm.campo({}, "nada", padrao="—") == "—"
    with pytest.raises(KeyError):
        llm.campo({}, "obrigatorio")


def test_campo_ignora_valor_vazio():
    assert llm.campo({"a": "", "b": "vale"}, "a", "b") == "vale"


def test_texto_junta_lista_onde_o_schema_pedia_string():
    assert llm.texto(["uma frase", "outra"]) == "uma frase outra"
    assert llm.texto(" limpo ") == "limpo"


def test_truncamento_detectado_pelo_uso_de_tokens(monkeypatch):
    """O hub devolve finish_reason 'stop' mesmo quando a resposta bateu no teto."""
    class _Escolha:
        finish_reason = "stop"
        message = type("m", (), {"content": '{"itens": [{"video": "abc'})()

    class _Cliente:
        class chat:
            class completions:
                @staticmethod
                def create(**k):
                    return type("r", (), {"choices": [_Escolha()],
                                          "usage": type("u", (), {"completion_tokens": 6000})()})()

    monkeypatch.setattr(llm, "_cliente", lambda: _Cliente())
    with pytest.raises(RuntimeError, match="gastou 6000"):
        llm.gerar_json("qualquer", max_tokens=6000)
