"""Grok (xAI) provider implementation.

xAI's API is OpenAI-compatible, so we can use the official openai package
pointed at https://api.x.ai/v1.
"""

from __future__ import annotations

import os
from typing import Optional

from openai import OpenAI

from dkplaylister.llm.base import LLMProvider
from dkplaylister.models import Curator, Playlist, StyleProfile


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
    ) -> str:
        """Generate a high-quality, personalized pitch using Grok."""

        curator_context = ""
        if curator:
            contact_bits = []
            if curator.email:
                contact_bits.append(f"Email: {curator.email}")
            if curator.instagram:
                contact_bits.append(f"Instagram: {curator.instagram}")
            if contact_bits:
                curator_context = "\nCurator contact info:\n" + "\n".join(contact_bits)

        playlist_context = f"""Playlist: {playlist.name}
Follower count: {playlist.follower_count or 'unknown'}
Description: {playlist.description or 'No description available'}
URL: {playlist.url}"""

        style_context = style_profile.raw_prompt

        lyrics_context = ""
        if lyrics:
            lyrics_context = f"\n\nSong Lyrics:\n{lyrics[:2500]}"  # safety cap

        system_prompt = """You are an expert independent music publicist who writes highly personalized, respectful, and effective playlist submission pitches.

Rules:
- Never sound desperate or overly salesy.
- Be specific: reference the playlist's vibe and why this song fits.
- Use the artist's actual lyrics and style description to create genuine connection.
- Keep emails relatively concise but emotionally resonant.
- For Instagram DMs, be even shorter and warmer.
- Always include the song title and a clean streaming link placeholder.
- End with a clear, low-pressure call to action.
"""

        user_prompt = f"""Artist Style Description:
{style_context}

Song Title: {song_title}
{lyrics_context}

Target Playlist:
{playlist_context}
{curator_context}

Pitch Format: {pitch_format}

{extra_instructions or ""}

Write a strong, personalized {pitch_format} pitch for this curator/playlist.
"""

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

        prompt = f"""Rate how well this playlist matches the following artist style on a scale of 0.0 to 1.0.

Artist Style:
{style_profile.raw_prompt}

Playlist:
Name: {playlist.name}
Description: {playlist.description or 'N/A'}
Genres/Tags: {', '.join(playlist.genres + playlist.tags) or 'unknown'}

Respond with ONLY a single number between 0.0 and 1.0 (e.g. 0.87). No explanation."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=20,
            )
            text = response.choices[0].message.content.strip()
            score = float(text)
            return max(0.0, min(1.0, score))
        except Exception:
            return 0.5  # safe fallback

    def close(self) -> None:
        # OpenAI client doesn't require explicit closing in most cases
        pass
