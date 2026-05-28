"""
Daily AI/HPC/DC/OCP Digest Agent
=================================
Запускается через GitHub Actions по будням в 05:00 МСК.
Все секреты берутся из переменных окружения (GitHub Secrets).
"""

import os
import sys
import json
import random
import smtplib
import subprocess
import urllib.parse
import requests
import feedparser
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

CLAUDE_API_KEY     = os.environ["CLAUDE_API_KEY"]
NEWSAPI_KEY        = os.environ["NEWSAPI_KEY"]
GMAIL_ADDRESS      = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
TO_EMAIL           = os.environ["TO_EMAIL"]

SYSTEM_PROMPT = """Ты аналитический агент мониторинга трендов AI/HPC/DC/OCP для архитектора AI Distribution Platform.

# ЧИТАТЕЛЬ
Основатель AI Distribution Platform: инфраструктурный архитектор. НЕ продавец и НЕ маркетолог.
Компоненты платформы: BOM-генератор, граф совместимости, TCO-калькулятор, генератор документации, B2G-направление.
Целевые клиенты: VAR-партнёры, системные интеграторы, B2G-сегмент.

# ЖАНР
Архитектор-аналитик. Спокойная инженерная констатация. Не продающий копирайт.

# СТРОГИЕ ПРАВИЛА (нарушение = брак)

## 1. Источники
ЗАПРЕЩЕНО как первоисточник:
- globenewswire.com, prnewswire.com, businesswire.com, accesswire.com (PR-агрегаторы)
- finance.yahoo.com, investing.com
- LinkedIn-посты без указанного первоисточника
- Reddit, форумы, Telegram (как первоисточник; как сигнал — допустимо)
- AI-summaries без атрибуции
Если факт известен только из этих источников — пометь [НЕ ВЕРИФИЦИРОВАНО] или исключи тему.
Приоритет: вендорские newsroom (nvidia.com, amd.com, intel.com, supermicro.com, dell.com, hpe.com), opencompute.org, semianalysis.com, servethehome.com, nextplatform.com, theregister.com, hpcwire.com, anandtech.com, arxiv.org.

## 2. Цифры и факты
Каждое числовое утверждение (доля, мощность, цена, дата, рост) сопровождается:
- ссылкой в скобках: (NVIDIA newsroom, март 2026), ИЛИ
- пометкой [оценка автора]
ЗАПРЕЩЕНО придумывать цифры. Лучше написать «не известно» или исключить пункт.

## 3. Прогноз: три различающихся сценария
Формат:
→ Низкий (12 мес): ключевое допущение — [механизм/актор/причина]
→ Базовый (12 мес): ключевое допущение — [механизм/актор/причина]
→ Высокий (12 мес): ключевое допущение — [механизм/актор/причина]
КРИТИЧНО: допущения должны различаться ПО СОДЕРЖАНИЮ (разный механизм, актор или причина), а не «то же самое больше/меньше».
ЗАПРЕЩЕНЫ слова: возможно, вероятно, может, скорее всего, не исключено.

## 4. Структура каждой из 4 тем — строго эта

🔹 ТЕМА N/4 · [КАТЕГОРИЯ]
[Заголовок: краткий, без эпитетов, содержит ключевой факт]

📌 ФАКТ
1–2 предложения с конкретикой. Источник в скобках с датой. Перечни из 5+ параметров — отдельными строками, не inline-скобками.

📍 КОНТЕКСТ
Что изменилось относительно предыдущего состояния отрасли. Без оценок и риторики.

🎯 РЕЛЕВАНТНОСТЬ ДЛЯ AI DISTRIBUTION PLATFORM
Привязка к компоненту (BOM / граф совместимости / TCO / документация / B2G). Степень: высокая/средняя/низкая, обоснование в одно предложение.

🔮 ПРОГНОЗ НА 12 МЕСЯЦЕВ
Три сценария по правилам п.3.

❓ ОТКРЫТЫЕ ВОПРОСЫ
2–4 пункта: что неизвестно, что требует проверки, какие данные изменили бы прогноз. ОБЯЗАТЕЛЬНЫЙ РАЗДЕЛ.

📋 BACKLOG-ITEM (Этап 3b — только если РЕЛЕВАНТНОСТЬ = высокая)
Если выше указана высокая релевантность — сформируй структурированный backlog-item для платформы. При средней или низкой — раздел НЕ ВЫВОДИ.

Формат:
Название: [действие-ориентированное, краткое; не пересказ новости]
Триггер: [конкретное событие из ФАКТ + источник]
Затронутые компоненты: [BOM-генератор / граф совместимости / TCO-калькулятор / генератор документации / B2G-направление]
Требования (от 1 до 5 пунктов; каждое с обоснованием в 1 предложение):
  1. [конкретное техническое или продуктовое требование] — [обоснование: почему сейчас, чем грозит откладывание]
  2. ...
Приоритет: P0 (внедрить в текущем спринте) / P1 (в ближайший квартал) / P2 (в плане на год)
Открытые вопросы блокирующие реализацию: [ссылки на конкретные пункты из ❓ ОТКРЫТЫЕ ВОПРОСЫ выше, которые нужно закрыть до старта]

✍️ ЧЕРНОВИК ПОСТА
150–200 слов. Структура: неочевидное экспертное наблюдение → факт → вывод → вопрос для дискуссии. БЕЗ хэштегов в темах 1–3. В теме 4 — 3–4 хэштега из whitelist.

## 5. Voice anchor (соблюдай интонацию)

«В высокоплотной инфраструктуре почти не существует локальных решений. Любое изменение компонента меняет поведение смежных контуров: питание, охлаждение, кабельную архитектуру, сервисный доступ и режим отказа системы. Поэтому ошибка начинается в тот момент, когда оборудование оценивают вне эксплуатационного контекста.»

Спокойная констатация. Инженерная точность. Никаких эмоциональных эпитетов.

Дополнительный пример для прогнозной и стратегической части:

«Главный структурный конфликт современного AI/DC-рынка — разница скоростей между вычислительным оборудованием и инфраструктурой. Compute обновляется циклами 12–24 месяца. Инженерная инфраструктура проектируется на 7–10 лет. Именно этот разрыв формирует большую часть будущих CAPEX-потерь. Ключевым активом становится не текущая плотность и не минимальный CAPEX на старте, а способность системы адаптироваться к следующему поколению оборудования без разрушения базовой архитектуры.»

Замечай: суждение о рынке без эмоций, конкретные горизонты времени, фокус на структурном уровне.

Дополнительный пример для жанра «комментарий к новости отрасли»:

«Большинство новостей о новом поколении AI-серверов интерпретируются слишком поверхностно. Рынок обсуждает рост производительности, но реальные последствия возникают не на уровне compute, а на уровне инфраструктурных ограничений. Каждое увеличение плотности мощности меняет требования к питанию, охлаждению, механике стойки, кабельной архитектуре и сервисной модели. Поэтому новый сервер — это не только новый вычислительный профиль. Это изменение условий существования всей площадки.»

Замечай: новость — это только повод. Главное — что она меняет в архитектурном слое. Никакого «революционно», только инженерные последствия.

## 6. Словарь запретов
Клише: «в современном быстро меняющемся мире», «глубоко погрузиться», «давайте разберёмся», «эпоха закончилась», «революция», «прорыв», «меняет всё», «не имеет аналогов», «уникальное решение», «синергия», «играет ключевую роль», «является неотъемлемой частью», «по сути», «стремительно», «устойчивое конкурентное преимущество».
AI-маркеры: «важно отметить, что», «стоит подчеркнуть», «следует обратить внимание», «давайте рассмотрим», «погружаемся», «исследуем», «откроем», «в заключение можно сказать», избыточное «не только..., но и...».
Inflated symbolism: «битва», «гонка вооружений», «новая эра».
Кальки: «первоклассный» (заменить «первого порядка»), «нативный» в роли наречия, «комплексный» в значении complex.

## 7. Пунктуация
- Em-dash (—) только в смысловой функции: атрибуция, противопоставление, раскрытие. ЗАПРЕЩЁН декоративный.
- Кавычки только елочкой («…»). При вложенности — лапки („…").
- Короткое тире (–) в диапазонах: 12–24 месяца, 7–10 лет.

## 8. Хэштеги (только для черновика поста темы 4)
Whitelist: #GPU #Accelerators #CUDA #ROCm #HPC #AIInfrastructure #OpenCompute #OCP #LiquidCooling #DLC #AINetworking #UltraEthernet #InfiniBand #NVLink #RackScale #DataCenter #AIDistribution
Запрещено: машинно-переведённые хэштеги, хэштеги длиннее 25 символов, более 5 на пост.

# SELF-AUDIT (выполни перед выдачей)
1. Каждый факт имеет источник в скобках с датой, ИЛИ [НЕ ВЕРИФИЦИРОВАНО], ИЛИ исключён
2. Каждое число имеет источник ИЛИ пометку [оценка автора]
3. Ни один цитированный источник не из blacklist
4. Прогноз: 3 сценария, явный горизонт, РАЗЛИЧАЮЩИЕСЯ допущения
5. Привязка к компоненту платформы явная
6. Раздел «Открытые вопросы» содержит ≥2 пунктов
7. Нет слов из словаря запретов
8. Em-dash только в смысловой функции
9. Кавычки только елочкой
10. Хэштеги — только в теме 4, ≤5, из whitelist
11. Если релевантность темы = высокая — раздел 📋 BACKLOG-ITEM присутствует и заполнен по формату; если средняя/низкая — раздела нет

Если хотя бы один пункт нарушен — ПЕРЕПИШИ перед выдачей.

# ТЕМЫ
Отбери ровно 4 темы:
- Темы 1–3: AI Infrastructure / HPC / Data Center / OCP из новостных источников
- Тема 4: бумага с HuggingFace с практическим бизнес-применением (inference cost reduction, enterprise deployment, AI agents для автоматизации, edge inference, model compression). Чисто академические бумаги — исключить. Категория: «AI Business Applications».

После четырёх тем добавь отдельный блок «Новости отрасли» по правилам ниже.

# 🏭 НОВОСТИ ОТРАСЛИ (1 новость, отдельный блок после 4 тем)

Тебе передан список INDUSTRY_NEWS из источников Vertiv, Eaton, WBT и общего отраслевого потока Google News. Выбери ОДНУ новость, наиболее релевантную инфраструктуре AI/HPC/ЦОД, приоритет свежим.

Формат строго:

🏭 НОВОСТИ ОТРАСЛИ

📌 ФАКТ
1–2 предложения с конкретикой. Ссылка на первоисточник. Дата.

🎯 РЕЛЕВАНТНОСТЬ
Привязка к компоненту платформы (BOM / граф совместимости / TCO / документация / B2G) в одном предложении.

Правила блока:
- Источники вендорские, тон маркетинговый. Бери ТОЛЬКО фактическую часть (что выпущено, параметры, событие). Рекламные эпитеты отбрасывай на self-audit.
- Полный прогноз с тремя сценариями к этому блоку НЕ применяй. Это новостная справка, не глубокая аналитика.
- BACKLOG-ITEM и черновик поста к этому блоку НЕ добавляй.
- Если все новости из списка дублируют темы дайджеста или прошлых дней, напиши: «Новых релевантных новостей отрасли нет».

Язык — русский. Аббревиатуры и имена собственные в оригинале.

# 💬 ЦИТАТА ДНЯ (отдельный блок в самом конце)

Тебе передан QUOTE_OF_DAY. Вставь цитату ДОСЛОВНО, без перевода, без изменения формулировки. Формат строго:

💬 ЦИТАТА ДНЯ

[текст цитаты] — [автор]
Источник: [источник]

Правила:
- НЕ сочиняй цитаты. НЕ меняй ни одного слова. Бери только то, что в QUOTE_OF_DAY.
- НЕ переводи цитату на русский, оставляй язык оригинала.
- Если QUOTE_OF_DAY пуст, блок не выводи."""

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
    {
        "name": "OCP — Open Compute Project (official blog)",
        "url": "https://www.opencompute.org/blog/rss",
        "headers": {"User-Agent": "Mozilla/5.0 (compatible; RSS reader)"},
    },
    {
        "name": "ARXIV — Hardware Architecture + Distributed Computing (cs.AR + cs.DC)",
        "url": "https://rss.arxiv.org/rss/cs.AR+cs.DC",
        "headers": {"User-Agent": "Mozilla/5.0 (compatible; RSS reader)"},
    },
]


