"""Scoring engine for DKPlaylister.

Implements the configurable prioritization logic documented in docs/prioritization.md.

Core idea:
- We want high-value playlists for *this specific artist*, not just big numbers.
- Primary signals: Activity + Fit
- Secondary: Openness, Contact quality, Follower reach (log scaled)
- Penalties for risk signals
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Optional

from dkplaylister.llm import LLMProvider, get_provider
from dkplaylister.models import Playlist, ScoreBreakdown, StyleProfile


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class ScoringConfig:
    """Configurable weights for playlist scoring (all values 0.0–1.0)."""

    # Main category weights (should sum close to 1.0)
    weight_activity: float = 0.25
    weight_fit: float = 0.30
    weight_openness: float = 0.15
    weight_followers: float = 0.12
    weight_contact: float = 0.10
    weight_history: float = 0.08

    # Penalties
    risk_penalty_weight: float = 0.20   # How heavily risk subtracts

    # Tunable thresholds
    min_followers_for_score: int = 500
    high_follower_cap: int = 150_000    # Diminishing returns after this

    # Keyword lists (can be extended)
    submission_keywords: list[str] = field(default_factory=lambda: [
        "submission", "submissions", "accepting", "accept", "pitch", "demo",
        "demos", "send your", "open to", "now accepting", "curator", "playlist push"
    ])

    bad_signals: list[str] = field(default_factory=lambda: [
        "pay to play", "paid placement", "buy playlist", "sponsored add",
        "guaranteed streams", "bot", "fake plays"
    ])


DEFAULT_CONFIG = ScoringConfig()


# =============================================================================
# Main Scorer
# =============================================================================

class PlaylistScorer:
    """Scores playlists against a StyleProfile using configurable logic + LLM."""

    def __init__(
        self,
        style_profile: StyleProfile,
        config: ScoringConfig = DEFAULT_CONFIG,
        llm_provider: Optional[LLMProvider] = None,
    ):
        self.style = style_profile
        self.config = config
        self.llm = llm_provider or get_provider("grok")

    def score(self, playlist: Playlist) -> ScoreBreakdown:
        """Compute a full ScoreBreakdown for a playlist."""

        breakdown = ScoreBreakdown()

        # 1. Activity Score
        breakdown.activity_score = self._score_activity(playlist)

        # 2. Fit Score (LLM + keyword overlap)
        breakdown.fit_score = self._score_fit(playlist)

        # 3. Openness Score
        breakdown.openness_score = self._score_openness(playlist)

        # 4. Follower Score (log scaled)
        breakdown.follower_score = self._score_followers(playlist)

        # 5. Contact Quality
        breakdown.contact_quality_score = self._score_contact_quality(playlist)

        # 6. History (placeholder for now – will improve with Submission data)
        breakdown.personal_history_bonus = 0.0

        # 7. Risk Penalty
        breakdown.risk_penalty = self._score_risk(playlist)

        # Calculate final composite score (0-100)
        breakdown.total_value_score = self._compute_total(breakdown)

        # Generate human-readable explanation
        breakdown.explanation = self._generate_explanation(playlist, breakdown)

        # Attach to playlist
        playlist.current_score = breakdown

        return breakdown

    # -------------------------------------------------------------------------
    # Individual scoring methods
    # -------------------------------------------------------------------------

    def _score_activity(self, playlist: Playlist) -> float:
        """Higher score for recently active playlists."""
        if not playlist.last_activity_at:
            # No data → neutral/mild positive if it has a description
            return 0.45 if playlist.description else 0.35

        # Simple recency scoring (can be made much smarter later)
        days_ago = (playlist.last_activity_at - __import__("datetime").datetime.utcnow()).days
        if days_ago <= 14:
            return 0.95
        elif days_ago <= 45:
            return 0.80
        elif days_ago <= 90:
            return 0.65
        else:
            return 0.40

    def _score_fit(self, playlist: Playlist) -> float:
        """Semantic + keyword fit between style and playlist."""
        # Try LLM first (best signal)
        try:
            llm_score = self.llm.score_playlist_fit(self.style, playlist)
            if 0.0 <= llm_score <= 1.0:
                return round(llm_score, 3)
        except Exception:
            pass

        # Fallback: keyword overlap between style prompt and playlist description + genres
        text = " ".join([
            self.style.raw_prompt.lower(),
            " ".join(self.style.primary_genres + self.style.secondary_genres).lower(),
            (playlist.description or "").lower(),
            " ".join(playlist.genres + playlist.tags).lower(),
        ])

        style_keywords = set(re.findall(r"\b\w{4,}\b", self.style.raw_prompt.lower()))
        playlist_keywords = set(re.findall(r"\b\w{4,}\b", text))

        if not style_keywords:
            return 0.5

        overlap = len(style_keywords & playlist_keywords) / len(style_keywords)
        return round(min(1.0, overlap * 1.4), 3)  # boost a bit

    def _score_openness(self, playlist: Playlist) -> float:
        """How explicitly open to submissions this playlist appears."""
        text = " ".join([
            (playlist.description or "").lower(),
            " ".join(playlist.tags).lower(),
            playlist.submission_guidelines or "",
        ])

        score = 0.3  # baseline

        # Strong boost from Playlister (they only show playlists with public contact)
        if playlist.source and "playlister" in str(playlist.source).lower():
            score += 0.35

        # Keyword matches
        for kw in self.config.submission_keywords:
            if kw.lower() in text:
                score += 0.12
                break

        # Explicit flag
        if playlist.is_accepting_submissions:
            score += 0.25

        return min(1.0, round(score, 3))

    def _score_followers(self, playlist: Playlist) -> float:
        """Log-scaled follower score with diminishing returns."""
        followers = playlist.follower_count or 0

        if followers < self.config.min_followers_for_score:
            return 0.15

        # Log scale
        log_score = math.log10(max(followers, 1)) / math.log10(self.config.high_follower_cap)
        return min(1.0, round(log_score, 3))

    def _score_contact_quality(self, playlist: Playlist) -> float:
        """Quality of contact information available."""
        if not playlist.curator:
            # Still give some credit if Playlister surfaced it
            if playlist.source and "playlister" in str(playlist.source).lower():
                return 0.55
            return 0.25

        c = playlist.curator
        score = 0.2

        if c.email:
            score += 0.45
        if c.instagram:
            score += 0.25
        if c.website:
            score += 0.15

        return min(1.0, round(score, 3))

    def _score_risk(self, playlist: Playlist) -> float:
        """Negative score for red flags."""
        text = " ".join([
            (playlist.description or "").lower(),
            (playlist.submission_guidelines or "").lower(),
        ])

        penalty = 0.0
        for signal in self.config.bad_signals:
            if signal.lower() in text:
                penalty += 0.35

        # Very large playlists with no recent activity are risky
        if (playlist.follower_count or 0) > 100_000 and not playlist.last_activity_at:
            penalty += 0.20

        return min(0.6, round(penalty, 3))  # cap the penalty

    # -------------------------------------------------------------------------
    # Final composite + explanation
    # -------------------------------------------------------------------------

    def _compute_total(self, b: ScoreBreakdown) -> float:
        cfg = self.config

        positive = (
            b.activity_score * cfg.weight_activity +
            b.fit_score * cfg.weight_fit +
            b.openness_score * cfg.weight_openness +
            b.follower_score * cfg.weight_followers +
            b.contact_quality_score * cfg.weight_contact +
            b.personal_history_bonus * cfg.weight_history
        )

        # Apply risk penalty
        total = positive - (b.risk_penalty * cfg.risk_penalty_weight)
        return round(max(0.0, min(100.0, total * 100)), 1)

    def _generate_explanation(self, playlist: Playlist, b: ScoreBreakdown) -> str:
        reasons = []

        if b.activity_score > 0.75:
            reasons.append("very active recently")
        elif b.activity_score < 0.4:
            reasons.append("low recent activity")

        if b.fit_score > 0.75:
            reasons.append("strong stylistic fit")
        elif b.fit_score > 0.55:
            reasons.append("decent fit")

        if b.openness_score > 0.7:
            reasons.append("clearly open to submissions")

        if b.follower_score > 0.7:
            reasons.append("good reach")
        elif b.follower_score < 0.3:
            reasons.append("small audience")

        if b.risk_penalty > 0.2:
            reasons.append("some risk signals detected")

        if not reasons:
            reasons.append("balanced profile")

        return ", ".join(reasons).capitalize() + "."
