# main.py
# Ponto de entrada do sistema — o script que você executa.
# Ele orquestra (coordena) os outros módulos em sequência:
#   1. Busca a previsão do tempo
#   2. Determina as atividades do dia
#   3. Gera o site HTML
#   4. Envia o e-mail

import argparse
import hashlib
import json
import math
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Garante UTF-8 no stdout/stderr (necessário no Windows com charmap padrão)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from google import genai                            # SDK da API do Gemini
from dotenv import load_dotenv                      # Lê o arquivo .env para variáveis de ambiente
from jinja2 import Environment, FileSystemLoader    # Motor de templates HTML

from weather import fetch_weather
from schedule import get_today_schedule, get_today_workout, DAY_NAMES, CURRENT_BOOK, count_reading_days
from email_sender import send_daily_email
from spotify import get_spotify_taste_profile, search_album

# load_dotenv() lê o arquivo .env e carrega as variáveis.
# Em produção (GitHub Actions), as variáveis já existem no ambiente — isso não faz mal.
load_dotenv()

# Fuso horário de Brasília = UTC - 3 horas
BRT = timezone(timedelta(hours=-3))


def generate_message_with_llm(day_name: str, date_str: str, weather: dict, activities: list) -> str:
    """
    Usa a API do Claude para gerar uma mensagem de bom dia personalizada e criativa.

    Conceito: em vez de regras fixas ("se treinar, diga X"), passamos os dados
    reais do dia para o modelo e ele cria um texto natural e variado a cada execução.

    Retorna o texto gerado. Em caso de erro (sem internet, chave inválida, etc.),
    chama o fallback build_daily_message() para garantir que o e-mail sempre seja enviado.
    """
    priority_1 = [a["name"] for a in activities if a["priority"] == 1]
    priority_2 = [a["name"] for a in activities if a["priority"] == 2]

    prompt = f"""Você é o assistente pessoal do Flávio. Gere uma mensagem de bom dia curta, natural e motivadora.

Dados do dia:
- Data: {day_name}, {date_str}
- Previsão do tempo (São José/SC, bairro Campinas):
  Manhã:  {weather['manha']['temp_min']}–{weather['manha']['temp_max']}°C, {weather['manha']['condition']}, chuva {weather['manha']['rain_prob']}%
  Tarde:  {weather['tarde']['temp_min']}–{weather['tarde']['temp_max']}°C, {weather['tarde']['condition']}, chuva {weather['tarde']['rain_prob']}%
  Noite:  {weather['noite']['temp_min']}–{weather['noite']['temp_max']}°C, {weather['noite']['condition']}, chuva {weather['noite']['rain_prob']}%
- Atividades prioritárias (fazer primeiro): {', '.join(priority_1) or 'nenhuma'}
- Atividades secundárias: {', '.join(priority_2) or 'nenhuma'}

Instruções:
- Escreva em português brasileiro, tom amigável e próximo
- Inclua: saudação com o nome Flávio, dia da semana e data, comentário sobre o tempo, atividades do dia, frase de encerramento motivadora
- Seja criativo: varie metáforas, humor leve, referências ao contexto. Não repita sempre o mesmo padrão
- Máximo de 4–5 frases diretas
- Retorne APENAS o texto da mensagem, sem aspas nem formatação extra"""

    return _generate(prompt)


def build_daily_message(day_name: str, date_str: str, weather: dict, activities: list) -> str:
    """
    Fallback: monta a mensagem com regras fixas caso a API do Claude esteja indisponível.
    Garante que o e-mail seja enviado mesmo sem conexão com a API.
    """
    names = [a["name"] for a in activities]
    activities_text = (
        " e ".join(names) if len(names) <= 2
        else ", ".join(names[:-1]) + f" e {names[-1]}"
    )
    return (
        f"Bom dia, Flávio! Hoje é {day_name.lower()}, {date_str}. "
        f"Suas atividades de hoje: {activities_text}. "
        f"Que seja um ótimo dia!"
    )


READING_PLAN_PATH     = Path("reading_plan.json")
NEXT_BOOK_PATH        = Path("next_book.json")
STRETCHING_PLAN_PATH  = Path("stretching_plan.json")
PROGRAMMING_PLAN_PATH = Path("programming_plan.json")
RUNNING_PLAN_PATH     = Path("running_plan.json")
MUSIC_PLAN_PATH       = Path("music_plan.json")
DIET_PLAN_PATH        = Path("diet_plan.json")
ALBUM_SUGGESTION_PATH = Path("album_suggestion.json")
ALBUM_HISTORY_PATH    = Path("album_history.json")
PSALM_OF_DAY_PATH     = Path("psalm_of_day.json")


