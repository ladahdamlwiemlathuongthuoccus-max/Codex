from src.bot.formatter import format_digest, format_instant, MAX_DIGEST_ARTICLES


def _article(importance=7, source="Test Source", tags='["models"]', title_ru="Тест", summary_ru="Описание"):
    return {
        "id": 1,
        "title": "Test Article",
        "title_ru": title_ru,
        "summary_ru": summary_ru,
        "source_name": source,
        "url": "https://example.com/article",
        "tags": tags,
        "importance_score": importance,
    }


class TestFormatDigest:
    def test_empty_articles(self):
        result = format_digest([], "05 April 2026")
        assert len(result) == 1
        assert "нет" in result[0].lower()

    def test_filters_low_importance(self):
        articles = [_article(importance=3)]
        result = format_digest(articles, "05 April 2026")
        assert "значимых" in result[0].lower() or "нет" in result[0].lower()

    def test_includes_high_importance(self):
        articles = [_article(importance=9)]
        result = format_digest(articles, "05 April 2026")
        combined = "".join(result)
        assert "Тест" in combined

    def test_max_5_articles(self):
        articles = [_article(importance=8) for _ in range(10)]
        result = format_digest(articles, "05 April 2026")
        combined = "".join(result)
        # Should have numbered items 1-5 only
        assert "1." in combined
        assert f"{MAX_DIGEST_ARTICLES}." in combined

    def test_numbered_format(self):
        articles = [_article(importance=8)]
        result = format_digest(articles, "05 April 2026")
        combined = "".join(result)
        assert "1." in combined

    def test_header_present(self):
        articles = [_article(importance=8)]
        result = format_digest(articles, "05 April 2026")
        assert "AI-дайджест" in result[0]

    def test_source_count_in_footer(self):
        articles = [_article(importance=8, source="Source A"), _article(importance=7, source="Source B")]
        # Give unique URLs to avoid same article
        articles[0]["url"] = "https://a.com/1"
        articles[1]["url"] = "https://b.com/2"
        result = format_digest(articles, "05 April 2026")
        combined = "".join(result)
        assert "2 источников" in combined or "2 источник" in combined


class TestFormatInstant:
    def test_contains_title_and_link(self):
        result = format_instant(_article())
        assert "Тест" in result
        assert "https://example.com/article" in result

    def test_contains_source(self):
        result = format_instant(_article(source="OpenAI Blog"))
        assert "OpenAI Blog" in result

    def test_html_escaping(self):
        article = _article(title_ru="<script>alert('xss')</script>")
        result = format_instant(article)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_compact_no_tag_line(self):
        result = format_instant(_article())
        # Should not have loose emoji tag line, emoji is part of title
        assert result.startswith("🧠")  # models tag emoji
