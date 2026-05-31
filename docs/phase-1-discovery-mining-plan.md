# Phase 1: Discovery & Mining Plan

**Goal**: Move from purely manual/semi-automatic playlist ingestion to **intelligent, Style-driven discovery and mining**.

Phase 1 builds directly on the solid Phase 0 foundation (multi-band catalog, scoring engine, real Pitch/Submission records, reliable `init` + `doctor`).

---

## Current State (End of Phase 0)

- Excellent **enrichment** (`fetch_playlist` + curator mining + scoring).
- Strong **manual ingestion paths**:
  - `dkplaylister add` / `import`
  - Playlister HTML → heuristic tracker CSVs → "Process Playlister Imports" UI mode
- Scoring works well **after** a playlist is already known.
- Style Prompts are used for **scoring** and **pitch generation**, but not for **finding** new targets.
- No proactive mining from the Style Prompt.
- `MiningRun` model exists as a stub only.
- `discovery_query` field exists but is only populated manually.

---

## Phase 1 Vision

**Style Prompt becomes an active discovery engine**, not just a scoring filter.

Key capabilities:
- Take a rich Style Profile and automatically generate high-quality search queries (genre + mood + keywords + similar artists).
- Hybrid discovery: Playlister (human) + Spotify search/recommendations + saved artist top tracks influence.
- Better candidate ranking before full enrichment.
- Record `MiningRun` sessions for traceability.
- Improved assisted import workflows in both CLI and UI.
- Strong explainability: "This target was discovered because of strong genre + mood alignment with your Style Prompt."

---

## P1 Priorities

### 1. Style Prompt → Intelligent Query Generation
- Use Grok (or pluggable LLM) to expand a `StyleProfile.raw_prompt` into structured search terms:
  - Primary genres + subgenres
  - Mood/vibe keywords
  - Similar artists (current listening + style)
  - Playlist title/description patterns that have worked historically
- Store expanded query metadata on `StyleProfile` or in a new `DiscoveryConfig`.

### 2. Spotify-Powered Discovery Commands
- New `dkplaylister mine` command (and UI equivalent):
  - `dkplaylister mine --style latest --limit 50`
  - Uses expanded queries against Spotify Search API (playlists) and possibly Recommendations.
  - Returns candidates with preliminary scores.
  - User reviews and selectively enriches + imports.
- Respect rate limits and Spotify ToS.

### 3. Hybrid Playlister + Spotify Workflow
- Keep Playlister as the high-signal human discovery source.
- Add ability to take a Playlister search term and intelligently expand it using the current band's Style.
- Better deduplication and candidate management before full `fetch_playlist`.

### 4. MiningRun Provenance & History
- Make `MiningRun` a real, persisted model.
- Record what style + query + parameters produced which candidates.
- Surface mining history in the UI and CLI (`dkplaylister mining history`).

### 5. UI Improvements for Discovery
- New or enhanced mode in Streamlit for "Discover New Targets".
- Show generated search queries with ability to edit before running.
- Candidate review queue before committing to the main target database.

### 6. Data Integrity & Validation (carry-over from old P1)
- Add validation that a `Song` belongs to the same band as the `StyleProfile` being used.
- Stronger guards when generating scores or pitches across bands.

### 7. Error Handling & Resilience (carry-over)
- Better, user-friendly messages around Spotify rate limits, auth failures, and LLM generation failures during mining.
- Retry logic and clear "what to do next" guidance in `doctor`.

---

## Recommended Execution Order

1. **Style expansion + query generation** (foundational for everything else in Phase 1)
2. Basic `mine` command in CLI using expanded queries + Spotify search
3. Persist real `MiningRun` records
4. Add corresponding discovery UI in Streamlit
5. Hybrid Playlister-aware mining improvements
6. Polish: validation, error handling, history commands, documentation

---

## Success Criteria for Phase 1

- From a well-written Style Profile, the user can run a discovery command and get relevant, high-signal playlist candidates they did not already have in their targets.
- Mining sessions are traceable (`MiningRun` records).
- The system can explain *why* it suggested a particular search or playlist.
- User still remains in control (review + selective import) — no fully automatic spam.
- All new discovery flows respect current band scoping.

---

## Out of Scope for Phase 1 (defer to Phase 2+)

- Fully automatic nightly mining campaigns
- Playlist modification features
- Advanced personalization using `user-top-read` history (this is a cross-cutting high-value item that can start in parallel but is not required for core Phase 1)

---

## Relationship to Other Plans

- Builds on Phase 0 foundation tools (documented in `foundation-tools.md`).
- Spotify user auth strategic items remain in [docs/spotify-user-auth-plan.md](spotify-user-auth-plan.md).
- Scoring philosophy stays in [docs/prioritization.md](prioritization.md).

---

**Status**: Early implementation complete. Hardening phase has begun.

**Early Progress**:
- `LLMProvider.expand_style_for_discovery()` + `StyleDiscoveryExpansion` model.
- `dkplaylister style expand` and `dkplaylister mine` (MVP) commands.

**Hardening Plan Created**:
- [docs/phase-1-hardening-plan.md](phase-1-hardening-plan.md)
- [docs/phase-1-hardening-plan-detailed.md](phase-1-hardening-plan-detailed.md)

See the hardening plan for the prioritized work needed to make Phase 1 production-ready.

*Created immediately after Phase 0 completion.*