def _parse_json_response(text: str) -> dict:
    """Remove markdown code fences e parseia JSON."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())
    return json.loads(cleaned.strip())


def _generate(prompt: str) -> str:
    """Chama o Gemini e retorna o texto da resposta."""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    return response.text.strip()


def get_reading_plan() -> dict:
    # Se o browser sinalizou um próximo livro, consome o arquivo e força nova consulta
    if NEXT_BOOK_PATH.exists():
        book = json.loads(NEXT_BOOK_PATH.read_text(encoding="utf-8"))
        NEXT_BOOK_PATH.unlink()
        if READING_PLAN_PATH.exists():
            READING_PLAN_PATH.unlink()
        print(f"Próximo livro detectado: {book['title']} ({book.get('edition', '')})")
    else:
        book = CURRENT_BOOK

    if READING_PLAN_PATH.exists():
        cached = json.loads(READING_PLAN_PATH.read_text(encoding="utf-8"))
        if cached.get("title") == book["title"] and cached.get("edition") == book.get("edition"):
            return cached

    prompt = (
        f'Quantas páginas tem o livro "{book["title"]}" '
        f'de {book["author"]} na edição {book.get("edition", "edição padrão")}? '
        f'Responda APENAS com um número inteiro. Exemplo: 250'
    )
    total_units = int(_generate(prompt))

    readings_per_week = count_reading_days()      # 3
    total_sessions    = readings_per_week * 4     # 12
    units_per_session = math.ceil(total_units / total_sessions)

    plan = {
        "title": book["title"],
        "author": book["author"],
        "edition": book.get("edition", ""),
        "total_units": total_units,
        "unit_type": "páginas",
        "readings_per_week": readings_per_week,
        "total_sessions": total_sessions,
        "units_per_session": units_per_session,
    }
    READING_PLAN_PATH.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return plan


def get_stretching_plan(date_str: str, weekday: int) -> dict:
    if STRETCHING_PLAN_PATH.exists():
        cached = json.loads(STRETCHING_PLAN_PATH.read_text(encoding="utf-8"))
        if cached.get("date") == date_str:
            return cached

    is_weekend = weekday in (5, 6)
    if is_weekend:
        context_hint = (
            "Final de semana: gere uma rotina mais simples e relaxante. "
            "Foco em mobilidade geral e bem-estar. 15 minutos."
        )
    else:
        context_hint = (
            "Dia de semana, rotina matinal: foco em saúde da coluna (mobilidade da lombar e torácica), "
            "mobilidade das pernas (alcançar o chão / flexão do quadril), "
            "e alongamentos essenciais para preparar o corpo para o dia. Rotina completa, 15 minutos."
        )

    prompt = f"""Gere uma rotina de alongamento matinal de exatamente 15 minutos para hoje ({date_str}).
Contexto: {context_hint}
Retorne APENAS um objeto JSON válido, sem markdown, sem explicações, sem ```json```.

Formato exato:
{{
  "date": "{date_str}",
  "duration_minutes": 15,
  "focus": "Descrição curta do foco da sessão (ex: Coluna e mobilidade de quadril)",
  "exercises": [
    {{
      "name": "Nome do exercício",
      "duration": "X segundos" ou "X minutos",
      "instruction": "Instrução curta e objetiva em 1 frase"
    }}
  ]
}}

Requisitos:
- Entre 6 e 8 exercícios, duração total 15 minutos
- Instruções em português, tom direto"""

    plan = _parse_json_response(_generate(prompt))
    STRETCHING_PLAN_PATH.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return plan


def get_running_plan(date_str: str) -> dict:
    if RUNNING_PLAN_PATH.exists():
        return json.loads(RUNNING_PLAN_PATH.read_text(encoding="utf-8"))

    prompt = f"""Crie um plano de corrida progressivo de 4 meses para iniciante chegar a 10km.
Data início: {date_str} | Frequência: 2x/semana | Total: 32 sessões (16 semanas)

Progressão:
- Semanas 1-4 (sessões 1-8): base aeróbica com intervalos e corrida contínua crescente
- Semanas 5-8 (sessões 9-16): aumento de volume, corrida contínua de 25-35 min
- Semanas 9-12 (sessões 17-24): foco em distância, 5km → 8km
- Semanas 13-16 (sessões 25-32): consolidação e 10km final

REGRA CRÍTICA: goal_description DEVE ser uma instrução de treino ESPECÍFICA e OBJETIVA.
NÃO use frases vagas, motivacionais ou poéticas.

