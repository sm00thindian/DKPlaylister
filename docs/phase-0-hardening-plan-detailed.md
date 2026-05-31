# Phase 0 Hardening Plan – Detailed Task Breakdown

**Objective**: Bring DKPlaylister to a genuinely solid, reliable foundation (Phase 0) before continuing to add major new features.

This document expands the high-level plan into concrete, prioritized tasks with specific files, order of attack, and clear deliverables.

---

## Recommended Execution Order (P0 First)

We strongly recommend completing the P0 items in roughly this sequence:

1. **Database Migrations** (foundational for everything else)
2. **Test Coverage on Core** (builds confidence while refactoring)
3. **Make Pitch & Submission Records Real**
4. **Consistent Band Scoping Audit & Fixes**
5. **Improve `init` + First-Run Experience**

P1 items can be interleaved once the above are in good shape.

---

## P0 Tasks – Detailed Breakdown

### P0-1: Adopt Proper Database Migrations (Alembic)

**Why**: The current manual migration system is unsustainable and risky.

**Subtasks** (in suggested order):

| # | Task | Files / Areas | Deliverable | Notes |
|---|------|---------------|-------------|-------|
| 1.1 | Set up Alembic in the project | `alembic.ini`, `alembic/env.py`, `alembic/versions/` | Working Alembic configuration | Use `alembic init` and configure it to use the existing `Base` metadata |
| 1.2 | Create initial migration from current models | `alembic/versions/0001_initial.py` | Migration that creates all current tables | Should match the existing schema exactly |
| 1.3 | Convert existing manual migrations to Alembic | `storage.py` + new migration files | Remove or deprecate the 4 `_migrate_*` functions | Create one migration per previous manual change |
| 1.4 | Update `get_session()` and `init` command | `storage.py`, `cli.py` | `get_session` no longer calls manual migrations | `init` command should run `alembic upgrade head` |
| 1.5 | Document migration workflow | `docs/database-migrations.md` (new) | Clear guide for future schema changes | Include how to generate + review migrations |

**Estimated Effort**: Medium-High (2–4 days)

**Dependencies**: None

**Risk if skipped**: High – future schema changes will become increasingly dangerous.

---

### P0-2: Add Meaningful Test Coverage on Core Foundation

**Why**: We currently have almost no safety net for the most important parts of the system.

**Priority Areas** (in rough order):

| # | Area | Key Files | Suggested Tests | Effort |
|---|------|-----------|------------------|--------|
| 2.1 | Model roundtrips | `models.py`, `storage.py` | Create → save → load → compare for Band, Song, Album, StyleProfile, Playlist | Low |
| 2.2 | SongRepository | `storage.py` | `create`, `get_by_id`, `list_by_band`, `update` with various edge cases | Medium |
| 2.3 | StyleProfileRepository + band scoping | `storage.py` | Filtering by `band_id`, `get_latest(band_id=...)` | Medium |
| 2.4 | PlaylistRepository + provenance | `storage.py` | Saving curator data, `contact_revealed_via`, `source`, `discovery_query` | Medium |
| 2.5 | Scoring engine | `scoring.py` | `PlaylistScorer.score()` with various weight configurations and edge cases | Medium |
| 2.6 | Band isolation | Multiple | Ensure data from one band does not leak into another in key flows | Medium |

**Deliverables**:
- At least 30–40 meaningful tests
- Tests runnable via `pytest`
- Basic CI configuration (GitHub Actions recommended)

**Estimated Effort**: Medium (3–5 days)

---

### P0-3: Make Pitch and Submission Records Functional

**Current Problem**: The models exist but are almost never created or used.

**Tasks**:

| # | Task | Files | Deliverable |
|---|------|-------|-------------|
| 3.1 | Add `Pitch` creation on generation | `llm/grok.py`, `cli.py`, `ui/streamlit_app.py` | Every pitch generation creates a `Pitch` record |
| 3.2 | Link Pitch to proper foreign keys | `models.py`, repositories | `band_id`, `song_id`, `style_profile_id`, `playlist_id` are correctly set |
| 3.3 | Create minimal Submission flow | `cli.py` + new `pitch mark-sent` or UI button | User can mark a generated pitch as sent → creates `Submission` |
| 3.4 | Update scoring to use real history (placeholder → real) | `scoring.py` | `personal_history_bonus` starts using actual submission data |
| 3.5 | Add basic UI/CLI visibility | Streamlit + CLI | Show "Pitches generated" and "Submissions" counts |

**Estimated Effort**: Medium-High

---

### P0-4: Ensure Consistent Band Scoping

**Goal**: Every major flow must respect the selected band.

**Audit Checklist** (turn into tasks):

- [ ] `dkplaylister add` / `import` – should optionally accept `--band`
- [ ] Scoring when importing from CLI
- [ ] All "Generate Pitch" paths (including tracker-sourced targets)
- [ ] `dkplaylister targets` listing
- [ ] Streamlit "Review Targets" and "Generate Pitch" modes
- [ ] Any remaining global `get_latest()` calls without `band_id`

**Deliverable**: A short audit document + fixes for any leaks found.

**Estimated Effort**: Medium

---

### P0-5: Improve `init` Command and First-Run Experience

**Tasks**:

| # | Task | Files | Notes |
|---|------|-------|-------|
| 5.1 | Make `init` actually create tables + run migrations | `cli.py` | Should be safe to run multiple times |
| 5.2 | Add environment validation | `cli.py` | Warn if `XAI_API_KEY` or Spotify credentials are missing |
| 5.3 | Add `dkplaylister doctor` or `dkplaylister status` command | `cli.py` | Shows DB status, auth status, number of bands/styles/songs/targets |
| 5.4 | Improve error messages on first use | Multiple | Better guidance when things are not set up |

**Estimated Effort**: Low-Medium

---

## Suggested Execution Sequence (Recommended)

1. **Start with P0-1** (Alembic migrations) — this unblocks safe future work.
2. **Do P0-2** (tests) in parallel or immediately after — especially on storage and scoring.
3. Tackle **P0-3** (Pitch/Submission records) — this makes the core value loop real.
4. Run the **P0-4** band scoping audit and fix issues as they are found.
5. Finish with **P0-5** (init + doctor command) for better onboarding.

---

## Success Criteria

Phase 0 can be considered "rock solid" when:

- A fresh clone + `dkplaylister init` + basic setup lets a user create a band, style, song, import 5–10 playlists, and generate pitches without schema or scoping surprises.
- All P0 tasks above have been completed or consciously deferred with documented reasoning.
- New contributors (or future you) feel confident making changes to the core without fear of breaking the foundation.

---

**Next Step Recommendation**: Start with **P0-1 (Database Migrations)**. Would you like me to begin that work now? I can create the initial Alembic setup and the first proper migration.

---

**Phase 0 Completion Note**: All items in this plan have been executed. The resulting stable foundation tools are documented in [docs/foundation-tools.md](foundation-tools.md).

Phase 1 early implementation complete. Dedicated hardening plan created: [docs/phase-1-hardening-plan.md](phase-1-hardening-plan.md) and detailed breakdown.