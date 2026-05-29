# DKPlaylister

> Find the right playlists. Pitch your music. Get heard.

**DKPlaylister** is a personal toolkit for independent musicians to discover playlist submission opportunities, manage outreach campaigns, and track results across platforms.

## Why DKPlaylister?

As an artist, finding legitimate playlists that actually accept submissions (and respond) is time-consuming and scattered across Spotify, Instagram, Reddit, curator websites, and more. Paid services are expensive. Existing open-source tools are limited to one platform or lack workflow features.

DKPlaylister aims to be the **end-to-end open-source solution** for ethical, efficient music promotion via playlists.

## Key Features (Roadmap)

### Phase 1: Discovery
- **Spotify Integration** — Search public playlists using the official Web API. Filter by genre, mood, follower count, keywords ("submissions", "accepting", "demos", "pitch me").
- **Curator Extraction** — Automatically pull emails, Instagram, Twitter/X, TikTok, websites, and submission guidelines from playlist descriptions and curator profiles.
- **Multi-Platform Support** — Extend beyond Spotify to YouTube Music, SoundCloud, and user-curated lists.
- **Smart Matching** — Score playlists for fit based on your genre, BPM, mood, and release type.

### Phase 2: Outreach Workflow
- Local database (SQLite) to store playlists, contacts, and submission history.
- Submission tracker: status (Sent, Opened, Accepted, Rejected, No Response), dates, notes, follow-ups.
- Personalized pitch generator (template + optional LLM assistance for customization).
- Bulk export to CSV/Excel for campaigns or import into email tools.
- Respect for curator preferences (opt-out lists, "no unsolicited" flags).

### Phase 3: Analytics & Automation
- Stats: response rates by genre/playlist size, best times to pitch, curator tiers.
- Duplicate & spam detection.
- Optional: integration with Spotify for Artists pitching (editorial playlists).
- Email/SM automation helpers (respecting rate limits and laws like CAN-SPAM/GDPR).

## Ethical & Legal Notes

- Uses **official APIs only** where possible (Spotify Web API). No scraping of private data.
- Designed for **personalized, respectful outreach** — not spam or bulk automation.
- You are responsible for complying with all applicable laws and each curator's stated guidelines.
- Always personalize your pitches. Generic mass emails hurt everyone.

## Quick Start (Planned)

```bash
# After cloning
uv sync  # or pip install -e ".[dev]"

# Setup Spotify credentials (free at developer.spotify.com)
cp .env.example .env
# edit .env with your SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET

dkplaylister auth spotify
dkplaylister search --genre "lofi" --keywords "submissions" --min-followers 5000
dkplaylister export --format excel
```

See [docs/getting-started.md](docs/getting-started.md) once available.

## Installation (Future)

Will support:

- `uv tool install dkplaylister`
- `pipx install dkplaylister`
- Docker for advanced use

## Project Structure

```
DKPlaylister/
├── src/dkplaylister/     # Main package
│   ├── cli.py            # Typer CLI entrypoint
│   ├── spotify.py        # Spotify API client + search logic
│   ├── models.py         # Pydantic models (Playlist, Curator, Submission)
│   ├── storage.py        # SQLite persistence
│   └── ...
├── data/                 # Local data (gitignored)
├── exports/              # Generated campaign files
├── tests/
├── pyproject.toml
└── README.md
```

## Contributing

This started as a personal tool for my own music promotion. Contributions, ideas, and curation lists are welcome!

- Open issues for feature requests or bugs
- PRs for new platform integrations or improvements
- Share your successful playlist lists (ethically)

## Alternatives

- [Playlist Farm](https://github.com/josephvolmer/playlist-farm) — Excellent Spotify-focused CLI/TUI
- [Spotify Playlist Curator Fetcher](https://github.com/MLK97/Spotify-Playlist-Curator-Fetcher) — GUI version
- Commercial: Playlist Push, SubmitHub, Groover, etc.
- Spotify for Artists (editorial playlists)

## License

MIT License — see [LICENSE](LICENSE).

## Author

Kilynn Weber (sm00thindian)

---

*Built with love for the independent music community. Let's get more great music heard.*
