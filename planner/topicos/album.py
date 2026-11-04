"""Caderno do Álbum — dois discos por dia, por caminhos diferentes, e a discoteca.

O primeiro sai do gosto dele; o segundo, do estilo que ele digita na própria página. Desde
2026-11-03 é um caderno de três páginas (Pelo seu gosto · Pelo estilo pedido · Discoteca),
desenhado no navegador por caderno-album.js.

O gosto deixou de depender do Spotify estar de pé:
- o perfil que funcionou fica salvo em gerado/perfil-gosto.json; quando o refresh token cai
  (invalid_grant), o disco do gosto sai por esse perfil, com um aviso discreto;
- a nota que ele dá em cada disco ("gostei" / "não curti") entra no prompt do gosto;
- a capa vem pela busca pública do Spotify (client credentials), que não precisa do login
  dele — era por isso que as capas tinham sumido junto com o token.

Requisito literal dele sobre a caixa de estilo: o valor persiste, e trocar o estilo hoje
muda a sugestão **a partir de amanhã** — a edição de hoje já está publicada.
"""

import json
from datetime import date
from pathlib import Path

from planner import conteudo, llm

RAIZ = Path(__file__).resolve().parent.parent.parent
HISTORICO = RAIZ / "album_history.json"
PERFIL = RAIZ / "gerado" / "perfil-gosto.json"
SECAO = "estilo"
CHAVE = "pedido"
ESTILO_PADRAO = "o que combinar com o que você anda ouvindo"
# A planilha de backtracking dos discos (zerada em 2026-11-03, a pedido dele).
PLANILHA = "https://docs.google.com/spreadsheets/d/1M8SWWZydgzkNtAnsdeuYxOKdeQzhkIxlQP1ByvKVofs/edit"
NOTAS = ("gostei", "não curti", "não ouvi")
EVITAR = 120          # discos lembrados para não repetir: ~2 meses com dois por dia

