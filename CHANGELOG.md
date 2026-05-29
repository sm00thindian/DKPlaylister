# Changelog

All notable changes to DKPlaylister will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
