# email_sender.py
# Envia o e-mail diário via Gmail SMTP.
#
# SMTP = Simple Mail Transfer Protocol, o protocolo padrão de envio de e-mail.
# Porta 587 com TLS = conexão criptografada (segura).
# As credenciais vêm SEMPRE de variáveis de ambiente, nunca hardcoded no código.

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_daily_email(
    site_url: str,
    day_name: str,
    date: str,
    message: str,
) -> None:
    """
    Envia o e-mail de bom dia com link para o site personalizado do dia.

    Parâmetros:
    - site_url: URL do GitHub Pages
    - day_name: Nome do dia em português (ex: "Segunda-feira")
    - date: Data formatada (ex: "09/03/2026")
    - message: Texto dinâmico gerado pelo build_daily_message()
    """
    # Lê as credenciais das variáveis de ambiente.
    # os.environ["CHAVE"] lança erro se a variável não existir — isso é intencional:
    # queremos saber imediatamente se algo está mal configurado.
    gmail_user = os.environ["GMAIL_USER"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]
    gmail_to = os.environ["GMAIL_TO"]

    # MIMEMultipart("alternative") permite enviar HTML com fallback em texto puro
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Resumo {day_name} {date}"
    msg["From"] = gmail_user
    msg["To"] = gmail_to

    html_body = f"""
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                 max-width: 520px; margin: 0 auto; padding: 24px; background: #f8fafc; color: #1e293b;">

        <!-- Cabeçalho -->
        <div style="background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%);
                    border-radius: 14px; padding: 16px 20px; margin-bottom: 20px;
                    display: flex; align-items: center; justify-content: space-between;">
            <div>
                <p style="color: rgba(255,255,255,0.85); font-size: 13px; font-weight: 700;
                          margin: 0 0 2px;">
                    ☕ Bom dia, Flávio!
                </p>
                <p style="color: #ffffff; font-size: 20px; font-weight: 800; margin: 0;">
                    {day_name}, <span style="font-weight: 400;">{date}</span>
                </p>
            </div>
        </div>

        <!-- Mensagem do dia -->
        <div style="background: #ffffff; border-radius: 12px; padding: 22px 24px;
                    margin-bottom: 16px; border-left: 4px solid #2563eb;
                    box-shadow: 0 1px 4px rgba(0,0,0,0.06);">
            <p style="font-size: 11px; font-weight: 700; color: #2563eb;
                      letter-spacing: 1.2px; text-transform: uppercase; margin: 0 0 10px;">
                📓 Resumo do dia
            </p>
            <p style="font-size: 15px; line-height: 1.75; color: #1e293b; margin: 0;">
                {message}
            </p>
        </div>

        <!-- CTA -->
        <div style="text-align: center; margin: 24px 0 20px;">
            <a href="{site_url}"
               style="display: inline-block; background: #2563eb; color: #ffffff;
                      padding: 13px 28px; border-radius: 10px; text-decoration: none;
                      font-weight: 700; font-size: 15px; letter-spacing: 0.3px;">
                Ver dia completo
            </a>
        </div>

        <!-- Rodapé -->
        <p style="color: #94a3b8; font-size: 11px; text-align: center; margin-top: 24px;">
            Gerado automaticamente pelo <strong style="color: #64748b;">Daily Organizer</strong>.
        </p>

    </body>
    </html>
    """

    msg.attach(MIMEText(html_body, "html"))

    # Contexto "with" garante que a conexão seja fechada mesmo se der erro
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()                           # Ativa criptografia TLS
        server.login(gmail_user, gmail_password)    # Login com App Password
        server.sendmail(gmail_user, gmail_to, msg.as_string())

    print(f"E-mail enviado para {gmail_to}")
