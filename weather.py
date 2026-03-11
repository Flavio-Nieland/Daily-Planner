# weather.py
# Consulta a API gratuita Open-Meteo para obter a previsão do tempo.
# Não requer chave de API — pode usar direto!
#
# Conceito de API: é como um "garçom". Você faz um pedido (requisição HTTP GET)
# com parâmetros específicos, e ele traz os dados (resposta JSON) do servidor.

import requests

# Coordenadas de São José/SC, bairro Campinas
LATITUDE = -27.6
LONGITUDE = -48.6

# Mapeamento dos códigos WMO (padrão meteorológico) para texto em português.
# Fonte: https://open-meteo.com/en/docs#weathervariables
WMO_CODES = {
    0: "Céu limpo",
    1: "Principalmente limpo",
    2: "Parcialmente nublado",
    3: "Nublado",
    45: "Neblina",
    48: "Neblina com gelo",
    51: "Garoa fraca",
    53: "Garoa moderada",
    55: "Garoa forte",
    61: "Chuva fraca",
    63: "Chuva moderada",
    65: "Chuva forte",
    71: "Neve fraca",
    73: "Neve moderada",
    75: "Neve forte",
    80: "Pancadas fracas",
    81: "Pancadas moderadas",
    82: "Pancadas fortes",
    95: "Tempestade",
    96: "Tempestade com granizo",
    99: "Tempestade forte",
}


def fetch_weather() -> dict:
    """
    Busca a previsão do tempo horária para hoje e agrupa em 3 períodos.

    Retorna um dicionário com as chaves 'manha', 'tarde' e 'noite'.
    Cada período contém: temp_min, temp_max, condition, rain_prob.

    Exemplo:
    {
        "manha": {"temp_min": 18.0, "temp_max": 22.5, "condition": "Parcialmente nublado", "rain_prob": 10},
        "tarde": {...},
        "noite": {...},
    }
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": "temperature_2m,weathercode,precipitation_probability",
        "timezone": "America/Sao_Paulo",
        "forecast_days": 1,  # Apenas hoje
    }

    # timeout=10 garante que o script não trava se a API demorar
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()  # Lança erro se status != 200 (ex: 404, 500)
    data = response.json()

    hours = data["hourly"]["time"]                              # ["2024-01-15T00:00", ...]
    temps = data["hourly"]["temperature_2m"]                    # [18.2, 17.9, ...]
    codes = data["hourly"]["weathercode"]                       # [0, 1, 2, ...]
    rain_probs = data["hourly"]["precipitation_probability"]    # [0, 10, 20, ...]

    def summarize_period(start_hour: int, end_hour: int) -> dict:
        """Resume temperatura e condição para um período (ex: 6 a 12)."""
        # "T" separa data e hora: "2024-01-15T08:00" → hora = "08"
        period_data = [
            {"temp": temps[i], "code": codes[i], "rain_prob": rain_probs[i]}
            for i in range(len(hours))
            if start_hour <= int(hours[i].split("T")[1].split(":")[0]) < end_hour
        ]

        if not period_data:
            return {"temp_min": "-", "temp_max": "-", "condition": "Sem dados", "rain_prob": 0}

        temp_min = round(min(d["temp"] for d in period_data), 1)
        temp_max = round(max(d["temp"] for d in period_data), 1)
        rain_prob = max(d["rain_prob"] for d in period_data)

        # Condição mais frequente no período
        all_codes = [d["code"] for d in period_data]
        most_common_code = max(set(all_codes), key=all_codes.count)

        return {
            "temp_min": temp_min,
            "temp_max": temp_max,
            "condition": WMO_CODES.get(most_common_code, "Desconhecido"),
            "rain_prob": rain_prob,
        }

    return {
        "manha": summarize_period(6, 12),
        "tarde": summarize_period(12, 18),
        "noite": summarize_period(18, 24),
    }
