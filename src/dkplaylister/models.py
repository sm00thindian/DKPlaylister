"""Core data models for DKPlaylister.

This module defines the central concepts:
- StyleProfile: Your music's detailed DNA (the foundation)
- Playlist: Enriched targets with provenance and scoring
- Pitch: LLM-generated (and human-refined) submissions
- Supporting workflow models
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Literal

from pydantic import BaseModel, Field, HttpUrl, ConfigDict


# =============================================================================
# Enums
# =============================================================================

class Platform(str, Enum):
    SPOTIFY = "spotify"
    YOUTUBE = "youtube"
    SOUNDCLOUD = "soundcloud"
    OTHER = "other"


class PlaylistSource(str, Enum):
    """Where this playlist target was originally discovered."""
    PLAYLISTER = "playlister"
    SPOTIFY_DIRECT = "spotify_direct"
    MANUAL = "manual"
    IMPORT = "import"
    OTHER = "other"


class SubmissionStatus(str, Enum):
    NOT_CONTACTED = "not_contacted"
    PITCH_SENT = "pitch_sent"
    FOLLOWED_UP = "followed_up"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NO_RESPONSE = "no_response"
    OPTED_OUT = "opted_out"


class PitchFormat(str, Enum):
    EMAIL = "email"
    INSTAGRAM_DM = "instagram_dm"
    SUBMISSION_FORM = "submission_form"
    TIKTOK_COMMENT = "tiktok_comment"
    OTHER = "other"


class OperatingMode(str, Enum):
    SEMI_AUTOMATIC = "semi_automatic"   # Default
    INTERACTIVE = "interactive"
    AUTOMATIC = "automatic"


# =============================================================================
# Multi-Band Support (New in v2)
# =============================================================================

class Band(BaseModel):
    """An artist or band that can have multiple styles and songs."""

    id: Optional[int] = None
    name: str
    slug: str  # e.g. "kilynn-ross" — used for folder organization
    notes: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class Song(BaseModel):
    """A song with lyrics belonging to a specific band."""

    id: Optional[int] = None
    band_id: int
    title: str
    lyrics: str
    notes: Optional[str] = None

    # Optional metadata
    key: Optional[str] = None
    tempo: Optional[int] = None
    duration_seconds: Optional[int] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


# =============================================================================
# StyleProfile - The heart of the system
# =============================================================================

class StyleProfile(BaseModel):
    """Rich, structured description of an artist's music.

    This is the single source of truth that drives genre expansion,
    fit scoring, and personalized pitch generation.

    In v2, styles belong to a specific Band.
    """

    id: Optional[int] = None
    band_id: Optional[int] = None   # New in v2 — null during transition period
    name: str = "Default"
    raw_prompt: str = Field(..., description="The full, detailed style description provided by the user")
    primary_genres: list[str] = Field(default_factory=list)
    secondary_genres: list[str] = Field(default_factory=list)
    bpm_range: tuple[int, int] = (60, 110)
    energy_level: Literal["low", "medium-low", "medium", "medium-high", "high"] = "medium"
    mood_keywords: list[str] = Field(default_factory=list)
    sonic_characteristics: list[str] = Field(default_factory=list)  # e.g. "reverb-drenched", "jangly", "cinematic"
    vocal_style: Optional[str] = None
    production_notes: Optional[str] = None
    target_audience: Optional[str] = None
    similar_artists: list[str] = Field(default_factory=list)

    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


# =============================================================================
# Scoring & Prioritization
# =============================================================================

class ScoreBreakdown(BaseModel):
    """Explainable scoring for a playlist against a StyleProfile."""

    activity_score: float = 0.0          # 0-1
    fit_score: float = 0.0               # 0-1 (semantic + keyword)
    openness_score: float = 0.0          # 0-1
    follower_score: float = 0.0          # log-scaled
    contact_quality_score: float = 0.0
    risk_penalty: float = 0.0            # negative or zero
    personal_history_bonus: float = 0.0

    total_value_score: float = 0.0       # Final composite (0-100 or 0-1)

    explanation: Optional[str] = None    # Human-readable reason for the score


class Playlist(BaseModel):
    """A music playlist that may accept submissions.

    Heavily enriched with provenance, scoring, and activity signals.
    """

    id: Optional[int] = None

    # Core identity
    platform: Platform
    external_id: str
    name: str
    url: HttpUrl
    description: Optional[str] = None

    # Provenance
    source: PlaylistSource = PlaylistSource.SPOTIFY_DIRECT
    discovery_query: Optional[str] = None          # e.g. Playlister search term
    discovered_at: datetime = Field(default_factory=datetime.utcnow)

    # Curator
    curator: Optional["Curator"] = None

    # Metrics
    follower_count: Optional[int] = None
    track_count: Optional[int] = None
    last_activity_at: Optional[datetime] = None    # When it last added a track (best effort)

    # Classification
    genres: list[str] = Field(default_factory=list)
    moods: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    # Submission signals
    is_accepting_submissions: Optional[bool] = None
    submission_guidelines: Optional[str] = None
    contact_revealed_via: Optional[str] = None     # e.g. "playlister_popup", "description"

    # Scoring (populated when evaluated against a StyleProfile)
    current_score: Optional[ScoreBreakdown] = None
    score_history: list[ScoreBreakdown] = Field(default_factory=list)

    # User annotations
    notes: Optional[str] = None
    user_rating: Optional[int] = None              # 1-5
    do_not_contact: bool = False

    last_checked: Optional[datetime] = None

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


# =============================================================================
# Curator
# =============================================================================

class Curator(BaseModel):
    """A playlist curator or playlist owner."""

    id: Optional[int] = None
    name: Optional[str] = None
    email: Optional[str] = None
    instagram: Optional[str] = None
    twitter: Optional[str] = None
    tiktok: Optional[str] = None
    website: Optional[str] = None
    other_links: list[str] = Field(default_factory=list)
    notes: Optional[str] = None

    last_contacted_at: Optional[datetime] = None
    response_rate: Optional[float] = None   # 0-1, learned over time


# =============================================================================
# Pitch Generation
# =============================================================================

class Pitch(BaseModel):
    """A generated (and potentially edited) submission for a specific song + target."""

    id: Optional[int] = None

    band_id: Optional[int] = None          # New in v2
    style_profile_id: int
    song_id: Optional[int] = None          # Preferred over raw title/lyrics in v2
    playlist_id: int

    song_title: str                        # Kept for backward compat / display
    song_lyrics: Optional[str] = None      # Kept for backward compat

    format: PitchFormat = PitchFormat.EMAIL

    # Generation metadata
    llm_provider: str = "grok"
    llm_model: str
    prompt_version: str = "v1"

    generated_text: str
    user_edited_text: Optional[str] = None

    # Final text actually used (falls back to edited → generated)
    final_text: Optional[str] = None

    # Tracking
    sent: bool = False
    sent_at: Optional[datetime] = None
    submission_id: Optional[int] = None   # Link to Submission record

    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


# =============================================================================
# Submission Record (outreach history)
# =============================================================================

class Submission(BaseModel):
    """Record of actual outreach to a playlist/curator."""

    id: Optional[int] = None
    playlist_id: int
    pitch_id: Optional[int] = None

    track_title: str
    artist: str = "DK"   # TODO: make configurable

    status: SubmissionStatus = SubmissionStatus.NOT_CONTACTED
    pitch_text_used: Optional[str] = None

    sent_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    response_notes: Optional[str] = None
    follow_up_count: int = 0

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


# =============================================================================
# Supporting / Future
# =============================================================================

class MiningRun(BaseModel):
    """A recorded mining / discovery session against a StyleProfile."""

    id: Optional[int] = None
    style_profile_id: int
    operating_mode: OperatingMode = OperatingMode.SEMI_AUTOMATIC
    query: Optional[str] = None
    min_followers: int = 1000
    playlists_found: int = 0
    playlists_imported: int = 0
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


# Rebuild forward refs
Playlist.model_rebuild()
