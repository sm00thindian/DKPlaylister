# DKPlaylister

> Mine high-value playlists. Generate powerful pitches. Get your music heard by real listeners.

**DKPlaylister** is a personal, Grok-powered toolkit that helps independent musicians **systematically discover high-value playlist targets** and generate **optimized, personalized submission pitches** — all driven from a rich description of your music and your actual song lyrics.

## The Core Idea

Most playlist tools focus on volume. DKPlaylister focuses on **signal**.

You describe your music once in detail (your "Style Prompt"). The system expands that into primary and related genres, helps you mine strong targets (with heavy emphasis on real listeners and active curators rather than raw follower counts), and then turns your **Song Title + Lyrics** into high-quality, context-aware pitches tailored to specific playlists and curators.

The goal is fewer, better pitches that actually have a chance of landing with the right people.

## Operating Modes

DKPlaylister is designed to be **semi-automatic by default** — you stay in control, especially when using rate-limited sources like Playlister.com.

| Mode              | Description                                                                 | Best For |
|-------------------|-----------------------------------------------------------------------------|----------|
| **Semi-automatic** (default) | You drive discovery (especially Playlister searches). The tool ingests results, enriches them, scores, ranks, and generates pitches. | Most users — best balance of power and control |
| **Interactive**       | Guided, step-by-step workflow with more prompts and confirmations          | Learning the system or careful campaigns |
| **Automatic**         | More hands-off mining and pitching (with strong rate limits and safeguards) | Advanced users with clear rules |

You can configure the default mode and safety rails in your settings.

## How We Prioritize Playlists

We deliberately **do not** optimize purely for the biggest numbers.

**Core Philosophy**: Maximize real human listener exposure from curators who are likely to actually listen, add, and keep your music.

### Default Scoring Factors (all configurable)

- **Activity & Freshness** (Very High weight) — Has the playlist added music recently? Is the curator still active? This is one of the strongest signals of a living, breathing playlist.
- **Genre + Vibe Fit** (Very High weight) — How well does the playlist match your detailed Style Prompt (semantic + keyword alignment).
- **Submission Openness** (High weight) — Explicit signals that the curator accepts music ("submissions open", "accepting demos", contact info shared publicly, etc.). Playlister results receive a natural boost here.
- **Follower Count** (Medium weight, log-scaled) — Important, but with strong diminishing returns. A well-curated 12k playlist often beats a neglected 150k one.
- **Contact Quality** (Medium-High) — Real email > active Instagram > tracked bit.ly > none.
- **Your Historical Performance** (High, improves over time) — Has this curator or similar playlists responded to you before?
- **Risk Penalties** (Strong negative) — Signs of botted playlists, pay-to-play language, suspiciously low engagement relative to size, or curators you've previously flagged.

The system should be able to clearly explain *why* one playlist ranks higher than another for *your* music.

All weights and thresholds are configurable so you can tune the system as you learn what actually works.

## LLM Strategy (Grok First)

**Grok (xAI)** is the primary and default language model for:
- Expanding and interpreting your Style Prompt
- Scoring playlist fit
- Generating personalized, high-quality submission pitches from your actual lyrics

The system is built from day one with a clean, pluggable LLM provider interface. Adding OpenAI, Anthropic, Groq, or local models (Ollama, etc.) later will be straightforward.

## The Role of Playlister.com

If you have DistroKid Ultimate access, Playlister.com is an extremely useful **discovery source** within the semi-automatic workflow:

- Its multi-pass searchbot often surfaces better "submission-friendly" Spotify playlists than basic API searches.
- It surfaces real Spotify playlist URLs + contact signals.
- You run the searches (respecting the daily limits), then feed the results into DKPlaylister for enrichment, scoring, deduplication, and pitch generation.

DKPlaylister treats Playlister as one powerful input among others (Spotify direct search, manual lists, future sources), not the only source.

## Updated Roadmap

### Phase 0: Foundation (Complete)
- Solid local database + provenance tracking
- StyleProfile, Playlist, Pitch, and Submission models
- Configurable prioritization and scoring engine
- Pluggable Grok-first LLM layer
- Full multi-band catalog (Bands, Styles, Albums, Songs)
- Hardened `init` + `doctor` + consistent band scoping

See [docs/foundation-tools.md](docs/foundation-tools.md) for the complete reference.

### Phase 1: Discovery & Mining (In Progress + Hardening)
- Style Prompt → intelligent query generation & target mining (`style expand`, `mine`)
- `MiningRun` provenance tracking (in progress)
- Improved assisted import workflows

**Hardening Plan** (to make Phase 1 rock solid): [docs/phase-1-hardening-plan.md](docs/phase-1-hardening-plan.md)

See [docs/phase-1-discovery-mining-plan.md](docs/phase-1-discovery-mining-plan.md) for the original feature vision.
- Strong Playlister + Spotify hybrid ingestion
- Style Prompt → genre expansion → target mining
- Smart ranking with explainable scores
- Manual + assisted import workflows

