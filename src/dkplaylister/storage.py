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

from dkplaylister.models import (
    Band, Song, Album, Playlist, Curator, PlaylistSource, Platform, 
    StyleProfile, ScoreBreakdown, Pitch, PitchFormat, SubmissionStatus,
    MiningRun, OperatingMode
)


class Base(DeclarativeBase):
    pass


# =============================================================================
# ORM Models
# =============================================================================

class StyleProfileDB(Base):
    """Database representation of a StyleProfile."""

    __tablename__ = "style_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    band_id: Mapped[Optional[int]] = mapped_column(default=None)  # v2
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
            band_id=self.band_id,
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

    # Contact / Curator enrichment (new for contact mining)
    curator_json: Mapped[Optional[str]] = mapped_column(default=None)
    contact_revealed_via: Mapped[Optional[str]] = mapped_column(default=None)

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

        curator = None
        if self.curator_json:
            try:
                cdata = json.loads(self.curator_json)
                curator = Curator(**cdata)
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
            curator=curator,
            contact_revealed_via=self.contact_revealed_via,
            current_score=score,
            notes=self.notes,
            do_not_contact=self.do_not_contact,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class BandDB(Base):
    """Database representation of a Band."""

    __tablename__ = "bands"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str]
    slug: Mapped[str] = mapped_column(unique=True)
    notes: Mapped[Optional[str]] = mapped_column(default=None)

    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())


class SongDB(Base):
    """Database representation of a Song with lyrics."""

    __tablename__ = "songs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    band_id: Mapped[int]
    album_id: Mapped[Optional[int]] = mapped_column(default=None)
    title: Mapped[str]
    lyrics: Mapped[str]
    notes: Mapped[Optional[str]] = mapped_column(default=None)

    key: Mapped[Optional[str]] = mapped_column(default=None)
    tempo: Mapped[Optional[int]] = mapped_column(default=None)
    duration_seconds: Mapped[Optional[int]] = mapped_column(default=None)

    # Streaming links after release (stored as JSON: {"spotify": "...", "apple_music": "...", ...})
    streaming_links: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())


class AlbumDB(Base):
    """Database representation of an Album / Release."""

    __tablename__ = "albums"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    band_id: Mapped[int]
    title: Mapped[str]
    release_date: Mapped[Optional[str]] = mapped_column(default=None)
    notes: Mapped[Optional[str]] = mapped_column(default=None)

    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())


class PitchDB(Base):
    """Database representation of a generated Pitch."""

    __tablename__ = "pitches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    band_id: Mapped[Optional[int]] = mapped_column(default=None)
    style_profile_id: Mapped[int]
    song_id: Mapped[Optional[int]] = mapped_column(default=None)
    playlist_id: Mapped[int]

    song_title: Mapped[str]
    song_lyrics: Mapped[Optional[str]] = mapped_column(default=None)

    format: Mapped[str] = mapped_column(default=PitchFormat.EMAIL.value)

    llm_provider: Mapped[str] = mapped_column(default="grok")
    llm_model: Mapped[str]
    prompt_version: Mapped[str] = mapped_column(default="v1")

    generated_text: Mapped[str]
    user_edited_text: Mapped[Optional[str]] = mapped_column(default=None)
    final_text: Mapped[Optional[str]] = mapped_column(default=None)

    sent: Mapped[bool] = mapped_column(default=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    submission_id: Mapped[Optional[int]] = mapped_column(default=None)

    created_at: Mapped[datetime] = mapped_column(default=func.now())


class SubmissionDB(Base):
    """Database representation of a Submission (outreach record)."""

    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    band_id: Mapped[Optional[int]] = mapped_column(default=None)
    playlist_id: Mapped[int]
    song_id: Mapped[Optional[int]] = mapped_column(default=None)
    pitch_id: Mapped[Optional[int]] = mapped_column(default=None)

    status: Mapped[str] = mapped_column(default=SubmissionStatus.PITCH_SENT.value)
    sent_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    notes: Mapped[Optional[str]] = mapped_column(default=None)

    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())


