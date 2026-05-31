"""Grok (xAI) provider implementation.

xAI's API is OpenAI-compatible, so we can use the official openai package
pointed at https://api.x.ai/v1.
"""

from __future__ import annotations

import os
from typing import Optional

from openai import OpenAI

from dkplaylister.llm.base import LLMProvider
from dkplaylister.models import Curator, Playlist, StyleProfile, StyleDiscoveryExpansion


class GrokProvider(LLMProvider):
    """Grok provider via xAI's OpenAI-compatible endpoint."""

    name = "grok"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "grok-3",
        base_url: str = "https://api.x.ai/v1",
    ):
        self.api_key = api_key or os.getenv("XAI_API_KEY")
        if not self.api_key:
            raise ValueError("XAI_API_KEY is required for GrokProvider")

        self.model = model
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=base_url,
        )

    def generate_pitch(
        self,
        style_profile: StyleProfile,
        song_title: str,
        lyrics: Optional[str],
        playlist: Playlist,
        curator: Optional[Curator] = None,
        pitch_format: str = "email",
        extra_instructions: Optional[str] = None,
        artist_name: Optional[str] = None,
        song_streaming_links: Optional[dict[str, str]] = None,
    ) -> str:
        """Generate a high-quality, personalized pitch using Grok."""

        artist = artist_name or "the artist"
        curator_context = ""
        effective_curator = curator or getattr(playlist, "curator", None)
        if effective_curator:
            contact_bits = []
            if effective_curator.email:
                contact_bits.append(f"Email: {effective_curator.email}")
            if effective_curator.instagram:
                contact_bits.append(f"Instagram: {effective_curator.instagram}")
            if effective_curator.website:
                contact_bits.append(f"Website/Profile: {effective_curator.website}")
            if contact_bits:
                curator_context = "\nCurator contact info:\n" + "\n".join(contact_bits)

        playlist_context = f"""Playlist Name: {playlist.name}
Follower Count: {playlist.follower_count or 'unknown'}
Playlist Description / Vibe: {playlist.description or 'No description available'}
URL: {playlist.url}"""

        # Use structured style data when available for richer personalization
        style_context = style_profile.raw_prompt
        if style_profile.target_audience:
            style_context += f"\n\nTarget Audience the artist usually connects with: {style_profile.target_audience}"
        if style_profile.similar_artists:
            style_context += f"\n\nSimilar artists this music sits alongside: {', '.join(style_profile.similar_artists)}"

        lyrics_context = ""
        if lyrics:
            lyrics_context = f"\n\nSong Lyrics (key excerpts):\n{lyrics[:2800]}"

        streaming_context = ""
        if song_streaming_links:
            links = "\n".join([f"- {platform.title().replace('_', ' ')}: {url}" for platform, url in song_streaming_links.items()])
            streaming_context = f"\n\nStreaming Links:\n{links}"

        system_prompt = f"""You are an expert independent music publicist who writes highly personalized, respectful, and effective playlist submission pitches.

You are writing on behalf of the artist/band **{artist}**.

Core Rules:
- Sound like a real human who genuinely respects this curator's taste — never desperate or salesy.
- Deeply personalize: Analyze the playlist's description to understand its specific audience and explain why this particular song from {artist} will resonate with *those* listeners.
- Weave in specific emotional or lyrical themes from the song that align with the playlist's vibe.
- Use the artist's detailed style description to show authentic fit.
- Reference the song title naturally.
- Keep the tone warm, concise, and confident.
- When streaming links are provided, include the best one (Spotify preferred) as a clean, short link.
- End with a low-pressure call to action.
"""

        user_prompt = f"""Artist / Band: {artist}

Artist Style & Identity:
{style_context}

Song Title: {song_title}
{lyrics_context}
{streaming_context}

Target Playlist & Audience:
{playlist_context}
{curator_context}

Desired Pitch Format: {pitch_format}

{extra_instructions or ""}

Write a strong, personalized {pitch_format} pitch from {artist} to this curator/playlist. Make it feel written specifically for this audience.
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.75,
            max_tokens=1400,
        )

        return response.choices[0].message.content.strip()

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=1200,
        )

        return response.choices[0].message.content.strip()

    def score_playlist_fit(
        self,
        style_profile: StyleProfile,
        playlist: Playlist,
    ) -> float:
        """Ask Grok to score how well the playlist fits the artist's style (0.0–1.0)."""

        # Build rich structured context from the full StyleProfile
        style_details = f"""Primary Genres: {', '.join(style_profile.primary_genres) or 'Not specified'}
Secondary/Related Genres: {', '.join(style_profile.secondary_genres) or 'Not specified'}
BPM Range: {style_profile.bpm_range[0]}–{style_profile.bpm_range[1]}
Energy Level: {style_profile.energy_level}
Mood Keywords: {', '.join(style_profile.mood_keywords) or 'Not specified'}
Sonic Characteristics: {', '.join(style_profile.sonic_characteristics) or 'Not specified'}
Vocal Style: {style_profile.vocal_style or 'Not specified'}
Production Notes: {style_profile.production_notes or 'Not specified'}
Similar Artists: {', '.join(style_profile.similar_artists) or 'Not specified'}"""

        prompt = f"""You are an expert A&R and playlist curator analyst.

Rate how well this playlist matches the artist's specific musical style on a scale from 0.0 to 1.0.

**Important (Feb 2026 API changes):** Do NOT rely on removed fields such as popularity, available_markets, or artist followers. Base your judgment only on name, description, genres/tags, and follower count.

Artist Style Profile:
{style_profile.raw_prompt}

Structured Details:
{style_details}

Target Playlist:
- Name: {playlist.name}
- Description: {playlist.description or 'No description available'}
- Reported Genres/Tags: {', '.join(playlist.genres + playlist.tags) or 'Unknown'}
- Followers: {playlist.follower_count or 'Unknown'}

Scoring Guidelines:
- 0.90–1.00 = Extremely strong match (very close to the artist's sound and aesthetic)
- 0.70–0.89 = Good match (clear overlap in genre, mood, and production)
- 0.50–0.69 = Moderate / partial match
- 0.30–0.49 = Weak match
- 0.00–0.29 = Poor match

Respond with ONLY a single decimal number between 0.0 and 1.0 (example: 0.83). 
No explanation or extra text."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=10,
            )
            text = response.choices[0].message.content.strip()
            score = float(text)
            return max(0.0, min(1.0, score))
        except Exception:
            return 0.5  # safe fallback

    def expand_style_for_discovery(
        self,
        style_profile: StyleProfile,
    ) -> StyleDiscoveryExpansion:
        """
        Use Grok to expand the artist's StyleProfile into structured signals
        useful for discovery and mining (Phase 1).
        """
        prompt = f"""You are an expert music discovery strategist for independent artists.

