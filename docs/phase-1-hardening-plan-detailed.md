# Phase 1 Hardening Plan – Detailed Task Breakdown

**Objective**: Bring the Discovery & Mining layer (Phase 1) to the same level of stability and trustworthiness that Phase 0 achieved.

This document expands the high-level `phase-1-hardening-plan.md` into concrete, prioritized tasks with specific files, order of attack, and clear deliverables.

---

## Current Reality Check (Before Hardening)

| Area                        | Status          | Notes |
|----------------------------|-----------------|-------|
| Style expansion (LLM)      | Early working   | Functional but no tests, no persistence |
| `style expand` CLI         | Basic           | Useful for debugging |
| `mine` command             | MVP             | Brittle, no history, limited resilience |
| `MiningRun`                | Stub only       | Model exists, nothing uses it |
| Tests                      | None            | Zero coverage of Phase 1 logic |
| UI Discovery               | Non-existent    | Only manual discovery_query fields |
| Band scoping               | Unknown         | New flows added quickly |
| Error handling             | Weak            | Generic try/except with minimal user guidance |
| Documentation              | Minimal         | Commands exist but not well documented |

---

## Recommended Execution Order (P1-H First)

We strongly recommend completing the hardening items in roughly this sequence:

1. **H1: MiningRun Persistence** (foundational for provenance)
2. **H2: Test Coverage** (safety net while surface area is small)
3. **H3: Harden the `mine` Command** (primary user-facing feature)
4. **H4: Band Scoping Audit & Fixes**
5. **H5–H7**: UI, resilience, and documentation

---

## Detailed Hardening Tasks

### H1: Make MiningRun Real & Persisted

**Why**: Without this, Phase 1 has no memory or learning capability.

| # | Task | Files / Areas | Deliverable | Priority |
|---|------|---------------|-------------|----------|
| H1.1 | Complete `MiningRun` model + add DB table support | `models.py`, `storage.py` | Full model + SQLAlchemy `MiningRunDB` | Critical |
| H1.2 | Create `MiningRunRepository` | `storage.py` | `create`, `get_by_id`, `list_by_band`, `list_recent` | Critical |
| H1.3 | Wire `MiningRun` creation into `mine` command | `cli.py` | Every `mine` run creates and saves a record with stats | Critical |
| H1.4 | Add CLI commands for history | `cli.py` (`mining` subcommand or top-level) | `dkplaylister mining history` and `dkplaylister mining show <id>` | High |
| H1.5 | Surface mining activity in `doctor` | `cli.py` | Shows recent runs, success rate, most productive styles | Medium |

**Estimated Effort**: Medium

---

### H2: Add Meaningful Test Coverage for Phase 1 Core

**Why**: The LLM-driven parts are the riskiest new code.

| # | Area | Key Files | Suggested Tests | Effort |
|---|------|-----------|------------------|--------|
| H2.1 | `StyleDiscoveryExpansion` model | `models.py` | Roundtrips, validation, JSON serialization | Low |
| H2.2 | `expand_style_for_discovery` | `llm/grok.py`, `llm/base.py` | Mocked successful response, fallback behavior, structured output | Medium |
| H2.3 | `mine` command core logic | `cli.py` | Candidate collection, scoring pipeline, deduplication logic (with mocks) | Medium-High |
| H2.4 | Band scoping in mining | Multiple | Ensure mining always uses correct band's style and records band_id | Medium |
| H2.5 | `MiningRunRepository` | `storage.py` | CRUD + list_by_band isolation | Medium |

**Deliverables**:
- At least 15–20 new tests specifically for Phase 1 discovery logic
- Tests runnable via `pytest`

**Estimated Effort**: Medium

---

### H3: Harden the `mine` Command & Discovery Pipeline

**Current Weaknesses** (to address):
- Very basic deduplication
- Limited query count and no user control over queries
- Weak handling of LLM or Spotify failures
- No preview / dry-run mode
- Auto-import is all-or-nothing
- No recording of which queries actually produced results

