"""Core model and repository tests for Phase 0 foundation."""

import tempfile
from pathlib import Path

import pytest

from dkplaylister.models import (
    Band, Song, StyleProfile, Playlist, Platform, PlaylistSource, Curator,
    Pitch, PitchFormat, Submission, SubmissionStatus
)
from dkplaylister.storage import (
    get_session, BandRepository, SongRepository, 
    StyleProfileRepository, PlaylistRepository, PitchRepository, SubmissionRepository
)


@pytest.fixture
def temp_db():
    """Provide a fresh temporary database for each test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        session = get_session(db_path)
        yield session
        session.close()


def test_band_repository_crud(temp_db):
    repo = BandRepository(temp_db)
    band = Band(name="Test Band", slug="test-band")
    created = repo.create(band)

    assert created.id is not None
    assert created.name == "Test Band"

    fetched = repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.name == "Test Band"


def test_song_repository_with_band(temp_db):
    band_repo = BandRepository(temp_db)
    song_repo = SongRepository(temp_db)

    band = band_repo.create(Band(name="Artist One", slug="artist-one"))

    song = Song(
        band_id=band.id,
        title="Test Song",
        lyrics="These are the lyrics",
        streaming_links={"spotify": "https://open.spotify.com/track/xxx"}
    )
    created = song_repo.create(song)

    assert created.id is not None
    fetched = song_repo.get_by_id(created.id)
    assert fetched.streaming_links["spotify"].startswith("https")


def test_style_profile_belongs_to_band(temp_db):
    band_repo = BandRepository(temp_db)
    style_repo = StyleProfileRepository(temp_db)

    band = band_repo.create(Band(name="Test Artist", slug="test-artist"))

    style = StyleProfile(
        band_id=band.id,
        name="Main Style",
        raw_prompt="Detailed style description here"
    )
    created = style_repo.create(style)

    latest = style_repo.get_latest(band_id=band.id)
    assert latest is not None
    assert latest.id == created.id


def test_playlist_provenance_and_curator(temp_db):
    repo = PlaylistRepository(temp_db)

    curator = Curator(email="curator@example.com", instagram="coolcurator")
    playlist = Playlist(
        platform=Platform.SPOTIFY,
        external_id="abc123def456ghi789jkl0",
        name="Test Indie Folk Playlist",
        url="https://open.spotify.com/playlist/abc123def456ghi789jkl0",
        source=PlaylistSource.PLAYLISTER,
        discovery_query="Indie Folk",
        curator=curator,
        contact_revealed_via="playlister_popup",
    )

    created = repo.create_or_update(playlist)
    fetched = repo.get_by_id(created.id)

    assert fetched.source == PlaylistSource.PLAYLISTER
    assert fetched.curator is not None
    assert fetched.curator.email == "curator@example.com"
    assert fetched.contact_revealed_via == "playlister_popup"
    assert fetched.has_contact_info is True


def test_playlist_scorer_basic():
    from dkplaylister.scoring import PlaylistScorer
    from dkplaylister.models import StyleProfile

    style = StyleProfile(
        name="Test Style",
        raw_prompt="Atmospheric indie folk with reverb guitars and baritone vocals"
    )

    playlist = Playlist(
        platform=Platform.SPOTIFY,
        external_id="testplaylist1234567890ab",
        name="Indie Folk Vibes",
        url="https://open.spotify.com/playlist/testplaylist1234567890ab",
        description="Cozy indie folk and singer songwriter music. Submissions welcome.",
        follower_count=18500,
        source=PlaylistSource.PLAYLISTER,
    )

    scorer = PlaylistScorer(style)
    breakdown = scorer.score(playlist)

    assert breakdown.total_value_score > 0
    assert breakdown.openness_score > 0.3  # Should get boost from "submissions welcome"
    assert breakdown.explanation is not None


def test_band_isolation_styles(temp_db):
    """Styles created for one band should not appear when querying another band."""
    band_repo = BandRepository(temp_db)
    style_repo = StyleProfileRepository(temp_db)

    band_a = band_repo.create(Band(name="Band A", slug="band-a"))
    band_b = band_repo.create(Band(name="Band B", slug="band-b"))

    style_a = StyleProfile(band_id=band_a.id, name="Style A", raw_prompt="Style for band A")
    style_b = StyleProfile(band_id=band_b.id, name="Style B", raw_prompt="Style for band B")

    style_repo.create(style_a)
    style_repo.create(style_b)

    styles_for_a = style_repo.list_all(band_id=band_a.id)
    styles_for_b = style_repo.list_all(band_id=band_b.id)

    assert len(styles_for_a) == 1
    assert styles_for_a[0].name == "Style A"

    assert len(styles_for_b) == 1
    assert styles_for_b[0].name == "Style B"


def test_band_isolation_songs(temp_db):
    """Songs must be isolated by band."""
    band_repo = BandRepository(temp_db)
    song_repo = SongRepository(temp_db)

    band_a = band_repo.create(Band(name="Band A", slug="band-a"))
    band_b = band_repo.create(Band(name="Band B", slug="band-b"))

    song_repo.create(Song(band_id=band_a.id, title="Song for A", lyrics="Lyrics A"))
    song_repo.create(Song(band_id=band_b.id, title="Song for B", lyrics="Lyrics B"))

    songs_a = song_repo.list_by_band(band_a.id)
    songs_b = song_repo.list_by_band(band_b.id)

    assert len(songs_a) == 1 and songs_a[0].title == "Song for A"
    assert len(songs_b) == 1 and songs_b[0].title == "Song for B"


def test_band_isolation_pitches(temp_db):
    """Pitches must be isolated by band (P0-4 band scoping)."""
    band_repo = BandRepository(temp_db)
    style_repo = StyleProfileRepository(temp_db)
    song_repo = SongRepository(temp_db)
    playlist_repo = PlaylistRepository(temp_db)
    pitch_repo = PitchRepository(temp_db)

    band_a = band_repo.create(Band(name="Band A", slug="band-a"))
    band_b = band_repo.create(Band(name="Band B", slug="band-b"))

    style_a = style_repo.create(StyleProfile(band_id=band_a.id, name="Style A", raw_prompt="A"))
    style_b = style_repo.create(StyleProfile(band_id=band_b.id, name="Style B", raw_prompt="B"))

    song_a = song_repo.create(Song(band_id=band_a.id, title="Song A", lyrics="Lyrics A"))
    song_b = song_repo.create(Song(band_id=band_b.id, title="Song B", lyrics="Lyrics B"))

    # Minimal playlist (global targets)
    pl = playlist_repo.create_or_update(Playlist(
        platform=Platform.SPOTIFY, external_id="p123", name="Test PL",
        url="https://open.spotify.com/playlist/p123", source=PlaylistSource.PLAYLISTER
    ))

    pitch_repo.create(Pitch(
        band_id=band_a.id, style_profile_id=style_a.id, song_id=song_a.id,
        playlist_id=pl.id, song_title="Song A", generated_text="Pitch for A",
        llm_model="grok-3", format=PitchFormat.EMAIL
    ))
    pitch_repo.create(Pitch(
        band_id=band_b.id, style_profile_id=style_b.id, song_id=song_b.id,
        playlist_id=pl.id, song_title="Song B", generated_text="Pitch for B",
        llm_model="grok-3", format=PitchFormat.EMAIL
    ))

    pitches_a = pitch_repo.list_by_band(band_a.id)
    pitches_b = pitch_repo.list_by_band(band_b.id)

    assert len(pitches_a) == 1 and pitches_a[0].song_title == "Song A"
    assert len(pitches_b) == 1 and pitches_b[0].song_title == "Song B"


def test_submission_respects_band_id(temp_db):
    """Submission records accept and persist band_id for scoping (P0-4)."""
    sub_repo = SubmissionRepository(temp_db)
    band_repo = BandRepository(temp_db)
    band = band_repo.create(Band(name="Scoped Band", slug="scoped"))

    sub = Submission(
        band_id=band.id,
        playlist_id=1,
        track_title="Test Track",
        status=SubmissionStatus.PITCH_SENT,
        notes="Created in test"
    )
    created = sub_repo.create(sub)
    assert created is not None
    subs = sub_repo.list_by_band(band.id)
    assert len(subs) >= 1
    # Note: full roundtrip via _to_pydantic not implemented for Submission yet,
    # but band_id is stored on the DB row via getattr path.


# =============================================================================
# Phase 1 Discovery / Mining Tests (H2)
# =============================================================================

def test_style_discovery_expansion_model():
    """StyleDiscoveryExpansion model roundtrips correctly (Phase 1)."""
    from dkplaylister.models import StyleDiscoveryExpansion

    exp = StyleDiscoveryExpansion(
        primary_genres=["indie rock", "atmospheric"],
        search_queries=["indie cinematic playlists", "dream pop submissions"],
        explanation="Strong reverb and cinematic feel matches certain curators."
    )
    assert "indie rock" in exp.primary_genres
    assert len(exp.search_queries) == 2


def test_mining_run_model_and_band_isolation(temp_db):
    """MiningRun supports band scoping and full fields (Phase 1 hardening)."""
    from dkplaylister.models import MiningRun, OperatingMode, Band
    from dkplaylister.storage import BandRepository, MiningRunRepository

    band_repo = BandRepository(temp_db)
    mining_repo = MiningRunRepository(temp_db)

    band = band_repo.create(Band(name="Test Artist", slug="test-artist"))

    run = MiningRun(
        band_id=band.id,
        style_profile_id=42,
        style_profile_name="Main Style",
        operating_mode=OperatingMode.SEMI_AUTOMATIC,
        queries_used=["atmospheric indie", "reverb guitar playlists"],
        playlists_found=17,
        playlists_imported=3,
        top_score=82.5,
        expansion_explanation="Good fit for mid-size active curators.",
    )
    created = mining_repo.create(run)

    assert created is not None
    fetched = mining_repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.band_id == band.id
    assert len(fetched.queries_used) == 2
    assert fetched.playlists_found == 17

    runs_for_band = mining_repo.list_by_band(band.id)
    assert len(runs_for_band) >= 1


def test_mining_run_with_queries_and_stats(temp_db):
    """Full-featured MiningRun captures queries and results (Phase 1 H2/H3)."""
    from dkplaylister.models import MiningRun, Band
    from dkplaylister.storage import BandRepository, MiningRunRepository

    band_repo = BandRepository(temp_db)
    mining_repo = MiningRunRepository(temp_db)

    band = band_repo.create(Band(name="Discovery Artist", slug="discovery-artist"))

    run = MiningRun(
        band_id=band.id,
        style_profile_id=99,
        style_profile_name="Cinematic Indie",
        queries_used=[
            "atmospheric indie rock playlists",
            "reverb guitar submissions 2026",
            "dreamy cinematic indie"
        ],
        playlists_found=42,
        playlists_imported=7,
        top_score=91.0,
        notes="Per-query: {'atmospheric indie rock playlists': 15, 'reverb guitar submissions 2026': 20}"
    )
    created = mining_repo.create(run)

    fetched = mining_repo.get_by_id(created.id)
    assert len(fetched.queries_used) == 3
    assert "reverb guitar submissions 2026" in fetched.queries_used
    assert fetched.top_score == 91.0
    assert "Per-query" in (fetched.notes or "")


def test_style_discovery_expansion_fallback_behavior():
    """Expansion model handles partial/empty data gracefully (Phase 1 resilience)."""
    from dkplaylister.models import StyleDiscoveryExpansion

    # Simulate poor LLM output fallback
    exp = StyleDiscoveryExpansion(
        search_queries=["fallback query from raw prompt"],
        explanation="Fallback used due to LLM error"
    )
    assert len(exp.search_queries) == 1
    assert "Fallback" in exp.explanation
    assert exp.primary_genres == []  # defaults ok
