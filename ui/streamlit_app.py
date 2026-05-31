"""
DKPlaylister - Local Web UI (Streamlit)

This provides a friendlier interface for the core workflow:
- Manage Style Profile
- Review imported/scored targets from Playlister
- Process saved Playlister HTML/CSV results
- Generate and edit pitches using Grok

Run with:
    streamlit run ui/streamlit_app.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv
import pandas as pd

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
from dkplaylister.models import (
    StyleProfile, Band, Song, Album, Curator, PlaylistSource, Platform, 
    Pitch, PitchFormat
)
from dkplaylister.spotify import fetch_playlist
from dkplaylister.discovery import run_discovery_mining
from dkplaylister.storage import PlaylistRepository


def build_curator_from_tracker_row(row: dict) -> Curator:
    """Helper to construct a Curator object from a Playlister tracker row."""
    curator = Curator()
    contact_type = str(row.get("Contact Type", "") or "").lower()
    contact_detail = str(row.get("Contact Detail", "") or "").strip()

    if not contact_detail:
        return curator

    if "ig" in contact_type or contact_detail.startswith("@"):
        curator.instagram = contact_detail.lstrip("@")
    elif "@" in contact_detail and "." in contact_detail:
        curator.email = contact_detail
    else:
        curator.notes = f"{row.get('Contact Type', 'Contact')}: {contact_detail}"

    return curator


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

mode_options = ["Review Targets", "Discover Targets", "Generate Pitch", "Manage Catalog", "Process Playlister Imports"]
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

latest_style = style_repo.get_latest(band_id=current_band_id) if current_band_id else style_repo.get_latest()
if latest_style:
    st.sidebar.success(f"Style Profile: **{latest_style.name}** (ID {latest_style.id})")
else:
    st.sidebar.warning("No Style Profile loaded yet.")

# --- Main Content ---

if mode == "Review Targets":
    st.header("Your Scored Targets")
    st.caption("Imported from Playlister + enriched + scored against your Style Profile")

    # --- Option 2: Quick "Add Target" form directly in the UI (great for Playlister popup data) ---
    with st.expander("➕ Add New Target (with Playlister contact details)", expanded=False):

        if "target_form_counter" not in st.session_state:
            st.session_state.target_form_counter = 0

        target_form_key = f"add_target_form_{st.session_state.target_form_counter}"

        with st.form(target_form_key):
            new_url = st.text_input("Spotify Playlist URL", placeholder="https://open.spotify.com/playlist/...")
            col_a, col_b = st.columns(2)
            with col_a:
                new_source = st.selectbox("Source", ["playlister", "spotify", "manual"], index=0)
                new_query = st.text_input("Discovery Query (e.g. 'Indie Cinematic')")
            with col_b:
                new_name = st.text_input("Override Name (optional)")

            st.markdown("**Contact info from Playlister popup (highly recommended)**")
            c1, c2, c3 = st.columns(3)
            with c1:
                new_email = st.text_input("Curator Email")
            with c2:
                new_ig = st.text_input("Instagram @handle")
            with c3:
                new_web = st.text_input("bit.ly / form / website")

            new_notes = st.text_area("Contact notes", height=60)
            submitted = st.form_submit_button("Add / Update Target", type="primary")

            if submitted and new_url:
                try:
                    from dkplaylister.spotify import fetch_playlist
                    from dkplaylister.models import Curator, PlaylistSource
                    p = fetch_playlist(new_url)
                    if p:
                        if new_name:
                            p.name = new_name
                        p.source = PlaylistSource(new_source)
                        p.discovery_query = new_query or None

                        if any([new_email, new_ig, new_web, new_notes]):
                            c = p.curator or Curator()
                            if new_email: c.email = new_email
                            if new_ig: c.instagram = new_ig
                            if new_web: c.website = new_web
                            if new_notes: c.notes = new_notes
                            p.curator = c
                            p.contact_revealed_via = "playlister_popup" if new_source == "playlister" else "manual"

                        # Auto-score if we have a style (respect current band)
                        style = style_repo.get_latest(band_id=current_band_id) if current_band_id else style_repo.get_latest()
                        if style:
                            try:
                                scorer = PlaylistScorer(style)
                                scorer.score(p)
                            except Exception:
                                pass

                        playlist_repo.create_or_update(p)
                        st.success(f"Added: {p.name}")
                        st.session_state.target_form_counter += 1
                        st.rerun()
                    else:
                        st.error("Could not fetch playlist from Spotify. Check the URL.")
                except Exception as e:
                    st.error(f"Error adding target: {e}")

    st.divider()

    # --- Main list ---
    min_score = st.slider("Minimum Score", 0, 100, 50, 5)

    targets = playlist_repo.list_all(min_score=min_score)

    if not targets:
        st.info("No targets match the filter. Try lowering the minimum score or import some playlists first.")
    else:
        st.write(f"Showing **{len(targets)}** targets ≥ {min_score}")

        for t in targets:
            score = t.current_score.total_value_score if t.current_score else 0

            # Contact status badge
            if t.has_contact_info:
                if t.curator and t.curator.email:
                    contact_badge = "🟢 Has email"
                elif t.contact_revealed_via == "playlister_popup":
                    contact_badge = "🔵 Playlister popup"
                elif t.curator and (t.curator.instagram or t.curator.website):
                    contact_badge = "🟡 IG / web only"
                else:
                    contact_badge = "🟢 Contact signal"
            else:
                contact_badge = "🔴 No contact info"

            # Header row
            cols = st.columns([3.5, 0.9, 0.9, 1.2, 1.5])
            with cols[0]:
                st.markdown(f"**{t.name}**")
                if t.discovery_query:
                    st.caption(f"From Playlister: *{t.discovery_query}*")
                st.caption(str(t.url))

            with cols[1]:
                st.metric("Score", f"{score:.0f}")

            with cols[2]:
                st.metric("Followers", f"{t.follower_count:,}" if t.follower_count else "—")

            with cols[3]:
                st.markdown(f"**Contact**  \n{contact_badge}")

            with cols[4]:
                if st.button("Use for Pitch", key=f"use_{t.id}"):
                    st.session_state.selected_target = t
                    st.toast("Target selected! Switch to 'Generate Pitch' mode in the sidebar.", icon="🎯")

            # Expanded contact details (Option 1 visibility)
            if t.curator or t.contact_revealed_via or t.description:
                with st.expander("Curator & Contact Details", expanded=False):
                    if t.curator:
                        c = t.curator
                        if c.name:
                            st.write(f"**Curator:** {c.name}")
                        contact_lines = []
                        if c.email:
                            contact_lines.append(f"📧 **Email:** {c.email}")
                        if c.instagram:
                            contact_lines.append(f"📷 **Instagram:** @{c.instagram}")
                        if c.website:
                            contact_lines.append(f"🔗 **Website/Profile:** {c.website}")
                        if c.notes:
                            contact_lines.append(f"📝 Notes: {c.notes}")
                        if contact_lines:
                            st.markdown("\n".join(contact_lines))
                        else:
                            st.caption("No direct contact methods captured yet.")
                    else:
                        st.caption("No curator object stored.")

                    if t.contact_revealed_via:
                        st.caption(f"Contact revealed via: **{t.contact_revealed_via}**")

                    if t.description:
                        st.caption("Playlist description (may contain more signals):")
                        st.text_area("Description", value=t.description[:400] + ("..." if len(t.description or "") > 400 else ""), height=80, disabled=True, key=f"desc_{t.id}", label_visibility="collapsed")

            # Show score explanation if present
            if t.current_score and t.current_score.explanation:
                st.caption(f"Score reason: {t.current_score.explanation}")

            st.divider()

elif mode == "Discover Targets":
    st.header("Discover New Targets (Phase 1)")

    if not current_band_id:
        st.warning("Please select a band in the sidebar first.")
        st.stop()

    if not llm:
        st.error("XAI_API_KEY required for style expansion and discovery.")
        st.stop()

    # Get style for current band
    style = style_repo.get_latest(band_id=current_band_id)
    if not style:
        st.warning("No Style Profile for this band yet. Go to Manage Catalog → Styles to create one.")
        st.stop()

    st.subheader(f"Using Style: {style.name}")

    # Quick connection status (Phase 1 robustness)
    if st.button("🔄 Check Spotify Connection", key="check_spotify_conn"):
        with st.spinner("Checking..."):
            try:
                from dkplaylister.spotify import check_spotify_connection
                status = check_spotify_connection()
                if status["ok"]:
                    st.success(status["message"])
                else:
                    st.error(status["message"])
            except Exception as e:
                st.error(f"Check failed: {e}")

    # Step 1: Expansion
    if "discovery_expansion" not in st.session_state:
        st.session_state.discovery_expansion = None
        st.session_state.discovery_queries = []

    if st.button("🔍 Expand Style for Discovery", type="primary"):
        with st.spinner("Expanding style with Grok..."):
            try:
                expansion = llm.expand_style_for_discovery(style)
                st.session_state.discovery_expansion = expansion
                st.session_state.discovery_queries = expansion.search_queries or []
                st.success("Expansion complete!")
            except Exception as e:
                st.error(f"Expansion failed: {e}")

    # Editable queries (full-featured)
    if st.session_state.discovery_queries:
        st.markdown("**Search Queries** (edit these to refine discovery)")

        # Main editable queries
        queries_text = st.text_area(
            "One query per line",
            value="\n".join(st.session_state.discovery_queries),
            height=150,
            key="discovery_queries_editor"
        )
        if st.button("Save Edited Queries"):
            st.session_state.discovery_queries = [q.strip() for q in queries_text.splitlines() if q.strip()]
            st.success("Queries updated for this session.")

    # Step 2: Run Mining
    with st.expander("What happens when you press 'Run Discovery Mining'?"):
        st.markdown("""
        **The process:**
        1. Takes your (edited) search queries
        2. For each query, searches Spotify for playlists
        3. For every playlist found:
           - Fetches full details (followers, description, etc.)
           - Scores it against your Style Profile using the same engine as the CLI
        4. Deduplicates results across queries
        5. Returns the top candidates above your minimum score

        This can take 10–60+ seconds depending on how many queries and how many results Spotify returns.
        """)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        mine_limit = st.number_input("Max candidates", 5, 100, st.session_state.get("mine_limit", 25), key="mine_limit")
    with col2:
        mine_min_score = st.number_input("Min score (0-100)", 0, 100, st.session_state.get("mine_min_score", 50), key="mine_min_score")
    with col3:
        dry_run_ui = st.checkbox("Dry run (preview only)", value=False)
    with col4:
        exclude_existing = st.checkbox("Exclude already imported", value=st.session_state.get("exclude_existing", True), key="exclude_existing", help="Skip playlists already in your database")

    # Live filters for the "candidates found so far" table (Phase 1 optimization)
    st.markdown("**Live Filters** (adjust while mining is running)")
    live_col1, live_col2 = st.columns(2)
    with live_col1:
        live_min_score = st.slider("Min Score (live)", 0, 100, 0, key="live_min_score")
    with live_col2:
        live_min_followers = st.number_input("Min Followers (live)", min_value=0, value=0, step=1000, key="live_min_followers")

    # --- Full Mining Configuration Presets (Phase 1 full-featured #4) ---
    # Fully self-contained loading (no import from discovery to avoid any name errors)
    presets = {}
    preset_names = []
    try:
        from pathlib import Path
        import json as _json
        path = Path("data/discovery_presets") / f"band_{current_band_id}.json"
        if path.exists():
            data = _json.loads(path.read_text())
            for name, value in data.items():
                if isinstance(value, list):
                    presets[name] = {"queries": value, "limit": 25, "min_score": 50, "exclude_existing": True}
                else:
                    presets[name] = value
            preset_names = list(presets.keys())
    except Exception:
        pass  # Presets are optional; don't break the page

    st.markdown("**Mining Presets** (save/load full configuration)")
    col_p1, col_p2, col_p3 = st.columns([2.5, 1.5, 1.5])
    with col_p1:
        if preset_names:
            selected_preset = st.selectbox(
                "Load preset (restores queries + settings)",
                ["(none)"] + preset_names,
                key="full_preset_select"
            )
            if selected_preset != "(none)" and st.button("Load Full Preset", key="load_full_preset"):
                try:
                    from pathlib import Path
                    import json as _json
                    path = Path("data/discovery_presets") / f"band_{current_band_id}.json"
                    if path.exists():
                        data = _json.loads(path.read_text())
                        raw = data.get(selected_preset, {})
                        if isinstance(raw, list):
                            p = {"queries": raw, "limit": 25, "min_score": 50, "exclude_existing": True}
                        else:
                            p = raw
                        st.session_state.discovery_queries = p.get("queries", [])
                        st.session_state.mine_limit = p.get("limit", 25)
                        st.session_state.mine_min_score = p.get("min_score", 50)
                        st.session_state.exclude_existing = p.get("exclude_existing", True)
                        st.rerun()
                except Exception as e:
                    st.error(f"Failed to load preset: {e}")
        else:
            st.caption("No presets saved for this band yet.")

    with col_p2:
        new_full_name = st.text_input("Preset name", placeholder="My Refined Set", key="new_full_preset", label_visibility="collapsed")
        if st.button("💾 Save Full Config", key="save_full_preset") and new_full_name:
            try:
                # Inline implementation to avoid import issues
                from pathlib import Path
                import json as _json

                PRESETS_DIR = Path("data/discovery_presets")
                PRESETS_DIR.mkdir(parents=True, exist_ok=True)
                path = PRESETS_DIR / f"band_{current_band_id}.json"

                presets = {}
                if path.exists():
                    try:
                        presets = _json.loads(path.read_text())
                    except Exception:
                        presets = {}

                presets[new_full_name] = {
                    "queries": st.session_state.get("discovery_queries", []),
                    "limit": mine_limit,
                    "min_score": mine_min_score,
                    "exclude_existing": exclude_existing
                }
                path.write_text(_json.dumps(presets, indent=2))
                st.success(f"Saved '{new_full_name}'")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save preset: {e}")

    with col_p3:
        if preset_names:
            del_name = st.selectbox("Delete", preset_names, key="del_full_preset", label_visibility="collapsed")
            if st.button("🗑 Delete Preset", key="delete_full_preset"):
                try:
                    from pathlib import Path
                    import json as _json
                    path = Path("data/discovery_presets") / f"band_{current_band_id}.json"
                    if path.exists():
                        data = _json.loads(path.read_text())
                        if del_name in data:
                            del data[del_name]
                            path.write_text(_json.dumps(data, indent=2))
                            st.success(f"Deleted '{del_name}'")
                            st.rerun()
                except Exception as e:
                    st.error(f"Failed to delete preset: {e}")

    if st.button("🚀 Run Discovery Mining", disabled=not st.session_state.discovery_queries):
        # Clear previous results when starting a new run
        if "discovery_results" in st.session_state:
            del st.session_state.discovery_results

        # === Pre-flight authentication / connection check ===
        with st.spinner("Checking Spotify connection..."):
            try:
                from dkplaylister.spotify import check_spotify_connection
                conn_status = check_spotify_connection()
            except Exception as e:
                conn_status = {"ok": False, "message": f"Could not check connection: {e}"}

        if not conn_status.get("ok"):
            st.error(f"Spotify connection issue: {conn_status.get('message')}")
            st.info(
                "Please verify your Spotify credentials in the `.env` file.\n"
                "You can also run `dkplaylister auth spotify --status` in the terminal to check user authentication."
            )
            st.stop()

        if conn_status.get("using_user_auth"):
            st.success("Using authenticated user Spotify session (better data access).")
        else:
            st.caption("Using public Spotify access (Client Credentials). Some curator data may be limited.")

        if dry_run_ui:
            st.info("Dry Run — these queries would be used:")
            for q in st.session_state.discovery_queries[:10]:
                st.write(f"• {q}")
            st.stop()

        # === Full progress monitoring UI ===
        queries_to_run = st.session_state.discovery_queries[:10]
        total_queries = len(queries_to_run)

        status = st.status("Running discovery mining...", expanded=True)
        progress_bar = st.progress(0, text="Starting...")

        status.write(f"**Queries to process:** {total_queries}")
        status.write(f"**Target limit:** {mine_limit} candidates (min score: {mine_min_score})")

        # Live results container for candidates found so far
        live_results_container = st.container()
        live_candidates = []  # Will hold (playlist, score) tuples for live display

        def mining_progress_callback(event: dict):
            """Live progress callback from the mining engine."""
            etype = event.get("type")

            if etype == "start":
                status.write(f"Starting search across **{event['total_queries']}** queries...")

            elif etype == "query_start":
                pct = int((event["index"] / max(total_queries, 1)) * 100)
                progress_bar.progress(
                    pct,
                    text=f"Processing query {event['index']+1}/{total_queries}: {event['query'][:55]}..."
                )
                status.write(f"🔎 Searching: `{event['query']}`")

            elif etype == "candidate_found":
                live_candidates.append((
                    event.get("playlist_name"),
                    event.get("score"),
                    event.get("followers"),
                    event.get("query"),
                    "Yes" if event.get("already_imported") else "No"
                ))

                # Live update the preview table — fast and clean during mining
                with live_results_container:
                    st.markdown("**Candidates found so far** (updates live as they are discovered)")

                    if live_candidates:
                        # Apply live filters from the sliders above
                        filtered_live = [
                            (name, score, followers, q)
                            for name, score, followers, q in live_candidates
                            if score >= st.session_state.get("live_min_score", 0)
                            and followers >= st.session_state.get("live_min_followers", 0)
                        ]

                        if filtered_live:
                            live_df = pd.DataFrame(
                                filtered_live[-20:],
                                columns=["Name", "Score", "Followers", "From Query", "Already Imported"]
                            )
                            st.dataframe(
                                live_df,
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "Score": st.column_config.NumberColumn(format="%.1f"),
                                    "Followers": st.column_config.NumberColumn(format="%d"),
                                    "Already Imported": st.column_config.TextColumn(
                                        help="Already in your database"
                                    ),
                                }
                            )
                            st.caption(f"Showing {len(filtered_live)} matching candidates (last 20). Full selection & bulk import after mining completes.")
                        else:
                            st.caption("No candidates match the current live filters yet.")

            elif etype == "query_complete":
                new = event.get("new_candidates", 0)
                total = event.get("total_candidates", 0)
                status.write(f"   → Found **{new}** new candidates (total so far: {total})")

            elif etype == "query_error":
                # We should rarely reach here now because 403s are silenced upstream,
                # but keep this as a final safety net.
                error_msg = event.get('error', '')
                if "403" not in error_msg:
                    status.write(f"   ⚠️ {error_msg}")

        try:
            result = run_discovery_mining(
                style=style,
                queries=queries_to_run,
                limit=mine_limit,
                min_score=mine_min_score,
                llm_provider=llm,
                progress_callback=mining_progress_callback,
                exclude_existing=exclude_existing,
            )

            st.session_state.discovery_results = result
            progress_bar.progress(100, text="Complete!")

            status.update(label="✅ Discovery mining complete", state="complete")
            status.write(f"**Final results:** {len(result['candidates'])} candidates found")

            # Clear the live preview container now that we're done
            live_results_container.empty()

            # Auto-record one MiningRun for the whole session (much better UX)
            try:
                from dkplaylister.storage import MiningRunRepository
                from dkplaylister.models import MiningRun, OperatingMode

                top_score = max(
                    (getattr(getattr(pl, "current_score", None), "total_value_score", 0) 
                     for pl in result["candidates"]), 
                    default=0
                )

                run = MiningRun(
                    band_id=current_band_id,
                    style_profile_id=style.id,
                    style_profile_name=style.name,
                    operating_mode=OperatingMode.INTERACTIVE,
                    queries_used=result["queries_used"],
                    playlists_found=len(result["candidates"]),
                    playlists_imported=0,   # User still decides which to import
                    top_score=top_score,
                    notes="Full mining run from Discover Targets UI",
                )
                MiningRunRepository().create(run)
                status.write(f"_Mining session recorded (ID will be visible in history)._")
            except Exception as e:
                status.warning(f"Could not auto-record mining run: {e}")

            # Show per-query breakdown
            if result.get("query_stats"):
                with status.expander("Per-query breakdown"):
                    for q, count in result["query_stats"].items():
                        st.write(f"- `{q}` → **{count}** candidates")

        except Exception as e:
            progress_bar.progress(100, text="Failed")
            status.update(label="❌ Mining failed", state="error")
            status.error(f"Error: {e}")

    # Results
    if st.session_state.get("discovery_results"):
        result = st.session_state.discovery_results
        st.subheader(f"Results ({len(result['candidates'])} candidates)")

        if result.get("query_stats"):
            st.caption(f"Per-query hits: {result['query_stats']}")

        # Nicer results table
        display_data = []
        for i, pl in enumerate(result["candidates"][:25]):
            score = getattr(getattr(pl, "current_score", None), "total_value_score", 0)
            already_imported = getattr(pl, "_already_imported", False)
            display_data.append({
                "Score": round(score, 1),
                "Name": pl.name,
                "Followers": pl.follower_count or 0,
                "Description": (pl.description or "")[:180] + ("..." if pl.description and len(pl.description) > 180 else ""),
                "URL": str(pl.url),
                "Already Imported": "Yes" if already_imported else "No",
                "row_index": i
            })

        if display_data:
            # Use data_editor with selection for bulk import (much better UX)
            df = pd.DataFrame(display_data)

            # Add a selection column
            df.insert(0, "Select", False)

            # Show row_index for lookup but hide it from display
            edited_df = st.data_editor(
                df[["Select", "Score", "Name", "Followers", "Description", "Already Imported", "row_index"]],
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                column_config={
                    "Select": st.column_config.CheckboxColumn(required=True),
                    "Score": st.column_config.NumberColumn(format="%.1f"),
                    "Followers": st.column_config.NumberColumn(format="%d"),
                    "Already Imported": st.column_config.TextColumn(
                        help="Already in your database"
                    ),
                    "row_index": st.column_config.Column(disabled=True, label="", width="small"),
                },
                key="discover_results_editor"
            )

            selected_rows = edited_df[edited_df["Select"] == True]

            if not selected_rows.empty:
                st.markdown(f"**{len(selected_rows)} candidates selected**")

                if st.button(f"Import {len(selected_rows)} Selected", type="primary"):
                    imported_count = 0
                    for _, row in selected_rows.iterrows():
                        try:
                            idx = int(row["row_index"])
                            pl = result["candidates"][idx]
                            playlist_repo.create_or_update(pl)
                            # Live update the flag so the table reflects it immediately after rerun
                            setattr(pl, "_already_imported", True)
                            imported_count += 1
                        except Exception as e:
                            st.error(f"Failed to import one: {e}")

                    # Update the latest MiningRun for this band with the imported count
                    try:
                        from dkplaylister.storage import MiningRunRepository
                        from dkplaylister.models import MiningRun

                        runs = MiningRunRepository().list_by_band(current_band_id, limit=1)
                        if runs:
                            latest_run = runs[0]
                            # Create an updated record (simple approach)
                            updated_run = MiningRun(
                                band_id=latest_run.band_id,
                                style_profile_id=latest_run.style_profile_id,
                                style_profile_name=latest_run.style_profile_name,
                                queries_used=latest_run.queries_used,
                                playlists_found=latest_run.playlists_found,
                                playlists_imported=latest_run.playlists_imported + imported_count,
                                top_score=latest_run.top_score,
                                notes=latest_run.notes + f" | Bulk imported {imported_count}",
                            )
                            MiningRunRepository().create(updated_run)

                    except Exception:
                        pass

                    st.success(f"Successfully imported {imported_count} candidates! The table will now show them as 'Already Imported'.")
                    # Refresh results — the objects have been updated with the flag, so the table reflects it immediately
                    st.rerun()

                # Bulk "Import All Above Threshold" (very useful full-featured action)
                if st.button(f"Import All Above {mine_min_score}", key="import_above_threshold"):
                    imported_count = 0
                    for i, pl in enumerate(result["candidates"]):
                        score = getattr(getattr(pl, "current_score", None), "total_value_score", 0)
                        if score >= mine_min_score:
                            try:
                                playlist_repo.create_or_update(pl)
                                # Live update the flag for immediate visual feedback
                                setattr(pl, "_already_imported", True)
                                imported_count += 1
                            except Exception:
                                pass

                    if imported_count > 0:
                        # Update MiningRun
                        try:
                            from dkplaylister.storage import MiningRunRepository
                            from dkplaylister.models import MiningRun

                            runs = MiningRunRepository().list_by_band(current_band_id, limit=1)
                            if runs:
                                latest_run = runs[0]
                                updated_run = MiningRun(
                                    band_id=latest_run.band_id,
                                    style_profile_id=latest_run.style_profile_id,
                                    style_profile_name=latest_run.style_profile_name,
                                    queries_used=latest_run.queries_used,
                                    playlists_found=latest_run.playlists_found,
                                    playlists_imported=latest_run.playlists_imported + imported_count,
                                    top_score=latest_run.top_score,
                                    notes=latest_run.notes + f" | Bulk imported {imported_count} above {mine_min_score}",
                                )
                                MiningRunRepository().create(updated_run)
                        except Exception:
                            pass

                        st.success(f"Imported {imported_count} candidates above score {mine_min_score}! They now show as 'Already Imported'.")
                        st.rerun()
                    else:
                        st.info(f"No candidates currently above score {mine_min_score}.")

        else:
            st.info("No candidates met your filters.")

        # Quick Mining History for this band (Phase 1 UX improvement)
        with st.expander("Recent mining runs for this band"):
            try:
                from dkplaylister.storage import MiningRunRepository
                recent_runs = MiningRunRepository().list_by_band(current_band_id, limit=5)
                if recent_runs:
                    for r in recent_runs:
                        st.write(f"- **{r.started_at.strftime('%Y-%m-%d %H:%M')}** — {r.playlists_found} found, top score {r.top_score or 0:.0f}")
                else:
                    st.caption("No previous mining runs for this band yet.")
            except Exception:
                st.caption("Could not load recent mining history.")

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

    # Style selection
    style_options = {f"{s.name} (ID {s.id})": s for s in styles}
    selected_style_label = st.selectbox("Style Profile", list(style_options.keys()))
    style = style_options[selected_style_label]

    # Target selection (moved earlier so song selection can be conditional)
    st.subheader("1. Target Playlist")

    target_source = st.radio(
        "Target source",
        ["From Database (previously imported)", "From Playlister Tracker Spreadsheet"],
        horizontal=True,
        key="target_source"
    )

    selected_target = None
    tracker_row = None
    tracker_file_path = None
    multi_song_mode = False
    selected_songs_for_pitch = []

    if target_source == "From Database (previously imported)":
        targets = playlist_repo.list_all(min_score=40)

        if not targets:
            st.info("No targets available in database. Import some first or use a Playlister tracker below.")
            st.stop()

        target_options = {f"{t.name} (Score: {t.current_score.total_value_score:.0f})": t for t in targets}

        default_target_index = 0
        if st.session_state.selected_target:
            for i, t in enumerate(targets):
                if t.id == st.session_state.selected_target.id:
                    default_target_index = i
                    break

        selected_target_label = st.selectbox("Target Playlist", list(target_options.keys()), index=default_target_index)
        selected_target = target_options[selected_target_label]

        if st.session_state.selected_target:
            st.session_state.selected_target = None

        with st.expander("Target details", expanded=False):
            st.write(f"**{selected_target.name}**")
            st.write(f"Followers: **{selected_target.follower_count:,}**" if selected_target.follower_count else "Followers: Unknown")
            if selected_target.current_score:
                st.write(f"Score vs your style: **{selected_target.current_score.total_value_score:.0f}/100**")
                st.caption(selected_target.current_score.explanation)

        # Song selection for DB targets (single song, existing behavior)
        st.subheader("2. Song (optional)")
        use_saved_song = st.checkbox("Use a saved song", value=bool(songs))

        song_title = ""
        lyrics = ""
        selected_song_streaming_links = None

        if use_saved_song and songs:
            song_options = {f"{s.title} (ID {s.id})": s for s in songs}
            selected_song_label = st.selectbox("Saved Song", list(song_options.keys()))
            selected_song = song_options[selected_song_label]
            song_title = selected_song.title
            lyrics = selected_song.lyrics
            selected_song_streaming_links = selected_song.streaming_links or {}
        else:
            song_title = st.text_input("Song Title", value="If I Get My Say")
            lyrics = st.text_area("Lyrics", height=280, value="""[Paste your full lyrics here]""")

    else:
        # From Playlister Tracker Spreadsheet
        imports_dir = Path("data/playlister_imports")
        csv_files = sorted(imports_dir.glob("*.csv"))

        if not csv_files:
            st.warning("No Playlister tracker CSVs found.")
            st.stop()

        file_options = {f.name: f for f in csv_files}
        selected_tracker_name = st.selectbox("Tracker file", list(file_options.keys()), key="tracker_for_pitch")
        tracker_path = file_options[selected_tracker_name]

        tracker_df = pd.read_csv(tracker_path)

        # Only show rows that have both a Spotify URL and Contact Detail
        ready_df = tracker_df[
            (tracker_df["Spotify URL"].fillna("").astype(str).str.len() > 10) &
            (tracker_df["Contact Detail"].fillna("").astype(str).str.len() > 2)
        ].copy()

        if ready_df.empty:
            st.info("No rows with both a Spotify URL and Contact Detail in this tracker yet.")
            st.stop()

        # Build nice labels
        def make_label(row):
            contact = ""
            if pd.notna(row.get("Contact Type")) and pd.notna(row.get("Contact Detail")):
                contact = f" — {row['Contact Type']}: {row['Contact Detail']}"
            return f"{row['Title']} ({int(row['Subscribers']):,} subs){contact}"

        ready_df["label"] = ready_df.apply(make_label, axis=1)
        label_to_row = {label: row for label, row in zip(ready_df["label"], ready_df.to_dict("records"))}

        selected_label = st.selectbox("Target from tracker", list(ready_df["label"]), key="tracker_target_select")
        tracker_row = label_to_row[selected_label]
        tracker_file_path = tracker_path

        # Fetch live + attach curator from the row
        with st.spinner("Fetching playlist..."):
            selected_target = fetch_playlist(tracker_row["Spotify URL"])

        if not selected_target:
            st.error("Could not fetch this playlist from Spotify.")
            st.stop()

        # Attach curator from tracker data
        selected_target.curator = build_curator_from_tracker_row(tracker_row)
        selected_target.contact_revealed_via = "playlister_popup"

        with st.expander("Target details", expanded=False):
            st.write(f"**{selected_target.name}**")
            st.write(f"Followers: **{selected_target.follower_count:,}**" if selected_target.follower_count else "Followers: Unknown")
            if selected_target.curator:
                c = selected_target.curator
                if c.instagram:
                    st.write(f"Instagram: **@{c.instagram}**")
                if c.email:
                    st.write(f"Email: **{c.email}**")
                if c.notes:
                    st.write(f"Contact notes: {c.notes}")

        # Multi-song support specifically for tracker targets
        st.subheader("Songs to pitch to this curator")

        if songs:
            song_options = {f"{s.title} (ID {s.id})": s for s in songs}
            selected_song_labels = st.multiselect(
                "Select songs (you can pitch multiple to the same curator)",
                list(song_options.keys()),
                default=[list(song_options.keys())[0]] if song_options else []
            )
            selected_songs_for_pitch = [song_options[label] for label in selected_song_labels]
        else:
            st.info("No saved songs yet. Paste lyrics manually below for a single song.")
            selected_songs_for_pitch = []

        # === Multi-song support for tracker targets ===
        st.subheader("2. Songs to pitch to this curator")

        if not songs:
            st.info("No saved songs for this band yet. You can still paste lyrics manually below.")
            song_title = st.text_input("Song Title", value="If I Get My Say")
            lyrics = st.text_area("Lyrics", height=280, value="""[Paste your full lyrics here]""")
            selected_song_streaming_links = None
        else:
            multi_song = st.checkbox("Pitch multiple songs to this curator (recommended)", value=True)

            song_options = {f"{s.title} (ID {s.id})": s for s in songs}

            if multi_song:
                selected_song_labels = st.multiselect(
                    "Select songs to pitch",
                    list(song_options.keys()),
                    default=list(song_options.keys())[:2] if len(song_options) >= 2 else list(song_options.keys())
                )
                selected_songs_for_pitch = [song_options[label] for label in selected_song_labels]
            else:
                selected_song_label = st.selectbox("Song", list(song_options.keys()))
                selected_songs_for_pitch = [song_options[selected_song_label]]

            # For single-song compatibility with existing generation flow
            if len(selected_songs_for_pitch) == 1:
                song_title = selected_songs_for_pitch[0].title
                lyrics = selected_songs_for_pitch[0].lyrics
                selected_song_streaming_links = selected_songs_for_pitch[0].streaming_links or {}
            else:
                # Will be handled in generation loop
                song_title = ""
                lyrics = ""
                selected_song_streaming_links = None

    format_choice = st.selectbox("Pitch Format", ["email", "instagram_dm", "submission_form"])

    # Get artist name for better personalization
    artist_name = None
    try:
        if current_band_id:
            band = band_repo.get_by_id(current_band_id)
            if band:
                artist_name = band.name
    except Exception:
        pass

    if st.button("Generate Pitch with Grok", type="primary"):
        with st.spinner("Generating pitch(es)..."):
            try:
                pitches = []

                if target_source == "From Playlister Tracker Spreadsheet" and 'selected_songs_for_pitch' in locals() and len(selected_songs_for_pitch) > 0:
                    # Multi-song generation for tracker targets
                    for song in selected_songs_for_pitch:
                        gen = llm.generate_pitch(
                            style_profile=style,
                            song_title=song.title,
                            lyrics=song.lyrics,
                            playlist=selected_target,
                            curator=selected_target.curator if selected_target else None,
                            pitch_format=format_choice,
                            artist_name=artist_name,
                            song_streaming_links=song.streaming_links or {},
                        )
                        pitches.append({"song": song, "pitch": gen})

                    st.session_state.last_multi_pitches = pitches
                    st.session_state.last_target = selected_target
                    st.session_state.last_style = style
                    st.session_state.last_pitch_source = "tracker"
                    if 'tracker_row' in locals() and tracker_row:
                        st.session_state.last_tracker_row = tracker_row
                        st.session_state.last_tracker_file = str(tracker_file_path) if 'tracker_file_path' in locals() else None

                    # Record multiple pitches (Phase 0)
                    try:
                        from dkplaylister.storage import PitchRepository
                        pr = PitchRepository()
                        for item in pitches:
                            song = item["song"]
                            gen = item["pitch"]
                            pitch_record = Pitch(
                                band_id=current_band_id,
                                style_profile_id=style.id,
                                song_id=song.id,
                                playlist_id=getattr(selected_target, 'id', None) or 0,
                                song_title=song.title,
                                song_lyrics=song.lyrics,
                                format=PitchFormat(format_choice),
                                llm_provider="grok",
                                llm_model="grok-3",
                                prompt_version="v2",
                                generated_text=gen,
                            )
                            pr.create(pitch_record)
                    except Exception:
                        pass

                else:
                    # Single song (existing flow)
                    generated = llm.generate_pitch(
                        style_profile=style,
                        song_title=song_title,
                        lyrics=lyrics,
                        playlist=selected_target,
                        curator=selected_target.curator if selected_target else None,
                        pitch_format=format_choice,
                        artist_name=artist_name,
                        song_streaming_links=selected_song_streaming_links,
                    )
                    st.session_state.last_pitch = generated
                    st.session_state.last_song = song_title
                    st.session_state.last_target = selected_target
                    st.session_state.last_style = style
                    st.session_state.last_pitch_source = "tracker" if 'tracker_row' in locals() and tracker_row else "database"
                    if 'tracker_row' in locals() and tracker_row:
                        st.session_state.last_tracker_row = tracker_row
                        st.session_state.last_tracker_file = str(tracker_file_path) if 'tracker_file_path' in locals() else None

                    # Record Pitch (Phase 0)
                    try:
                        from dkplaylister.storage import PitchRepository
                        song_id_for_pitch = None
                        if 'selected_song' in locals() and selected_song:
                            song_id_for_pitch = selected_song.id

                        pitch_record = Pitch(
                            band_id=current_band_id,
                            style_profile_id=style.id,
                            song_id=song_id_for_pitch,
                            playlist_id=getattr(selected_target, 'id', None) or 0,
                            song_title=song_title,
                            song_lyrics=lyrics,
                            format=PitchFormat(format_choice),
                            llm_provider="grok",
                            llm_model="grok-3",
                            prompt_version="v2",
                            generated_text=generated,
                        )
                        PitchRepository().create(pitch_record)
                    except Exception:
                        pass  # Don't fail generation if recording fails

            except Exception as e:
                st.error(f"Failed to generate pitch: {e}")

    # Display single pitch (from database or single-song tracker)
    if "last_pitch" in st.session_state:
        st.subheader(f"Generated Pitch — {st.session_state.last_song}")

        st.caption(f"Band: **{current_band_id}** | Style: **{st.session_state.last_style.name}** | Target: **{st.session_state.last_target.name}**")

        edited = st.text_area("Edit as needed", value=st.session_state.last_pitch, height=420, key="edited_pitch")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save Pitch to File", width="stretch"):
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
                width="stretch",
            )

        # Offer to update tracker when coming from spreadsheet
        if st.session_state.get("last_pitch_source") == "tracker" and st.session_state.get("last_tracker_file"):
            st.divider()
            st.markdown("**Update Playlister Tracker?**")
            tracker_file = st.session_state.last_tracker_file
            row = st.session_state.last_tracker_row

            if st.button("Mark this target as 'Pitched' in tracker", type="secondary"):
                try:
                    tracker_df = pd.read_csv(tracker_file)
                    for col in ["Notes", "Status", "Spotify URL", "Contact Type", "Contact Detail"]:
                        if col in tracker_df.columns:
                            tracker_df[col] = tracker_df[col].fillna("").astype(str)

                    mask = tracker_df["Playlister Internal ID"] == row["Playlister Internal ID"]
                    if mask.any():
                        tracker_df.loc[mask, "Status"] = "Pitched"
                        tracker_df.loc[mask, "Notes"] = (tracker_df.loc[mask, "Notes"] + f" Pitched on {datetime.now().strftime('%Y-%m-%d')}").str.strip()
                        tracker_df.to_csv(tracker_file, index=False)

                        # Create Submission record (P0-3)
                        try:
                            from dkplaylister.storage import SubmissionRepository
                            from dkplaylister.models import Submission, SubmissionStatus
                            sub = Submission(
                                band_id=current_band_id,
                                playlist_id=getattr(selected_target, 'id', None) or 0,
                                status=SubmissionStatus.PITCH_SENT,
                                sent_at=datetime.utcnow(),
                                track_title=st.session_state.get("last_song", "Unknown"),
                                notes=f"Pitched via UI tracker on {datetime.now().strftime('%Y-%m-%d')}"
                            )
                            SubmissionRepository().create(sub)
                        except Exception:
                            pass

                        st.success(f"Updated status to 'Pitched' in {Path(tracker_file).name}")
                        st.session_state.last_pitch_source = None
                        st.session_state.last_tracker_row = None
                        st.session_state.last_tracker_file = None
                        st.rerun()
                    else:
                        st.warning("Could not find the matching row in the tracker file.")
                except Exception as e:
                    st.error(f"Failed to update tracker: {e}")

    # Display multiple pitches (from tracker multi-song selection)
    if "last_multi_pitches" in st.session_state:
        st.subheader("Generated Pitches")

        for item in st.session_state.last_multi_pitches:
            song = item["song"]
            pitch = item["pitch"]

            with st.expander(f"Pitch for: {song.title}", expanded=True):
                st.caption(f"Target: **{st.session_state.last_target.name}**")
                edited = st.text_area("Edit", value=pitch, height=380, key=f"multi_pitch_{song.id}")

                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Save to File", key=f"save_multi_{song.id}", width="stretch"):
                        pitches_dir = Path("pitches")
                        pitches_dir.mkdir(exist_ok=True)
                        fname = f"{song.title.replace(' ', '_')}.txt"
                        (pitches_dir / fname).write_text(edited)
                        st.success(f"Saved {fname}")

                with c2:
                    st.download_button(
                        "Download",
                        data=edited,
                        file_name=f"{song.title.replace(' ', '_')}.txt",
                        key=f"dl_multi_{song.id}",
                        width="stretch"
                    )

        # Single "Mark as Pitched" for the target (not per song)
        if st.session_state.get("last_pitch_source") == "tracker" and st.session_state.get("last_tracker_file"):
            st.divider()
            st.markdown("**Update Playlister Tracker?**")
            tracker_file = st.session_state.last_tracker_file
            row = st.session_state.last_tracker_row

            if st.button("Mark this target as 'Pitched' in tracker (for all songs above)", type="secondary"):
                try:
                    tracker_df = pd.read_csv(tracker_file)
                    for col in ["Notes", "Status", "Spotify URL", "Contact Type", "Contact Detail"]:
                        if col in tracker_df.columns:
                            tracker_df[col] = tracker_df[col].fillna("").astype(str)

                    mask = tracker_df["Playlister Internal ID"] == row["Playlister Internal ID"]
                    if mask.any():
                        tracker_df.loc[mask, "Status"] = "Pitched"
                        tracker_df.loc[mask, "Notes"] = (tracker_df.loc[mask, "Notes"] + f" Pitched multiple songs on {datetime.now().strftime('%Y-%m-%d')}").str.strip()
                        tracker_df.to_csv(tracker_file, index=False)
                        st.success(f"Marked target as 'Pitched' in {Path(tracker_file).name}")
                        st.session_state.last_pitch_source = None
                        st.session_state.last_tracker_row = None
                        st.session_state.last_tracker_file = None
                        st.session_state.last_multi_pitches = None
                        st.rerun()
                except Exception as e:
                    st.error(f"Failed to update tracker: {e}")

elif mode == "Manage Catalog":
    st.header("Band Catalog Management")

    if not current_band_id:
        st.warning("Please select or create a band in the sidebar first.")
        st.stop()

    current_band = band_repo.get_by_id(current_band_id)
    st.subheader(f"Managing: {current_band.name}")

    tab1, tab2, tab3, tab4 = st.tabs(["Bands", "Styles", "Albums", "Songs"])

    # --- Bands Tab (global) ---
    with tab1:
        st.subheader("All Bands")
        all_bands = band_repo.list_all()

        for b in all_bands:
            with st.expander(f"{b.name} ({b.slug}) - ID {b.id}"):
                st.write(f"**Notes:** {b.notes or '—'}")
                if st.button("Set as Current Band", key=f"set_band_{b.id}"):
                    st.session_state.current_band_id = b.id
                    st.rerun()

        st.markdown("**Create New Band**")
        with st.form("create_band_catalog"):
            new_name = st.text_input("Band Name")
            new_slug = st.text_input("Slug (for folders)", value="")
            new_notes = st.text_area("Notes")
            submitted = st.form_submit_button("Create Band")
            if submitted and new_name:
                slug = new_slug or new_name.lower().replace(" ", "-")
                try:
                    new_band = Band(name=new_name, slug=slug, notes=new_notes or None)
                    created = band_repo.create(new_band)
                    st.session_state.current_band_id = created.id
                    st.success(f"Band created: {new_name}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # --- Styles Tab ---
    with tab2:
        st.subheader("Styles")
        styles = style_repo.list_all(band_id=current_band_id)

        if styles:
            for s in styles:
                with st.expander(f"{s.name} (ID {s.id})"):
                    st.text_area("Current Prompt", value=s.raw_prompt, height=160, disabled=True, key=f"view_style_{s.id}")

                    # Edit mode
                    edit_key = f"edit_style_{s.id}"
                    if st.checkbox("Edit this style", key=edit_key):
                        with st.form(f"edit_style_form_{s.id}"):
                            edited_name = st.text_input("Style Name", value=s.name)
                            edited_prompt = st.text_area("Style Description", value=s.raw_prompt, height=200)
                            col1, col2 = st.columns(2)
                            with col1:
                                save_edit = st.form_submit_button("Save Changes")
                            with col2:
                                delete_style = st.form_submit_button("Delete Style", type="secondary")

                            if save_edit:
                                updated_style = StyleProfile(
                                    id=s.id,
                                    band_id=current_band_id,
                                    name=edited_name,
                                    raw_prompt=edited_prompt
                                )
                                style_repo.update(updated_style)
                                st.success("Style updated!")
                                st.rerun()

                            if delete_style:
                                confirm = st.checkbox(f"Confirm delete '{s.name}'?", key=f"confirm_del_style_{s.id}")
                                if confirm:
                                    style_repo.delete(s.id)
                                    st.success(f"Deleted style '{s.name}'")
                                    st.rerun()
        else:
            st.info("No styles yet for this band.")

        st.markdown("**Add New Style**")

        if "style_form_counter" not in st.session_state:
            st.session_state.style_form_counter = 0

        style_form_key = f"add_style_form_{st.session_state.style_form_counter}"

        with st.form(style_form_key):
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
                st.session_state.style_form_counter += 1
                st.rerun()

    # --- Albums Tab ---
    with tab3:
        st.subheader("Albums / Releases")
        albums = album_repo.list_by_band(current_band_id)

        if albums:
            for a in albums:
                with st.expander(f"{a.title} ({a.release_date or 'No date'}) - ID {a.id}"):
                    st.write(f"**Notes:** {a.notes or '—'}")

                    edit_key = f"album_edit_checkbox_{a.id}"
                    if st.checkbox("Edit this album", key=edit_key):
                        with st.form(f"edit_album_form_{a.id}"):
                            edited_title = st.text_input("Album Title", value=a.title)
                            edited_date = st.text_input("Release Date (YYYY-MM-DD)", value=a.release_date or "")
                            edited_notes = st.text_area("Notes", value=a.notes or "")
                            col1, col2 = st.columns(2)
                            with col1:
                                save_edit = st.form_submit_button("Save Changes")
                            with col2:
                                delete_album = st.form_submit_button("Delete Album", type="secondary")

                            if save_edit:
                                updated_album = Album(
                                    id=a.id,
                                    band_id=current_band_id,
                                    title=edited_title,
                                    release_date=edited_date or None,
                                    notes=edited_notes or None
                                )
                                album_repo.update(updated_album)
                                st.success("Album updated!")
                                st.rerun()

                            if delete_album:
                                if st.checkbox(f"Confirm delete '{a.title}'?", key=f"confirm_del_album_{a.id}"):
                                    album_repo.delete(a.id)
                                    st.success(f"Deleted album '{a.title}'")
                                    st.rerun()
        else:
            st.info("No albums yet.")

        st.markdown("**Add New Album**")

        if "album_form_counter" not in st.session_state:
            st.session_state.album_form_counter = 0

        album_form_key = f"add_album_form_{st.session_state.album_form_counter}"

        with st.form(album_form_key):
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
                st.session_state.album_form_counter += 1
                st.rerun()

    # --- Songs Tab ---
    with tab4:
        st.subheader("Songs / Lyrics")

        band_albums = album_repo.list_by_band(current_band_id)
        album_lookup = {a.id: a.title for a in band_albums}

        songs = song_repo.list_by_band(current_band_id)

        if songs:
            for s in songs:
                album_name = album_lookup.get(s.album_id, "No Album") if s.album_id else "No Album"
                with st.expander(f"{s.title} ({album_name}) - ID {s.id}"):
                    st.text_area("Lyrics", value=s.lyrics, height=180, disabled=True, key=f"view_song_{s.id}")
                    st.write(f"**Notes:** {s.notes or '—'}")
                    st.caption(f"Album: {album_name}")

                    # Edit mode for song
                    edit_key = f"edit_song_{s.id}"
                    if st.checkbox("Edit this song", key=edit_key):
                        with st.form(f"edit_song_form_{s.id}"):
                            edited_title = st.text_input("Title", value=s.title)
                            edited_lyrics = st.text_area("Lyrics", value=s.lyrics, height=200)
                            edited_notes = st.text_area("Notes", value=s.notes or "")

                            # Album reassignment
                            album_opts = ["No Album"] + [f"{a.title} (ID {a.id})" for a in band_albums]
                            current_album_label = "No Album"
                            if s.album_id and s.album_id in album_lookup:
                                current_album_label = f"{album_lookup[s.album_id]} (ID {s.album_id})"

                            new_album_label = st.selectbox(
                                "Album", 
                                album_opts, 
                                index=album_opts.index(current_album_label) if current_album_label in album_opts else 0,
                                key=f"song_edit_album_select_{s.id}"
                            )

                            # Streaming links (for released songs)
                            st.markdown("**Streaming Links** (add after release)")
                            current_links = s.streaming_links or {}
                            spotify_link = st.text_input("Spotify", value=current_links.get("spotify", ""), key=f"song_spotify_{s.id}")
                            apple_link = st.text_input("Apple Music", value=current_links.get("apple_music", ""), key=f"song_apple_{s.id}")
                            youtube_link = st.text_input("YouTube Music", value=current_links.get("youtube_music", ""), key=f"song_yt_{s.id}")
                            other_links = st.text_area("Other links (one per line, platform: url)", value="\n".join([f"{k}: {v}" for k, v in current_links.items() if k not in ["spotify", "apple_music", "youtube_music"]]), height=80, key=f"song_other_links_{s.id}")

                            col1, col2 = st.columns(2)
                            with col1:
                                save_song = st.form_submit_button("Save Changes")
                            with col2:
                                delete_song = st.form_submit_button("Delete Song", type="secondary")

                            if save_song:
                                chosen_album_id = None
                                if new_album_label != "No Album":
                                    chosen_album_id = int(new_album_label.split("(ID ")[1].split(")")[0])

                                # Parse other links
                                other_dict = {}
                                for line in other_links.splitlines():
                                    if ":" in line:
                                        k, v = line.split(":", 1)
                                        other_dict[k.strip().lower().replace(" ", "_")] = v.strip()

                                streaming_links = {}
                                if spotify_link.strip(): streaming_links["spotify"] = spotify_link.strip()
                                if apple_link.strip(): streaming_links["apple_music"] = apple_link.strip()
                                if youtube_link.strip(): streaming_links["youtube_music"] = youtube_link.strip()
                                streaming_links.update(other_dict)

                                updated_song = Song(
                                    id=s.id,
                                    band_id=current_band_id,
                                    album_id=chosen_album_id,
                                    title=edited_title,
                                    lyrics=edited_lyrics,
                                    notes=edited_notes or None,
                                    streaming_links=streaming_links
                                )
                                song_repo.update(updated_song)
                                st.success("Song updated!")
                                st.rerun()

                            if delete_song:
                                if st.checkbox(f"Confirm delete '{s.title}'?", key=f"confirm_del_song_{s.id}"):
                                    song_repo.delete(s.id)
                                    st.success(f"Deleted song '{s.title}'")
                                    st.rerun()
        else:
            st.info("No songs yet for this band.")

        st.markdown("**Add New Song**")

        if "song_form_counter" not in st.session_state:
            st.session_state.song_form_counter = 0

        form_key = f"add_song_form_{st.session_state.song_form_counter}"

        with st.form(form_key):
            song_title = st.text_input("Song Title")
            song_lyrics = st.text_area("Lyrics", height=250)
            song_notes = st.text_area("Notes")

            album_options = ["No Album"] + [f"{a.title} (ID {a.id})" for a in band_albums]
            selected_album_label = st.selectbox(
                "Album (optional)", 
                album_options, 
                key=f"new_song_album_{st.session_state.song_form_counter}"
            )

            # Streaming links for released songs
            st.markdown("**Streaming Links** (optional, add after release)")
            new_spotify = st.text_input("Spotify URL", key=f"new_spotify_{st.session_state.song_form_counter}")
            new_apple = st.text_input("Apple Music URL", key=f"new_apple_{st.session_state.song_form_counter}")
            new_youtube = st.text_input("YouTube Music URL", key=f"new_yt_{st.session_state.song_form_counter}")
            new_other = st.text_area("Other platforms (platform: url, one per line)", height=60, key=f"new_other_links_{st.session_state.song_form_counter}")

            submitted = st.form_submit_button("Save Song")

            if submitted and song_title and song_lyrics:
                chosen_album_id = None
                if selected_album_label != "No Album":
                    chosen_album_id = int(selected_album_label.split("(ID ")[1].split(")")[0])

                # Parse streaming links for new song
                other_dict = {}
                for line in new_other.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        other_dict[k.strip().lower().replace(" ", "_")] = v.strip()

                streaming_links = {}
                if new_spotify.strip(): streaming_links["spotify"] = new_spotify.strip()
                if new_apple.strip(): streaming_links["apple_music"] = new_apple.strip()
                if new_youtube.strip(): streaming_links["youtube_music"] = new_youtube.strip()
                streaming_links.update(other_dict)

                new_song = Song(
                    band_id=current_band_id,
                    album_id=chosen_album_id,
                    title=song_title,
                    lyrics=song_lyrics,
                    notes=song_notes or None,
                    streaming_links=streaming_links
                )
                db_s = song_repo.create(new_song)
                st.success(f"Song '{song_title}' added (ID {db_s.id})")
                st.session_state.song_form_counter += 1
                st.rerun()

elif mode == "Process Playlister Imports":
    st.header("Process Playlister Results")

    imports_dir = Path("data/playlister_imports")
    if not imports_dir.exists():
        st.error("No `data/playlister_imports/` folder found.")
        st.stop()

    csv_files = sorted(imports_dir.glob("*.csv"))
    if not csv_files:
        st.warning("No CSV files found in data/playlister_imports/")
        st.info("Run the Playlister HTML parser first to generate tracker CSVs.")
        st.stop()

    file_options = {f.name: f for f in csv_files}
    selected_name = st.selectbox("Select Playlister results file", list(file_options.keys()))
    selected_file = file_options[selected_name]

    if "playlister_df" not in st.session_state or st.session_state.get("loaded_file") != selected_name:
        df = pd.read_csv(selected_file)

        # Clean string columns so Streamlit data_editor doesn't complain about float/NaN
        string_cols = ["Spotify URL", "Contact Type", "Contact Detail", "Notes", "Status"]
        for col in string_cols:
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str)

        st.session_state.playlister_df = df
        st.session_state.loaded_file = selected_name

    df = st.session_state.playlister_df

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        min_subs = st.number_input("Min Subscribers", min_value=0, value=3000, step=1000)
    with col2:
        status_filter = st.multiselect(
            "Status",
            ["Not Reviewed", "Revealed - No Contact", "Revealed - Has Contact", "Imported", "Skipped", "Pitched"],
            default=["Not Reviewed"]
        )
    with col3:
        search_term = st.text_input("Search title", "")

    filtered = df.copy()
    if min_subs > 0:
        filtered = filtered[filtered["Subscribers"] >= min_subs]
    if status_filter:
        filtered = filtered[filtered["Status"].isin(status_filter)]
    if search_term:
        filtered = filtered[filtered["Title"].str.contains(search_term, case=False, na=False)]

    st.write(f"Showing **{len(filtered)}** of {len(df)} playlists")

    # Reorder columns so the most important ones (Title + contact info + Spotify URL) are grouped together at the front
    priority_cols = ["Title", "Contact Type", "Contact Detail", "Spotify URL"]
    other_cols = [col for col in filtered.columns if col not in priority_cols]
    desired_order = priority_cols + other_cols

    # Only include columns that actually exist in the dataframe
    final_order = [col for col in desired_order if col in filtered.columns]

    filtered = filtered[final_order]

    # Make key columns editable
    column_config = {
        "Spotify URL": st.column_config.TextColumn(width="large"),
        "Contact Type": st.column_config.SelectboxColumn(
            options=["IG Handle", "Email", "Form/Bitly", "SubmitHub", "Other", "Unknown"],
            width="medium"
        ),
        "Contact Detail": st.column_config.TextColumn(width="large"),
        "Status": st.column_config.SelectboxColumn(
            options=["Not Reviewed", "Revealed - No Contact", "Revealed - Has Contact", "Imported", "Skipped", "Pitched"],
            width="medium"
        ),
        "Notes": st.column_config.TextColumn(width="medium"),
    }

    edited_df = st.data_editor(
        filtered,
        column_config=column_config,
        width="stretch",
        num_rows="fixed",
        key="playlister_editor"
    )

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("💾 Save Progress to File", type="primary"):
            for idx, row in edited_df.iterrows():
                st.session_state.playlister_df.loc[idx] = row
            st.session_state.playlister_df.to_csv(selected_file, index=False)
            st.success(f"Saved changes to {selected_name}")

    with col_b:
        ready = edited_df[
            (edited_df["Spotify URL"].str.len() > 10) &
            (edited_df["Contact Detail"].str.len() > 2) &
            (edited_df["Status"] == "Revealed - Has Contact")
        ]
        if st.button(f"🚀 Import {len(ready)} Ready Targets"):
            if ready.empty:
                st.warning("No rows ready (need Spotify URL + Contact Detail + Status = 'Revealed - Has Contact')")
            else:
                imported = 0
                for _, row in ready.iterrows():
                    try:
                        playlist = fetch_playlist(row["Spotify URL"])
                        if not playlist:
                            continue

                        curator = Curator()
                        contact_type = str(row.get("Contact Type", "")).lower()
                        contact_detail = str(row.get("Contact Detail", ""))

                        if "ig" in contact_type or "@" in contact_detail:
                            curator.instagram = contact_detail.replace("@", "").strip()
                        elif "@" in contact_detail and "." in contact_detail:
                            curator.email = contact_detail
                        else:
                            curator.notes = f"{contact_type}: {contact_detail}"

                        playlist.curator = curator
                        playlist.contact_revealed_via = "playlister_popup"
                        playlist.source = PlaylistSource.PLAYLISTER
                        playlist.discovery_query = selected_name

                        style = style_repo.get_latest(band_id=current_band_id)
                        if style:
                            scorer = PlaylistScorer(style)
                            scorer.score(playlist)

                        from dkplaylister.storage import PitchRepository
                        PlaylistRepository().create_or_update(playlist)
                        imported += 1
                    except Exception as e:
                        st.error(f"Failed on {row['Title']}: {e}")

                st.success(f"Imported {imported} playlists with contacts!")
                st.info("Refresh 'Review Targets' to see them.")

st.sidebar.markdown("---")
st.sidebar.caption("Run from CLI for full power: `dkplaylister --help`")