# main.py
# Ponto de entrada do sistema — o script que você executa.
# Ele orquestra (coordena) os outros módulos em sequência:
#   1. Busca a previsão do tempo
#   2. Determina as atividades do dia
#   3. Gera o site HTML
#   4. Envia o e-mail

import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Garante UTF-8 no stdout/stderr (necessário no Windows com charmap padrão)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import google.generativeai as genai                 # SDK da API do Gemini
from dotenv import load_dotenv                      # Lê o arquivo .env para variáveis de ambiente
from jinja2 import Environment, FileSystemLoader    # Motor de templates HTML

from weather import fetch_weather
from schedule import get_today_schedule, DAY_NAMES
from email_sender import send_daily_email

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

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    return response.text.strip()


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


def generate_site(weather: dict, activities: list, day_name: str, date_str: str) -> None:
    """
    Gera o arquivo docs/index.html usando o template Jinja2.

    Jinja2 funciona como um "molde": você passa variáveis Python e ele preenche
    os espaços {{ variavel }} no HTML, gerando um arquivo final estático.
    """
    # Configura o Jinja2 para procurar templates na pasta 'templates/'
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("daily.html")

    now_brt = datetime.now(tz=BRT)

    html = template.render(
        date=date_str,
        day_name=day_name,
        weather=weather,
        activities=activities,
        generated_at=now_brt.strftime("%H:%M"),
    )

    # Path("docs") cria um objeto que representa a pasta docs/
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)  # Cria a pasta se não existir

    output_path = docs_dir / "index.html"
    output_path.write_text(html, encoding="utf-8")
    print(f"Site gerado em {output_path}")


def main():
    now = datetime.now(tz=BRT)
    weekday = now.weekday()   # 0 = segunda-feira, 6 = domingo
    day_name = DAY_NAMES[weekday]
    date_str = now.strftime("%d/%m/%Y")

    print(f"--- Daily Organizer ---")
    print(f"Data: {day_name}, {date_str}")

    # Passo 1: previsão do tempo
    print("Buscando previsão do tempo...")
    weather = fetch_weather()
    print(f"  Manhã: {weather['manha']['condition']} {weather['manha']['temp_min']}–{weather['manha']['temp_max']}°C")

    # Passo 2: atividades do dia
    activities = get_today_schedule(weekday)
    print(f"Atividades: {', '.join(a['name'] for a in activities)}")

    # Passo 3: gerar o site
    print("Gerando site HTML...")
    generate_site(weather, activities, day_name, date_str)

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
