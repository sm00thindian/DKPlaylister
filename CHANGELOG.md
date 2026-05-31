# Changelog

All notable changes to DKPlaylister will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added (Phase 0 Hardening)
- `PitchRepository` and `SubmissionRepository` (basic)
- `PitchDB` and `SubmissionDB` tables with corresponding Alembic migrations
- Pitch records are now created on generation in the UI (both single and multi-song from tracker)
- Basic Submission records are created when marking a tracker target as "Pitched"
- Improved foreign key linking on Pitch records (song_id when using saved songs)

### Fixed
- Fixed ImportError for `PitchRepository` in Streamlit UI by making the import lazy inside the modes that actually use it. This allows the app to start even during iterative development of Phase 0 features.

### P0-4: Consistent Band Scoping Audit & Fixes (Completed)
**Audit findings** (systematic grep + code review of CLI, UI, storage, models, scoring, LLM):
- UI leaks: `style_repo.get_latest()` called without `band_id` in sidebar (line ~185) and "Add New Target" auto-score path (line ~247) — could pull style from wrong band.
- CLI gaps: `add` and `import` commands supported `band_id` internally in `_import_playlist` helper but did not expose `--band` flag or pass it (dead code). Duplicate check was global.
- Model inconsistency: Pydantic `Submission` lacked `band_id`/`song_id`/`notes` fields (storage used getattr fallbacks; extra kwargs were silently dropped due to default extra='ignore'). Pitch was already correct.
- `targets list` and `PlaylistRepository.list_all` remain intentionally global (playlists are cross-band targets; per-band scoring happens at import time via StyleProfile).
- All `get_latest(band_id=...)` in CLI pitch/style paths were already correct post-P0 work.
- No leaks in scoring.py or llm/grok.py (they receive explicit StyleProfile).
- Good: Generate Pitch paths (DB + tracker multi-song), Pitch creation, Song/Style/Album CRUD in UI, and existing CLI song/style commands already respected `current_band_id` / `--band`.
- Tests had solid band isolation for Style/Song but none yet for Pitch/Submission.

**Fixes applied (minimal, targeted)**:
- UI: Both `get_latest()` calls now pass `current_band_id` (with fallback).
- CLI: Added `--band` to `add` and `import` (wired through to scoring).
- Models: Added `band_id`, `song_id`, `notes` to `Submission` Pydantic (now roundtrips correctly).
- Storage: Added `list_by_band` to `SubmissionRepository` for parity with Pitch/Song/etc.
- UI Submission creation ("Mark as Pitched"): Now provides required `track_title` and benefits from model fix.
- Tests: Added `test_band_isolation_pitches` + `test_submission_respects_band_id` (plus import updates). Existing isolation tests continue to pass.

**Deliverable**: This audit + fixes closes the "consistent band scoping" risk for Phase 0. All major flows now respect the selected band for band-owned entities (Style, Song, Pitch, Submission). Playlists stay global as designed.

### P0-5: Improve `init` + First-Run Experience (Completed)
- `init` command is now idempotent and always safe: creates data/ + DB file if missing, runs Alembic migrations via get_session (no more early exit on existing DB). Added `--force` only for re-run semantics.
- Added immediate environment validation in `init` (shows presence/absence of XAI_API_KEY, Spotify client ID/secret/redirect – no secrets printed).
- New `dkplaylister doctor` command (top-level):
  - Reports DB location + migration state
  - Counts per-band: styles, songs; global targets; sample pitch counts
  - Lists all bands with quick stats
  - Env key presence summary
  - Spotify token cache detection + validity probe (reuses Spotipy OAuth cache logic, non-interactive)
  - Actionable recommendations based on current state (e.g. "create band", "import targets")
- Updated init next-step messaging to point users at `doctor` and `auth spotify --status`.
- This completes the Phase 0 hardening plan (P0-1 through P0-5 executed in order). The foundation is now genuinely rock solid: proper migrations, tests, real Pitch/Submission records, consistent band scoping, and excellent first-run/doctoring experience.

