"""Discord message formatter — splits long responses to fit Discord's 2000-char limit."""

from __future__ import annotations

DISCORD_MAX_LENGTH = 2000


def format_response(response: str) -> list[str]:
    """Split a response string into Discord-safe chunks of ≤ 2000 characters.

    Splitting strategy (in priority order):
    1. If response fits → return as-is
    2. Split on paragraph breaks (double newline) when possible
    3. Fall back to line breaks (single newline) for very long paragraphs
    4. Hard-split at character boundary as last resort

    Args:
        response: The full agent response string

    Returns:
        List of strings each ≤ 2000 characters
    """
    if len(response) <= DISCORD_MAX_LENGTH:
        return [response]

    return _split_on_paragraphs(response)


def _split_on_paragraphs(text: str) -> list[str]:
    """Split text at paragraph boundaries (double newlines)."""
    chunks: list[str] = []
    current = ""

    paragraphs = text.split("\n\n")

    for para in paragraphs:
        separator = "\n\n" if current else ""
        candidate = current + separator + para

        if len(candidate) <= DISCORD_MAX_LENGTH:
            current = candidate
        else:
            # Flush current chunk
            if current:
                chunks.append(current)

            # The paragraph itself may be too long
            if len(para) > DISCORD_MAX_LENGTH:
                for sub in _split_on_lines(para):
                    chunks.append(sub)
                current = ""
            else:
                current = para

    if current:
        chunks.append(current)

    return chunks if chunks else [text[:DISCORD_MAX_LENGTH]]


def _split_on_lines(text: str) -> list[str]:
    """Split text at single newline boundaries."""
    chunks: list[str] = []
    current = ""

    for line in text.split("\n"):
        separator = "\n" if current else ""
        candidate = current + separator + line

        if len(candidate) <= DISCORD_MAX_LENGTH:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # Single line might still be > 2000 — hard split
            if len(line) > DISCORD_MAX_LENGTH:
                for i in range(0, len(line), DISCORD_MAX_LENGTH):
                    chunks.append(line[i : i + DISCORD_MAX_LENGTH])
                current = ""
            else:
                current = line

    if current:
        chunks.append(current)

    return chunks
