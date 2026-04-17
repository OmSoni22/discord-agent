"""Tests for the Discord message formatter."""

import pytest
from app.discord_bot.formatter import format_response, DISCORD_MAX_LENGTH
LIMIT = DISCORD_MAX_LENGTH


class TestFormatResponse:
    """Tests for the format_response() function."""

    def test_short_response_returned_as_single_chunk(self):
        """Responses under 2000 chars are returned as a single-item list."""
        result = format_response("Hello!")
        assert result == ["Hello!"]

    def test_exactly_2000_chars_not_split(self):
        """A response of exactly 2000 chars is NOT split."""
        text = "a" * LIMIT
        result = format_response(text)
        assert result == [text]

    def test_just_over_2000_chars_is_split(self):
        """A response of 2001 chars produces multiple chunks."""
        text = "a" * (LIMIT + 1)
        result = format_response(text)
        assert len(result) > 1
        assert all(len(chunk) <= LIMIT for chunk in result)

    def test_all_chunks_within_discord_limit(self):
        """No chunk exceeds 2000 characters regardless of input length."""
        text = "word " * 1000  # ~5000 chars
        result = format_response(text)
        assert all(len(chunk) <= LIMIT for chunk in result)

    def test_paragraph_breaks_preferred(self):
        """Splits prefer paragraph boundaries (double newline)."""
        para1 = ("First paragraph sentence. " * 40).strip()   # ~1040 chars
        para2 = ("Second paragraph sentence. " * 40).strip()  # ~1080 chars
        text = para1 + "\n\n" + para2
        result = format_response(text)
        assert len(result) == 2
        assert result[0] == para1
        assert result[1] == para2

    def test_no_content_loss(self):
        """All content from the original response is present across chunks."""
        text = "unique_keyword_xyz " * 200  # ~3800 chars
        result = format_response(text)
        combined = "".join(result)
        assert "unique_keyword_xyz" in combined

    def test_empty_string_returns_single_empty_chunk(self):
        """Empty input returns a list with one empty string."""
        result = format_response("")
        assert result == [""]