class MiningRunDB(Base):
    """Database representation of a MiningRun (Phase 1 discovery session)."""

    __tablename__ = "mining_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    band_id: Mapped[Optional[int]] = mapped_column(default=None)
    style_profile_id: Mapped[int]
    style_profile_name: Mapped[Optional[str]] = mapped_column(default=None)

    operating_mode: Mapped[str] = mapped_column(default="semi_automatic")

    queries_used_json: Mapped[Optional[str]] = mapped_column(default=None)  # JSON list
    min_followers: Mapped[int] = mapped_column(default=1000)
    expansion_explanation: Mapped[Optional[str]] = mapped_column(default=None)

    playlists_found: Mapped[int] = mapped_column(default=0)
    playlists_imported: Mapped[int] = mapped_column(default=0)
    top_score: Mapped[Optional[float]] = mapped_column(default=None)

    notes: Mapped[Optional[str]] = mapped_column(default=None)

    started_at: Mapped[datetime] = mapped_column(default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(default=None)


# =============================================================================
# Engine & Session helpers
# =============================================================================

def get_engine(db_path: Optional[Path] = None):
    """Get SQLAlchemy engine. Defaults to data/dkplaylister.db"""
    if db_path is None:
        db_path = Path("data") / "dkplaylister.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{db_path}", echo=False)


# Module-level guard so we only attempt Alembic upgrade once per process
# (prevents log spam on every get_session() call in Streamlit dev mode)
_alembic_upgraded = False


def get_session(db_path: Optional[Path] = None):
    """Get a new session (creates tables if they don't exist)."""
    global _alembic_upgraded

    engine = get_engine(db_path)

    # Run Alembic migrations if available (preferred path)
    if not _alembic_upgraded:
        import logging
        alembic_logger = logging.getLogger("alembic")
        original_level = alembic_logger.level
        alembic_logger.setLevel(logging.WARNING)  # Suppress noisy INFO during startup

        try:
            from alembic.config import Config
            from alembic import command
            from alembic.migration import MigrationContext

            alembic_cfg = Config("alembic.ini")
            if db_path:
                alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

            # Quiet revision check (no stdout, minimal logging)
            current_rev = None
            try:
                with engine.connect() as connection:
                    context = MigrationContext.configure(connection)
                    current_rev = context.get_current_revision()
            except Exception:
                current_rev = None

            if current_rev is None or "8efdfa768246" not in str(current_rev):
                command.upgrade(alembic_cfg, "head")

            _alembic_upgraded = True

        except Exception:
            # Fallback path (legacy manual migrations)
            Base.metadata.create_all(engine)
            _run_legacy_migrations(engine)

            # Auto-stamp if modern tables exist but Alembic version is stale
            try:
                from sqlalchemy import inspect
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                if "pitches" in tables or "mining_runs" in tables:
                    from alembic.config import Config
                    from alembic import command
                    alembic_cfg = Config("alembic.ini")
                    if db_path:
                        alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
                    command.stamp(alembic_cfg, "head")
            except Exception:
                pass

            _alembic_upgraded = True

        finally:
            # Always restore logging level
            alembic_logger.setLevel(original_level)
    else:
        # After first successful run in this process, just ensure tables exist
        Base.metadata.create_all(engine)

    return sessionmaker(bind=engine)()


def _run_legacy_migrations(engine):
    """Temporary fallback for legacy manual migrations during transition to Alembic."""
    _migrate_add_band_id_to_styles(engine)
    _migrate_add_album_id_to_songs(engine)
    _migrate_add_contact_fields_to_playlists(engine)
    _migrate_add_streaming_links_to_songs(engine)


def _migrate_add_band_id_to_styles(engine):
    """Safe migration to add band_id column to style_profiles table."""
    with engine.connect() as conn:
        try:
            # Check if column exists (SQLite specific)
            result = conn.exec_driver_sql("PRAGMA table_info(style_profiles)")
            columns = [row[1] for row in result.fetchall()]
            if "band_id" not in columns:
                conn.exec_driver_sql("ALTER TABLE style_profiles ADD COLUMN band_id INTEGER")
                conn.commit()
        except Exception:
            # Column might already exist or table doesn't exist yet — safe to ignore
            pass


