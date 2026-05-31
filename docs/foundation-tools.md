# Foundation Tools Reference

**DKPlaylister — Phase 0 Hardened Core**

These are the stable, reliable **foundation tools** that make up the Phase 0 baseline. They were intentionally hardened before adding more advanced features.

Everything in this document is considered part of the solid foundation you can depend on.

---

## 1. Setup & Health

These commands establish and maintain a healthy local environment.

| Command                              | Description                                                                 | When to Use |
|--------------------------------------|-----------------------------------------------------------------------------|-------------|
| `dkplaylister init`                  | Creates `data/`, the SQLite database, and runs all Alembic migrations. Now fully idempotent and safe to re-run. | First run, after pulling changes, or when the DB feels out of sync |
| `dkplaylister doctor`                | Comprehensive health check: database state, schema version, per-band counts, environment variables, Spotify auth status, and actionable recommendations. | Regularly, or whenever something feels off |
| `dkplaylister auth spotify --status` | Check current Spotify authentication status without opening a browser.     | Before using features that need user-authenticated data |

**Recommended first step after cloning:**
```bash
dkplaylister init
dkplaylister doctor
```

---

## 2. Database & Migration Utilities

| Command                                      | Description |
|----------------------------------------------|-------------|
| `dkplaylister db migrate-legacy-styles`      | One-time helper to assign legacy styles (with `band_id = NULL`) to a band. |
| `dkplaylister db clear-targets`              | Permanently deletes **all** playlist targets (use with caution). |

**Underlying migration system:** [Alembic](https://alembic.sqlalchemy.org/). See [docs/database-migrations.md](database-migrations.md) for the proper workflow when making schema changes.

---

## 3. Multi-Band Catalog Management

This is the heart of the Phase 0 data model (Band → Styles, Songs, Albums).

### Bands
```bash
dkplaylister band create "My Artist Name" --slug my-artist
dkplaylister band list
dkplaylister band show 1
dkplaylister band set-default 1
```

### Styles (your music description — the most important foundation artifact)
```bash
dkplaylister style set --file my-style.txt --name "Main Style" --band 1
dkplaylister style list --band 1
dkplaylister style show
```

### Songs & Lyrics
```bash
dkplaylister song add --band 1 --title "Song Title" --file lyrics.txt
dkplaylister song list --band 1
dkplaylister song show <song-id>
```

**Albums** are currently managed through the Streamlit UI (Manage Catalog → Albums tab).

---

## 4. Target Ingestion & Scoring

Core workflow for bringing in and evaluating playlists.

| Command | Description |
|---------|-------------|
| `dkplaylister add <spotify-url>` | Add a single playlist (supports rich Playlister contact flags + `--band`) |
| `dkplaylister import` | Bulk import from URLs or a text file (supports `--band`) |
| `dkplaylister targets` | List saved playlist targets with scores and contact summary |
| `dkplaylister score <spotify-url>` | Score a playlist against your current (or specified) Style Profile with full breakdown |

The `add` and `import` commands now correctly scope style selection for scoring when `--band` is provided.

---

## 5. Pitch Generation

| Command | Description |
|---------|-------------|
| `dkplaylister pitch` | Generate a personalized pitch using Grok + your Style + actual song lyrics. Supports saved songs, specific styles, `--band`, and multiple output formats. |

**Note:** The richest pitch generation experience (including multi-song pitching to the same curator and writing status back to Playlister tracker CSVs) is currently in the Streamlit UI under **Generate Pitch**.

---

## 5.1 Phase 1: Discovery & Mining (Hardening in Progress)

| Command | Description |
|---------|-------------|
| `dkplaylister style expand --band X` | Expand your Style Profile into genres, moods, search queries, and similar artists using Grok (foundation for mining). |
| `dkplaylister mine --band X [--dry-run] [--queries-file edited.txt] [--limit 30] [--min-score 70]` | Intelligent discovery: uses style expansion (or your edited queries) to search Spotify, enrich, score, and rank candidates. Records full `MiningRun` for history. |
| `dkplaylister mining history [--band X]` | View past mining sessions with results and queries used. |
| `dkplaylister mining show <id>` | Detailed view of a specific mining run. |

**Full-featured workflow example**:
```bash
dkplaylister mine --band 1 --dry-run                    # See what queries the LLM generated
# Edit/save the queries to a file
dkplaylister mine --band 1 --queries-file my-queries.txt --limit 40
dkplaylister mining history --band 1
```

See the Phase 1 hardening plan for current status and roadmap.

## 6. Authentication

```bash
dkplaylister auth spotify
```

Supports Authorization Code Flow + `user-top-read` scope (see [docs/spotify-user-auth-plan.md](spotify-user-auth-plan.md) for strategic scope planning).

---

## 7. Recommended Daily Interface

While the CLI is powerful for scripting and automation, **the Streamlit UI is currently the best way to use the full foundation**:

```bash
# Install UI extras
uv pip install -e ".[ui]"

# Run the app
streamlit run ui/streamlit_app.py
```

### UI Modes (all built on the hardened Phase 0 foundation)
- **Review Targets** — Browse scored playlists with curator/contact details
- **Generate Pitch** — Full workflow with database targets + Playlister tracker integration, multi-song support, and real `Pitch` record creation
- **Manage Catalog** — Complete CRUD for Bands, Styles, Albums, and Songs (properly band-scoped)
- **Process Playlister Imports** — Load heuristic tracker CSVs, fill in Spotify URLs + contact details, import directly with scoring

---

## 8. Supporting Commands

```bash
dkplaylister scoring list
dkplaylister scoring show <name>
dkplaylister scoring save <name>
```

Named `ScoringConfig` profiles for experimentation and reproducibility.

---

## 9. Getting Help from the Tools Themselves

All commands support `--help`:

```bash
dkplaylister --help
dkplaylister band --help
dkplaylister doctor --help
dkplaylister pitch --help
```

`dkplaylister doctor` is especially useful because it gives you a live view of your actual data state.

---

## Underlying Technical Foundation

Now considered stable after Phase 0:

- **Data Model**: `Band` (1:N `StyleProfile`, `Song`, `Album`) + global `Playlist` targets + `Pitch` + `Submission` records with full provenance
- **Storage**: SQLAlchemy + SQLite with Alembic migrations
- **Scorer**: `PlaylistScorer` + configurable `ScoringConfig`
- **LLM**: Pluggable provider interface (Grok-first via `GrokProvider`)
- **Band Scoping**: Consistently enforced across all band-owned entities

---

## Next Steps After Phase 0

See the roadmap in [README.md](../README.md) and the detailed Phase 0 plan artifacts in `docs/phase-0-hardening-plan*.md`.

The foundation is now solid enough that new features can be built with confidence.

---

*Maintained as part of the Phase 0 completion (April 2026).*