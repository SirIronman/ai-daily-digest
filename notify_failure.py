"""
Failure Notification Agent
==========================
Запускается через GitHub Actions, когда основной workflow упал.
Отправляет plain-text email с указанием на логи.
"""

import os
import sys
import smtplib
from datetime import datetime
from email.mime.text import MIMEText

GMAIL_ADDRESS      = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
TO_EMAIL           = os.environ["TO_EMAIL"]
WORKFLOW_NAME      = os.environ.get("WORKFLOW_NAME", "AI Digest workflow")
WORKFLOW_URL       = os.environ.get("WORKFLOW_URL", "(URL не передан)")


def send_alert():
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    body = f"""Workflow упал и дайджест сегодня не отправлен.

Workflow: {WORKFLOW_NAME}
Время: {now} МСК
Логи: {WORKFLOW_URL}

Типичные причины:
- Anthropic API: баланс закончился или ключ отозван
- Gmail SMTP: App Password сменился или 2FA отключилась
- Сеть/rate limit на одном из источников: можно перезапустить вручную

Открой логи по ссылке выше — там точная причина в шаге Run digest agent.
"""
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"⚠️ {WORKFLOW_NAME} — ОШИБКА · {now} МСК"
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = TO_EMAIL

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, TO_EMAIL, msg.as_string())
    print(f"[OK] Alert email отправлен на {TO_EMAIL}")


if __name__ == "__main__":
    try:
        send_alert()
    except Exception as e:
        print(f"[ERROR] Не удалось отправить alert: {e}", file=sys.stderr)
        sys.exit(1)