Exemplos CORRETOS:
- "Corra 10 minutos contínuos em ritmo leve (pace: conseguir falar frases curtas)"
- "Alterne: 2 min correndo + 1 min caminhando × 6 séries (18 min total)"
- "Corra 3km sem parar em ritmo confortável"
- "Corra 25 minutos contínuos, pace livre"
- "Corra 5km, mantendo pace constante do início ao fim"
- "Alterne: 3 min correndo + 1 min caminhando × 5 séries, depois 5 min contínuos"

Exemplos INCORRETOS (PROIBIDOS):
- "Começando a jornada! Aquecimento e corrida leve."
- "Construindo a base. Ritmo confortável, sem pressa."
- "Você está mais forte!"

Retorne APENAS JSON válido:
{{
  "goal": "10km em 4 meses",
  "start_date": "{date_str}",
  "runs_per_week": 2,
  "total_sessions": 32,
  "sessions": [
    {{ "session": 1, "week": 1, "goal_description": "Corra 10 minutos contínuos em ritmo leve (pace: conseguir falar frases curtas)", "duration_minutes": 10 }},
    ...
  ]
}}

Cada sessão: session (1-32), week (1-16), goal_description (instrução objetiva), duration_minutes OU distance_km."""

    plan = _parse_json_response(_generate(prompt))
    RUNNING_PLAN_PATH.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return plan


def get_music_plan(date_str: str) -> dict:
    if MUSIC_PLAN_PATH.exists():
        return json.loads(MUSIC_PLAN_PATH.read_text(encoding="utf-8"))

    # Gera em dois lotes (sessões 1-16 e 17-32) para evitar truncamento de JSON
    # com saídas longas (32 sessões × 5 steps × descrições detalhadas)
    def _batch_prompt(session_start: int, session_end: int, week_start: int, week_end: int) -> str:
        progressao = (
            "Violão: arpejos PIMA → bossa nova → fingerpicking\n"
            "Piano: escalas 2 mãos → voicings → comping básico"
            if week_start <= 4 else
            "Violão: chord-melody → capotraste → solo\n"
            "Piano: blues/soul → walking bass → extensões de acordes"
            if week_start <= 8 else
            "Violão: improvisação pentatônica → levadas complexas\n"
            "Piano: jazz comping → improv sobre II-V-I"
            if week_start <= 12 else
            "Violão: peças completas → repertório\n"
            "Piano: peças completas → arranjo"
        )
        return f"""Crie as sessões {session_start} a {session_end} de um plano musical para músico intermediário.

Contexto: plano de 32 sessões totais (16 semanas, 2x/semana).
Sessões ímpares = Violão | Sessões pares = Piano Elétrico.
Semanas {week_start}-{week_end}. Progressão desta fase:
{progressao}

Retorne APENAS JSON válido, sem markdown:
{{"sessions": [
  {{
    "session": {session_start},
    "week": {week_start},
    "instrument": "Violão",
    "topic": "Tópico específico (ex: Arpejo PIMA em Am-G-F-E)",
    "goal_description": "Objetivo da sessão em 1 frase objetiva",
    "steps": [
      {{"title": "Nome do exercício", "duration_minutes": 10, "description": "Instrução específica com BPM, repetições e tonalidade"}}
    ]
  }},
  ...sessões {session_start+1} até {session_end}...
]}}

REGRAS OBRIGATÓRIAS:
1. Gere EXATAMENTE as sessões {session_start} a {session_end} (total: {session_end - session_start + 1}).
2. Semanas: sessões {session_start}-{session_start+1} = semana {week_start}, sessões {session_start+2}-{session_start+3} = semana {week_start+1}, etc.
3. steps: entre 4 e 5 por sessão, duration_minutes somando EXATAMENTE 60.
4. step.description: instrução 100% específica. Inclua BPM, número de repetições, tonalidade.
5. instrument: EXATAMENTE "Violão" ou "Piano Elétrico".
6. PROIBIDO: frases vagas como "pratique com atenção", "explore criativamente", "toque de forma fluida".