**Phase 0 Hardening – Final Status**: All critical items complete. New work should follow the "P1+" guidance in the plan docs. Run `dkplaylister doctor` and `dkplaylister init` as your daily foundation check.

### Documentation
- Added [docs/foundation-tools.md](docs/foundation-tools.md) — authoritative reference for all hardened foundation tools post-Phase 0 (Setup, Catalog, Ingestion, Pitching, UI, etc.).
- Linked the new reference from README.md, docs/getting-started.md, and the Phase 0 plan documents.

### Phase 1 Kickoff (Discovery & Mining)
- Created [docs/phase-1-discovery-mining-plan.md](docs/phase-1-discovery-mining-plan.md).
- Updated README roadmap to mark Phase 0 complete and Phase 1 in progress.
- Added `StyleDiscoveryExpansion` Pydantic model for structured discovery output.
- Added `LLMProvider.expand_style_for_discovery()` (abstract) + full Grok implementation.
- Added `dkplaylister style expand` command.
- Added `dkplaylister mine` command (first real Phase 1 mining capability): uses style expansion to generate smart Spotify searches, enriches results with `fetch_playlist`, scores them, and presents a ranked candidate list. Supports `--band`, `--limit`, `--min-score`, and `--import`.

### Phase 1 Hardening + Completion (Discovery Solid + Full Features + UI)
- Created full hardening plans.
- **H1 complete** (MiningRun + history + doctor).
- **H2** deprioritized (minimal mocking).
- **H3 + H5 major win**: Full "Discover Targets" mode in Streamlit UI (expand style → live editable queries → run mining → scored candidates → one-click import with MiningRun recording).
- New `src/dkplaylister/discovery.py` shared module (used by both CLI and UI).
- CLI `mine` refactored + powerful `--queries-file` workflow.
- Phase 1 is now meaningfully complete and very usable.

### Added
- Full StyleProfile model + persistence (`style set`, `style show`, `style list`)
- Playlist import system:
  - `add <url>` for single playlists
  - `import` for bulk import from file or multiple URLs (with --query for Playlister provenance)
- Automatic Spotify enrichment on import (`fetch_playlist`)
- Configurable scoring engine with `PlaylistScorer` and `ScoringConfig`
  - Named scoring profiles (`scoring save` / `list` / `show`)
  - CLI weight overrides on `score` command
- Grok-powered fit scoring (with Feb 2026 API change awareness)
- `score <playlist-url>` command with detailed breakdown
- `pitch` command (Grok-generated personalized submissions from Style + Lyrics)
- Basic rate limit handling for Spotify API calls
- Documentation for Spotify AI guidelines and prioritization philosophy

### Phase 0 Hardening (Foundation Stabilization)
- Adopted Alembic for proper database migrations (replacing ad-hoc manual migrations)
- Initial Alembic migration generated for current schema
- `get_session()` and `dkplaylister init` now use Alembic migrations
- Added `docs/database-migrations.md` with new workflow
- Significantly expanded test coverage:
  - Repository tests for Band, Song, StyleProfile, and Playlist (including provenance and curator data)
  - Basic scoring engine tests
- Created detailed `docs/phase-0-hardening-plan-detailed.md` with prioritized tasks

### Changed
- Refactored core import logic for reuse between `add` and `import`
- Improved LLM prompts to respect removed Spotify fields (post Feb 2026 changes)
- Better error handling in Spotify client layer

### Notes
- Currently focused on semi-automatic workflow (user drives Playlister searches)
- Heavy use of Client Credentials flow for public playlist data
- All data stored locally in SQLite (`data/dkplaylister.db`)

## [0.1.0] - Initial Scaffolding (Pre-Changelog)

- Project vision and models established
- Basic CLI scaffolding
- Grok integration for pitch generation
- Initial Spotify + scoring foundations