def _migrate_add_album_id_to_songs(engine):
    """Safe migration to add album_id column to songs table."""
    with engine.connect() as conn:
        try:
            result = conn.exec_driver_sql("PRAGMA table_info(songs)")
            columns = [row[1] for row in result.fetchall()]
            if "album_id" not in columns:
                conn.exec_driver_sql("ALTER TABLE songs ADD COLUMN album_id INTEGER")
                conn.commit()
        except Exception:
            pass


def _migrate_add_contact_fields_to_playlists(engine):
    """Safe migration for curator contact mining (curator_json + contact_revealed_via)."""
    with engine.connect() as conn:
        try:
            result = conn.exec_driver_sql("PRAGMA table_info(playlists)")
            columns = [row[1] for row in result.fetchall()]
            if "curator_json" not in columns:
                conn.exec_driver_sql("ALTER TABLE playlists ADD COLUMN curator_json TEXT")
            if "contact_revealed_via" not in columns:
                conn.exec_driver_sql("ALTER TABLE playlists ADD COLUMN contact_revealed_via TEXT")
            conn.commit()
        except Exception:
            pass


def _migrate_add_streaming_links_to_songs(engine):
    """Safe migration to add streaming_links JSON column to songs table."""
    with engine.connect() as conn:
        try:
            result = conn.exec_driver_sql("PRAGMA table_info(songs)")
            columns = [row[1] for row in result.fetchall()]
            if "streaming_links" not in columns:
                conn.exec_driver_sql("ALTER TABLE songs ADD COLUMN streaming_links TEXT")
                conn.commit()
        except Exception:
            pass


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
            band_id=profile.band_id,
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

    def get_latest(self, band_id: Optional[int] = None) -> Optional[StyleProfile]:
        """Return the most recently updated StyleProfile (optionally scoped to a band)."""
        query = self.session.query(StyleProfileDB)
        if band_id is not None:
            query = query.filter(StyleProfileDB.band_id == band_id)
        db_obj = query.order_by(StyleProfileDB.updated_at.desc()).first()
        return db_obj.to_pydantic() if db_obj else None

    def list_all(self, band_id: Optional[int] = None) -> list[StyleProfile]:
        """Return all StyleProfiles (newest first, optionally filtered by band)."""
        query = self.session.query(StyleProfileDB)
        if band_id is not None:
            query = query.filter(StyleProfileDB.band_id == band_id)
        results = query.order_by(StyleProfileDB.updated_at.desc()).all()
        return [r.to_pydantic() for r in results]

    def update(self, profile: StyleProfile) -> Optional[StyleProfile]:
        """Update an existing StyleProfile."""
        if profile.id is None:
            return None

        db_obj = self.session.get(StyleProfileDB, profile.id)
        if not db_obj:
            return None

        bpm_str = f"{profile.bpm_range[0]}-{profile.bpm_range[1]}"

        db_obj.band_id = profile.band_id
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

    def migrate_legacy_styles_to_band(self, band_id: int) -> int:
        """Assigns styles with no band_id to the given band. Returns count updated."""
        updated = (
            self.session.query(StyleProfileDB)
            .filter(StyleProfileDB.band_id.is_(None))
            .update({StyleProfileDB.band_id: band_id})
        )
        self.session.commit()
        return updated


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

        curator_json = None
        if playlist.curator:
            try:
                curator_json = playlist.curator.model_dump_json()
            except Exception:
                curator_json = None

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
            existing.curator_json = curator_json
            existing.contact_revealed_via = playlist.contact_revealed_via or existing.contact_revealed_via

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
                curator_json=curator_json,
                contact_revealed_via=playlist.contact_revealed_via,
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

    def clear_all(self) -> int:
        """Delete all playlist targets. Returns number deleted. Use with extreme caution."""
        count = self.session.query(PlaylistDB).count()
        self.session.query(PlaylistDB).delete()
        self.session.commit()
        return count