| # | Task | Files | Deliverable |
|---|------|-------|-------------|
| H3.1 | Add `--dry-run` / `--preview` mode | `cli.py` | Shows what would be searched + estimated candidates without calling Spotify | High |
| H3.2 | Allow user to review/edit generated queries before search | `cli.py` | Interactive or `--queries-file` support | High |
| H3.3 | Improve deduplication & early filtering | `cli.py` + possibly new helpers | Better ID tracking + basic quality filters before full fetch | Medium |
| H3.4 | Robust error handling + user messaging | `cli.py`, `spotify.py` | Clear messages for rate limits, auth issues, empty results; continue on partial failures | High |
| H3.5 | Record per-query performance in `MiningRun` | `models.py`, `storage.py`, `cli.py` | Track which search queries returned how many candidates | Medium |
| H3.6 | Add `--band` enforcement + clear feedback | `cli.py` | Always require or default to a band; show which band is being used | Medium |

**Estimated Effort**: Medium-High

---

### H4: Consistent Band Scoping Audit for Phase 1

**Why**: We learned the hard way in Phase 0 that new features can accidentally leak across bands.

**Audit Checklist**:
- [ ] `mine` command always uses a specific band's latest style
- [ ] `MiningRun` records always have `band_id`
- [ ] Discovered playlists linked to mining runs carry correct provenance
- [ ] No global `get_latest()` calls without band context in new paths
- [ ] UI discovery flows (when added) respect sidebar band selector

**Deliverable**: Short audit report + fixes (similar to P0-4).

**Estimated Effort**: Medium

---

### H5: Basic UI Discovery Experience

| # | Task | Files | Deliverable |
|---|------|-------|-------------|
| H5.1 | Add "Discover Targets" mode in Streamlit | `ui/streamlit_app.py` | New mode that lets user trigger expansion + mining |
| H5.2 | Query review & editing UI | `ui/streamlit_app.py` | Show generated queries with checkboxes / edit boxes before running |
| H5.3 | Candidate review table | `ui/streamlit_app.py` | Data editor or table with score + "Import Selected" button |
| H5.4 | Mining history view | `ui/streamlit_app.py` | List of past `MiningRun` sessions with drill-down |

**Estimated Effort**: Medium-High

---

### H6: Error Handling & Resilience

- Improve messages in `doctor` related to discovery (e.g., "Last 5 mining runs had 3 failures due to rate limits").
- Add better retry / backoff around Spotify search during mining.
- Graceful handling when LLM returns poor/unusable expansion results.

**Estimated Effort**: Medium

---

### H7: Documentation & Polish

- Full documentation of `mine`, `style expand`, and future `mining` commands in `foundation-tools.md`.
- Update `getting-started.md` with a "Phase 1 Discovery Workflow" section.
- Improve command help text and examples.
- Add example output to the Phase 1 plan documents.

**Estimated Effort**: Low-Medium

---

## Success Criteria

Phase 1 can be considered "rock solid" when:

- Running `dkplaylister mine --band 1` produces traceable, reviewable results and creates a `MiningRun` record.
- All new discovery code has meaningful automated tests.
- Failures during mining do not crash the tool and give the user clear next steps.
- Band scoping is verified and consistent across CLI and (future) UI paths.
- A new user can understand and use the discovery features without confusion after reading `foundation-tools.md`.

---

**Status**: Major milestone — Phase 1 largely complete with full features + UI.
- H1, H3, H5, H7 done.
- New `discovery.py` shared module.
- Full "Discover Targets" mode in Streamlit: expand style, edit queries live, run mining, review scored candidates, one-click import (with MiningRun recording).
- CLI `mine` now very powerful (`--queries-file`, dry-run, stats).
- H2 deprioritized (minimal mocking).
- H4/H6 remain for polish.

Phase 1 Discovery is now a first-class experience.