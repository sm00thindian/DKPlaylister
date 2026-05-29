# Prioritization & Scoring in DKPlaylister

## Philosophy

We deliberately do **not** optimize for the biggest playlists.

The goal is to maximize **real human listener exposure** from curators who are likely to actually listen to your music, add it, and keep it in rotation.

Raw follower count is a signal — but it is far from the only (or even the most important) one.

## Default Scoring Factors

All factors below are **configurable** (weights, thresholds, and penalties can be adjusted in your local settings).

| Factor                    | Default Importance | Description |
|---------------------------|--------------------|-----------|
| **Activity & Freshness**      | Very High         | Has the playlist added tracks in the last 30–90 days? Is the curator still posting or active? This is one of the strongest signals of a living playlist. |
| **Genre + Vibe Fit**          | Very High         | How well the playlist matches your detailed Style Prompt (semantic understanding + keyword signals). This is where Grok helps significantly. |
| **Submission Openness**       | High              | Explicit or strong signals that the curator accepts outside music ("submissions", "accepting demos", public contact info, recent adds from similar artists, etc.). Playlister.com results get a natural boost here. |
| **Follower Count**            | Medium            | Log-scaled with strong diminishing returns. A thoughtfully curated 10–25k playlist often ranks higher than a neglected 100k+ playlist. |
| **Contact Quality**           | Medium-High       | Real email address > active and responsive Instagram > tracked bit.ly/short link > no usable contact. |
| **Your Historical Data**      | High (grows over time) | Has this curator or similar playlists responded positively to you before? Have you had success in this follower range or genre niche? |
| **Risk / Bot Penalties**      | Strong Negative   | Evidence or strong suspicion of botted playlists, pay-to-play language, extremely low engagement relative to size, or curators you've previously flagged as low quality. |

## How Scoring Is Used

- When you run a mining or import operation, every playlist receives a composite **Value Score**.
- The system can explain the ranking (e.g., "This playlist scored high because of strong fit + recent activity, despite lower follower count").
- You can override scores manually or add custom notes ("Great response last time", "Botted — avoid").
- Over time, your personal history becomes one of the highest-weighted signals.

## Configuration

(Planned)

You will be able to set custom weights and rules, for example:

- Increase the penalty for playlists over 80k if you believe very large playlists rarely engage with new artists in your genre.
- Boost "mid-size active curators" (8k–35k with recent adds) for your specific campaign.
- Create genre-specific scoring profiles.

## Playlister.com Specific Notes

Because Playlister surfaces playlists where curators have publicly shared contact information, these results receive an automatic boost in the **Submission Openness** category.

However, they are still run through the full scoring engine (especially Activity + Fit) so you are not just chasing volume from the daily 20-contact limit.

## Philosophy Summary

- **Quality over quantity**
- **Living playlists over vanity metrics**
- **Your actual results over generic assumptions**
- **Configurable** so the system improves with you

This is one of the most important differentiators of DKPlaylister compared to other tools.
