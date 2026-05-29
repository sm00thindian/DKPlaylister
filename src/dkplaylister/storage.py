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

from dkplaylister.models import StyleProfile


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
