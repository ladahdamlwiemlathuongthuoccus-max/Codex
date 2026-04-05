from __future__ import annotations

import json
from html import escape

TAG_LABELS = {
    "agentic": "Агентные системы",
    "llm_engineering": "LLM-инженерия",
    "models": "Модели",
    "research": "Исследования",
    "products": "Продукты",
    "open_source": "Open Source",
    "safety": "Безопасность AI",
    "mcp_a2a": "MCP / A2A",
    "sapr_ai": "САПР + AI",
    "business": "AI в бизнесе",
}

TAG_EMOJI = {
    "agentic": "🤖",
    "llm_engineering": "🔧",
    "models": "🧠",
    "research": "🔬",
    "products": "🚀",
    "open_source": "📦",
    "safety": "🛡",
    "mcp_a2a": "🔗",
    "sapr_ai": "📐",
    "business": "💼",
}

MAX_MESSAGE_LEN = 4000


def format_digest(articles: list[dict], date_str: str) -> list[str]:
    if not articles:
        return ["Новых AI-новостей пока нет. Попробуйте позже."]

    # Filter out low-importance noise
    articles = [a for a in articles if a.get("importance_score", 0) >= 4]

    if not articles:
        return ["Сегодня только мелкие обсуждения, значимых новостей нет."]

    messages = []
    current = f"📡 <b>AI-дайджест</b> | {escape(date_str)}\n"

    # Important articles (importance >= 8)
    important = [a for a in articles if a.get("importance_score", 0) >= 8]
    regular = [a for a in articles if 4 <= a.get("importance_score", 0) < 8]

    if important:
        current += "\n🔥 <b>Главное</b>\n\n"
        for article in important:
            current += _format_article(article, detailed=True) + "\n"

    # Group regular by first tag
    tag_groups: dict[str, list[dict]] = {}
    for article in regular:
        tags = _parse_tags(article.get("tags", "[]"))
        first_tag = tags[0] if tags else "other"
        tag_groups.setdefault(first_tag, []).append(article)

    # Sort groups by total importance
    sorted_groups = sorted(
        tag_groups.items(),
        key=lambda x: sum(a.get("importance_score", 0) for a in x[1]),
        reverse=True,
    )

    for tag_id, group in sorted_groups:
        emoji = TAG_EMOJI.get(tag_id, "📌")
        label = TAG_LABELS.get(tag_id, "Разное")
        section = f"\n{emoji} <b>{escape(label)}</b>\n\n"
        for article in group:
            section += _format_article(article, detailed=False) + "\n"

        if len(current) + len(section) > MAX_MESSAGE_LEN:
            messages.append(current)
            current = section
        else:
            current += section

    total = len(important) + len(regular)
    sources_count = len(set(a.get("source_name", "") for a in articles))
    footer = f"\n📊 <i>{total} новостей из {sources_count} источников</i>"

    if len(current) + len(footer) > MAX_MESSAGE_LEN:
        messages.append(current)
        messages.append(footer)
    else:
        current += footer
        messages.append(current)

    return messages


def format_instant(article: dict) -> str:
    tags = _parse_tags(article.get("tags", "[]"))
    tag_line = "  ".join(
        f"{TAG_EMOJI.get(t, '')} {TAG_LABELS.get(t, t)}"
        for t in tags
    )
    title = _get_title_ru(article)

    return (
        f"🔥 <b>{escape(title)}</b>\n\n"
        f"{escape(article.get('summary_ru', ''))}\n\n"
        f"{tag_line}\n"
        f"<a href=\"{escape(article['url'])}\">"
        f"📎 {escape(article.get('source_name', 'Источник'))}</a>"
    )


def _format_article(article: dict, detailed: bool) -> str:
    title = escape(_get_title_ru(article))
    summary = escape(article.get("summary_ru", ""))
    url = escape(article.get("url", ""))
    source = escape(article.get("source_name", ""))

    if detailed:
        tags = _parse_tags(article.get("tags", "[]"))
        tag_line = "  ".join(
            f"{TAG_EMOJI.get(t, '')} {TAG_LABELS.get(t, t)}"
            for t in tags
        )
        return (
            f"▸ <b>{title}</b>\n"
            f"{summary}\n"
            f"{tag_line}\n"
            f"<a href=\"{url}\">📎 {source}</a>\n"
        )
    else:
        return (
            f"▸ <b>{title}</b>\n"
            f"  {summary}\n"
            f"  <a href=\"{url}\">📎 {source}</a>\n"
        )


def _get_title_ru(article: dict) -> str:
    """Get Russian title if available, otherwise original."""
    title_ru = article.get("title_ru", "")
    if title_ru:
        return title_ru
    return article.get("title", "")


def _parse_tags(tags) -> list[str]:
    if isinstance(tags, list):
        return tags
    if isinstance(tags, str):
        try:
            return json.loads(tags)
        except (json.JSONDecodeError, TypeError):
            return []
    return []
