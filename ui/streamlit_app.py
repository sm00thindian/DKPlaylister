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

# Initialize session state
if "mode" not in st.session_state:
    st.session_state.mode = "Review Targets"
if "selected_target" not in st.session_state:
    st.session_state.selected_target = None

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
    index=["Review Targets", "Generate Pitch", "Manage Style"].index(st.session_state.get("mode", "Review Targets")),
    key="mode_selector",
)

# Keep session state in sync with the radio
st.session_state.mode = mode

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
                    st.session_state.mode = "Generate Pitch"
                    st.rerun()

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

    # Pre-select if coming from "Use for Pitch" button
    default_index = 0
    if st.session_state.selected_target:
        for i, t in enumerate(targets):
            if t.id == st.session_state.selected_target.id:
                default_index = i
                break

    selected_label = st.selectbox("Target Playlist", list(target_options.keys()), index=default_index)
    selected_target = target_options[selected_label]

    # Clear the pre-selection after use
    if st.session_state.selected_target:
        st.session_state.selected_target = None

    # Show target context
    with st.expander("Target details", expanded=False):
        st.write(f"**{selected_target.name}**")
        st.write(f"Followers: **{selected_target.follower_count:,}**" if selected_target.follower_count else "Followers: Unknown")
        if selected_target.current_score:
            st.write(f"Score vs your style: **{selected_target.current_score.total_value_score:.0f}/100**")
            st.caption(selected_target.current_score.explanation)
        if selected_target.description:
            st.write("Description:")
            st.caption(selected_target.description[:400] + "..." if len(selected_target.description) > 400 else selected_target.description)

    st.subheader("2. Song Details")

    # Simple in-session song storage
    if "songs" not in st.session_state:
        st.session_state.songs = {}

    song_title = st.text_input("Song Title", value="If I Get My Say", key="song_title_input")

    col_a, col_b = st.columns([3, 1])
    with col_a:
        lyrics = st.text_area("Lyrics", height=280, value="""[Paste your full lyrics here]""", key="lyrics_input")
    with col_b:
        st.markdown("**Quick songs**")
        if st.button("Load 'If I Get My Say'"):
            st.session_state.songs["If I Get My Say"] = lyrics  # will be updated on next rerun
            st.rerun()

        # Show previously used songs in this session
        if st.session_state.songs:
            for saved_title in list(st.session_state.songs.keys()):
                if st.button(f"Load: {saved_title}", key=f"load_{saved_title}"):
                    # This is a bit hacky without proper state management, but works for now
                    pass

    format_choice = st.selectbox("Pitch Format", ["email", "instagram_dm", "submission_form"], key="format_select")

    col1, col2 = st.columns([1, 1])
    with col1:
        generate_clicked = st.button("Generate Pitch with Grok", type="primary", use_container_width=True)
    with col2:
        if "last_pitch" in st.session_state:
            if st.button("Regenerate (same inputs)", use_container_width=True):
                generate_clicked = True

    if generate_clicked:
        with st.spinner("Generating pitch with Grok..."):
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
                st.session_state.last_format = format_choice
                # Save song for quick reload in this session
                st.session_state.songs[song_title] = lyrics
            except Exception as e:
                st.error(f"Failed to generate pitch: {e}")

    if "last_pitch" in st.session_state:
        st.subheader(f"Generated Pitch — {st.session_state.last_song}")

        # Show which target/style was used
        st.caption(f"Target: **{st.session_state.last_target.name}** | Style: **{style.name}** | Format: **{st.session_state.get('last_format', format_choice)}**")

        edited = st.text_area("Edit as needed", value=st.session_state.last_pitch, height=420, key="edited_pitch")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Save Pitch to File", use_container_width=True):
                pitches_dir = Path("pitches")
                pitches_dir.mkdir(exist_ok=True)
                filename = f"{st.session_state.last_song.replace(' ', '_')}_{st.session_state.last_target.name[:30].replace(' ', '_')}.txt"
                filepath = pitches_dir / filename
                filepath.write_text(edited)
                st.success(f"Saved to {filepath}")

        with col2:
            st.download_button(
                "Download",
                data=edited,
                file_name=f"pitch_{st.session_state.last_song.replace(' ', '_')}.txt",
                use_container_width=True,
            )

        with col3:
            if st.button("Copy to Clipboard (manual)", use_container_width=True):
                st.info("Select the text above and copy (Cmd/Ctrl+C)")

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