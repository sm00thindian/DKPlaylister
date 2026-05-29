"""Utility helpers: logging, rate limiting, text processing, exports."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import pandas as pd
from rich.console import Console

console = Console()


def extract_emails(text: str) -> list[str]:
    """Naive email extractor. Improve with better regex + validation in production."""
    if not text:
        return []
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    return list(set(re.findall(pattern, text)))


def extract_social_handles(text: str) -> dict[str, list[str]]:
    """Extract @mentions for common platforms."""
    handles: dict[str, list[str]] = {"instagram": [], "twitter": [], "tiktok": []}
    if not text:
        return handles

    # Very rough — real version needs platform-specific patterns + validation
    ig = re.findall(r"(?:ig|instagram)[^\w@]*@?([\w.]+)", text, re.I)
    tw = re.findall(r"(?:twitter|x\.com)[^\w@]*@?([\w.]+)", text, re.I)
    tt = re.findall(r"(?:tiktok|tt)[^\w@]*@?([\w.]+)", text, re.I)

    handles["instagram"] = ig
    handles["twitter"] = tw
    handles["tiktok"] = tt
    return handles


def export_to_excel(playlists: Iterable[dict], path: Path) -> Path:
    """Export list of playlist dicts to .xlsx with nice formatting."""
    df = pd.DataFrame(playlists)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(path, index=False, sheet_name="Playlists")
    return path


def rate_limit(seconds: float = 0.5):
    """Decorator placeholder for polite API usage."""
    # TODO: implement token bucket or simple sleep decorator
    pass
