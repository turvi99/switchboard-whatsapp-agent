"""
Resolves the free-text `media_keyword` the LLM picks into an actual asset
from the tenant's pre-seeded media library (Task 1's "Media Library:
pre-seeded URLs mapping query terms to assets").

Matching is intentionally forgiving (case-insensitive, substring-based, also
checks the human-readable `description` field) since the LLM won't always
echo the keyword back verbatim.
"""
from __future__ import annotations

from typing import Any, Optional


def find_media_asset(media_library: list[dict[str, Any]], keyword: Optional[str]) -> Optional[dict[str, Any]]:
    if not keyword or not media_library:
        return None

    needle = keyword.strip().lower()

    # 1. exact keyword match
    for asset in media_library:
        if asset.get("keyword", "").lower() == needle:
            return asset

    # 2. substring match against keyword or description, either direction
    for asset in media_library:
        kw = asset.get("keyword", "").lower()
        desc = asset.get("description", "").lower()
        if needle in kw or kw in needle or needle in desc:
            return asset

    return None


def describe_media_library(media_library: list[dict[str, Any]]) -> str:
    """Renders the media library as a short bullet list for the LLM's system prompt."""
    if not media_library:
        return "(no media assets configured for this tenant)"
    lines = []
    for asset in media_library:
        lines.append(
            f"- keyword='{asset.get('keyword')}' type={asset.get('type')} "
            f"description=\"{asset.get('description', '')}\""
        )
    return "\n".join(lines)