Given the following detailed style description, produce a structured JSON object that can be used to generate high-quality Spotify search queries and Playlister searches.

Style Description:
{style_profile.raw_prompt}

Return ONLY valid JSON with this exact structure (no markdown, no extra text):

{{
  "primary_genres": ["list", "of", "core", "genres"],
  "sub_genres": ["more", "specific", "subgenres"],
  "moods": ["atmospheric", "melancholic", ...],
  "search_queries": [
    "best search strings for Spotify playlist search",
    "another good query"
  ],
  "similar_artists": ["artists", "that", "fit", "this", "vibe"],
  "playlist_title_hints": ["words/phrases that often appear in good playlist titles for this style"],
  "explanation": "One short paragraph explaining the discovery strategy for this artist."
}}

Keep search_queries concise (3-8 words each) and effective for finding real curators who program this kind of music. Limit to 6-8 high-quality queries."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=800,
            )
            text = response.choices[0].message.content.strip()

            import json
            if text.startswith("```"):
                text = text.split("```")[1].replace("json", "").strip()

            data = json.loads(text)
            return StyleDiscoveryExpansion(**data)
        except Exception as e:
            # Safe fallback
            return StyleDiscoveryExpansion(
                search_queries=[style_profile.raw_prompt[:120]],
                similar_artists=style_profile.similar_artists or [],
                explanation=f"Fallback: Could not expand style with LLM ({e})",
            )

    def close(self) -> None:
        # OpenAI client doesn't require explicit closing in most cases
        pass
