"""
Weekly Meta Digest Agent
=========================
Запускается каждую пятницу в 06:30 МСК.
Читает дайджесты текущей рабочей недели из digests/, делает мета-анализ
через Claude Opus 4.8, отправляет результат email.
"""

import os
import sys
import smtplib
import requests
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

CLAUDE_API_KEY     = os.environ["CLAUDE_API_KEY"]
GMAIL_ADDRESS      = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
TO_EMAIL           = os.environ["TO_EMAIL"]


META_SYSTEM_PROMPT = """Ты аналитик-стратег недельного мета-обзора AI/HPC/DC/OCP трендов для архитектора AI Distribution Platform.

ВХОД: дайджесты за прошедшую рабочую неделю (пн-пт). Каждый содержит 4 темы с фактами, прогнозами, открытыми вопросами и backlog-items.

ЗАДАЧА: НЕ пересказывать новости. Найти МЕТА-ПАТТЕРНЫ.

ФОРМАТ ВЫХОДА — строго эта структура:

# НЕДЕЛЬНЫЙ МЕТА-ОБЗОР · [неделя ISO, диапазон дат]

## 1. ПОВТОРЯЮЩИЕСЯ ТЕМЫ
Какие вендоры, технологии или категории появлялись несколько раз. Что это говорит о смещении фокуса рынка?
Формат: «[Тема]: появлялась N раз ([дни]) — [интерпретация]»
Минимум 2, максимум 4 пункта.

## 2. CROSS-SOURCE СИГНАЛЫ
Что одновременно подтверждалось РАЗНЫМИ типами источников (вендорские пресс-релизы + отраслевые медиа + научные бумаги)? Подтверждённые двумя+ типами источников сигналы важнее единичных.
Минимум 1, максимум 3 пункта.

## 3. СМЕЩЕНИЕ ТОНА И ФРЕЙМИНГА
По одной теме — поменялся ли акцент за неделю? От гипотезы к подтверждению? От технической дискуссии к коммерческой? От «будет» к «уже есть»?
Если значимых смещений нет — указать «без значимых смещений на этой неделе».

## 4. ТРИ КЛЮЧЕВЫЕ ГИПОТЕЗЫ НЕДЕЛИ
Сформулируй три гипотезы для проверки или обсуждения с командой. Каждая:
- Формулируется как утверждение, не вопрос
- Привязана к компоненту платформы или сегменту клиентов (VAR / интегратор / B2G)
- Содержит проверяемое предсказание на 4-12 недель
- Указано, что подтвердит или опровергнет

Формат каждой:
ГИПОТЕЗА: [утверждение]
КОМПОНЕНТ: [компонент платформы или сегмент]
ПРЕДСКАЗАНИЕ (4-12 нед): [что должно произойти]
ПОДТВЕРДИТ: [конкретный сигнал]
ОПРОВЕРГНЕТ: [конкретный сигнал]

## 5. АГРЕГАТ BACKLOG-ITEMS НЕДЕЛИ
Все backlog-items недели, сгруппированные по затронутым компонентам. Показывает нагрузку на каждый компонент — где конкуренция за внимание.

Формат:
### BOM-генератор
- [item 1 из дайджеста дд.мм]
- ...
### Граф совместимости
- ...
### TCO-калькулятор
- ...
### Генератор документации
- ...
### B2G-направление
- ...

(Компоненты без backlog-items в эту неделю не выводи.)

## 6. АНТИПАТТЕРНЫ
Что НЕ появлялось, но должно было — пробелы покрытия. Если есть основания думать, что что-то происходит, но мы не поймали — отметить.
Формат: «Не освещено: [тема] — ожидалось бы потому, что [причина]»
Если пробелов нет — «существенных пробелов не выявлено».

ТРЕБОВАНИЯ К СТИЛЮ:
- Тон: архитектор-стратег. Спокойная констатация. Не маркетолог.
- Язык русский. Аббревиатуры в оригинале.
- Объём 600-900 слов.
- Без AI-маркеров и клише."""


def get_week_digests() -> list:
    """Получить все дайджесты текущей ISO-недели (понедельник — сегодня)."""
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())

    digests = []
    current = monday
    while current <= today:
        filepath = f"digests/{current.strftime('%Y-%m-%d')}.md"
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                weekday_name = current.strftime("%A")
                date_str = current.strftime("%d.%m.%Y")
                digests.append((f"{weekday_name} {date_str}", f.read()))
        current += timedelta(days=1)
    return digests


def call_claude_meta(combined: str) -> str:
    payload = {
        "model": "claude-opus-4-8",
        "max_tokens": 8000,
        "system": META_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": f"Дайджесты за неделю:\n\n{combined}"}],
    }
    last_error = None
    for attempt in range(1, 3):
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": CLAUDE_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=payload,
                timeout=600,
            )
            if resp.status_code != 200:
                print(f"[CLAUDE ERROR] {resp.status_code}: {resp.text}")
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]
        except requests.exceptions.Timeout as e:
            last_error = e
            print(f"[WARN] Таймаут Claude API (meta), попытка {attempt}/2")
    raise last_error


def send_meta_email(meta_text: str):
    week_num = datetime.now().isocalendar()[1]
    year = datetime.now().year
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📊 Недельный мета-обзор · Неделя {week_num}/{year}"
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = TO_EMAIL

    msg.attach(MIMEText(meta_text, "plain", "utf-8"))

    html_body = f"""<html><body>
<div style="font-family:Arial,sans-serif;font-size:14px;line-height:1.8;max-width:700px;white-space:pre-wrap;word-wrap:break-word">
{meta_text}
</div>
</body></html>"""
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, TO_EMAIL, msg.as_string())
    print(f"[OK] Мета-обзор отправлен на {TO_EMAIL}")


def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Запуск weekly meta...")

    digests = get_week_digests()
    print(f"  → Найдено {len(digests)} дайджестов за текущую неделю")

    if len(digests) < 2:
        print("[WARN] Меньше 2 дайджестов — мета-анализ не имеет смысла, выход")
        return

    combined = "\n\n---\n\n".join(
        [f"=== {day} ===\n{content}" for day, content in digests]
    )
    print(f"  → Объём для анализа: {len(combined)} символов")

    print("  → Отправка в Claude Opus 4.8...")
    meta = call_claude_meta(combined)
    print(f"  → Получен мета-обзор ({len(meta)} символов)")

    print("  → Отправка email...")
    send_meta_email(meta)
    print("[DONE]")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
