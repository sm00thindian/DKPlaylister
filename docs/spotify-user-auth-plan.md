# Spotify User Authentication & Personalization Plan

## Current State (as of now)

- Authorization Code Flow has been activated.
- Default scopes: `user-read-private user-read-email user-top-read`
- Functions available: `get_user_client()` and `get_oauth_client()`
- CLI support: `dkplaylister auth spotify [--status] [--scopes ...] [--force]`

## Strategic Value of User Authentication

The primary goal of adding user auth is **not** to access curator data (Spotify does not expose other users' emails or private data). 

Instead, the value comes from deeply understanding **the artist using the tool**:

- Their actual listening taste
- What they save
- What they listen to most
- Their own playlists

This data can significantly improve:
1. Playlist scoring accuracy
2. Quality of Grok-generated pitches
3. Overall relevance of recommended targets

## Scope Prioritization

### Tier 1 – Activate Now (High ROI)

| Scope                    | Value | Planned Use Cases |
|--------------------------|-------|-------------------|
| `user-top-read`          | ★★★★★ | Core input for scoring and pitch personalization. Artist's top artists/tracks become strong signals. |
| `user-library-read`      | ★★★★  | Understand what the artist actually likes and has saved. Use as positive examples for fit scoring. |
| `playlist-read-private`  | ★★★★  | Allow artists to reference their own private playlists when defining style. |

### Tier 2 – Next Phase

| Scope                          | Value | Planned Use Cases |
|--------------------------------|-------|-------------------|
| `user-read-recently-played`    | ★★★   | Detect active listening patterns. Could influence "freshness" weighting. |
| `playlist-read-collaborative`  | ★★★   | Capture collaborative playlists (common for bands with teams). |

### Tier 3 – Future Workflow Features (Write Access)

These enable powerful automation but require careful UX and trust-building:

| Scope                       | Potential Features |
|-----------------------------|--------------------|
| `playlist-modify-private`   | Auto-maintain a "DKPlaylister – My Targets" playlist with high-scoring playlists |
| `user-library-modify`       | One-click "Save best targets to my library" |
| `playlist-modify-public`    | Same as above but public (lower priority) |

## Proposed Feature Ideas (in rough priority order)

1. **"Enhance Style from My Listening"**  
   Pull top artists + top tracks and suggest additions or refinements to the artist's StyleProfile.

2. **Improved Scoring Using User Taste**  
   When scoring a target playlist, boost scores if the playlist contains artists the user actually listens to (from `user-top-read`).

3. **Better Pitch Context**  
   Pass the artist's top artists/genres into the Grok pitch prompt so pitches feel more authentic.

4. **Reference Playlists**  
   Allow selecting one of the artist's own playlists as additional context when generating pitches.

5. **"My Targets" Playlist Management** (requires write scope)  
   Automatically maintain a dedicated playlist of targets the artist is considering or has pitched.

6. **Listening-Based Alerts**  
   Surface playlists that the artist has recently engaged with (via recently played or library).

## Implementation Guidelines

- Always make additional scopes **opt-in** after the initial login.
- Clearly explain *why* each scope is being requested in the CLI/UI.
- Never request write scopes by default.
- Store the list of granted scopes alongside the band or user profile for future reference.
- When generating pitches or scores, gracefully degrade if the required scopes are not granted.

## Open Questions

- Should `user-top-read` data be used to *automatically* suggest new StyleProfiles?
- How much of the artist's listening data should be stored locally vs. fetched live?
- Do we want to support multiple connected Spotify accounts (e.g. artist + manager)?

## Next Actions

- [ ] Add `user-library-read` to the recommended default scopes (after user feedback on `user-top-read`)
- [ ] Build "Enhance Style from Listening History" feature (Phase 3)
- [ ] Prototype improved scoring that incorporates `user-top-read` data
- [ ] Evaluate demand for write scopes (`playlist-modify-private`)
- [ ] Update getting-started docs with recommended auth scopes

---

*This document should be reviewed whenever we consider requesting additional Spotify scopes.*