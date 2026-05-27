"""
Daily AI/HPC/DC/OCP Digest Agent
=================================
Запускается через GitHub Actions по будням в 05:00 МСК.
Все секреты берутся из переменных окружения (GitHub Secrets).
"""

import os
import sys
import smtplib
import requests
import feedparser
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

CLAUDE_API_KEY     = os.environ["CLAUDE_API_KEY"]
NEWSAPI_KEY        = os.environ["NEWSAPI_KEY"]
GMAIL_ADDRESS      = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
TO_EMAIL           = os.environ["TO_EMAIL"]

SYSTEM_PROMPT = """Ты — аналитический агент мониторинга трендов AI/HPC/DC/OCP для архитектора AI Distribution Platform (BOM-генерация, валидация совместимости, CAPEX/OPEX/TCO для VAR-партнёров и системных интеграторов).

Отбери ровно 4 темы: 3 из новостных источников по AI Infrastructure / HPC / Data Center / OCP + 1 бумага из HuggingFace с практическим бизнес-применением (фильтр: inference cost reduction, enterprise deployment, AI agents для автоматизации, edge inference, model compression). Чисто академические бумаги игнорируй.

Формат каждой темы:
🔹 ТЕМА N/4 · КАТЕГОРИЯ
[Заголовок]

📌 СУТЬ
[2-3 предложения с цифрами]

🎯 ПОЧЕМУ ЭТО ВАЖНО ДЛЯ ТЕБЯ
[прямая связь с AI Distribution Platform и VAR-нишей]

🔮 ПРОГНОЗ НА 12 МЕСЯЦЕВ
→ Тезис 1: что произойдёт на рынке
→ Тезис 2: как изменится поведение VAR-партнёров
→ Тезис 3: возможность или угроза для платформы

✍️ ЧЕРНОВИК ПОСТА
[150-200 слов для LinkedIn с провокационным началом, структура тезис→факт→вывод→дискуссия, 4-5 хэштегов на английском]

Разделяй темы линией ─────────────────────────────────────────────.

Правила:
- Язык русский (аббревиатуры и имена в оригинале)
- В прогнозе ЗАПРЕЩЕНЫ слова: возможно, вероятно, может, скорее всего
- Тема 4 — категория AI Business Applications"""

RSS_FEEDS = [
    {
        "name": "REDDIT (HPC / ML / DataCenter / OCP)",
        "url": "https://www.reddit.com/r/HPC+MachineLearning+artificial+DataCenter+opencompute/.rss?limit=15",
        "headers": {"User-Agent": "Mozilla/5.0 (compatible; RSS reader)"},
    },
    {
        "name": "GOOGLE NEWS — AI Infrastructure / OCP",
        "url": 'https://news.google.com/rss/search?q=AI+infrastructure+HPC+datacenter+"Open+Compute+Project"&hl=en-US&gl=US&ceid=US:en',
        "headers": {},
    },
    {
        "name": "GOOGLE NEWS — NVIDIA / AMD / Intel DC",
        "url": "https://news.google.com/rss/search?q=NVIDIA+AMD+Intel+datacenter+HPC+liquid+cooling&hl=en-US&gl=US&ceid=US:en",
        "headers": {},
    },
]


def fetch_rss(feed: dict, max_items: int = 12) -> str:
    try:
        resp = requests.get(feed["url"], headers=feed["headers"], timeout=20)
        parsed = feedparser.parse(resp.text)
        lines = [f"=== {feed['name']} ==="]
        for entry in parsed.entries[:max_items]:
            title = getattr(entry, "title", "").strip()
            summary = getattr(entry, "summary", "")[:300].strip()
            published = getattr(entry, "published", "")
            lines.append(f"• {title} ({published})\n  {summary}")
        return "\n".join(lines)
    except Exception as e:
        return f"=== {feed['name']} ===\nОшибка: {e}"


def fetch_newsapi(api_key: str, max_items: int = 12) -> str:
    try:
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        url = (
            "https://newsapi.org/v2/everything"
            "?q=(AI+infrastructure+OR+HPC+OR+datacenter+OR+%22Open+Compute+Project%22)"
            f"&sortBy=publishedAt&pageSize={max_items}&language=en"
            f"&from={yesterday}&apiKey={api_key}"
        )
        data = requests.get(url, timeout=20).json()
        articles = data.get("articles", [])
        lines = ["=== NEWSAPI — публикации и блоги ==="]
        for a in articles:
            title = a.get("title", "").strip()
            desc  = (a.get("description") or "")[:250].strip()
            src   = a.get("source", {}).get("name", "")
            lines.append(f"• [{src}] {title}\n  {desc}")
        return "\n".join(lines)
    except Exception as e:
        return f"=== NEWSAPI ===\nОшибка: {e}"


def fetch_huggingface(max_items: int = 15) -> str:
    try:
        url = "https://huggingface.co/api/daily_papers"
        papers = requests.get(url, timeout=20).json()
        lines = ["=== HUGGINGFACE DAILY PAPERS ==="]
        for p in papers[:max_items]:
            paper = p.get("paper", {})
            title = paper.get("title", "").strip()
            summary = paper.get("summary", "")[:400].strip()
            authors = ", ".join([a.get("name", "") for a in paper.get("authors", [])[:3]])
            lines.append(f"• {title}\n  Authors: {authors}\n  {summary}")
        return "\n".join(lines)
    except Exception as e:
        return f"=== HUGGINGFACE ===\nОшибка: {e}"


def call_claude(combined_content: str) -> str:
    user_message = (
        "Данные из источников за 24 часа. "
        "Проанализируй и составь дайджест по формату из system.\n\n"
        + combined_content
    )
    payload = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 4000,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_message}],
    }
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": CLAUDE_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json=payload,
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"]


def send_email(digest_text: str):
    today = datetime.now().strftime("%d.%m.%Y")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🔹 AI/HPC/DC/OCP Дайджест · {today}"
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = TO_EMAIL

    msg.attach(MIMEText(digest_text, "plain", "utf-8"))

    html_body = f"""<html><body>
<div style="font-family:Arial,sans-serif;font-size:14px;line-height:1.8;max-width:700px;white-space:pre-wrap;word-wrap:break-word">
{digest_text}
</div>
</body></html>"""
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, TO_EMAIL, msg.as_string())
    print(f"[OK] Письмо отправлено на {TO_EMAIL}")


def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Запуск агента...")

    sections = []
    for feed in RSS_FEEDS:
        print(f"  → Сбор {feed['name']}...")
        sections.append(fetch_rss(feed))

    print("  → Сбор NewsAPI...")
    sections.append(fetch_newsapi(NEWSAPI_KEY))

    print("  → Сбор HuggingFace papers...")
    sections.append(fetch_huggingface())

    combined = "\n\n".join(sections)
    print(f"  → Собрано {len(combined)} символов")

    print("  → Отправка в Claude API...")
    digest = call_claude(combined)
    print(f"  → Получен дайджест ({len(digest)} символов)")

    print("  → Отправка письма...")
    send_email(digest)
    print("[DONE]")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
