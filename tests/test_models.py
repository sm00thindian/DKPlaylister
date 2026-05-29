"""Basic model tests."""

from dkplaylister.models import Curator, Platform, Playlist


def test_playlist_model():
    p = Playlist(
        platform=Platform.SPOTIFY,
        external_id="37i9dQZF1DXcBWIGoYBM5M",
        name="Chillhop Essentials",
        url="https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
        follower_count=850000,
    )
    assert p.name == "Chillhop Essentials"
    assert p.platform == Platform.SPOTIFY


def test_curator_extraction_stub():
    c = Curator(name="Chillhop Team", email="chillhopmusic@gmail.com")
    assert "@" in c.email
