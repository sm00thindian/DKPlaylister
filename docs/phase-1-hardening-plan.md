# Phase 1 Hardening Plan

**Goal**: Make the new Discovery & Mining capabilities of Phase 1 genuinely "rock solid" before investing further in advanced automation or UI-heavy features.

Phase 1 (as defined in the roadmap and `phase-1-discovery-mining-plan.md`) focuses on turning Style Profiles into an active discovery engine:
- Intelligent query expansion from styles
- The `mine` command and future equivalents
- Traceable `MiningRun` sessions
- Hybrid Playlister + Spotify workflows

This plan identifies the gaps that prevent the current early Phase 1 work from feeling stable, reliable, and trustworthy as a foundation for the rest of the project.

---

## Current State (as of latest work)

- `StyleDiscoveryExpansion` model + `expand_style_for_discovery()` implemented (Grok)
- `dkplaylister style expand` command exists
- `dkplaylister mine` MVP command exists (style expansion → Spotify search → enrich + score → display)
- `MiningRun` model exists only as a stub (never persisted or used)
- No dedicated tests for expansion or mining logic
- `mine` command has basic error handling and deduplication but many rough edges
- No UI discovery experience yet
- No mining history / provenance visible to the user
- Limited integration between new mining flows and the rest of the hardened Phase 0 foundation (`doctor`, band scoping verification, etc.)

---

## Priority Levels

- **P1-H (Critical Hardening)**: Must be addressed before building more ambitious mining features. These represent real risk or incompleteness in the new discovery layer.
- **P1-M (Medium)**: Strongly recommended for reliability.
- **P1-L (Lower)**: Nice to have but can be deferred.

---

## P1-H – Critical Phase 1 Hardening

### H1. Make MiningRun a First-Class, Persisted Record
**Current State**: Stub model only. No repository, no creation during `mine`, no history.

**Why it matters**: Traceability and learning are core to Phase 1's value proposition. Without this, we have no memory of what styles/queries produced good targets.

**Tasks**:
- Complete `MiningRun` model and add `MiningRunRepository` in storage.
- Wire creation of `MiningRun` records inside the `mine` command (and future discovery paths).
- Add CLI command: `dkplaylister mining history` / `dkplaylister mining runs`.
- Surface basic mining stats in `dkplaylister doctor`.

### H2. Add Meaningful Test Coverage for Phase 1 Core
**Current State**: Zero tests for `expand_style_for_discovery`, `StyleDiscoveryExpansion`, or the `mine` flow.

**Why it matters**: The new LLM-driven discovery path is complex and will evolve. We need confidence it doesn't regress.

**Tasks**:
- Unit tests for `StyleDiscoveryExpansion` model roundtrips and validation.
- Tests for `expand_style_for_discovery` (mocked LLM responses).
- Integration-style tests for candidate discovery + scoring pipeline.
- Tests verifying band scoping in mining flows.

### H3. Harden the `mine` Command & Discovery Pipeline
**Current State**: Functional MVP but brittle in several areas.

**Why it matters**: This is the primary user-facing Phase 1 feature. It needs to feel reliable.

**Key Tasks**:
- Improve deduplication and candidate quality (better seen_ids, filter low-quality results early).
- Robust rate-limit handling and graceful degradation when Spotify/LLM calls fail.
- Better progress feedback and cancellation support.
- Add `--dry-run` / preview mode.
- Support for editing/curating the generated search queries before execution.
- Proper band scoping verification throughout the flow.
- Handle cases with no/poor expansion results more gracefully.

### H4. Consistent Band Scoping & Data Integrity for Discovery
**Current State**: New flows were added quickly; full audit has not been performed.

**Why it matters**: Repeats the risk we fixed in Phase 0 P0-4.

**Tasks**:
- Audit all new mining paths for correct `band_id` usage.
- Ensure `MiningRun`, discovered `Playlist` associations, and scores respect the selected band.
- Add validation that discovery always happens against a specific band's style.

---

## P1-M – Medium Priority Hardening

### H5. Basic UI Discovery Experience
- Add a "Discover New Targets" mode or section in the Streamlit app.
- Allow users to trigger expansion, review/edit queries, run mining, and review candidates before import.
- Show mining history in the UI.

### H6. Error Handling & Resilience Improvements
- Improve user messaging for LLM failures, Spotify rate limits, and empty results during mining.
- Update `doctor` to report on recent mining activity and any common failure patterns.
- Add lightweight retry logic where appropriate.

### H7. Documentation & Help Polish
- Update `foundation-tools.md` with detailed `mine` and mining-related commands.
- Improve `--help` text and examples for `mine`.
- Add a short "Phase 1 Discovery Workflow" guide.

---

## P1-L – Lower Priority / Future Polish

- Hybrid Playlister-aware expansion (using Playlister search terms + style).
- Caching of expansion results.
- More advanced candidate ranking before full enrichment.
- Integration with user-top-read data for better personalization of discovery (cross-cutting).

---

## Recommended Execution Order

1. **H1** (MiningRun persistence) – Foundational for everything else in Phase 1.
2. **H2** (Tests) – Build safety net while the surface area is still small.
3. **H3** (Harden `mine` command) – Make the primary user tool reliable.
4. **H4** (Band scoping audit) – Prevent the same class of bugs we fixed in Phase 0.
5. **H5–H7** (UI, error handling, docs) – Once the core is trustworthy.

---

## Success Criteria for "Rock Solid" Phase 1

- A user can run `dkplaylister mine --band X`, get useful candidates, and have the session recorded in `MiningRun` history.
- All discovery flows have reasonable test coverage and respect band boundaries.
- Failures during mining are handled gracefully with clear guidance.
- The experience feels like a natural, solid extension of the hardened Phase 0 foundation rather than experimental glue.

---

**Detailed Task Breakdown**: See [docs/phase-1-hardening-plan-detailed.md](phase-1-hardening-plan-detailed.md) for the full prioritized task list with files, deliverables, and suggested order.

**Current Status**: Phase 1 meaningfully complete with full features + excellent UI.
- "Discover Targets" mode in Streamlit is fully working (expansion → editable queries → mining → scored candidates → import + MiningRun).
- Shared `discovery.py` + powerful CLI (`--queries-file` workflow).
- H2 heavy mocking deprioritized.

See detailed plan for remaining polish items (H4, H6).