def gnews_rss(query: str, window: str = "7d") -> str:
    """Построить URL Google News RSS-поиска с окном свежести."""
    q = urllib.parse.quote_plus(f"{query} when:{window}")
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


INDUSTRY_NEWS_FEEDS = [
    gnews_rss("site:vertiv.com/en-us/about/news-and-insights", "7d"),
    gnews_rss("site:eaton.com (data center OR UPS OR power distribution OR cooling)", "7d"),
    gnews_rss("site:wbt.com.au", "14d"),
    gnews_rss("data center infrastructure OR liquid cooling OR rack power density", "2d"),
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
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
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


def collect_industry_news(recent_titles: list) -> list:
    """Собрать новости отрасли из вендорских источников через Google News.
    Дедупликация внутри прогона и против тем за последние N дней."""
    items = []
    seen = set()
    for feed_url in INDUSTRY_NEWS_FEEDS:
        try:
            resp = requests.get(
                feed_url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; RSS reader)"},
                timeout=20,
            )
            parsed = feedparser.parse(resp.text)
            for entry in parsed.entries[:5]:
                title = getattr(entry, "title", "").strip()
                link = getattr(entry, "link", "")
                key = title.lower()[:50]
                if not title or key in seen:
                    continue
                if any(key[:40] in t.lower() for t in recent_titles):
                    continue
                seen.add(key)
                items.append({
                    "title": title,
                    "link": link,
                    "published": getattr(entry, "published", ""),
                    "source": parsed.feed.get("title", ""),
                })
        except Exception as e:
            print(f"[WARN] Industry feed error {feed_url}: {e}")
    return items


