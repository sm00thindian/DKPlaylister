"""Core data models for DKPlaylister."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class Platform(str, Enum):
    SPOTIFY = "spotify"
    YOUTUBE = "youtube"
    SOUNDCLOUD = "soundcloud"
    OTHER = "other"


class SubmissionStatus(str, Enum):
    NOT_CONTACTED = "not_contacted"
    PITCH_SENT = "pitch_sent"
    FOLLOWED_UP = "followed_up"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NO_RESPONSE = "no_response"
    OPTED_OUT = "opted_out"


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


class Playlist(BaseModel):
    """A music playlist that may accept submissions."""

    id: Optional[int] = None
    platform: Platform
    external_id: str  # e.g. Spotify playlist ID
    name: str
    url: HttpUrl
    description: Optional[str] = None
    curator: Optional[Curator] = None
    follower_count: Optional[int] = None
    track_count: Optional[int] = None
    genres: list[str] = Field(default_factory=list)
    moods: list[str] = Field(default_factory=list)
    is_accepting_submissions: Optional[bool] = None
    submission_guidelines: Optional[str] = None
    last_checked: Optional[datetime] = None
    tags: list[str] = Field(default_factory=list)  # e.g. ["lofi", "chill", "submissions-open"]
    notes: Optional[str] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class Submission(BaseModel):
    """Record of outreach to a playlist/curator."""

    id: Optional[int] = None
    playlist_id: int
    track_title: str
    artist: str
    genre: Optional[str] = None
    release_date: Optional[datetime] = None
    pitch_text: Optional[str] = None
    status: SubmissionStatus = SubmissionStatus.NOT_CONTACTED
    sent_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    response_notes: Optional[str] = None
    follow_up_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SearchQuery(BaseModel):
    """Parameters for discovering playlists."""

    keywords: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    min_followers: int = 100
    max_followers: Optional[int] = None
    platforms: list[Platform] = Field(default_factory=lambda: [Platform.SPOTIFY])
    limit: int = 50