Exemplos CORRETOS de description:
- "Arpejo P-I-M-A em Dó maior, BPM 60, 20 repetições. Polegar fixo no baixo, dedos arqueados"
- "Escala de Sol maior com 2 mãos em paralelo, 2 oitavas, BPM 80, 10 repetições seguidas"
- "Voicing Dm7-G7-Cmaj7: mão esq. fundamental+quinta, mão dir. 3ª+7ª+9ª, 15 repetições"
"""

    sessions = []
    for s_start, s_end, w_start, w_end in [(1, 16, 1, 8), (17, 32, 9, 16)]:
        raw = _generate(_batch_prompt(s_start, s_end, w_start, w_end))
        batch = _parse_json_response(raw)
        sessions.extend(batch["sessions"])

    plan = {
        "goal": "Técnica avançada em violão e piano elétrico",
        "start_date": date_str,
        "sessions_per_week": 2,
        "total_sessions": 32,
        "sessions": sessions,
    }
    MUSIC_PLAN_PATH.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return plan


def get_programming_plan(date_str: str) -> dict:
    if PROGRAMMING_PLAN_PATH.exists():
        cached = json.loads(PROGRAMMING_PLAN_PATH.read_text(encoding="utf-8"))
        if cached.get("date") == date_str:
            return cached

    prompt = f"""Gere um plano de estudo de programação de exatamente 1 hora para hoje ({date_str}).
Retorne APENAS um objeto JSON válido, sem markdown, sem explicações, sem ```json```.

Formato exato:
{{
  "date": "{date_str}",
  "topic": "Tema central da sessão (conciso, ex: RAG com LangChain)",
  "tool": "Biblioteca ou ferramenta principal (ex: LangChain, pandas, FastAPI — ou 'Nenhuma' se for conceitual)",
  "level": "Intermediário",
  "steps": [
    {{
      "title": "Nome do passo",
      "duration": "X min",
      "description": "O que fazer neste passo, de forma objetiva e prática"
    }}
  ]
}}

Requisitos:
- 3 a 5 steps, totalizando ~60 minutos
- Temas variados a cada geração: Python avançado, IA prática (RAG, embeddings, agentes LLM),
  APIs REST, design patterns, SQL, automações, Docker, algoritmos
- Alterne entre estilos: projetos hands-on ("escreva X que faz Y") e estudos estruturados (conceito → exemplo → exercício)
- Conteúdo prático, nível intermediário, executável sem IDE especial
- Português, tom técnico e direto"""

    plan = _parse_json_response(_generate(prompt))
    PROGRAMMING_PLAN_PATH.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return plan


def get_diet_plan(date_str: str, now: datetime) -> dict:
    today_iso     = now.strftime("%Y-%m-%d")
    yesterday_iso = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow_iso  = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    # Cache hit: plano já é de hoje
    if DIET_PLAN_PATH.exists():
        cached = json.loads(DIET_PLAN_PATH.read_text(encoding="utf-8"))
        if cached.get("reference_date") == today_iso:
            print("Dieta carregada do cache.")
            return cached

    month = now.month
    if month in (12, 1, 2, 3):
        estacao = "Verão"
    elif month in (4, 5, 6):
        estacao = "Outono"
    elif month in (7, 8, 9):
        estacao = "Inverno"
    else:
        estacao = "Primavera"

    # Reaproveitar dias já gerados anteriormente para manter continuidade
    # "amanhã" de ontem → "hoje" de hoje
    # "hoje" de ontem → "ontem" de hoje
    # Só gera do zero o que não existe ainda
    carried_days = {}
    if DIET_PLAN_PATH.exists():
        prev = json.loads(DIET_PLAN_PATH.read_text(encoding="utf-8"))
        prev_days = prev.get("days", {})
        if today_iso in prev_days:
            carried_days[today_iso] = prev_days[today_iso]
        if yesterday_iso in prev_days:
            carried_days[yesterday_iso] = prev_days[yesterday_iso]
        if tomorrow_iso in prev_days:
            carried_days[tomorrow_iso] = prev_days[tomorrow_iso]

    days_to_generate = [d for d in [yesterday_iso, today_iso, tomorrow_iso] if d not in carried_days]

    if days_to_generate:
        carried_json = json.dumps(carried_days, ensure_ascii=False) if carried_days else "{}"
        prompt = f"""Monte refeições para os seguintes dias: {', '.join(days_to_generate)}.
Cada dia: 2800kcal, alimentos tipicamente brasileiros, saudáveis, custo barato ou médio.
5 refeições por dia. Equilíbrio para disposição, saúde e hipertrofia muscular.
Varie os alimentos entre os dias e em relação aos dias já existentes abaixo.
Use frutas e legumes da estação atual no Brasil ({estacao}).

Dias já definidos (NÃO alterar, apenas para evitar repetição):
{carried_json}

