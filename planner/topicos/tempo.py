"""Folha do Tempo — Open-Meteo, sem LLM.

Cabe mais que três temperaturas: a previsão hora a hora dividida em manhã, tarde e
noite, o vento, e a melhor janela para treinar ao ar livre — que é a decisão real que
ele toma olhando a previsão. Alerta quando houver chuva prevista no horário do treino.
"""

import requests

LATITUDE, LONGITUDE = -27.6, -48.6          # São José/SC, bairro Campinas
HORARIO_TREINO = (17, 19)                   # rotina dele: academia às 17:00
JANELA_AR_LIVRE = (6, 20)                   # onde faz sentido procurar horário de treino

WMO = {
    0: "Céu limpo", 1: "Principalmente limpo", 2: "Parcialmente nublado", 3: "Nublado",
    45: "Neblina", 48: "Neblina com gelo",
    51: "Garoa fraca", 53: "Garoa moderada", 55: "Garoa forte",
    61: "Chuva fraca", 63: "Chuva moderada", 65: "Chuva forte",
    71: "Neve fraca", 73: "Neve moderada", 75: "Neve forte",
    80: "Pancadas fracas", 81: "Pancadas moderadas", 82: "Pancadas fortes",
    95: "Tempestade", 96: "Tempestade com granizo", 99: "Tempestade forte",
}

PERIODOS = [("Manhã", 6, 12), ("Tarde", 12, 18), ("Noite", 18, 24)]


def _horas(dados: dict) -> list[dict]:
    h = dados["hourly"]
    return [
        {
            "hora": int(t.split("T")[1][:2]),
            "temp": h["temperature_2m"][i],
            "cond": WMO.get(h["weathercode"][i], "Desconhecido"),
            "chuva": h["precipitation_probability"][i],
            "vento": h["wind_speed_10m"][i],
        }
        for i, t in enumerate(h["time"])
    ]


def _resumo(horas: list[dict]) -> dict:
    conds = [x["cond"] for x in horas]
    return {
        "temp_min": round(min(x["temp"] for x in horas)),
        "temp_max": round(max(x["temp"] for x in horas)),
        "cond": max(set(conds), key=conds.count),
        "chuva": max(x["chuva"] for x in horas),
        "vento": round(max(x["vento"] for x in horas)),
    }


def _melhor_janela(horas: list[dict]) -> dict | None:
    """Duas horas seguidas com a menor chance de chuva; empate desempata pelo vento."""
    candidatas = [x for x in horas if JANELA_AR_LIVRE[0] <= x["hora"] < JANELA_AR_LIVRE[1]]
    if len(candidatas) < 2:
        return None
    pares = [
        {
            "inicio": a["hora"], "fim": a["hora"] + 2,
            "chuva": max(a["chuva"], b["chuva"]),
            "vento": round(max(a["vento"], b["vento"])),
            "temp": round((a["temp"] + b["temp"]) / 2),
            "cond": a["cond"],
        }
        for a, b in zip(candidatas, candidatas[1:]) if b["hora"] == a["hora"] + 1
    ]
    return min(pares, key=lambda p: (p["chuva"], p["vento"])) if pares else None


def _alerta_treino(horas: list[dict]) -> str | None:
    no_treino = [x for x in horas if HORARIO_TREINO[0] <= x["hora"] < HORARIO_TREINO[1]]
    pico = max((x["chuva"] for x in no_treino), default=0)
    if pico >= 40:
        return f"{pico}% de chance de chuva entre {HORARIO_TREINO[0]}h e {HORARIO_TREINO[1]}h."
    return None


def blocos() -> list[str]:
    """Os blocos da folha do Tempo, em HTML. Cada bloco é indivisível."""
    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": LATITUDE, "longitude": LONGITUDE,
            "hourly": "temperature_2m,weathercode,precipitation_probability,wind_speed_10m",
            "timezone": "America/Sao_Paulo", "forecast_days": 1,
        },
        timeout=15,
    )
    resp.raise_for_status()
    horas = _horas(resp.json())

    saida = []
    for nome, ini, fim in PERIODOS:
        faixa = [x for x in horas if ini <= x["hora"] < fim]
        if not faixa:
            continue
        r = _resumo(faixa)
        linhas = "".join(
            f'<tr><td>{x["hora"]:02d}h</td><td>{round(x["temp"])}°</td>'
            f'<td>{x["chuva"]}%</td><td>{x["cond"]}</td></tr>'
            for x in faixa
        )
        saida.append(
            f'<div class="bloco"><h4>{nome}</h4>'
            f'<p class="destaque">{r["temp_min"]}° a {r["temp_max"]}° · {r["cond"]}</p>'
            f'<p class="miudo">chuva até {r["chuva"]}% · vento até {r["vento"]} km/h</p>'
            f'<table class="horas">{linhas}</table></div>'
        )

    janela = _melhor_janela(horas)
    if janela:
        saida.append(
            f'<div class="bloco"><h4>Melhor janela ao ar livre</h4>'
            f'<p class="destaque">{janela["inicio"]}h às {janela["fim"]}h</p>'
            f'<p>{janela["temp"]}° · {janela["cond"]} · chuva {janela["chuva"]}% · '
            f'vento {janela["vento"]} km/h</p></div>'
        )

    alerta = _alerta_treino(horas)
    if alerta:
        saida.append(f'<div class="bloco alerta"><h4>Atenção no horário do treino</h4><p>{alerta}</p></div>')

    return saida
