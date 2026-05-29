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

from dkplaylister.storage import (
    PlaylistRepository, 
    StyleProfileRepository,
    BandRepository,
    SongRepository,
    AlbumRepository,
)
from dkplaylister.llm import get_provider
from dkplaylister.scoring import PlaylistScorer
from dkplaylister.models import StyleProfile, Band, Song

load_dotenv()

st.set_page_config(
    page_title="DKPlaylister",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state
if "desired_mode" not in st.session_state:
    st.session_state.desired_mode = "Review Targets"
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
band_repo = BandRepository()
song_repo = SongRepository()
album_repo = AlbumRepository()
llm = get_llm()

# Initialize band selection
if "current_band_id" not in st.session_state:
    default_band = band_repo.get_default()
    st.session_state.current_band_id = default_band.id if default_band else None

# --- Sidebar ---

st.sidebar.title("DKPlaylister")
st.sidebar.markdown("Local tool for high-signal playlist pitching")

# --- Band Selection ---
bands = band_repo.list_all()

if not bands:
    st.sidebar.warning("No bands yet. Create one below to get started.")
    with st.sidebar.form("create_first_band"):
        new_name = st.text_input("Band Name")
        new_slug = st.text_input("Slug (folder name)", value="")
        if st.form_submit_button("Create Band"):
            if new_name:
                slug = new_slug or new_name.lower().replace(" ", "-")
                try:
                    new_band = Band(name=new_name, slug=slug)
                    created = band_repo.create(new_band)
                    st.session_state.current_band_id = created.id
                    st.success(f"Band '{new_name}' created!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating band: {e}")
else:
    band_options = {f"{b.name} ({b.slug})": b.id for b in bands}
    current_band_id = st.session_state.current_band_id

    current_label = None
    for label, bid in band_options.items():
        if bid == current_band_id:
            current_label = label
            break

    if current_label is None:
        current_label = list(band_options.keys())[0]
        st.session_state.current_band_id = band_options[current_label]

    selected_label = st.sidebar.selectbox(
        "Current Band",
        list(band_options.keys()),
        index=list(band_options.keys()).index(current_label),
    )
    st.session_state.current_band_id = band_options[selected_label]

    # Quick "Create New Band" expander in sidebar
    with st.sidebar.expander("➕ Create New Band"):
        with st.form("create_band_sidebar"):
            new_name = st.text_input("Band Name")
            new_slug = st.text_input("Slug (for folders)", value="")
            submitted = st.form_submit_button("Create")
            if submitted and new_name:
                slug = new_slug or new_name.lower().replace(" ", "-")
                try:
                    new_band = Band(name=new_name, slug=slug)
                    created = band_repo.create(new_band)
                    st.session_state.current_band_id = created.id
                    st.success(f"Created band: {new_name}")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

current_band_id = st.session_state.current_band_id

st.sidebar.divider()

# --- Mode handling ---
if "desired_mode" not in st.session_state:
    st.session_state.desired_mode = "Review Targets"

mode_options = ["Review Targets", "Generate Pitch", "Manage Catalog"]
current_index = mode_options.index(st.session_state.desired_mode)

mode = st.sidebar.radio(
    "Mode",
    mode_options,
    index=current_index,
    key="mode_widget",
)

# Keep desired_mode in sync when user manually changes the radio
st.session_state.desired_mode = mode

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
                    st.toast("Target selected! Switch to 'Generate Pitch' mode in the sidebar to continue.", icon="🎯")

            st.divider()

elif mode == "Generate Pitch":
    st.header("Generate Personalized Pitch")

    if not current_band_id:
        st.warning("Please select a band first.")
        st.stop()

    if not llm:
        st.error("XAI_API_KEY not found. Add it to your .env to generate pitches with Grok.")
        st.stop()

    # Get styles and songs for the current band
    styles = style_repo.list_all(band_id=current_band_id)
    songs = song_repo.list_by_band(current_band_id)

    if not styles:
        st.warning("No styles for this band. Go to 'Manage Style' to create one.")
        st.stop()

    if not songs:
        st.info("No songs yet for this band. You can still paste lyrics manually.")

    # Style selection
    style_options = {f"{s.name} (ID {s.id})": s for s in styles}
    selected_style_label = st.selectbox("Style Profile", list(style_options.keys()))
    style = style_options[selected_style_label]

    # Song selection (optional)
    st.subheader("1. Song (optional)")
    use_saved_song = st.checkbox("Use a saved song", value=bool(songs))

    song_title = ""
    lyrics = ""

    if use_saved_song and songs:
        song_options = {f"{s.title} (ID {s.id})": s for s in songs}
        selected_song_label = st.selectbox("Saved Song", list(song_options.keys()))
        selected_song = song_options[selected_song_label]
        song_title = selected_song.title
        lyrics = selected_song.lyrics
    else:
        song_title = st.text_input("Song Title", value="If I Get My Say")
        lyrics = st.text_area("Lyrics", height=280, value="""[Paste your full lyrics here]""")

    # Target selection
    st.subheader("2. Target Playlist")
    targets = playlist_repo.list_all(min_score=40)

    if not targets:
        st.info("No targets available. Import some first using the CLI.")
        st.stop()

    target_options = {f"{t.name} (Score: {t.current_score.total_value_score:.0f})": t for t in targets}

    # Pre-select target if user clicked "Use for Pitch"
    default_target_index = 0
    if st.session_state.selected_target:
        for i, t in enumerate(targets):
            if t.id == st.session_state.selected_target.id:
                default_target_index = i
                break

    selected_target_label = st.selectbox("Target Playlist", list(target_options.keys()), index=default_target_index)
    selected_target = target_options[selected_target_label]

    # Clear pre-selection
    if st.session_state.selected_target:
        st.session_state.selected_target = None

    # Show target context
    with st.expander("Target details", expanded=False):
        st.write(f"**{selected_target.name}**")
        st.write(f"Followers: **{selected_target.follower_count:,}**" if selected_target.follower_count else "Followers: Unknown")
        if selected_target.current_score:
            st.write(f"Score vs your style: **{selected_target.current_score.total_value_score:.0f}/100**")
            st.caption(selected_target.current_score.explanation)

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
                st.session_state.last_style = style
            except Exception as e:
                st.error(f"Failed to generate pitch: {e}")

    if "last_pitch" in st.session_state:
        st.subheader(f"Generated Pitch — {st.session_state.last_song}")

        st.caption(f"Band: **{current_band_id}** | Style: **{st.session_state.last_style.name}** | Target: **{st.session_state.last_target.name}**")

        edited = st.text_area("Edit as needed", value=st.session_state.last_pitch, height=420, key="edited_pitch")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save Pitch to File", use_container_width=True):
                pitches_dir = Path("pitches")
                pitches_dir.mkdir(exist_ok=True)
                filename = f"{st.session_state.last_song.replace(' ', '_')}.txt"
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

elif mode == "Manage Catalog":
    st.header("Band Catalog Management")

    if not current_band_id:
        st.warning("Please select or create a band in the sidebar first.")
        st.stop()

    current_band = band_repo.get_by_id(current_band_id)
    st.subheader(f"Managing: {current_band.name}")

    tab1, tab2, tab3, tab4 = st.tabs(["Styles", "Albums", "Songs", "Bands"])

    # --- Styles Tab ---
    with tab1:
        st.subheader("Styles")
        styles = style_repo.list_all(band_id=current_band_id)

        if styles:
            for s in styles:
                with st.expander(f"{s.name} (ID {s.id})"):
                    st.text_area("Raw Prompt", value=s.raw_prompt, height=180, disabled=True, key=f"cat_style_{s.id}")
        else:
            st.info("No styles yet for this band.")

        st.markdown("**Add New Style**")
        with st.form("add_style_form"):
            new_style_name = st.text_input("Style Name")
            new_style_prompt = st.text_area("Full Style Description (raw prompt)", height=200)
            submitted = st.form_submit_button("Save Style")
            if submitted and new_style_name and new_style_prompt:
                new_style = StyleProfile(
                    band_id=current_band_id,
                    name=new_style_name,
                    raw_prompt=new_style_prompt
                )
                db_s = style_repo.create(new_style)
                st.success(f"Style '{new_style_name}' created (ID {db_s.id})")
                st.rerun()

    # --- Albums Tab ---
    with tab2:
        st.subheader("Albums / Releases")
        albums = album_repo.list_by_band(current_band_id)

        if albums:
            for a in albums:
                with st.expander(f"{a.title} ({a.release_date or 'No date'}) - ID {a.id}"):
                    st.write(f"**Notes:** {a.notes or '—'}")
        else:
            st.info("No albums yet.")

        st.markdown("**Add New Album**")
        with st.form("add_album_form"):
            album_title = st.text_input("Album Title")
            album_date = st.text_input("Release Date (YYYY-MM-DD)", placeholder="2025-06-01")
            album_notes = st.text_area("Notes")
            submitted = st.form_submit_button("Save Album")
            if submitted and album_title:
                new_album = Album(
                    band_id=current_band_id,
                    title=album_title,
                    release_date=album_date or None,
                    notes=album_notes or None
                )
                db_a = album_repo.create(new_album)
                st.success(f"Album created (ID {db_a.id})")
                st.rerun()

    # --- Songs Tab ---
    with tab3:
        st.subheader("Songs / Lyrics")
        songs = song_repo.list_by_band(current_band_id)

        if songs:
            for s in songs:
                with st.expander(f"{s.title} (ID {s.id})"):
                    st.text_area("Lyrics", value=s.lyrics, height=200, disabled=True, key=f"cat_song_{s.id}")
                    st.write(f"**Notes:** {s.notes or '—'}")
                    if s.album_id:
                        st.caption(f"Album ID: {s.album_id}")
        else:
            st.info("No songs yet for this band.")

        st.markdown("**Add New Song**")
        with st.form("add_song_form"):
            song_title = st.text_input("Song Title")
            song_lyrics = st.text_area("Lyrics", height=250)
            song_notes = st.text_area("Notes")
            submitted = st.form_submit_button("Save Song")
            if submitted and song_title and song_lyrics:
                new_song = Song(
                    band_id=current_band_id,
                    title=song_title,
                    lyrics=song_lyrics,
                    notes=song_notes or None
                )
                db_s = song_repo.create(new_song)
                st.success(f"Song '{song_title}' added (ID {db_s.id})")
                st.rerun()

    # --- Bands Tab (global) ---
    with tab4:
        st.subheader("All Bands")
        all_bands = band_repo.list_all()

        for b in all_bands:
            with st.expander(f"{b.name} ({b.slug}) - ID {b.id}"):
                st.write(f"**Notes:** {b.notes or '—'}")
                if st.button("Set as Current Band", key=f"set_band_{b.id}"):
                    st.session_state.current_band_id = b.id
                    st.rerun()

        st.markdown("**Create New Band**")
        with st.form("create_band_form"):
            new_band_name = st.text_input("Band Name")
            new_band_slug = st.text_input("Slug (for folders)", value="")
            new_band_notes = st.text_area("Notes")
            submitted = st.form_submit_button("Create Band")
            if submitted and new_band_name:
                slug = new_band_slug or new_band_name.lower().replace(" ", "-")
                new_band = Band(name=new_band_name, slug=slug, notes=new_band_notes or None)
                db_b = band_repo.create(new_band)
                st.success(f"Band created (ID {db_b.id})")
                st.session_state.current_band_id = db_b.id
                st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption("Run from CLI for full power: `dkplaylister --help`")