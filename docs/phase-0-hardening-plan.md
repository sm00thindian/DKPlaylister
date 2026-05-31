# Phase 0 Hardening Plan

**Goal**: Make the foundation of DKPlaylister genuinely "rock solid" before investing further in new features.

Phase 0 is defined in the README as:
- Solid local database + provenance tracking
- Core models (StyleProfile, Playlist, Pitch, Submission)
- Configurable prioritization and scoring engine
- Pluggable Grok-first LLM layer
- Multi-band support (Bands, Styles per band, Songs per band)

This plan identifies the gaps that prevent Phase 0 from feeling stable, reliable, and trustworthy as a foundation.

---

## Priority Levels

- **P0 (Critical)**: Must be addressed before building significant new functionality. These items represent real risk or foundational incompleteness.
- **P1 (High)**: Strongly recommended for a solid foundation. Should be done soon.
- **P2 (Medium)**: Improves quality and maintainability but can be deferred if needed.

---

## P0 – Critical Foundation Hardening

### 1. Proper Database Migrations
**Current State**: Multiple ad-hoc `_migrate_*` functions in `storage.py`. Alembic is listed as a dependency but is not used.

**Why it matters**: Manual migrations are fragile, hard to review, and will become a major source of bugs as the schema evolves.

**Tasks**:
- Decide on migration strategy (strongly recommend adopting Alembic properly).
- Convert existing manual migrations into proper Alembic migrations.
- Update `dkplaylister init` and `get_session` to use the migration system.
- Add documentation on how schema changes should be made going forward.

**Effort**: Medium-High

### 2. Meaningful Test Coverage on Core Foundation
**Current State**: Only 2 very basic tests in `tests/test_models.py`.

**Why it matters**: Without tests, we have no confidence that core behaviors (scoring, storage, model integrity, band scoping) remain correct as we iterate.

**Tasks**:
- Add tests for `SongRepository`, `StyleProfileRepository`, and `PlaylistRepository`.
- Add tests for `ScoringConfig` and `PlaylistScorer` (including edge cases).
- Add tests for multi-band scoping behavior.
- Set up CI to run tests on push (even if simple at first).

**Effort**: Medium

### 3. Make Pitch and Submission Records Actually Functional
**Current State**: `Pitch` and `Submission` models exist in `models.py` but are barely used in the real application flow.

**Why it matters**: These are explicitly listed as core Phase 0 models. The system currently generates pitches but does not create proper `Pitch` records or track `Submission` history.

**Tasks**:
- Decide on the minimal viable `Pitch` creation flow (even if "sent" is manual for now).
- Wire pitch generation so that a `Pitch` record is created and linked to `band_id`, `song_id`, `style_profile_id`, and `playlist_id`.
- Begin creating `Submission` records when a pitch is marked as sent (even manually).
- Update the UI and CLI to reflect this reality.

**Effort**: Medium

### 4. Consistent Band Scoping Across the Entire System
**Current State**: Multi-band support has been added in many places, but some paths (especially older ones and certain UI flows) still have global or leaky behavior.

**Why it matters**: This is one of the biggest structural changes in v2. Inconsistent scoping will cause confusing bugs and data integrity issues.

**Tasks**:
- Audit all major code paths (CLI commands, UI modes, scoring, pitch generation) for band scoping.
- Fix any remaining places where `current_band_id` is not properly respected.
- Add tests that verify band isolation.

**Effort**: Medium

### 5. Improve the `init` Command and First-Run Experience
**Current State**: `dkplaylister init` only creates a directory and touches a file. Real schema creation happens lazily.

**Why it matters**: A foundation tool should have a reliable, clear initialization experience.

**Tasks**:
- Make `init` actually create tables and run migrations.
- Add better feedback and next-step guidance.
- Consider a `--check` or `doctor` command that validates environment, database, and credentials.

**Effort**: Low-Medium

---

## P1 – High Priority Cleanup

### 6. Reduce Technical Debt from Rapid Feature Addition
- Audit recent advanced features (Playlister CSV processing, multi-song pitching from trackers, streaming links UI) and decide what truly belongs in Phase 0 vs. Phase 1+.
- Consider moving some of the more experimental tracker spreadsheet logic behind feature flags or into a separate "experimental" section until the core is hardened.

### 7. Improve Data Integrity and Validation
- Add better validation when creating/updating core entities.
- Consider adding lightweight integrity checks (e.g., ensuring a Song belongs to the same band as its StyleProfile when used together).

### 8. Strengthen Error Handling Around External Services
- Improve resilience and user messaging around Spotify API failures and Grok generation failures.
- Add better logging for debugging production issues.

---

## P2 – Medium Priority Improvements

- Expand LLM provider testing and add at least one additional provider (even as a stub) to validate the pluggable design.
- Refine the scoring engine with more real-world edge case handling and better documentation of default weights.
- Improve documentation specifically for Phase 0 concepts (core models, database schema, how to safely extend them).
- Add basic end-to-end tests for the most important user flows (e.g., create band → add style → add song → import playlist → generate pitch).

---

## Recommended Approach

1. **Start with P0 items 1–3** (Migrations, Tests, and making Pitch/Submission records real). These have the highest impact on long-term stability.
2. Tackle item 4 (Band Scoping consistency) in parallel or immediately after, as it affects almost everything.
3. Use this plan as a gate: Avoid adding major new features until the majority of P0 items are addressed.

---

## Success Criteria for "Rock Solid" Phase 0

- A new developer (or future you) can run `dkplaylister init`, set up a band + style + song, import a few playlists, and generate a pitch without hitting schema or scoping surprises.
- All core models have reasonable test coverage.
- Schema changes can be made safely and reviewed.
- The system has a clear, honest story about what is stable foundation vs. experimental.

---

*This document should be updated as items are completed or new risks are discovered.*

**Outcome**: The complete list of hardened foundation tools is documented in [docs/foundation-tools.md](foundation-tools.md).

Phase 1 (Discovery & Mining) planning and early implementation complete. Hardening plan now active: [docs/phase-1-hardening-plan.md](phase-1-hardening-plan.md).