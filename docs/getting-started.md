# Getting Started with DKPlaylister

## 1. Prerequisites

- Python 3.11+
- A free Spotify Developer account (https://developer.spotify.com/dashboard)
- (Optional) uv or pipx for easy installation

## 2. Installation (Development)

```bash
git clone https://github.com/sm00thindian/DKPlaylister.git
cd DKPlaylister

# Recommended: use uv
uv sync

# Or with pip
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 3. Configuration

```bash
cp .env.example .env
# Edit .env and add your Spotify Client ID + Secret
```

Create a Spotify app:
1. Go to https://developer.spotify.com/dashboard
2. Create new app (name it "DKPlaylister" or similar)
3. Copy Client ID and Client Secret into `.env`
4. No redirect URI needed for Client Credentials flow (public data only)

## 4. Initialize

```bash
dkplaylister init
```

## 5. First Search (once implemented)

```bash
dkplaylister search --genre lofi --keywords submissions,accepting --min-followers 2000
```

## Next Milestones

See the main [README](../README.md) for the full roadmap.

## Tips for Effective Use

- Start narrow: specific genres + "submissions" or "pitch" in keywords.
- Always verify contacts manually before blasting emails.
- Personalize every pitch with 1-2 sentences about why your track fits *that* playlist.
- Track everything — the database is your memory.

Happy pitching! 🎵
