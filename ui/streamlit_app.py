"""
DKPlaylister - Local Web UI (Streamlit)

This provides a friendlier interface for the core workflow:
- Manage Style Profile
- Review imported/scored targets from Playlister
- Generate and edit pitches using Grok

Run with:
    streamlit run ui/streamlit_app.py
"""

import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# Add src to path so we can import the package
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dkplaylister.storage import PlaylistRepository, StyleProfileRepository
from dkplaylister.llm import get_provider
from dkplaylister.scoring import PlaylistScorer
from dkplaylister.models import StyleProfile

load_dotenv()

st.set_page_config(
    page_title="DKPlaylister",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Helpers ---

@st.cache_resource
def get_repos():
    return PlaylistRepository(), StyleProfileRepository()

@st.cache_resource
def get_llm():
    if not os.getenv("XAI_API_KEY"):
        return None
    return get_provider("grok")

playlist_repo, style_repo = get_repos()
llm = get_llm()

# --- Sidebar ---

st.sidebar.title("DKPlaylister")
st.sidebar.markdown("Local tool for high-signal playlist pitching")

mode = st.sidebar.radio(
    "Mode",
    ["Review Targets", "Generate Pitch", "Manage Style"],
    index=0,
)

st.sidebar.divider()

latest_style = style_repo.get_latest()
if latest_style:
    st.sidebar.success(f"Style Profile: **{latest_style.name}** (ID {latest_style.id})")
else:
    st.sidebar.warning("No Style Profile loaded yet.")

# --- Main Content ---

if mode == "Review Targets":
    st.header("Your Scored Targets")
    st.caption("Imported from Playlister + enriched + scored against your Style Profile")

    min_score = st.slider("Minimum Score", 0, 100, 50, 5)

    targets = playlist_repo.list_all(min_score=min_score)

    if not targets:
        st.info("No targets match the filter. Try lowering the minimum score or import some playlists first.")
    else:
        st.write(f"Showing **{len(targets)}** targets ≥ {min_score}")

        for t in targets:
            score = t.current_score.total_value_score if t.current_score else 0
            cols = st.columns([3, 1, 1, 2])

            with cols[0]:
                st.markdown(f"**{t.name}**")
                if t.discovery_query:
                    st.caption(f"From Playlister search: *{t.discovery_query}*")
                st.caption(str(t.url))

            with cols[1]:
                st.metric("Score", f"{score:.0f}")

            with cols[2]:
                st.metric("Followers", f"{t.follower_count:,}" if t.follower_count else "—")

            with cols[3]:
                if st.button("Use for Pitch", key=f"use_{t.id}"):
                    st.session_state.selected_target = t
                    st.switch_page("Generate Pitch")  # This won't work in older streamlit, so we use a flag instead

            st.divider()

elif mode == "Generate Pitch":
    st.header("Generate Personalized Pitch")

    if not llm:
        st.error("XAI_API_KEY not found. Add it to your .env to generate pitches with Grok.")
        st.stop()

    # Style selection
    style = latest_style
    if not style:
        st.warning("No Style Profile found. Please go to 'Manage Style' first.")
        st.stop()

    st.subheader("1. Select Target Playlist")
    targets = playlist_repo.list_all(min_score=40)

    if not targets:
        st.info("No targets available. Import some first using the CLI (`dkplaylister import`).")
        st.stop()

    target_options = {f"{t.name} (Score: {t.current_score.total_value_score:.0f})": t for t in targets}
    selected_label = st.selectbox("Target Playlist", list(target_options.keys()))
    selected_target = target_options[selected_label]

    st.subheader("2. Song Details")
    song_title = st.text_input("Song Title", value="If I Get My Say")
    lyrics = st.text_area("Lyrics", height=300, value="""[Paste your full lyrics here]""")

    format_choice = st.selectbox("Pitch Format", ["email", "instagram_dm", "submission_form"])

    if st.button("Generate Pitch with Grok", type="primary"):
        with st.spinner("Generating pitch..."):
            try:
                generated = llm.generate_pitch(
                    style_profile=style,
                    song_title=song_title,
                    lyrics=lyrics,
                    playlist=selected_target,
                    pitch_format=format_choice,
                )
                st.session_state.last_pitch = generated
                st.session_state.last_song = song_title
                st.session_state.last_target = selected_target
            except Exception as e:
                st.error(f"Failed to generate pitch: {e}")

    if "last_pitch" in st.session_state:
        st.subheader("Generated Pitch")
        edited = st.text_area("Edit as needed", value=st.session_state.last_pitch, height=400)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save Pitch (placeholder)"):
                st.success("Pitch saved locally (feature coming soon).")
        with col2:
            st.download_button(
                "Download as .txt",
                data=edited,
                file_name=f"pitch_{st.session_state.last_song.replace(' ', '_')}.txt",
            )

elif mode == "Manage Style":
    st.header("Your Style Profile")

    style = latest_style

    if style:
        st.subheader(f"Current Profile: {style.name} (ID {style.id})")
        st.text_area("Raw Prompt", value=style.raw_prompt, height=300, disabled=True)
    else:
        st.info("No Style Profile saved yet.")

    st.subheader("Load / Update Style")
    uploaded = st.file_uploader("Upload a text file with your style description", type=["txt", "md"])
    new_name = st.text_input("Profile Name", value="My Current Style")

    if st.button("Save as New Style Profile") and uploaded:
        content = uploaded.read().decode("utf-8").strip()
        if content:
            new_style = StyleProfile(raw_prompt=content, name=new_name)
            db_profile = style_repo.create(new_style)
            st.success(f"Saved new Style Profile (ID: {db_profile.id})")
            st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption("Run from CLI for full power: `dkplaylister --help`")