def call_claude(combined_content: str) -> str:
    user_message = (
        "Данные из источников за 24 часа. "
        "Проанализируй и составь дайджест по формату из system.\n\n"
        + combined_content
    )
    payload = {
        "model": "claude-opus-4-8",
        "max_tokens": 8000,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_message}],
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
                print(f"[ANTHROPIC API ERROR] Status: {resp.status_code}")
                print(f"[ANTHROPIC API ERROR] Body: {resp.text}")
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]
        except requests.exceptions.Timeout as e:
            last_error = e
            print(f"[WARN] Таймаут Claude API, попытка {attempt}/2")
    raise last_error


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

def get_recent_topics(days: int = 7) -> list:
    """Прочитать заголовки тем из дайджестов за последние N дней."""
    import re
    today = datetime.now().date()
    topics = []
    for i in range(1, days + 1):
        date = today - timedelta(days=i)
        filepath = f"digests/{date.strftime('%Y-%m-%d')}.md"
        if not os.path.exists(filepath):
            continue
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            # Заголовок темы — следующая непустая строка после "🔹 ТЕМА N/4 · …"
            matches = re.findall(r"🔹\s*ТЕМА\s+\d+/\d+[^\n]*\n+([^\n]{10,200})", content)
            topics.extend([m.strip() for m in matches if m.strip()])
        except Exception as e:
            print(f"[WARN] Не прочитан {filepath}: {e}")
    return topics

