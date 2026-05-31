"""Phase 1 Discovery & Mining helpers.

Reusable functions for style expansion and running mining searches.
Used by both CLI (`mine`) and the Streamlit UI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, List, Dict, Tuple

from dkplaylister.models import (
    StyleProfile, Playlist, StyleDiscoveryExpansion, PlaylistSource, Platform
)
from dkplaylister.spotify import fetch_playlist, _handle_rate_limit, get_client
from dkplaylister.scoring import PlaylistScorer, ScoringConfig


def expand_style_for_discovery(
    style: StyleProfile, llm_provider=None
) -> StyleDiscoveryExpansion:
    """Run style expansion (or return a safe fallback)."""
    if llm_provider is None:
        # Try to get one if not passed
        try:
            from dkplaylister.llm import get_provider
            llm_provider = get_provider("grok")
        except Exception:
            llm_provider = None

    if llm_provider and hasattr(llm_provider, "expand_style_for_discovery"):
        try:
            return llm_provider.expand_style_for_discovery(style)
        except Exception:
            pass

    # Safe fallback
    return StyleDiscoveryExpansion(
        search_queries=[style.raw_prompt[:120]],
        explanation="Fallback expansion (LLM unavailable or failed)"
    )


def run_discovery_mining(
    style: StyleProfile,
    queries: Optional[List[str]] = None,
    limit: int = 30,
    min_score: Optional[float] = None,
    llm_provider=None,
    progress_callback=None,
) -> Dict:
    """
    Core mining logic extracted for reuse (CLI + UI).

    If `progress_callback` is provided, it will be called with progress events:
        callback({"type": "start", "total_queries": N})
        callback({"type": "query_start", "query": "...", "index": i, "total": N})
        callback({"type": "query_complete", "query": "...", "new_candidates": M, "total_candidates": X})

    Returns a dict with:
      - candidates: list of scored Playlist objects
      - queries_used: list
      - expansion: StyleDiscoveryExpansion
      - query_stats: dict
    """
    expansion = expand_style_for_discovery(style, llm_provider)

    if queries is None or len(queries) == 0:
        queries = expansion.search_queries or [style.raw_prompt[:100]]

    queries = queries[:10]  # safety cap

    if progress_callback:
        progress_callback({"type": "start", "total_queries": len(queries)})

    client = get_client()
    candidates: List[Playlist] = []
    seen_ids = set()
    seen_urls = set()
    query_stats: Dict[str, int] = {q: 0 for q in queries}

    scorer = PlaylistScorer(style, config=ScoringConfig())

    # Pre-load existing URLs for live marking of already-imported items (Phase 1 full feature #3)
    existing_urls = set()
    try:
        from dkplaylister.storage import PlaylistRepository
        existing = PlaylistRepository().list_all()
        existing_urls = {str(p.url).strip() for p in existing if getattr(p, "url", None)}
    except Exception:
        pass

    for idx, q in enumerate(queries):
        if progress_callback:
            progress_callback({
                "type": "query_start",
                "query": q,
                "index": idx,
                "total": len(queries)
            })

        try:
            results = _handle_rate_limit(
                client.search,
                q=q,
                type="playlist",
                limit=10,
            )
            new_for_this_query = 0

            for item in (results.get("playlists", {}) or {}).get("items", []) or []:
                if not item:
                    continue
                pid = item.get("id")
                url = (item.get("external_urls") or {}).get("spotify")
                if pid in seen_ids or (url and url in seen_urls):
                    continue
                if pid:
                    seen_ids.add(pid)
                if url:
                    seen_urls.add(url)

                is_already_imported = url in existing_urls

                pl = fetch_playlist(url) if url else None
                if pl:
                    try:
                        breakdown = scorer.score(pl)
                        if min_score is None or breakdown.total_value_score >= min_score:
                            pl.current_score = breakdown
                            # Attach flag for live marking in UI
                            setattr(pl, "_already_imported", is_already_imported)
                            candidates.append(pl)
                            query_stats[q] = query_stats.get(q, 0) + 1
                            new_for_this_query += 1

                            if progress_callback:
                                progress_callback({
                                    "type": "candidate_found",
                                    "playlist_name": pl.name,
                                    "score": breakdown.total_value_score,
                                    "followers": pl.follower_count,
                                    "query": q,
                                    "total_candidates": len(candidates),
                                    "already_imported": is_already_imported
                                })

                            if len(candidates) >= limit:
                                break
                    except Exception:
                        pass

            if progress_callback:
                progress_callback({
                    "type": "query_complete",
                    "query": q,
                    "new_candidates": new_for_this_query,
                    "total_candidates": len(candidates)
                })

        except Exception as err:
            err_str = str(err)
            # Aggressively silence all 403 errors during discovery mining.
            # These come from private/restricted user profiles and are expected.
            if "403" in err_str:
                continue
            if progress_callback:
                progress_callback({
                    "type": "query_error",
                    "query": q,
                    "error": "Some enrichment calls failed (common on Spotify)"
                })
            continue

        if len(candidates) >= limit:
            break

    # Sort by score
    candidates.sort(
        key=lambda p: getattr(getattr(p, "current_score", None), "total_value_score", 0),
        reverse=True
    )

    return {
        "candidates": candidates[:limit],
        "queries_used": queries,
        "expansion": expansion,
        "query_stats": {k: v for k, v in query_stats.items() if v > 0},
    }


def score_and_filter_candidates(
    candidates: List[Playlist], style: StyleProfile, min_score: Optional[float] = None
) -> List[Tuple[Playlist, float]]:
    """Score list of playlists and filter by min_score."""
    scorer = PlaylistScorer(style, config=ScoringConfig())
    scored = []
    for pl in candidates:
        try:
            breakdown = scorer.score(pl)
            score = breakdown.total_value_score
            if min_score is None or score >= min_score:
                scored.append((pl, score))
        except Exception:
            continue
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


# =============================================================================
# Query Presets (Phase 1 full-featured)
# =============================================================================

PRESETS_DIR = Path("data/discovery_presets")
PRESETS_DIR.mkdir(parents=True, exist_ok=True)


def save_mining_preset(band_id: int, name: str, queries: list[str], limit: int = 25, min_score: int = 50, exclude_existing: bool = True) -> bool:
    """Save a full mining configuration preset for a band (queries + settings)."""
    if not name or not queries:
        return False
    path = PRESETS_DIR / f"band_{band_id}.json"
    presets = {}
    if path.exists():
        try:
            presets = json.loads(path.read_text())
        except Exception:
            presets = {}
    presets[name] = {
        "queries": queries,
        "limit": limit,
        "min_score": min_score,
        "exclude_existing": exclude_existing
    }
    path.write_text(json.dumps(presets, indent=2))
    return True


def save_query_preset(band_id: int, name: str, queries: list[str]) -> bool:
    """Legacy wrapper — saves queries only (for backward compatibility)."""
    return save_mining_preset(band_id, name, queries)


def load_mining_presets(band_id: int) -> dict[str, dict]:
    """Load all saved mining presets for a band (full config)."""
    path = PRESETS_DIR / f"band_{band_id}.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        # Support both old (list) and new (dict) formats
        normalized = {}
        for name, value in data.items():
            if isinstance(value, list):
                normalized[name] = {
                    "queries": value,
                    "limit": 25,
                    "min_score": 50,
                    "exclude_existing": True
                }
            else:
                # Ensure all keys exist for older presets
                value.setdefault("limit", 25)
                value.setdefault("min_score", 50)
                value.setdefault("exclude_existing", True)
                normalized[name] = value
        return normalized
    except Exception:
        return {}


def load_query_presets(band_id: int) -> dict[str, list[str]]:
    """Legacy helper returning just queries."""
    presets = load_mining_presets(band_id)
    return {name: data["queries"] for name, data in presets.items()}


def delete_query_preset(band_id: int, name: str) -> bool:
    """Delete a preset for a band."""
    path = PRESETS_DIR / f"band_{band_id}.json"
    if not path.exists():
        return False
    try:
        presets = json.loads(path.read_text())
        if name in presets:
            del presets[name]
            path.write_text(json.dumps(presets, indent=2))
            return True
    except Exception:
        pass
    return False


import json  # ensure json is available for the preset functions above


def run_discovery_mining(
    style: StyleProfile,
    queries: Optional[List[str]] = None,
    limit: int = 30,
    min_score: Optional[float] = None,
    llm_provider=None,
    progress_callback=None,
    exclude_existing: bool = True,
) -> Dict:
    """
    Full-featured mining with optional exclusion of already-imported targets.
    """
    expansion = expand_style_for_discovery(style, llm_provider)

    if queries is None or len(queries) == 0:
        queries = expansion.search_queries or [style.raw_prompt[:100]]

    queries = queries[:10]

    if progress_callback:
        progress_callback({"type": "start", "total_queries": len(queries)})

    client = get_client()
    candidates: List[Playlist] = []
    seen_ids = set()
    seen_urls = set()
    query_stats: Dict[str, int] = {q: 0 for q in queries}

    scorer = PlaylistScorer(style, config=ScoringConfig())

    # Pre-load existing URLs for exclusion (Phase 1 full feature)
    existing_urls = set()
    if exclude_existing:
        try:
            from dkplaylister.storage import PlaylistRepository
            existing = PlaylistRepository().list_all()
            existing_urls = {str(p.url).strip() for p in existing if getattr(p, "url", None)}
        except Exception:
            pass

    for idx, q in enumerate(queries):
        if progress_callback:
            progress_callback({"type": "query_start", "query": q, "index": idx, "total": len(queries)})

        try:
            results = _handle_rate_limit(client.search, q=q, type="playlist", limit=10)
            new_for_this_query = 0

            for item in (results.get("playlists", {}) or {}).get("items", []) or []:
                if not item:
                    continue
                pid = item.get("id")
                url = (item.get("external_urls") or {}).get("spotify")
                if not url:
                    continue
                if pid in seen_ids or url in seen_urls:
                    continue
                if exclude_existing and url in existing_urls:
                    continue

                if pid:
                    seen_ids.add(pid)
                seen_urls.add(url)

                pl = fetch_playlist(url)
                if pl:
                    try:
                        breakdown = scorer.score(pl)
                        if min_score is None or breakdown.total_value_score >= min_score:
                            pl.current_score = breakdown
                            candidates.append(pl)
                            query_stats[q] += 1
                            new_for_this_query += 1

                            if progress_callback:
                                progress_callback({
                                    "type": "candidate_found",
                                    "playlist_name": pl.name,
                                    "score": breakdown.total_value_score,
                                    "followers": pl.follower_count,
                                    "query": q,
                                    "total_candidates": len(candidates)
                                })

                            if len(candidates) >= limit:
                                break
                    except Exception:
                        pass

            if progress_callback:
                progress_callback({
                    "type": "query_complete",
                    "query": q,
                    "new_candidates": new_for_this_query,
                    "total_candidates": len(candidates)
                })

        except Exception as err:
            err_str = str(err)
            # Completely silence 403s — they are expected and non-fatal during bulk discovery.
            if "403" in err_str:
                continue
            if progress_callback:
                progress_callback({"type": "query_error", "query": q, "error": err_str})
            continue

        if len(candidates) >= limit:
            break

    candidates.sort(
        key=lambda p: getattr(getattr(p, "current_score", None), "total_value_score", 0),
        reverse=True
    )

    return {
        "candidates": candidates[:limit],
        "queries_used": queries,
        "expansion": expansion,
        "query_stats": {k: v for k, v in query_stats.items() if v > 0},
    }
