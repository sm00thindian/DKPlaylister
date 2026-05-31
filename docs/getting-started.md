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
# - (Optional but recommended) SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
# - XAI_API_KEY (required for pitch generation)
```

Create a Spotify app:
1. Go to https://developer.spotify.com/dashboard
2. Create a new app and name it **DKPlaylister**
3. Under "Redirect URIs", add this one (recommended):
   `http://127.0.0.1:8888/callback`
4. Copy the **Client ID** and **Client Secret** into your `.env` file.

> **Note**: You only need the Client Credentials flow right now (for public playlist data).  
> The redirect URI is required by Spotify and will be used later if we add user-authenticated features.

## 4. Initialize

```bash
dkplaylister init
```

## 5. Current Focus (Early Development)

The project is currently focused on:

- Defining and storing your **Style Prompt**
- Bulk importing + scoring targets from Playlister
- Grok-powered personalized pitch generation

## Running the Local Web UI (Recommended for daily use)

For a much nicer experience than pure CLI, run the Streamlit interface:

```bash
# Install UI dependencies
uv pip install -e ".[ui]"

# Run the web UI
streamlit run ui/streamlit_app.py
```

**macOS users**: If you see a message recommending `watchdog`, you can install it with:

```bash
xcode-select --install
pip install watchdog
```

(Or just run `pip install -e ".[ui]"` again — it now includes watchdog.)

The UI lets you:
- Review and manage your Style Profile
- Browse scored targets
- Generate and edit pitches interactively

See the main [README](../README.md) for the current vision and roadmap.

**After completing Phase 0**, the authoritative reference for the hardened foundation is:
- [Foundation Tools Reference](foundation-tools.md) — Every stable command and interface you can rely on.

## Tips for Effective Use

- Your Style Prompt is the foundation. The more specific and vivid, the better the results.
- Playlister.com is treated as a powerful **discovery aid**, not the final source of truth. You control the searches.
- Always review and personalize LLM-generated pitches before sending.
- Track everything — your historical response data will become one of the highest-weighted signals over time.

Happy pitching! 🎵
