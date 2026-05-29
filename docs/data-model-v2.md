# Data Model v2: Band, Style, and Song Management

## Goals

- Support multiple bands/artists under one DKPlaylister installation.
- Allow one band to have many distinct styles (e.g. "Cinematic Indie", "Heavy Rock", "Acoustic Folk").
- Allow one band to have many songs with full lyrics.
- Make pitching and scoring always happen in the context of a specific band + chosen style + chosen song.
- Keep the existing "semi-automatic from Playlister" workflow.

## Proposed Core Entities

### Band
- id
- name (e.g. "Kilynn Ross")
- slug (e.g. "kilynn-ross") — used for folder organization under inputs/band/
- notes (optional)
- created_at, updated_at

### Style (formerly StyleProfile)
- id
- band_id (FK → Band)
- name (e.g. "Cinematic Indie Base", "Heavy Version")
- raw_prompt (the long descriptive text)
- Structured fields (primary_genres, bpm_range, energy_level, etc.)
- version
- created_at, updated_at

### Song
- id
- band_id (FK → Band)
- title
- lyrics (full text)
- notes (optional)
- metadata (key, tempo, duration, etc. — flexible JSON for now)
- created_at, updated_at

### Relationships
- Band → many Styles (1:many)
- Band → many Songs (1:many)
- Pitch will now reference:
  - song_id
  - style_id
  - playlist_id (existing)

## Migration Considerations

Current tables:
- style_profiles (will be deprecated/renamed)
- playlists (can stay mostly the same, may add band_id later if needed)

New tables:
- bands
- styles
- songs

For early development we can:
- Keep the old `style_profiles` table for backward compatibility during transition.
- Or do a clean break since this is still pre-1.0.

## CLI Commands (Proposed)

```bash
# Band management
dkplaylister band create "Kilynn Ross" --slug kilynn-ross
dkplaylister band list
dkplaylister band set-default <id>

# Style management (scoped to band)
dkplaylister style set --band kilynn-ross --file inputs/band/kilynn-ross/style/cinematic.txt --name "Cinematic Base"
dkplaylister style list --band kilynn-ross
dkplaylister style show <id>

# Song / Lyrics management
dkplaylister song add --band kilynn-ross --title "If I Get My Say" --file inputs/band/kilynn-ross/songs/if-i-get-my-say.txt
dkplaylister song list --band kilynn-ross
dkplaylister song show <id>

# Pitching (now requires choosing band + style + song)
dkplaylister pitch --band kilynn-ross --style <id> --song <id> --target <playlist-id>
```

## Streamlit UI Changes

- Add a "Current Band" selector (or default band in sidebar).
- Separate sections or tabs for:
  - Bands
  - Styles (per selected band)
  - Songs / Lyrics library (per selected band)
- When generating a pitch, force selection of Band → Style → Song → Target.

## Folder Structure (Recommended)

```
inputs/
  band/
    kilynn-ross/
      style/
        cinematic.txt
        heavy.txt
      songs/
        if-i-get-my-say.txt
        another-song.txt
      playlists/
        my-playlister-exports/
```

This matches the user's existing `inputs/band/kilynn-ross/` pattern.

## Open Questions

- Should a Style belong to a Band or be global? → Strongly recommend per-band.
- Do we need "Projects" or "Releases" on top of Band + Song? (Defer for now.)
- How do we handle submission history per Band? (Probably add band_id to Submission later.)

## Implementation Phases

1. Add Band model + table + repository + basic CLI
2. Update Style to require band_id (migration + update repositories + CLI/UI)
3. Add Song model + table + repository + CLI
4. Update Pitch generation to require song + style
5. Update Streamlit UI with band/style/song management
6. Backfill or deprecate old global StyleProfile behavior
