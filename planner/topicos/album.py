"""Folha do Álbum — dois discos por dia, por caminhos diferentes.

O primeiro sai do gosto dele no Spotify; o segundo, do estilo que ele digita na própria
folha. O texto deixa de ser justificativa genérica e passa a ser **a história do disco**.

Requisito literal dele sobre a caixa de estilo: o valor persiste, e trocar o estilo hoje
muda a sugestão **a partir de amanhã** — a edição de hoje já está publicada.

Lição do teste com conteúdo real (ADR 0001): capa, história e faixa-chave são **um bloco
só** por disco. Em três blocos separados a paginação jogou a capa numa coluna e a história
em outra, separando o que é uma coisa só.
"""

import json
from datetime import date
from pathlib import Path

from planner import llm

HISTORICO = Path(__file__).resolve().parent.parent.parent / "album_history.json"
SECAO = "estilo"
CHAVE = "pedido"
ESTILO_PADRAO = "o que combinar com o que você anda ouvindo"

PROMPT = """Você escreve a folha de música de um jornal pessoal, em português do Brasil.

{contexto}

Escolha UM álbum e conte a história dele. Não repita nenhum destes, já sugeridos antes:
{evitar}

Responda SÓ com JSON neste formato:
{{
  "album": "string, o nome do disco",
  "artista": "string, o nome do artista",
  "ano": "string, o ano de lançamento",
  "historia": "string, 3 frases: quando saiu, o que mudou, por que importa",
  "faixa": "string, a faixa-chave e uma frase dizendo o que ouvir nela"
}}
Sem markdown e sem texto fora do JSON."""


def estilo_vigente(estado: dict, dia: date) -> tuple[str, str | None]:
    """(estilo que vale hoje, estilo pedido hoje que só vale amanhã)."""
    registro = (estado.get(SECAO) or {}).get(CHAVE)
    if not isinstance(registro, dict) or not registro.get("estilo"):
        return ESTILO_PADRAO, None
    try:
        pedido_em = date.fromisoformat(str(registro.get("dia", "")))
    except ValueError:
        return ESTILO_PADRAO, None
    if pedido_em < dia:
        return llm.texto(registro["estilo"]), None
    return ESTILO_PADRAO, llm.texto(registro["estilo"])


def _historico() -> list[dict]:
    if not HISTORICO.exists():
        return []
    try:
        return json.loads(HISTORICO.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _guardar(dia: date, discos: list[dict]) -> None:
    registros = _historico()
    for disco in discos:
        registros.append({"data": dia.isoformat(), "album": disco["album"],
                          "artista": disco["artista"], "origem": disco["origem"]})
    HISTORICO.write_text(json.dumps(registros, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")


def _sugerir(contexto: str, evitar: list[str]) -> dict:
    lista = "\n".join(f"- {x}" for x in evitar[-40:]) or "- (nenhum ainda)"
    bruto = llm.gerar_json(PROMPT.format(contexto=contexto, evitar=lista), max_tokens=3000)
    return {
        "album": llm.texto(llm.campo(bruto, "album", "álbum", "disco", "title")),
        "artista": llm.texto(llm.campo(bruto, "artista", "artist", "banda")),
        "ano": llm.texto(llm.campo(bruto, "ano", "year", "lancamento", padrao="")),
        "historia": llm.texto(llm.campo(bruto, "historia", "história", "story", "texto")),
        "faixa": llm.texto(llm.campo(bruto, "faixa", "faixa_chave", "track", padrao="")),
    }


def _capa(disco: dict) -> str:
    from spotify import search_album

    try:
        achado = search_album(disco["album"], disco["artista"])
    except Exception:                                  # noqa: BLE001 — capa é enfeite
        return ""
    if not achado.get("cover_url"):
        return ""
    link = (f'<a class="ouvir" href="https://open.spotify.com/album/{achado["spotify_id"]}">ouvir</a>'
            if achado.get("spotify_id") else "")
    return (f'<img class="capa" src="{achado["cover_url"]}" alt="capa de {disco["album"]}" '
            f'loading="lazy">{link}')


def _bloco(disco: dict, chapeu: str) -> str:
    """Um disco é um bloco só: capa, história e faixa nunca se separam."""
    ano = f' <span class="miudo">({disco["ano"]})</span>' if disco["ano"] else ""
    faixa = f'<p class="miudo"><b>Faixa-chave:</b> {disco["faixa"]}</p>' if disco["faixa"] else ""
    return (
        f'<div class="bloco disco"><h4>{chapeu}</h4>{_capa(disco)}'
        f'<p class="destaque-texto">{disco["album"]}{ano}</p>'
        f'<p class="artista">{disco["artista"]}</p>'
        f'<p>{disco["historia"]}</p>{faixa}</div>'
    )


def _perfil() -> tuple[dict, str | None]:
    """O gosto no Spotify, ou o motivo de não ter vindo.

    O disco do estilo pedido não depende do Spotify — perder a conta não pode custar a
    folha inteira, só a metade que realmente precisa do perfil.
    """
    from spotify import get_spotify_taste_profile

    try:
        return get_spotify_taste_profile(), None
    except Exception as erro:                      # noqa: BLE001
        return {}, f"{erro.__class__.__name__}"


def blocos(dia: date, estado: dict) -> list[str]:
    vigente, pendente = estilo_vigente(estado, dia)
    ja_sugeridos = [f'{r["album"]} — {r["artista"]}' for r in _historico()]

    perfil, sem_spotify = _perfil()
    salvos = [f'{a["album"]} — {a["artist"]}' for a in perfil.get("saved_albums", [])]

    if sem_spotify:
        do_gosto = None
    else:
        contexto_gosto = (
            f'Ele ouve muito: {", ".join(perfil.get("top_artists", [])[:8])}. '
            f'Gêneros: {", ".join(perfil.get("top_genres", [])[:5])}. '
            "Sugira um disco que converse com esse gosto e que ele provavelmente não conhece."
        )
        do_gosto = _sugerir(contexto_gosto, ja_sugeridos + salvos)
        do_gosto["origem"] = "gosto"

    evitar = ja_sugeridos + salvos
    if do_gosto:
        evitar = evitar + [f'{do_gosto["album"]} — {do_gosto["artista"]}']
    contexto_estilo = f'Ele pediu para ouvir hoje: "{vigente}". Sugira um disco desse estilo.'
    do_estilo = _sugerir(contexto_estilo, evitar)
    do_estilo["origem"] = "estilo"

    _guardar(dia, [d for d in (do_gosto, do_estilo) if d])

    aviso = (f'<p class="miudo">Você pediu "{pendente}" hoje — entra na edição de amanhã.</p>'
             if pendente else
             f'<p class="miudo">Em vigor: {vigente}.</p>')
    caixa = (
        '<div class="bloco"><h4>Quer ouvir outro estilo?</h4>'
        '<p class="campo"><input type="text" id="estilo-valor" placeholder="jazz modal" '
        f'aria-label="estilo que você quer ouvir" data-dia="{dia.isoformat()}">'
        '<button type="button" id="estilo-gravar">pedir</button></p>'
        f'{aviso}<p class="miudo" id="estilo-aviso">O pedido vale até você trocar de novo.</p></div>'
    )

    primeiro = (_bloco(do_gosto, "Pelo seu gosto") if do_gosto else
                '<div class="bloco falhou"><h4>Sem o disco do seu gosto hoje</h4>'
                f'<p>O Spotify não respondeu ({sem_spotify}), então o disco que sai do seu '
                'perfil ficou de fora desta edição.</p></div>')
    return [primeiro, _bloco(do_estilo, "Pelo estilo que você pediu"), caixa]