Retorne APENAS JSON válido com os dias solicitados:
{{
  {', '.join(f'"{d}": {{"date": "{d}", "total_kcal": 2800, "meals": [{{"name": "Café da Manhã", "time": "07:00", "kcal": 550, "items": [{{"food": "...", "qty": "..."}}]}}, {{"name": "Lanche da Manhã", "time": "10:00", "kcal": 300, "items": [...]}}, {{"name": "Almoço", "time": "12:30", "kcal": 800, "items": [...]}}, {{"name": "Lanche da Tarde", "time": "16:00", "kcal": 350, "items": [...]}}, {{"name": "Jantar", "time": "19:30", "kcal": 800, "items": [...]}}]}}' for d in days_to_generate)}
}}
Nomes fixos das refeições: "Café da Manhã", "Lanche da Manhã", "Almoço", "Lanche da Tarde", "Jantar"."""

        new_days = _parse_json_response(_generate(prompt))
        carried_days.update(new_days)

    plan = {
        "reference_date": today_iso,
        "days": {d: carried_days[d] for d in [yesterday_iso, today_iso, tomorrow_iso] if d in carried_days},
    }
    DIET_PLAN_PATH.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Dieta gerada.")
    return plan


def get_album_suggestion(taste_profile: dict, date_str: str) -> dict:
    """
    Gera a sugestão de álbum do dia usando o perfil Spotify + Gemini.
    - 75% dos dias: álbum novo (não está nos saved albums)
    - 25% dos dias: revisita um álbum da biblioteca
    Decisão determinística por data (hash MD5).
    Cacheado em album_suggestion.json.
    """
    import hashlib

    if ALBUM_SUGGESTION_PATH.exists():
        cached = json.loads(ALBUM_SUGGESTION_PATH.read_text(encoding="utf-8"))
        if cached.get("date") == date_str:
            return cached

    day_hash = int(hashlib.md5(date_str.encode()).hexdigest(), 16) % 100
    is_new   = day_hash < 75

    saved_albums  = taste_profile.get("saved_albums", [])
    top_genres    = taste_profile.get("top_genres", [])
    top_artists   = taste_profile.get("top_artists", [])
    top_tracks    = taste_profile.get("top_tracks", [])

    # Carrega histórico de álbuns já sugeridos
    history: list[dict] = []
    if ALBUM_HISTORY_PATH.exists():
        try:
            history = json.loads(ALBUM_HISTORY_PATH.read_text(encoding="utf-8"))
        except Exception:
            history = []

    if is_new:
        saved_list = "\n".join(
            f'- {a["album"]} — {a["artist"]}' for a in saved_albums[:20]
        )
        history_list = "\n".join(
            f'- {h["album"]} — {h["artist"]}' for h in history
        )
        prompt = f"""Sugira UM álbum musical para Flávio ouvir hoje.

Perfil musical (Spotify):
- Gêneros favoritos: {', '.join(top_genres) or 'variado'}
- Artistas favoritos: {', '.join(top_artists) or 'variado'}
- Músicas favoritas: {', '.join(top_tracks[:5]) or 'variado'}

Álbuns que Flávio JÁ TEM na biblioteca (NÃO sugerir nenhum destes):
{saved_list or '(nenhum salvo ainda)'}

Álbuns que JÁ FORAM sugeridos nos últimos dias (NÃO repetir nenhum destes):
{history_list or '(nenhum ainda)'}

Critérios:
- Deve ser um álbum que Flávio provavelmente NÃO conhece
- Estilo coerente com o gosto musical acima
- Pode ser clássico consagrado ou lançamento recente
- Álbum completo (não EP ou single)

Retorne APENAS JSON válido, sem markdown:
{{
  "album": "Nome do álbum",
  "artist": "Nome do artista",
  "year": "Ano de lançamento",
  "genre": "Gênero principal",
  "why": "2-3 frases explicando por que combina com o gosto do Flávio e vale ouvir hoje"
}}"""

        data       = _parse_json_response(_generate(prompt))
        album_info = search_album(data.get("album", ""), data.get("artist", ""))
        suggestion = {
            "date":       date_str,
            "type":       "new",
            "album":      data.get("album", ""),
            "artist":     data.get("artist", ""),
            "year":       data.get("year", ""),
            "genre":      data.get("genre", ""),
            "why":        data.get("why", ""),
            "cover_url":  album_info["cover_url"],
            "spotify_id": album_info["spotify_id"],
        }

    else:
        if not saved_albums:
            return {}

        album = saved_albums[day_hash % len(saved_albums)]
        prompt = f"""Flávio vai revisitar hoje o álbum "{album['album']}" de {album['artist']} ({album.get('year', '')}).

Escreva 2-3 frases motivando a escuta deste álbum hoje, mencionando o que o torna especial.
Tom: caloroso, entusiasmado, pessoal.

