"""Uma porta só para o modelo: gpt-5.6-luna no hub (ADR 0004).

Duas lições que custaram caro no teste com conteúdo real (ADR 0001):

1. **Repetir o schema completo em cada prompt.** Dizer "JSON igual ao padrão" fez o modelo
   devolver `horario` por `hora` e `quantidade` por `qtd`.
2. **Normalizar chaves de qualquer jeito.** Mesmo com o schema repetido o modelo varia;
   aceitar a lista de nomes possíveis por campo evita a folha sumir por KeyError.

E resposta longa trunca o JSON — por isso `max_tokens` é sempre explícito.
"""

import json
import os
import re

MODELO = os.environ.get("LLM_MODEL_V2", "gpt-5.6-luna")
BASE = os.environ.get("LLM_BASE_URL", "https://hub.seazone.dev/v1")


def _cliente():
    from openai import OpenAI

    chave = os.environ.get("LLM_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if not chave:
        raise RuntimeError("sem chave do hub (LLM_API_KEY)")
    return OpenAI(api_key=chave, base_url=BASE)


def _limpar(texto: str) -> str:
    sem_cerca = re.sub(r"^```(?:json)?\s*", "", texto.strip(), flags=re.IGNORECASE)
    return re.sub(r"\s*```$", "", sem_cerca.strip()).strip()


def gerar_json(prompt: str, max_tokens: int = 2000) -> dict:
    resposta = _cliente().chat.completions.create(
        model=MODELO,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        max_tokens=max_tokens,
    )
    escolha = resposta.choices[0]

    # Resposta longa trunca o JSON, e o erro que chega é um JSONDecodeError sem pista
    # nenhuma. O modelo ainda gasta tokens de raciocínio dentro deste mesmo limite, então
    # o teto precisa de folga — dizer isso aqui é o que evita caçar o problema no escuro.
    if getattr(escolha, "finish_reason", None) == "length":
        raise RuntimeError(f"resposta truncada no limite de {max_tokens} tokens")

    texto = _limpar(escolha.message.content or "")
    if not texto:
        raise ValueError("o modelo devolveu resposta vazia")
    return json.loads(texto, strict=False)


def campo(dados: dict, *nomes: str, padrao=None):
    """O primeiro nome que existir. É a normalização de chaves, em cinco linhas."""
    for nome in nomes:
        if nome in dados and dados[nome] not in (None, "", []):
            return dados[nome]
    if padrao is None:
        raise KeyError(f"nenhum destes campos veio na resposta: {', '.join(nomes)}")
    return padrao


def texto(valor) -> str:
    """O modelo às vezes manda lista onde o schema pedia string."""
    if isinstance(valor, list):
        return " ".join(str(x).strip() for x in valor if str(x).strip())
    return str(valor).strip()
