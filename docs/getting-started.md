# Getting Started with DKPlaylister

## 1. Prerequisites

- Python 3.11+
- A free Spotify Developer account (https://developer.spotify.com/dashboard)
- An xAI API key (for Grok-powered pitch generation and analysis)
- (Optional but recommended) uv or pipx for easy installation

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
# Edit .env and add:
# - SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET
# - XAI_API_KEY (required for pitch generation)
```

Create a Spotify app:
1. Go to https://developer.spotify.com/dashboard
2. Create a new app (name it "DKPlaylister")
3. Copy the Client ID and Client Secret into `.env`

## 4. Initialize

```bash
dkplaylister init
```

## 5. Current Focus (Early Development)

The project is currently focused on:

- Defining and storing your **Style Prompt** (the detailed description of your music)
- Building the pluggable Grok-powered pitch generation system
- Creating the configurable scoring/prioritization engine

See the main [README](../README.md) for the current vision and roadmap.

## Next Steps (Planned)

- `dkplaylister style set` — Load your detailed music description
- `dkplaylister mine` — Semi-automatic target discovery (Playlister + Spotify)
- `dkplaylister pitch` — Generate optimized submissions from your lyrics

## Tips for Effective Use

- Your Style Prompt is the foundation. The more specific and vivid, the better the results.
- Playlister.com is treated as a powerful **discovery aid**, not the final source of truth. You control the searches.
- Always review and personalize LLM-generated pitches before sending.
- Track everything — your historical response data will become one of the highest-weighted signals over time.

Happy pitching! 🎵