Retorne APENAS JSON válido, sem markdown:
{{
  "why": "2-3 frases motivando a revisita"
}}"""

        data = _parse_json_response(_generate(prompt))
        suggestion = {
            "date":       date_str,
            "type":       "revisit",
            "album":      album["album"],
            "artist":     album["artist"],
            "year":       album.get("year", ""),
            "genre":      "",
            "why":        data.get("why", ""),
            "cover_url":  album.get("cover_url"),
            "spotify_id": album.get("spotify_id"),
        }

    ALBUM_SUGGESTION_PATH.write_text(
        json.dumps(suggestion, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Adiciona ao histórico se ainda não estiver registrado nesta data
    if not any(h.get("date") == date_str for h in history):
        history.append({"date": date_str, "album": suggestion["album"], "artist": suggestion["artist"]})
        ALBUM_HISTORY_PATH.write_text(
            json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    return suggestion


def get_random_psalm(date_str: str) -> dict | None:
    if PSALM_OF_DAY_PATH.exists():
        cached = json.loads(PSALM_OF_DAY_PATH.read_text(encoding="utf-8"))
        if cached.get("date") == date_str:
            return cached

    h = int(hashlib.md5(date_str.encode()).hexdigest(), 16)
    num = h % 150 + 1

    try:
        import requests
        resp = requests.get(
            f"https://bible-api.com/salmos+{num}?translation=almeida",
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        raw_text = data.get("text", "").strip()
        # Separa versículos por quebra de linha (a API usa \xa0 \xa0 como separador)
        text = raw_text.replace("\xa0 \xa0", "\n").replace("\xa0", " ").strip()
        result = {
            "date": date_str,
            "number": num,
            "text": text,
            "reference": data.get("reference", f"Salmos {num}"),
        }
        PSALM_OF_DAY_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result
    except Exception as e:
        print(f"[psalm] Erro ao buscar salmo: {e}")
        return None


def generate_site(
    weather: dict, activities: list, day_name: str, date_str: str, workout, weekday: int,
    reading_plan=None, stretching_plan=None, programming_plan=None, running_plan=None, music_plan=None,
    diet_plan=None, album_suggestion=None, psalm_of_day=None,
) -> None:
    """
    Gera docs/index.html e, se houver treino no dia, docs/treino.html.
    """
    env = Environment(loader=FileSystemLoader("templates"))
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)

    now_brt = datetime.now(tz=BRT)
    generated_at = now_brt.strftime("%H:%M")

    html = env.get_template("daily.html").render(
        date=date_str,
        day_name=day_name,
        weather=weather,
        activities=activities,
        workout=workout,
        weekday=weekday,
        generated_at=generated_at,
        reading_plan=reading_plan,
        stretching_plan=stretching_plan,
        programming_plan=programming_plan,
        running_plan=running_plan,
        music_plan=music_plan,
        diet_plan=diet_plan,
        album_suggestion=album_suggestion,
        psalm_of_day=psalm_of_day,
    )
    (docs_dir / "index.html").write_text(html, encoding="utf-8")
    print(f"Site gerado em {docs_dir / 'index.html'}")

    if workout:
        treino_html = env.get_template("treino.html").render(
            date=date_str,
            day_name=day_name,
            workout=workout,
            generated_at=generated_at,
        )
        (docs_dir / "treino.html").write_text(treino_html, encoding="utf-8")
        print(f"Treino gerado em {docs_dir / 'treino.html'}")

    if reading_plan:
        leitura_html = env.get_template("leitura.html").render(
            date=date_str, day_name=day_name,
            reading_plan=reading_plan, generated_at=generated_at,
        )
        (docs_dir / "leitura.html").write_text(leitura_html, encoding="utf-8")
        print(f"Leitura gerada em {docs_dir / 'leitura.html'}")

    if stretching_plan:
        along_html = env.get_template("alongamento.html").render(
            date=date_str, day_name=day_name,
            stretching_plan=stretching_plan, generated_at=generated_at,
        )
        (docs_dir / "alongamento.html").write_text(along_html, encoding="utf-8")
        print(f"Alongamento gerado em {docs_dir / 'alongamento.html'}")

    if programming_plan:
        prog_html = env.get_template("programacao.html").render(
            date=date_str, day_name=day_name,
            programming_plan=programming_plan, generated_at=generated_at,
        )
        (docs_dir / "programacao.html").write_text(prog_html, encoding="utf-8")
        print(f"Programação gerada em {docs_dir / 'programacao.html'}")

    if running_plan:
        corrida_html = env.get_template("corrida.html").render(
            date=date_str, day_name=day_name,
            running_plan=running_plan, generated_at=generated_at,
        )
        (docs_dir / "corrida.html").write_text(corrida_html, encoding="utf-8")
        print(f"Corrida gerada em {docs_dir / 'corrida.html'}")

    if music_plan:
        musica_html = env.get_template("musica.html").render(
            date=date_str, day_name=day_name,
            music_plan=music_plan, generated_at=generated_at,
        )
        (docs_dir / "musica.html").write_text(musica_html, encoding="utf-8")
        print(f"Música gerada em {docs_dir / 'musica.html'}")


def mock_weather(manha: str, tarde: str, noite: str) -> dict:
    """Monta um dicionário de clima falso para testes visuais."""
    def period(cond):
        return {"temp_min": 18, "temp_max": 24, "condition": cond, "rain_prob": 0}
    return {"manha": period(manha), "tarde": period(tarde), "noite": period(noite)}


def main():
    parser = argparse.ArgumentParser(description="Daily Organizer")
    parser.add_argument("--manha", metavar="COND", help='Condição da manhã para teste (ex: "Pancadas fracas")')
    parser.add_argument("--tarde", metavar="COND", help='Condição da tarde para teste')
    parser.add_argument("--noite", metavar="COND", help='Condição da noite para teste')
    parser.add_argument("--dia", metavar="N", type=int, choices=range(7),
                        help="Simula um dia da semana: 0=Segunda, 1=Terça, 2=Quarta, 3=Quinta, 4=Sexta, 5=Sábado, 6=Domingo")
    args = parser.parse_args()

    now = datetime.now(tz=BRT)
    weekday = args.dia if args.dia is not None else now.weekday()
    day_name = DAY_NAMES[weekday]
    date_str = now.strftime("%d/%m/%Y")

    print(f"--- Daily Organizer ---")
    if args.dia is not None:
        print(f"[TESTE] Simulando: {day_name}")
    print(f"Data: {day_name}, {date_str}")

    # Modo teste: clima passado via CLI ou dia simulado — sem API e sem e-mail
    if args.manha or args.tarde or args.noite or args.dia is not None:
        manha = args.manha or "Céu limpo"
        tarde = args.tarde or "Céu limpo"
        noite = args.noite or "Céu limpo"
        print(f"[TESTE] Manhã: {manha} | Tarde: {tarde} | Noite: {noite}")
        activities = get_today_schedule(weekday)
        workout = get_today_workout(weekday)
        has_reading = any(a["name"] == "ler" for a in activities)
        try:
            reading_plan = get_reading_plan() if has_reading else None
        except Exception as e:
            print(f"Aviso: plano de leitura indisponível ({e}). Leitura desativada.")
            reading_plan = None
        has_stretching = any(a["name"] == "alongar" for a in activities)
        try:
            stretching_plan = get_stretching_plan(date_str, weekday) if has_stretching else None
        except Exception as e:
            print(f"Aviso: plano de alongamento indisponível ({e}). Alongamento desativado.")
            stretching_plan = None
        has_programming = any(a["name"] in ("programação", "programar") for a in activities)
        try:
            programming_plan = get_programming_plan(date_str) if has_programming else None
        except Exception as e:
            print(f"Aviso: plano de programação indisponível ({e}). Programação desativada.")
            programming_plan = None
        has_running = any(a["name"] == "correr" for a in activities)
        try:
            running_plan = get_running_plan(date_str) if has_running else None
        except Exception as e:
            print(f"Aviso: plano de corrida indisponível ({e}). Corrida desativada.")
            running_plan = None
        has_music = any(a["name"] == "musica" for a in activities)
        try:
            music_plan = get_music_plan(date_str) if has_music else None
        except Exception as e:
            print(f"Aviso: plano de música indisponível ({e}). Música desativada.")
            music_plan = None
        try:
            diet_plan = get_diet_plan(date_str, now)
        except Exception as e:
            print(f"Aviso: plano de dieta indisponível ({e}). Dieta desativada.")
            diet_plan = None
        try:
            taste_profile   = get_spotify_taste_profile()
            album_suggestion = get_album_suggestion(taste_profile, date_str)
        except Exception as e:
            print(f"Aviso: sugestão de álbum indisponível ({e}). Seção desativada.")
            album_suggestion = None
        try:
            psalm_of_day = get_random_psalm(date_str)
        except Exception as e:
            print(f"Aviso: salmo indisponível ({e}). Seção desativada.")
            psalm_of_day = None
        generate_site(mock_weather(manha, tarde, noite), activities, day_name, date_str, workout, weekday,
                      reading_plan=reading_plan, stretching_plan=stretching_plan, programming_plan=programming_plan,
                      running_plan=running_plan, music_plan=music_plan, diet_plan=diet_plan,
                      album_suggestion=album_suggestion, psalm_of_day=psalm_of_day)
        print("HTML gerado. Execute: start docs\\index.html")
        return

    # Passo 1: previsão do tempo
    print("Buscando previsão do tempo...")
    weather = fetch_weather()
    print(f"  Manhã: {weather['manha']['condition']} {weather['manha']['temp_min']}–{weather['manha']['temp_max']}°C")

    # Passo 2: atividades do dia
    activities = get_today_schedule(weekday)
    workout = get_today_workout(weekday)
    print(f"Atividades: {', '.join(a['name'] for a in activities)}")
    has_reading = any(a["name"] == "ler" for a in activities)
    try:
        reading_plan = get_reading_plan() if has_reading else None
    except Exception as e:
        print(f"Aviso: plano de leitura indisponível ({e}). Leitura desativada.")
        reading_plan = None
    has_stretching = any(a["name"] == "alongar" for a in activities)
    try:
        stretching_plan = get_stretching_plan(date_str, weekday) if has_stretching else None
    except Exception as e:
        print(f"Aviso: plano de alongamento indisponível ({e}). Alongamento desativado.")
        stretching_plan = None
    has_programming = any(a["name"] in ("programação", "programar") for a in activities)
    try:
        programming_plan = get_programming_plan(date_str) if has_programming else None
    except Exception as e:
        print(f"Aviso: plano de programação indisponível ({e}). Programação desativada.")
        programming_plan = None
    has_running = any(a["name"] == "correr" for a in activities)
    try:
        running_plan = get_running_plan(date_str) if has_running else None
    except Exception as e:
        print(f"Aviso: plano de corrida indisponível ({e}). Corrida desativada.")
        running_plan = None
    has_music = any(a["name"] == "musica" for a in activities)
    try:
        music_plan = get_music_plan(date_str) if has_music else None
    except Exception as e:
        print(f"Aviso: plano de música indisponível ({e}). Música desativada.")
        music_plan = None
    try:
        diet_plan = get_diet_plan(date_str, now)
    except Exception as e:
        print(f"Aviso: plano de dieta indisponível ({e}). Dieta desativada.")
        diet_plan = None
    try:
        print("Buscando perfil Spotify e gerando sugestão de álbum...")
        taste_profile    = get_spotify_taste_profile()
        album_suggestion = get_album_suggestion(taste_profile, date_str)
    except Exception as e:
        print(f"Aviso: sugestão de álbum indisponível ({e}). Seção desativada.")
        album_suggestion = None
    try:
        psalm_of_day = get_random_psalm(date_str)
    except Exception as e:
        print(f"Aviso: salmo indisponível ({e}). Seção desativada.")
        psalm_of_day = None

    # Passo 3: gerar o site
    print("Gerando site HTML...")
    generate_site(weather, activities, day_name, date_str, workout, weekday,
                  reading_plan=reading_plan, stretching_plan=stretching_plan, programming_plan=programming_plan,
                  running_plan=running_plan, music_plan=music_plan, diet_plan=diet_plan,
                  album_suggestion=album_suggestion, psalm_of_day=psalm_of_day)

    # Passo 4: enviar e-mail
    # URL onde o GitHub Pages vai servir o site
    repo_owner = os.environ.get("GITHUB_REPO_OWNER", "seu-usuario")
    repo_name = os.environ.get("GITHUB_REPO_NAME", "daily-organizer")
    site_url = f"https://{repo_owner}.github.io/{repo_name}/"

    # Gera a mensagem: tenta com Claude, cai no fallback se houver erro
    print("Gerando mensagem com Claude...")
    try:
        message = generate_message_with_llm(day_name, date_str, weather, activities)
        print(f"Mensagem (Claude): {message}")
    except Exception as e:
        print(f"Aviso: API do Claude indisponível ({e}). Usando fallback.")
        message = build_daily_message(day_name, date_str, weather, activities)
        print(f"Mensagem (fallback): {message}")

    print("Enviando e-mail...")
    send_daily_email(
        site_url=site_url,
        day_name=day_name,
        date=date_str,
        message=message,
    )

    print("Tudo pronto!")


# Este bloco garante que main() só rode quando você executar o arquivo diretamente
# (python main.py), não quando outro módulo importar este arquivo.
if __name__ == "__main__":
    main()