# =============================================================================
# Band & Song Repositories (v2)
# =============================================================================

class BandRepository:
    """Data access for Bands."""

    def __init__(self, session=None):
        self.session = session or get_session()

    def create(self, band: Band) -> BandDB:
        db_band = BandDB(
            name=band.name,
            slug=band.slug,
            notes=band.notes,
        )
        self.session.add(db_band)
        self.session.commit()
        self.session.refresh(db_band)
        return db_band

    def get_by_id(self, band_id: int) -> Optional[Band]:
        db_obj = self.session.get(BandDB, band_id)
        if not db_obj:
            return None
        return Band(
            id=db_obj.id,
            name=db_obj.name,
            slug=db_obj.slug,
            notes=db_obj.notes,
            created_at=db_obj.created_at,
            updated_at=db_obj.updated_at,
        )

    def get_by_slug(self, slug: str) -> Optional[Band]:
        db_obj = self.session.query(BandDB).filter_by(slug=slug).first()
        if not db_obj:
            return None
        return Band(
            id=db_obj.id,
            name=db_obj.name,
            slug=db_obj.slug,
            notes=db_obj.notes,
            created_at=db_obj.created_at,
            updated_at=db_obj.updated_at,
        )

    def list_all(self) -> list[Band]:
        db_bands = self.session.query(BandDB).order_by(BandDB.name).all()
        return [
            Band(
                id=b.id,
                name=b.name,
                slug=b.slug,
                notes=b.notes,
                created_at=b.created_at,
                updated_at=b.updated_at,
            )
            for b in db_bands
        ]

    def get_default(self) -> Optional[Band]:
        """Return the first band (useful as a default during transition)."""
        db_obj = self.session.query(BandDB).order_by(BandDB.id).first()
        if not db_obj:
            return None
        return Band(
            id=db_obj.id,
            name=db_obj.name,
            slug=db_obj.slug,
            notes=db_obj.notes,
            created_at=db_obj.created_at,
            updated_at=db_obj.updated_at,
        )

    def get_or_create_default(self, name: str = "Personal", slug: str = "personal") -> Band:
        """Get the first band, or create a default one if none exists."""
        existing = self.get_default()
        if existing:
            return existing

        new_band = Band(name=name, slug=slug)
        db_band = self.create(new_band)
        return Band(
            id=db_band.id,
            name=db_band.name,
            slug=db_band.slug,
            notes=db_band.notes,
            created_at=db_band.created_at,
            updated_at=db_band.updated_at,
        )

    def migrate_legacy_styles_to_default_band(self) -> int:
        """
        Phase 0 migration helper:
        Assigns all styles that have band_id=NULL to the default band.
        Returns number of styles updated.
        """
        default_band = self.get_or_create_default()
        if not default_band:
            return 0

        updated = (
            self.session.query(StyleProfileDB)
            .filter(StyleProfileDB.band_id.is_(None))
            .update({StyleProfileDB.band_id: default_band.id})
        )
        self.session.commit()
        return updated

    def set_default(self, band_id: int) -> bool:
        """Mark a band as the default (simple implementation: we just return it as default)."""
        band = self.get_by_id(band_id)
        return band is not None

    def update(self, band: Band) -> Optional[Band]:
        if band.id is None:
            return None
        db_obj = self.session.get(BandDB, band.id)
        if not db_obj:
            return None

        db_obj.name = band.name
        db_obj.slug = band.slug
        db_obj.notes = band.notes

        self.session.commit()
        self.session.refresh(db_obj)
        return self.get_by_id(db_obj.id)

    def delete(self, band_id: int) -> bool:
        db_obj = self.session.get(BandDB, band_id)
        if not db_obj:
            return False
        self.session.delete(db_obj)
        self.session.commit()
        return True


