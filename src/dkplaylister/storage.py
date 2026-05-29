"""Local persistence layer using SQLite + SQLAlchemy.

This module provides:
- ORM models (DB layer)
- Engine/session helpers
- Repository classes for clean data access
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import JSON, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from dkplaylister.models import Playlist, PlaylistSource, Platform, StyleProfile, ScoreBreakdown


class Base(DeclarativeBase):
    pass


# =============================================================================
# ORM Models
# =============================================================================

class StyleProfileDB(Base):
    """Database representation of a StyleProfile."""

    __tablename__ = "style_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(default="Default")
    raw_prompt: Mapped[str]

    # Structured fields stored as JSON for flexibility
    primary_genres: Mapped[list[str]] = mapped_column(JSON, default=list)
    secondary_genres: Mapped[list[str]] = mapped_column(JSON, default=list)
    bpm_range: Mapped[str] = mapped_column(default="60-110")  # stored as string "min-max"
    energy_level: Mapped[str] = mapped_column(default="medium")
    mood_keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    sonic_characteristics: Mapped[list[str]] = mapped_column(JSON, default=list)
    vocal_style: Mapped[Optional[str]] = mapped_column(default=None)
    production_notes: Mapped[Optional[str]] = mapped_column(default=None)
    target_audience: Mapped[Optional[str]] = mapped_column(default=None)
    similar_artists: Mapped[list[str]] = mapped_column(JSON, default=list)

    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    def to_pydantic(self) -> StyleProfile:
        """Convert DB row to Pydantic StyleProfile model."""
        bpm_parts = self.bpm_range.split("-")
        bpm = (int(bpm_parts[0]), int(bpm_parts[1])) if len(bpm_parts) == 2 else (60, 110)

        return StyleProfile(
            id=self.id,
            name=self.name,
            raw_prompt=self.raw_prompt,
            primary_genres=self.primary_genres or [],
            secondary_genres=self.secondary_genres or [],
            bpm_range=bpm,
            energy_level=self.energy_level,  # type: ignore
            mood_keywords=self.mood_keywords or [],
            sonic_characteristics=self.sonic_characteristics or [],
            vocal_style=self.vocal_style,
            production_notes=self.production_notes,
            target_audience=self.target_audience,
            similar_artists=self.similar_artists or [],
            version=self.version,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class PlaylistDB(Base):
    """Database representation of a Playlist target."""

    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    platform: Mapped[str]
    external_id: Mapped[str]
    name: Mapped[str]
    url: Mapped[str]
    description: Mapped[Optional[str]] = mapped_column(default=None)

    source: Mapped[str] = mapped_column(default=PlaylistSource.SPOTIFY_DIRECT.value)
    discovery_query: Mapped[Optional[str]] = mapped_column(default=None)   # e.g. "Indie Cinematic" from Playlister

    follower_count: Mapped[Optional[int]] = mapped_column(default=None)
    track_count: Mapped[Optional[int]] = mapped_column(default=None)

    # JSON fields
    genres: Mapped[list[str]] = mapped_column(JSON, default=list)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)

    # Scoring
    current_score_json: Mapped[Optional[str]] = mapped_column(default=None)  # Store ScoreBreakdown as JSON

    # User data
    notes: Mapped[Optional[str]] = mapped_column(default=None)
    do_not_contact: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    def to_pydantic(self) -> Playlist:
        score = None
        if self.current_score_json:
            try:
                data = json.loads(self.current_score_json)
                score = ScoreBreakdown(**data)
            except Exception:
                pass

        return Playlist(
            id=self.id,
            platform=Platform(self.platform),
            external_id=self.external_id,
            name=self.name,
            url=self.url,
            description=self.description,
            source=PlaylistSource(self.source),
            discovery_query=self.discovery_query,
            follower_count=self.follower_count,
            track_count=self.track_count,
            genres=self.genres or [],
            tags=self.tags or [],
            current_score=score,
            notes=self.notes,
            do_not_contact=self.do_not_contact,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


# =============================================================================
# Engine & Session helpers
# =============================================================================

def get_engine(db_path: Optional[Path] = None):
    """Get SQLAlchemy engine. Defaults to data/dkplaylister.db"""
    if db_path is None:
        db_path = Path("data") / "dkplaylister.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{db_path}", echo=False)


def get_session(db_path: Optional[Path] = None):
    """Get a new session (creates tables if they don't exist)."""
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


# =============================================================================
# Repositories
# =============================================================================

class StyleProfileRepository:
    """Data access layer for StyleProfiles."""

    def __init__(self, session=None):
        self.session = session or get_session()

    def create(self, profile: StyleProfile) -> StyleProfileDB:
        """Create a new StyleProfile in the database."""
        bpm_str = f"{profile.bpm_range[0]}-{profile.bpm_range[1]}"

        db_profile = StyleProfileDB(
            name=profile.name,
            raw_prompt=profile.raw_prompt,
            primary_genres=profile.primary_genres,
            secondary_genres=profile.secondary_genres,
            bpm_range=bpm_str,
            energy_level=profile.energy_level,
            mood_keywords=profile.mood_keywords,
            sonic_characteristics=profile.sonic_characteristics,
            vocal_style=profile.vocal_style,
            production_notes=profile.production_notes,
            target_audience=profile.target_audience,
            similar_artists=profile.similar_artists,
            version=profile.version,
        )
        self.session.add(db_profile)
        self.session.commit()
        self.session.refresh(db_profile)
        return db_profile

    def get_by_id(self, profile_id: int) -> Optional[StyleProfile]:
        """Fetch a StyleProfile by ID and return as Pydantic model."""
        db_obj = self.session.get(StyleProfileDB, profile_id)
        return db_obj.to_pydantic() if db_obj else None

    def get_latest(self) -> Optional[StyleProfile]:
        """Return the most recently updated StyleProfile."""
        db_obj = (
            self.session.query(StyleProfileDB)
            .order_by(StyleProfileDB.updated_at.desc())
            .first()
        )
        return db_obj.to_pydantic() if db_obj else None

    def list_all(self) -> list[StyleProfile]:
        """Return all StyleProfiles (newest first)."""
        results = (
            self.session.query(StyleProfileDB)
            .order_by(StyleProfileDB.updated_at.desc())
            .all()
        )
        return [r.to_pydantic() for r in results]

    def update(self, profile: StyleProfile) -> Optional[StyleProfile]:
        """Update an existing StyleProfile."""
        if profile.id is None:
            return None

        db_obj = self.session.get(StyleProfileDB, profile.id)
        if not db_obj:
            return None

        bpm_str = f"{profile.bpm_range[0]}-{profile.bpm_range[1]}"

        db_obj.name = profile.name
        db_obj.raw_prompt = profile.raw_prompt
        db_obj.primary_genres = profile.primary_genres
        db_obj.secondary_genres = profile.secondary_genres
        db_obj.bpm_range = bpm_str
        db_obj.energy_level = profile.energy_level
        db_obj.mood_keywords = profile.mood_keywords
        db_obj.sonic_characteristics = profile.sonic_characteristics
        db_obj.vocal_style = profile.vocal_style
        db_obj.production_notes = profile.production_notes
        db_obj.target_audience = profile.target_audience
        db_obj.similar_artists = profile.similar_artists
        db_obj.version = profile.version

        self.session.commit()
        self.session.refresh(db_obj)
        return db_obj.to_pydantic()

    def delete(self, profile_id: int) -> bool:
        """Delete a StyleProfile by ID."""
        db_obj = self.session.get(StyleProfileDB, profile_id)
        if not db_obj:
            return False
        self.session.delete(db_obj)
        self.session.commit()
        return True


# =============================================================================
# Playlist Repository
# =============================================================================

class PlaylistRepository:
    """Data access for playlist targets with scoring support."""

    def __init__(self, session=None):
        self.session = session or get_session()

    def create_or_update(self, playlist: Playlist) -> PlaylistDB:
        """Create or update a playlist record (by platform + external_id)."""
        existing = (
            self.session.query(PlaylistDB)
            .filter_by(platform=playlist.platform.value, external_id=playlist.external_id)
            .first()
        )

        score_json = None
        if playlist.current_score:
            try:
                score_json = playlist.current_score.model_dump_json()
            except Exception:
                score_json = None

        if existing:
            existing.name = playlist.name
            existing.description = playlist.description
            existing.url = str(playlist.url)
            existing.follower_count = playlist.follower_count
            existing.track_count = playlist.track_count
            existing.genres = playlist.genres
            existing.tags = playlist.tags
            existing.current_score_json = score_json
            existing.source = playlist.source.value
            existing.discovery_query = playlist.discovery_query or existing.discovery_query
            existing.notes = playlist.notes or existing.notes
            existing.do_not_contact = playlist.do_not_contact

            self.session.commit()
            self.session.refresh(existing)
            return existing
        else:
            db_obj = PlaylistDB(
                platform=playlist.platform.value,
                external_id=playlist.external_id,
                name=playlist.name,
                url=str(playlist.url),
                description=playlist.description,
                source=playlist.source.value,
                discovery_query=playlist.discovery_query,
                follower_count=playlist.follower_count,
                track_count=playlist.track_count,
                genres=playlist.genres or [],
                tags=playlist.tags or [],
                current_score_json=score_json,
                notes=playlist.notes,
                do_not_contact=playlist.do_not_contact,
            )
            self.session.add(db_obj)
            self.session.commit()
            self.session.refresh(db_obj)
            return db_obj

    def get_by_id(self, playlist_id: int) -> Optional[Playlist]:
        db_obj = self.session.get(PlaylistDB, playlist_id)
        return db_obj.to_pydantic() if db_obj else None

    def list_all(self, min_score: Optional[float] = None) -> list[Playlist]:
        """Return playlists, optionally filtered by minimum value score."""
        db_playlists = (
            self.session.query(PlaylistDB)
            .order_by(PlaylistDB.updated_at.desc())
            .all()
        )

        results = []
        for db_p in db_playlists:
            p = db_p.to_pydantic()
            if min_score is not None and p.current_score:
                if p.current_score.total_value_score < min_score:
                    continue
            results.append(p)
        return results

    def count(self) -> int:
        return self.session.query(PlaylistDB).count()