PROMPT = """Você escreve a página de música de um jornal pessoal, em português do Brasil.

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
    """Os discos daquela data SUBSTITUEM o que havia — nunca somam (build roda 2x por dia)."""
    hoje = dia.isoformat()
    registros = [r for r in _historico() if r.get("data") != hoje]
    for disco in discos:
        registros.append({"data": hoje, "album": disco["album"],
                          "artista": disco["artista"], "origem": disco["origem"]})
    HISTORICO.write_text(json.dumps(registros, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")


def notas(estado: dict) -> dict[str, str]:
    """{"AAAA-MM-DD:gosto": "gostei", ...} — o que ele marcou em cada disco."""
    saida = {}
    for chave, valor in (estado.get("feito") or {}).items():
        if chave.startswith("disco:") and valor in NOTAS:
            saida[chave[len("disco:"):]] = valor
    return saida


def _sugerir(contexto: str, evitar: list[str]) -> dict:
    lista = "\n".join(f"- {x}" for x in evitar[-EVITAR:]) or "- (nenhum ainda)"
    bruto = llm.gerar_json(PROMPT.format(contexto=contexto, evitar=lista), max_tokens=6000)
    return {
        "album": llm.texto(llm.campo(bruto, "album", "álbum", "disco", "title")),
        "artista": llm.texto(llm.campo(bruto, "artista", "artist", "banda")),
        "ano": llm.texto(llm.campo(bruto, "ano", "year", "lancamento", padrao="")),
        "historia": llm.texto(llm.campo(bruto, "historia", "história", "story", "texto")),
        "faixa": llm.texto(llm.campo(bruto, "faixa", "faixa_chave", "track", padrao="")),
    }


def _capa(disco: dict) -> dict:
    """{"capa": url, "id": spotify_id} pela busca pública; vazio quando não achou."""
    from planner.spotify import search_album

    try:
        achado = search_album(disco["album"], disco["artista"])
    except Exception:                                  # noqa: BLE001 — capa é enfeite
        return {}
    return {"capa": achado.get("cover_url"), "id": achado.get("spotify_id")}


def _perfil(dia: date) -> tuple[dict, str | None, str | None]:
    """(perfil, motivo de o Spotify não ter vindo, data do perfil salvo usado no lugar).

    Spotify de pé: salva o perfil e usa. Caiu: usa o último salvo. Nunca houve: sem perfil.
    """
    from planner.spotify import get_spotify_taste_profile

    try:
        perfil = get_spotify_taste_profile()
    except Exception as erro:                      # noqa: BLE001
        motivo = (str(erro).strip() or erro.__class__.__name__)[:160]
        try:
            salvo = json.loads(PERFIL.read_text(encoding="utf-8"))
            return salvo, motivo, salvo.get("atualizado")
        except (OSError, json.JSONDecodeError):
            return {}, motivo, None
    PERFIL.parent.mkdir(parents=True, exist_ok=True)
    PERFIL.write_text(json.dumps({**perfil, "atualizado": dia.isoformat(), "origem": "spotify"},
                                 ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return perfil, None, None


def _contexto_notas(historico: list[dict], marcadas: dict[str, str]) -> str:
    por_chave = {f'{r["data"]}:{r["origem"]}': f'{r["album"]} — {r["artista"]}' for r in historico}
    gostou = [por_chave[k] for k, v in marcadas.items() if v == "gostei" and k in por_chave]
    nao = [por_chave[k] for k, v in marcadas.items() if v == "não curti" and k in por_chave]
    partes = []
    if gostou:
        partes.append("Discos que ele ouviu e GOSTOU: " + "; ".join(gostou[-15:]) + ".")
    if nao:
        partes.append("Discos que ele ouviu e NÃO CURTIU (evite a mesma linha): " + "; ".join(nao[-15:]) + ".")
    return " ".join(partes)


def caderno(dia: date, estado: dict) -> dict:
    vigente, pendente = estilo_vigente(estado, dia)
    historico = _historico()
    ja_sugeridos = [f'{r["album"]} — {r["artista"]}' for r in historico]
    marcadas = notas(estado)

    perfil, sem_spotify, perfil_de = _perfil(dia)
    salvos = [f'{a["album"]} — {a["artist"]}' for a in perfil.get("saved_albums", [])]
    pelas_notas = _contexto_notas(historico, marcadas)

    # Cada metade cacheia por data em arquivo próprio: se o perfil não vier no primeiro build
    # do dia, só o disco do gosto fica sem cache e o build seguinte tenta de novo.
    if not perfil:
        do_gosto = None
    else:
        contexto_gosto = (
            f'Ele ouve muito: {", ".join(perfil.get("top_artists", [])[:10])}. '
            + (f'Gêneros: {", ".join(perfil.get("top_genres", [])[:5])}. ' if perfil.get("top_genres") else "")
            + (pelas_notas + " " if pelas_notas else "")
            + "Sugira um disco que converse com esse gosto e que ele provavelmente não conhece."
        )
        do_gosto = conteudo.obter_por_data(
            "album-gosto", dia, lambda: _sugerir(contexto_gosto, ja_sugeridos + salvos))
        do_gosto["origem"] = "gosto"

    evitar = ja_sugeridos + salvos
    if do_gosto:
        evitar = evitar + [f'{do_gosto["album"]} — {do_gosto["artista"]}']
    contexto_estilo = f'Ele pediu para ouvir hoje: "{vigente}". Sugira um disco desse estilo.'
    do_estilo = conteudo.obter_por_data(
        "album-estilo", dia, lambda: _sugerir(contexto_estilo, evitar))
    do_estilo["origem"] = "estilo"

    _guardar(dia, [d for d in (do_gosto, do_estilo) if d])

    discos = {}
    for qual, disco in (("gosto", do_gosto), ("estilo", do_estilo)):
        if disco:
            discos[qual] = {**{k: disco.get(k, "") for k in ("album", "artista", "ano", "historia", "faixa")},
                            **_capa(disco)}
    return {"caderno": "album", "dados": {
        "hoje": dia.isoformat(),
        "gosto": discos.get("gosto"),
        "estilo": discos["estilo"],
        # o perfil do Spotify não veio: o motivo, e de quando é o perfil salvo usado no lugar
        "sem_spotify": sem_spotify,
        "perfil_de": perfil_de,
        "vigente": vigente,
        "pendente": pendente,
        "discoteca": list(reversed(_historico()))[:60],
        "planilha": PLANILHA,
    }}