class SongRepository:
    """Data access for Songs."""

    def __init__(self, session=None):
        self.session = session or get_session()

    def create(self, song: Song) -> SongDB:
        db_song = SongDB(
            band_id=song.band_id,
            album_id=song.album_id,
            title=song.title,
            lyrics=song.lyrics,
            notes=song.notes,
            key=song.key,
            tempo=song.tempo,
            duration_seconds=song.duration_seconds,
            streaming_links=song.streaming_links or {},
        )
        self.session.add(db_song)
        self.session.commit()
        self.session.refresh(db_song)
        return db_song

    def get_by_id(self, song_id: int) -> Optional[Song]:
        db_obj = self.session.get(SongDB, song_id)
        if not db_obj:
            return None
        return Song(
            id=db_obj.id,
            band_id=db_obj.band_id,
            album_id=db_obj.album_id,
            title=db_obj.title,
            lyrics=db_obj.lyrics,
            notes=db_obj.notes,
            key=db_obj.key,
            tempo=db_obj.tempo,
            duration_seconds=db_obj.duration_seconds,
            streaming_links=db_obj.streaming_links or {},
            created_at=db_obj.created_at,
            updated_at=db_obj.updated_at,
        )

    def list_by_band(self, band_id: int) -> list[Song]:
        db_songs = (
            self.session.query(SongDB)
            .filter_by(band_id=band_id)
            .order_by(SongDB.title)
            .all()
        )
        return [
            Song(
                id=s.id,
                band_id=s.band_id,
                album_id=s.album_id,
                title=s.title,
                lyrics=s.lyrics,
                notes=s.notes,
                key=s.key,
                tempo=s.tempo,
                duration_seconds=s.duration_seconds,
                streaming_links=s.streaming_links or {},
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in db_songs
        ]

    def update(self, song: Song) -> Optional[Song]:
        if song.id is None:
            return None
        db_obj = self.session.get(SongDB, song.id)
        if not db_obj or db_obj.band_id != song.band_id:
            return None

        db_obj.album_id = song.album_id
        db_obj.title = song.title
        db_obj.lyrics = song.lyrics
        db_obj.notes = song.notes
        db_obj.key = song.key
        db_obj.tempo = song.tempo
        db_obj.duration_seconds = song.duration_seconds
        db_obj.streaming_links = song.streaming_links or {}

        self.session.commit()
        self.session.refresh(db_obj)
        return self.get_by_id(db_obj.id)

    def delete(self, song_id: int) -> bool:
        db_obj = self.session.get(SongDB, song_id)
        if not db_obj:
            return False
        self.session.delete(db_obj)
        self.session.commit()
        return True


# =============================================================================
# Pitch Repository (Phase 0 Hardening)
# =============================================================================

class PitchRepository:
    """Data access for generated Pitches."""

    def __init__(self, session=None):
        self.session = session or get_session()

    def create(self, pitch: Pitch) -> PitchDB:
        db_pitch = PitchDB(
            band_id=pitch.band_id,
            style_profile_id=pitch.style_profile_id,
            song_id=pitch.song_id,
            playlist_id=pitch.playlist_id,
            song_title=pitch.song_title,
            song_lyrics=pitch.song_lyrics,
            format=pitch.format.value if hasattr(pitch.format, 'value') else pitch.format,
            llm_provider=pitch.llm_provider,
            llm_model=pitch.llm_model,
            prompt_version=pitch.prompt_version,
            generated_text=pitch.generated_text,
            user_edited_text=pitch.user_edited_text,
            final_text=pitch.final_text,
            sent=pitch.sent,
            sent_at=pitch.sent_at,
            submission_id=pitch.submission_id,
        )
        self.session.add(db_pitch)
        self.session.commit()
        self.session.refresh(db_pitch)
        return db_pitch

    def get_by_id(self, pitch_id: int) -> Optional[Pitch]:
        db_obj = self.session.get(PitchDB, pitch_id)
        if not db_obj:
            return None
        return self._to_pydantic(db_obj)

    def list_by_band(self, band_id: int) -> list[Pitch]:
        db_pitches = (
            self.session.query(PitchDB)
            .filter_by(band_id=band_id)
            .order_by(PitchDB.created_at.desc())
            .all()
        )
        return [self._to_pydantic(p) for p in db_pitches]

    def mark_sent(self, pitch_id: int) -> Optional[Pitch]:
        db_obj = self.session.get(PitchDB, pitch_id)
        if not db_obj:
            return None
        db_obj.sent = True
        db_obj.sent_at = datetime.utcnow()
        self.session.commit()
        return self._to_pydantic(db_obj)

    def _to_pydantic(self, db_obj: PitchDB) -> Pitch:
        fmt = db_obj.format
        try:
            pitch_format = PitchFormat(fmt)
        except ValueError:
            pitch_format = PitchFormat.EMAIL

        return Pitch(
            id=db_obj.id,
            band_id=db_obj.band_id,
            style_profile_id=db_obj.style_profile_id,
            song_id=db_obj.song_id,
            playlist_id=db_obj.playlist_id,
            song_title=db_obj.song_title,
            song_lyrics=db_obj.song_lyrics,
            format=pitch_format,
            llm_provider=db_obj.llm_provider,
            llm_model=db_obj.llm_model,
            prompt_version=db_obj.prompt_version,
            generated_text=db_obj.generated_text,
            user_edited_text=db_obj.user_edited_text,
            final_text=db_obj.final_text,
            sent=db_obj.sent,
            sent_at=db_obj.sent_at,
            submission_id=db_obj.submission_id,
            created_at=db_obj.created_at,
        )


class SubmissionRepository:
    """Basic data access for Submissions (Phase 0)."""

    def __init__(self, session=None):
        self.session = session or get_session()

    def create(self, submission) -> SubmissionDB:
        # submission can be a Pydantic Submission or a simple dict-like
        db_sub = SubmissionDB(
            band_id=getattr(submission, 'band_id', None),
            playlist_id=submission.playlist_id,
            song_id=getattr(submission, 'song_id', None),
            pitch_id=getattr(submission, 'pitch_id', None),
            status=getattr(submission, 'status', SubmissionStatus.PITCH_SENT).value 
                   if hasattr(getattr(submission, 'status', None), 'value') 
                   else str(getattr(submission, 'status', SubmissionStatus.PITCH_SENT)),
            sent_at=getattr(submission, 'sent_at', None),
            notes=getattr(submission, 'notes', None),
        )
        self.session.add(db_sub)
        self.session.commit()
        self.session.refresh(db_sub)
        return db_sub

    def list_by_band(self, band_id: int) -> list:
        """Return submissions for a specific band (P0-4 consistency)."""
        db_subs = (
            self.session.query(SubmissionDB)
            .filter_by(band_id=band_id)
            .order_by(SubmissionDB.created_at.desc())
            .all()
        )
        # Lightweight return; full _to_pydantic can be added later
        return db_subs


# =============================================================================
# MiningRun Repository (Phase 1)
# =============================================================================

class MiningRunRepository:
    """Data access for discovery/mining sessions (Phase 1)."""

    def __init__(self, session=None):
        self.session = session or get_session()

    def create(self, run: MiningRun) -> MiningRunDB:
        import json

        queries_json = json.dumps(run.queries_used) if run.queries_used else None

        db_run = MiningRunDB(
            band_id=run.band_id,
            style_profile_id=run.style_profile_id,
            style_profile_name=run.style_profile_name,
            operating_mode=run.operating_mode.value if hasattr(run.operating_mode, "value") else str(run.operating_mode),
            queries_used_json=queries_json,
            min_followers=run.min_followers,
            expansion_explanation=run.expansion_explanation,
            playlists_found=run.playlists_found,
            playlists_imported=run.playlists_imported,
            top_score=run.top_score,
            notes=run.notes,
            started_at=run.started_at,
            completed_at=run.completed_at,
        )
        self.session.add(db_run)
        self.session.commit()
        self.session.refresh(db_run)
        return db_run

    def get_by_id(self, run_id: int) -> Optional[MiningRun]:
        db_obj = self.session.get(MiningRunDB, run_id)
        if not db_obj:
            return None
        return self._to_pydantic(db_obj)

    def list_by_band(self, band_id: int, limit: int = 50) -> list[MiningRun]:
        db_runs = (
            self.session.query(MiningRunDB)
            .filter_by(band_id=band_id)
            .order_by(MiningRunDB.started_at.desc())
            .limit(limit)
            .all()
        )
        return [self._to_pydantic(r) for r in db_runs]

    def list_recent(self, limit: int = 20) -> list[MiningRun]:
        db_runs = (
            self.session.query(MiningRunDB)
            .order_by(MiningRunDB.started_at.desc())
            .limit(limit)
            .all()
        )
        return [self._to_pydantic(r) for r in db_runs]

    def _to_pydantic(self, db_obj: MiningRunDB) -> MiningRun:
        import json

        queries = []
        if db_obj.queries_used_json:
            try:
                queries = json.loads(db_obj.queries_used_json)
            except Exception:
                queries = []

        try:
            mode = OperatingMode(db_obj.operating_mode)
        except Exception:
            mode = OperatingMode.SEMI_AUTOMATIC

        return MiningRun(
            id=db_obj.id,
            band_id=db_obj.band_id,
            style_profile_id=db_obj.style_profile_id,
            style_profile_name=db_obj.style_profile_name,
            operating_mode=mode,
            queries_used=queries,
            min_followers=db_obj.min_followers,
            expansion_explanation=db_obj.expansion_explanation,
            playlists_found=db_obj.playlists_found,
            playlists_imported=db_obj.playlists_imported,
            top_score=db_obj.top_score,
            notes=db_obj.notes,
            started_at=db_obj.started_at,
            completed_at=db_obj.completed_at,
        )


# =============================================================================
# Album Repository
# =============================================================================

class AlbumRepository:
    """Data access for Albums."""

    def __init__(self, session=None):
        self.session = session or get_session()

    def create(self, album: Album) -> AlbumDB:
        db_album = AlbumDB(
            band_id=album.band_id,
            title=album.title,
            release_date=album.release_date,
            notes=album.notes,
        )
        self.session.add(db_album)
        self.session.commit()
        self.session.refresh(db_album)
        return db_album

    def get_by_id(self, album_id: int) -> Optional[Album]:
        db_obj = self.session.get(AlbumDB, album_id)
        if not db_obj:
            return None
        return Album(
            id=db_obj.id,
            band_id=db_obj.band_id,
            title=db_obj.title,
            release_date=db_obj.release_date,
            notes=db_obj.notes,
            created_at=db_obj.created_at,
            updated_at=db_obj.updated_at,
        )

    def list_by_band(self, band_id: int) -> list[Album]:
        db_albums = (
            self.session.query(AlbumDB)
            .filter_by(band_id=band_id)
            .order_by(AlbumDB.release_date.desc().nullslast(), AlbumDB.title)
            .all()
        )
        return [
            Album(
                id=a.id,
                band_id=a.band_id,
                title=a.title,
                release_date=a.release_date,
                notes=a.notes,
                created_at=a.created_at,
                updated_at=a.updated_at,
            )
            for a in db_albums
        ]

    def update(self, album: Album) -> Optional[Album]:
        if album.id is None:
            return None
        db_obj = self.session.get(AlbumDB, album.id)
        if not db_obj or db_obj.band_id != album.band_id:
            return None

        db_obj.title = album.title
        db_obj.release_date = album.release_date
        db_obj.notes = album.notes

        self.session.commit()
        self.session.refresh(db_obj)
        return self.get_by_id(db_obj.id)

    def delete(self, album_id: int) -> bool:
        db_obj = self.session.get(AlbumDB, album_id)
        if not db_obj:
            return False
        self.session.delete(db_obj)
        self.session.commit()
        return True