### Phase 2: Pitch Generation (High Priority)
- High-quality pitch generation from Song Title + Lyrics + Style + Target Playlist
- Multiple output formats (email, Instagram DM, submission form)
- Iteration and refinement of pitches

### Phase 3: Workflow & Intelligence
- Full submission tracking and learning loop
- Campaign management
- "What worked" analytics
- Optional automation with strict safeguards

### Spotify User Authentication & Personalization (Cross-cutting)
- **Current (Activated):** Authorization Code Flow support + `user-top-read` as default scope
- **High Value Next:** Leverage `user-top-read` + `user-library-read` to dramatically improve scoring accuracy and pitch personalization by understanding the artist's actual taste
- **Strategic Opportunities:**
  - Use artist's top artists/tracks as strong signals in the scoring engine
  - Allow "Enhance Style Profile from my listening history" feature
  - Read private playlists for better style reference material
  - Future: `playlist-modify-private` to auto-maintain a "My Pitch Targets" playlist
  - Future: `user-library-modify` for one-click saving of high-value targets

See [docs/spotify-user-auth-plan.md](docs/spotify-user-auth-plan.md) for detailed prioritization of user data features and the full development plan.

## Ethical & Legal Notes

- This tool is built for **respectful, personalized outreach** — not volume spam.
- Always respect platform limits (especially Playlister's daily caps) and each curator's stated preferences.
- LLM-generated pitches are starting points. **You are responsible for reviewing and personalizing** every message you send.
- We strongly penalize (in scoring) known bot farms and pay-to-play schemes.
- You are responsible for complying with all applicable laws (CAN-SPAM, GDPR, etc.).

Generic mass pitches hurt everyone. The entire point of this system is to help you do the opposite.

## Quick Start (Current State)

```bash
# Clone and install
git clone https://github.com/sm00thindian/DKPlaylister.git
cd DKPlaylister
uv sync   # or pip install -e ".[dev]"

# Setup environment
cp .env.example .env
# Add your SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET
# Add your XAI_API_KEY for Grok pitch generation

dkplaylister init
```

### Local Web UI (Recommended)

For day-to-day use, install the UI extras and run:

```bash
uv pip install -e ".[ui]"
streamlit run ui/streamlit_app.py
```

This gives you a much better interface for reviewing targets and generating pitches.

Future commands (in active development):

```bash
# Define or load your style
dkplaylister style set --file my-style.txt

# Mine targets (semi-automatic flow)
dkplaylister mine --style "atmospheric cinematic indie..." --min-followers 8000

# Generate a pitch for a specific song + target
dkplaylister pitch --song "If I Get My Say" --playlist <id-or-url>
```

See the evolving docs in `/docs`.

**Key reference after Phase 0 completion:**
- [Foundation Tools Reference](docs/foundation-tools.md) — Complete list of the hardened core commands and interfaces.

**Foundation Tools at a Glance**

| Category             | Main Commands                              |
|----------------------|--------------------------------------------|
| Setup & Health       | `init`, `doctor`                           |
| Multi-Band Catalog   | `band`, `style`, `song`                    |
| Targets & Scoring    | `add`, `import`, `targets`, `score`        |
| Pitch Generation     | `pitch` (CLI) + full UI workflow           |
| Authentication       | `auth spotify`                             |
| Database Utilities   | `db migrate-legacy-styles`, `db clear-targets` |

Full details in the [Foundation Tools Reference](docs/foundation-tools.md).

## Example Style Prompt (Real Test Data)

This is the actual style description currently being used to develop the system:

> Atmospheric cinematic indie rock / indie folk, expansive soundstage with room to breathe, mid-tempo to slow ballad (72-95 BPM), deeply reverb-drenched shimmering jangly atmospheric guitars with delicate fingerpicked arpeggios that build into rich layered tones and tasteful overdriven textures, lush dripping reverb and long ethereal delays on everything, warm pulsing bass, heavy room mics for natural organic depth.
> Deep resonant baritone male vocals with warm rich low chest voice, raw earnest delivery full of gentle cracks and yearning emotion that can rise into grounded belted passages and lush harmonies...

(Full lyrics for the song *"If I Get My Say"* are also being used during development.)

## Project Structure

```
DKPlaylister/
├── src/dkplaylister/          # Core Python package + CLI
├── ui/
│   └── streamlit_app.py       # Local web UI (recommended for daily use)
├── docs/
├── data/
├── CHANGELOG.md
├── pyproject.toml
└── README.md
```

## Contributing

This is a personal tool being built in public for real music promotion use. Ideas, feedback, and contributions are welcome — especially around:

- Better prioritization signals
- Pitch quality and tone
- Playlister/Spotify ingestion improvements
- LLM prompt engineering for music pitching

## License

MIT License — see [LICENSE](LICENSE).

## Author

Kilynn Weber (sm00thindian)

---

*Built for artists who want to do this the right way.*