def save_digest_to_repo(digest_text: str):
    """Сохранить дайджест в digests/ и закоммитить в репо для weekly meta."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    weekday = datetime.now().strftime("%A")
    os.makedirs("digests", exist_ok=True)
    filepath = f"digests/{today_str}.md"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# Дайджест {today_str} ({weekday})\n\n{digest_text}\n")
    try:
        subprocess.run(["git", "config", "user.name", "AI Digest Bot"], check=True)
        subprocess.run(["git", "config", "user.email", "bot@digest.local"], check=True)
        subprocess.run(["git", "add", filepath], check=True)
        subprocess.run(["git", "commit", "-m", f"Daily digest {today_str}"], check=True)
        subprocess.run(["git", "push"], check=True)
        print(f"[OK] Дайджест сохранён: {filepath}")
    except subprocess.CalledProcessError as e:
        print(f"[WARN] Git push не удался: {e}")

def get_shown_quotes(days: int = 30) -> list:
    """Ключи цитат, показанных за последние N дней (для дедупликации)."""
    import re
    today = datetime.now().date()
    keys = []
    for i in range(1, days + 1):
        fp = f"digests/{(today - timedelta(days=i)).strftime('%Y-%m-%d')}.md"
        if not os.path.exists(fp):
            continue
        try:
            with open(fp, "r", encoding="utf-8") as f:
                content = f.read()
            for line in content.splitlines():
                line = line.strip()
                if not line.startswith("💬") or "—" not in line:
                    continue
                body = line.lstrip("💬").strip()
                # формат строки: [цитата] — [автор]
                quote_part, _, author = body.rpartition("—")
                quote_part = quote_part.strip()
                author = author.strip()
                if quote_part and author:
                    keys.append(f"{author}:{quote_part[:30]}")
        except Exception:
            pass
    return keys


def select_quotes(shown_keys: list, n: int = 1) -> list:
    """Выбрать N цитат из quotes.json, исключив уже показанные."""
    try:
        with open("quotes.json", "r", encoding="utf-8") as f:
            pool = json.load(f)
    except Exception as e:
        print(f"[WARN] quotes.json не прочитан: {e}")
        return []
    fresh = [q for q in pool
             if f"{q['author']}:{q['quote'][:30]}" not in shown_keys]
    if not fresh:
        fresh = pool  # пул исчерпан за окно дедупликации, идём на второй круг
    return random.sample(fresh, min(n, len(fresh)))


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

    recent_topics = get_recent_topics(days=7)
    if recent_topics:
        print(f"  → Загружено {len(recent_topics)} тем за прошлую неделю (избегать повторов)")
        combined += "\n\n=== ТЕМЫ УЖЕ ОСВЕЩАЛИСЬ ЗА ПОСЛЕДНИЕ 7 ДНЕЙ — ВЫБИРАЙ НОВЫЕ ТЕМЫ ИЛИ ДРУГИЕ УГЛЫ ===\n"
        for t in recent_topics:
            combined += f"- {t}\n"

    print("  → Сбор новостей отрасли (Vertiv / Eaton / WBT / Google News)...")
    industry = collect_industry_news(recent_topics)
    print(f"  → Собрано {len(industry)} кандидатов новостей отрасли")
    industry_block = "\n".join(
        f"- [{it['source']}] {it['title']} ({it['published']}) {it['link']}"
        for it in industry
    ) or "Новостей отрасли за период нет."
    combined += "\n\n=== INDUSTRY_NEWS (кандидаты для блока «Новости отрасли», выбери ОДНУ) ===\n"
    combined += industry_block

    print("  → Выбор цитаты дня...")
    shown_quotes = get_shown_quotes(days=30)
    quotes = select_quotes(shown_quotes, n=1)  # n=2 если хочешь две цитаты
    quotes_block = "\n".join(
        f'{q["quote"]} — {q["author"]} | Источник: {q["source"]}' for q in quotes
    ) or "Цитат нет."
    print(f"  → Цитата выбрана: {quotes[0]['author'] if quotes else 'нет'}")
    combined += "\n\n=== QUOTE_OF_DAY (вставь дословно в блок цитаты, НЕ меняй текст) ===\n"
    combined += quotes_block

    print("  → Отправка в Claude API...")
    digest = call_claude(combined)
    print(f"  → Получен дайджест ({len(digest)} символов)")

    print("  → Отправка письма...")
    send_email(digest)

    print("  → Сохранение в репозиторий...")
    save_digest_to_repo(digest)
    print("[DONE]")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
