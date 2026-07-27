import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timezone, timedelta

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Live FPL Draft Board", layout="wide", page_icon="⚽", initial_sidebar_state="collapsed")

# --- INITIALISE SESSION STATE ---
if "active_league_id" not in st.session_state:
    st.session_state.active_league_id = None
if "picks_made" not in st.session_state:
    st.session_state.picks_made = 0
if "total_picks" not in st.session_state:
    st.session_state.total_picks = 0
if "board_html" not in st.session_state:
    st.session_state.board_html = ""
if "pause_updates" not in st.session_state:
    st.session_state.pause_updates = False
if "draft_ended" not in st.session_state:
    st.session_state.draft_ended = False 

# Replay & Playback State Variables
if "max_picks_seen" not in st.session_state:
    st.session_state.max_picks_seen = 0
if "last_rendered_picks" not in st.session_state:
    st.session_state.last_rendered_picks = -1
if "is_playing" not in st.session_state:
    st.session_state.is_playing = False
if "just_clicked_play" not in st.session_state:
    st.session_state.just_clicked_play = False

# --- CUSTOM CSS FOR BROADCAST UI WITH RESPONSIVE TEXT SCALING ---
st.markdown("""
    <style>
    .block-container {
        padding-top: 3rem !important; 
        padding-bottom: 2rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        max-width: 100% !important;
    }
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;}
    
    [data-testid="stMetricValue"] { font-size: 1.4rem !important; }
    [data-testid="stMetricLabel"] { font-size: 0.75rem !important; }
    h3 { margin-top: 0px !important; margin-bottom: 0px !important; padding-bottom: 0px !important; }
    
    .draft-board-wrapper { width: 100%; margin-bottom: 20px; }
    .draft-container {
        display: flex; gap: 4px; width: 100%; height: calc(100vh - 200px); 
        overflow-x: auto;
        padding-bottom: 8px;
    }
    .manager-col {
        flex: 1 1 0; display: flex; flex-direction: column; 
        min-width: 110px;
        background-color: var(--secondary-background-color);
        border: 1px solid var(--border-color); border-radius: 4px; padding: 4px; overflow: hidden;
    }
    
    /* PICKER STATUS ABOVE FRAME */
    .picker-status-container {
        height: 16px; 
        text-align: center;
        margin-bottom: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .picker-status {
        font-size: clamp(0.5rem, 0.65vw, 0.75rem);
        font-weight: 800;
        white-space: nowrap;
        letter-spacing: 0.5px;
    }
    .status-now { color: #22c55e; }
    .status-next { color: #eab308; }
    
    /* MANAGER HEADER (THE FRAME) */
    .manager-header {
        flex-shrink: 0; text-align: center; font-weight: 700; 
        font-size: clamp(0.8rem, 1.1vw, 1.2rem);
        margin-bottom: 0px; padding: 4px 2px; 
        border: 2px solid transparent; /* Permanently reserves 2px for the border */
        border-radius: 4px;
        box-sizing: border-box;
        transition: border-color 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease;
    }
    .header-picking-now {
        border-color: #22c55e !important;
        background-color: rgba(34, 197, 94, 0.08);
        box-shadow: 0 0 8px rgba(34, 197, 94, 0.35) !important;
    }
    .header-picking-next {
        border-color: #eab308 !important;
        background-color: rgba(234, 179, 8, 0.05);
    }
    
    .manager-title-wrap {
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .team-name {
        font-size: clamp(0.55rem, 0.8vw, 1rem); 
        font-weight: 400; opacity: 0.7; display: block;
        margin-top: 0px; line-height: 1.2;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    
    /* SQUAD VALUE & EMOJIS */
    .squad-value {
        font-size: clamp(0.7rem, 0.85vw, 1rem); 
        font-weight: 400; 
        margin-top: 4px; 
    }
    .squad-value-1st { font-weight: 700; }
    .rank-badge {
        font-size: clamp(0.7rem, 0.85vw, 1rem);
        opacity: 1.0; margin-left: 2px; vertical-align: baseline;
    }
    
    /* STATS DIVIDER AND SPACING */
    .manager-stats-top {
        display: flex; justify-content: space-evenly; gap: 4px;
        font-size: clamp(0.6rem, 0.75vw, 0.85rem);
        font-weight: normal; opacity: 0.9; 
        margin-top: 4px; margin-bottom: 4px; padding-bottom: 4px; 
        border-bottom: 1px solid var(--border-color); 
    }
    .manager-stats-top span { white-space: nowrap; }
    
    .time-slow { color: #ef4444; font-weight: 800; }
    .auto-high { color: #ef4444; font-weight: 800; }
    
    .pos-divider {
        flex-shrink: 0; height: 1px; background-color: var(--border-color);
        margin: 6px 2px 4px 2px; opacity: 0.6;
    }
    
    /* SCALABLE PLAYER CARDS */
    .player-card, .empty-card {
        flex: 1 1 0; display: flex; align-items: center; 
        background-color: var(--background-color); 
        border: 1px solid var(--border-color); /* Permanently reserves 1px */
        box-sizing: border-box; /* Ensures border is calculated inside dimensions */
        padding: 0 4px 0 8px; margin-bottom: 3px; border-radius: 3px;
        font-size: clamp(0.75rem, 0.95vw, 1.1rem);
        font-weight: 500; white-space: nowrap; overflow: hidden;
        text-overflow: ellipsis; box-shadow: 0 1px 2px rgba(0,0,0,0.05); position: relative; 
    }
    
    .card-round-1 {
        border-color: rgba(212, 175, 55, 0.6) !important;
        background-color: rgba(212, 175, 55, 0.08) !important;
        box-shadow: 0 0 3px rgba(212, 175, 55, 0.4) !important;
    }

    /* LAST PICK HIGHLIGHT */
    .card-last-picked {
        border-color: #3b82f6 !important;
        background-color: rgba(59, 130, 246, 0.18) !important;
        box-shadow: 0 0 6px rgba(59, 130, 246, 0.5) !important;
    }

    /* POSITIONAL COLOUR CODING BARS */
    .card-gk::before, .card-def::before, .card-mid::before, .card-fwd::before {
        content: ""; position: absolute; left: 0; top: 20%; bottom: 20%; width: 3px;
        border-radius: 0 2px 2px 0; opacity: 0.55; 
    }
    .card-gk::before { background-color: #eab308; }  
    .card-def::before { background-color: #3b82f6; } 
    .card-mid::before { background-color: #22c55e; } 
    .card-fwd::before { background-color: #ef4444; } 
    
    .empty-card {
        background-color: transparent; border: 1px dashed var(--border-color);
        justify-content: center; opacity: 0.3; padding: 0 4px; 
    }
    .pl-team { 
        opacity: 0.5; 
        font-size: clamp(0.65rem, 0.8vw, 0.9rem); 
        margin-left: 4px; 
    }
    </style>
""", unsafe_allow_html=True)

# --- CACHED DATA FETCHING ---
@st.cache_data(ttl=3600)
def fetch_players_data():
    game_data_url = "https://draft.premierleague.com/api/bootstrap-static"
    try:
        response = requests.get(game_data_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        players_df = pd.DataFrame(data["elements"])[["id", "web_name", "element_type", "team"]]
        teams_df = pd.DataFrame(data["teams"])[["id", "short_name"]]
        team_map = dict(zip(teams_df["id"], teams_df["short_name"]))
        players_df["team_name"] = players_df["team"].map(team_map)
        return players_df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_main_game_prices():
    main_game_url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    try:
        response = requests.get(main_game_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        prices_df = pd.DataFrame(data["elements"])[["id", "now_cost"]]
        prices_df["cost_mil"] = prices_df["now_cost"] / 10.0
        return prices_df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_league_details(league_id):
    league_details_url = f"https://draft.premierleague.com/api/league/{league_id}/details"
    try:
        response = requests.get(league_details_url, timeout=10)
        if response.status_code == 404:
            return None, None
        response.raise_for_status()
        data = response.json()
        league_name = data.get("league", {}).get("name", f"League {league_id}")
        draft_dt = data.get("league", {}).get("draft_dt", None)
        return league_name, draft_dt
    except Exception:
        return f"League {league_id}", None

def format_time(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m}m{s}s"

POSITION_MAP = {1: "Goalkeepers", 2: "Defenders", 3: "Midfielders", 4: "Forwards"}
POS_CLASS_MAP = {1: "card-gk", 2: "card-def", 3: "card-mid", 4: "card-fwd"}
ROSTER_LIMITS = {1: 2, 2: 5, 3: 5, 4: 3} 

# --- LANDING PAGE COMPONENT ---
def render_landing_page():
    st.markdown("<h1 style='text-align: center; margin-top: 1rem;'>⚽ Live FPL Draft Boards</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 1.1rem; opacity: 0.8;'>Track your Premier League Draft live in real-time with squad values, pick alerts, and draft stats.</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("🔑 Enter Your League ID")
        entered_id = st.number_input("League ID Number", min_value=1, value=217, step=1, key="league_id_input")
        st.info("💡 **Where to find your League ID?**\n\nURL: `https://draft.premierleague.com/league/YOUR_LEAGUE_ID/edit`")
        
        if st.button("🚀 Load Draft Board", use_container_width=True, type="primary"):
            st.session_state.active_league_id = entered_id
            st.session_state.picks_made = 0
            st.session_state.board_html = ""
            st.session_state.draft_ended = False
            st.session_state.max_picks_seen = 0
            st.session_state.last_rendered_picks = -1
            st.session_state.is_playing = False
            st.rerun()

# --- MAIN APP ROUTING & DRAFT BOARD VIEW ---
if not st.session_state.active_league_id:
    render_landing_page()
else:
    league_id = st.session_state.active_league_id
    league_name, draft_start_dt = fetch_league_details(league_id)
    
    if league_name is None:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.error("❌ **League does not exist.** Please check your League ID and try again.")
            if st.button("👈 Return to Landing Page", use_container_width=True):
                st.session_state.active_league_id = None
                st.session_state.is_playing = False
                st.rerun()
        st.stop()

    # --- SIDEBAR CONTROLS ---
    st.sidebar.header("⚙️ Draft Settings")
    st.sidebar.caption(f"Active League: **#{league_id}**")
    
    if st.sidebar.button("👈 Switch League", use_container_width=True):
        st.session_state.active_league_id = None
        st.session_state.is_playing = False
        st.rerun()

    st.sidebar.markdown("---")
    refresh_seconds = st.sidebar.slider("Refresh Interval (Seconds)", min_value=3, max_value=30, value=5)

    prev_champs_input = st.sidebar.text_input(
        "🏆 Previous Champions", 
        placeholder="Comma-separated names...", 
        help="Enter exact Manager or Team names separated by commas to award them a gold star on the board."
    )
    prev_champs_list = [name.strip().lower() for name in prev_champs_input.split(",") if name.strip()]

    st.sidebar.markdown("---")
    st.sidebar.toggle("⏸️ Pause Live Updates", key="pause_updates")

    if st.sidebar.button("🔄 Manual Refresh", use_container_width=True):
        st.session_state.picks_made = -1 
        st.session_state.draft_ended = False 
        st.session_state.last_rendered_picks = -1
        st.session_state.is_playing = False
        st.cache_data.clear() 

    is_paused = st.session_state.pause_updates or st.session_state.draft_ended or st.session_state.is_playing
    refresh_timer = None if is_paused else timedelta(seconds=refresh_seconds)

    # --- AUTO-REFRESHING LIVE COMPONENT ---
    @st.fragment(run_every=refresh_timer)
    def render_live_draft_board():
            
        def draw_board_ui(display_count, start_str="--:--", end_str="--:--", dur_str="--"):
            """Renders the top panel header metrics."""
            col_title, col1, col_times, col2, col3 = st.columns([1.5, 0.8, 1.2, 1.2, 0.8]) 
            with col_title:
                st.markdown(f"### ⚽ {league_name}") 

            with col1:
                st.metric("Picks Shown", f"{max(0, display_count)} / {st.session_state.total_picks}")
                
            with col_times:
                st.markdown(
                    f"<div style='font-size: 0.85rem; line-height: 1.4; opacity: 0.9; margin-top: -0.2rem;'>"
                    f"<strong>Start:</strong> {start_str}<br>"
                    f"<strong>End:</strong> {end_str}<br>"
                    f"<strong>Duration:</strong> {dur_str}</div>", 
                    unsafe_allow_html=True
                )
            
            with col2:
                if st.session_state.draft_ended:
                    st.success("✅ Draft Complete!")
                elif st.session_state.is_playing:
                    st.info("▶️ Replay Playing...")
                elif st.session_state.pause_updates:
                    st.warning("⏸️ Updates Paused")
                elif st.session_state.total_picks > 0:
                    st.write("🚧 **Draft In Progress**")
                    progress_val = max(0.0, min(1.0, display_count / st.session_state.total_picks))
                    st.progress(progress_val)
                else:
                    st.info("🟡 Waiting for draft...")
                    
            with col3:
                now_bst = datetime.now(timezone.utc) + timedelta(hours=1)
                st.metric("Last Synced", now_bst.strftime("%H:%M:%S BST"))

            st.markdown("<hr style='margin: 0rem 0 0.5rem 0'>", unsafe_allow_html=True) 
            
            if st.session_state.board_html:
                st.markdown(st.session_state.board_html, unsafe_allow_html=True)

        players_df = fetch_players_data()
        if players_df.empty:
            st.toast("⚠️ Base player data unavailable. Retrying...")
            draw_board_ui(st.session_state.get("replay_pick_slider", 0))
            return

        choices_url = f"https://draft.premierleague.com/api/draft/{league_id}/choices"
        try:
            response = requests.get(choices_url, timeout=10)
            response.raise_for_status()
            choices_data = response.json()
        except requests.exceptions.RequestException:
            st.toast("⚠️ FPL API blip. Keeping previous board on screen while retrying...")
            draw_board_ui(st.session_state.get("replay_pick_slider", 0))
            return
            
        choices = choices_data.get("choices", [])
        is_pre_draft = False
        
        if not choices:
            is_pre_draft = True
        else:
            df_choices = pd.DataFrame(choices)
            if "element" not in df_choices.columns or df_choices["element"].isna().all():
                is_pre_draft = True
        
        if is_pre_draft:
            now_utc = datetime.now(timezone.utc)
            if draft_start_dt:
                draft_time = pd.to_datetime(draft_start_dt)
                if draft_time > now_utc:
                    time_diff = draft_time - now_utc
                    days = time_diff.days
                    seconds = time_diff.seconds
                    hours = seconds // 3600
                    minutes = (seconds % 3600) // 60
                    
                    st.info(f"⏳ **Draft has not started yet.** Scheduled for: {draft_time.strftime('%d %b %Y %H:%M')} (UTC)")
                    st.markdown("### ⏲️ Time Until Draft")
                    col_d, col_h, col_m, _ = st.columns([1, 1, 1, 3])
                    col_d.metric("Days", days)
                    col_h.metric("Hours", hours)
                    col_m.metric("Minutes", minutes)
                    return
                    
            st.info("🟡 Draft room is open! Waiting for the first pick to be made...")
            return

        choices_df_raw = pd.DataFrame(choices).sort_values("index").reset_index(drop=True)
        if "was_auto" not in choices_df_raw.columns:
            choices_df_raw["was_auto"] = False
            
        choices_df = choices_df_raw[["entry_name", "player_first_name", "player_last_name", "element", "index", "choice_time", "was_auto"]]
        made_picks_df = choices_df[choices_df["element"].notna()].copy()
        
        current_picks_made = len(made_picks_df)
        current_total_picks = len(choices_df)
        st.session_state.total_picks = current_total_picks
        
        start_str, end_str, dur_str = "--:--", "--:--", "--"
        if not choices_df_raw.empty and "choice_time" in choices_df_raw.columns:
            valid_times = pd.to_datetime(choices_df_raw["choice_time"]).dropna()
            if not valid_times.empty:
                first_t = valid_times.min()
                last_t = valid_times.max()
                
                start_str = (first_t + timedelta(hours=1)).strftime("%d %b %H:%M")
                
                if current_picks_made == current_total_picks and current_total_picks > 0:
                    end_str = (last_t + timedelta(hours=1)).strftime("%d %b %H:%M")
                    dur_secs = (last_t - first_t).total_seconds()
                else:
                    end_str = "TBD"
                    dur_secs = (datetime.now(timezone.utc) - first_t).total_seconds()
                    
                h, rem = divmod(int(dur_secs), 3600)
                m, s = divmod(rem, 60)
                dur_str = f"{h}h {m}m" if h > 0 else f"{m}m {s}s"

        if current_total_picks > 0 and current_picks_made == current_total_picks:
            if not st.session_state.draft_ended:
                st.session_state.draft_ended = True

        if "replay_pick_slider" not in st.session_state:
            st.session_state.replay_pick_slider = current_picks_made
            st.session_state.max_picks_seen = current_picks_made
            
        if current_picks_made > st.session_state.max_picks_seen:
            if st.session_state.replay_pick_slider == st.session_state.max_picks_seen:
                st.session_state.replay_pick_slider = current_picks_made
            st.session_state.max_picks_seen = current_picks_made

        if st.session_state.is_playing:
            if st.session_state.get("just_clicked_play", False):
                st.session_state.just_clicked_play = False
            else:
                if st.session_state.replay_pick_slider < current_picks_made:
                    st.session_state.replay_pick_slider += 1
                else:
                    st.session_state.is_playing = False

        with st.sidebar:
            st.markdown("---")
            st.subheader("⏪ Draft Replay")
            
            if current_picks_made > 0:
                col_btn1, col_btn2, col_btn3 = st.columns(3)
                
                with col_btn1:
                    if st.button("▶️ Play", use_container_width=True):
                        if st.session_state.replay_pick_slider >= current_picks_made:
                            st.session_state.replay_pick_slider = 0 
                        st.session_state.is_playing = True
                        st.session_state.just_clicked_play = True
                
                with col_btn2:
                    if st.button("⏸️ Pause", use_container_width=True):
                        st.session_state.is_playing = False
                
                with col_btn3:
                    if st.button("⏹️ Stop", use_container_width=True):
                        st.session_state.is_playing = False
                        st.session_state.replay_pick_slider = current_picks_made

                display_picks = st.slider(
                    "Show Picks Up To", 
                    min_value=0, 
                    max_value=current_picks_made, 
                    key="replay_pick_slider",
                    help="Drag this slider backward to replay the draft pick-by-pick as it happened."
                )
            else:
                display_picks = 0
                st.info("No picks made yet.")

        if display_picks != st.session_state.last_rendered_picks or st.session_state.board_html == "" or st.session_state.is_playing:
            
            display_picks_df = made_picks_df.head(display_picks).copy()
            
            manager_info_df = choices_df_raw.drop_duplicates("entry_name").copy()
            manager_info_df["manager_display"] = manager_info_df["player_first_name"].fillna('') + " " + manager_info_df["player_last_name"].fillna('').str[:1]
            manager_names = manager_info_df.set_index("entry_name")["manager_display"].to_dict()
            manager_order = choices_df_raw.groupby("entry_name")["index"].min().sort_values().index.tolist()
            
            curr_picking_mgr_entry = None
            if display_picks < current_total_picks and current_total_picks > 0:
                curr_choice = choices_df_raw.iloc[display_picks]
                curr_picking_mgr_entry = curr_choice["entry_name"]

            next_picking_mgr_entry = None
            if display_picks + 1 < current_total_picks and current_total_picks > 0:
                next_choice = choices_df_raw.iloc[display_picks + 1]
                next_picking_mgr_entry = next_choice["entry_name"]

            if not display_picks_df.empty:
                display_picks_df["player_display"] = display_picks_df["player_first_name"] + " " + display_picks_df["player_last_name"].str[0]
                merged_df = display_picks_df.merge(players_df, left_on="element", right_on="id", how="left")
                merged_df["position"] = merged_df["element_type"].map(POSITION_MAP)
                merged_df["player_name"] = merged_df["web_name"] + " <span class='pl-team'>(" + merged_df["team_name"] + ")</span>"
                merged_df["hover_name"] = merged_df["web_name"] + " (" + merged_df["team_name"] + ")"
            else:
                merged_df = pd.DataFrame(columns=["entry_name", "element_type", "index", "player_name", "hover_name"])

            manager_stats = {}
            if display_picks == current_total_picks and current_total_picks > 0:
                report_df = display_picks_df.sort_values("index").copy()
                report_df["choice_time_dt"] = pd.to_datetime(report_df["choice_time"])
                report_df["time_taken"] = report_df["choice_time_dt"].diff().dt.total_seconds()
                
                if draft_start_dt:
                    api_start_time = pd.to_datetime(draft_start_dt)
                    first_pick_duration = (report_df["choice_time_dt"].iloc[0] - api_start_time).total_seconds()
                    if first_pick_duration > 90 or first_pick_duration < 0:
                        first_pick_duration = 60
                    report_df.iloc[0, report_df.columns.get_loc('time_taken')] = first_pick_duration
                else:
                    report_df["time_taken"] = report_df["time_taken"].fillna(60) 

                prices_df = fetch_main_game_prices()
                if not prices_df.empty:
                    report_df = report_df.merge(prices_df, left_on="element", right_on="id", how="left")
                else:
                    report_df["cost_mil"] = 0.0 

                raw_stats = {}
                for m in manager_order:
                    mgr_data = report_df[report_df["entry_name"] == m]
                    raw_stats[m] = {
                        "total_time": mgr_data["time_taken"].sum(),
                        "total_value": mgr_data["cost_mil"].sum(),
                        "auto": mgr_data["was_auto"].sum()
                    }

                valid_times = [s["total_time"] for s in raw_stats.values() if s["total_time"] > 0]
                auto_counts = [s["auto"] for s in raw_stats.values()]
                valid_values_sorted = sorted([s["total_value"] for s in raw_stats.values() if s["total_value"] > 0], reverse=True)
                
                max_time = max(valid_times) if valid_times else -1
                max_auto = max(auto_counts) if auto_counts else -1

                for m in manager_order:
                    t = raw_stats[m]["total_time"]
                    v = raw_stats[m]["total_value"]
                    a = raw_stats[m]["auto"]

                    time_formatted = format_time(t)
                    auto_formatted = str(int(a))

                    if t > 0 and t == max_time:
                        time_formatted = f'<span class="time-slow" title="Slowest Drafter...">{time_formatted}</span>'
                    
                    if a > 0 and a == max_auto:
                        auto_formatted = f'<span class="auto-high" title="Most Autopicks!">{auto_formatted}</span>'
                        
                    val_class = ""
                    if v > 0:
                        rank = valid_values_sorted.index(v) + 1
                        if rank == 1:
                            rank_indicator = "🥇"
                            val_class = " squad-value-1st"
                        elif rank == len(valid_values_sorted) and len(valid_values_sorted) > 3:
                            rank_indicator = "🥄" 
                        else:
                            rank_indicator = ""
                            
                        if rank_indicator:
                            val_formatted = f"£{v:.1f}m <span class='rank-badge'>{rank_indicator}</span>"
                        else:
                            val_formatted = f"£{v:.1f}m"
                    else:
                        val_formatted = "N/A"

                    manager_stats[m] = {
                        "value_html": val_formatted,
                        "val_class": val_class,
                        "time_html": time_formatted,
                        "auto_html": auto_formatted
                    }

            if not merged_df.empty:
                merged_df = merged_df.sort_values(["element_type", "index"])

            # BUILD HTML
            html_out = '<div class="draft-board-wrapper">'
            html_out += '<div class="draft-container">'

            for m in manager_order:
                is_curr_picker = (m == curr_picking_mgr_entry)
                is_next_picker = (m == next_picking_mgr_entry)

                html_out += '<div class="manager-col">'
                
                html_out += '<div class="picker-status-container">'
                if is_curr_picker:
                    html_out += '<div class="picker-status status-now">🟢 CURRENTLY PICKING</div>'
                elif is_next_picker:
                    html_out += '<div class="picker-status status-next">⏳ PICKING NEXT</div>'
                html_out += '</div>'
                
                mgr_name_display = manager_names.get(m, "Unknown")
                is_champ = (m.lower() in prev_champs_list) or (mgr_name_display.lower() in prev_champs_list)
                champ_star = " ⭐" if is_champ else ""
                
                header_classes = "manager-header"
                if is_curr_picker:
                    header_classes += " header-picking-now"
                elif is_next_picker:
                    header_classes += " header-picking-next"

                html_out += f'<div class="{header_classes}" title="{mgr_name_display}">'
                html_out += f'<div class="manager-title-wrap">{mgr_name_display}{champ_star}</div>'
                html_out += f'<span class="team-name" title="{m}">{m}</span>'
                
                if m in manager_stats:
                    stats = manager_stats[m]
                    html_out += f'<div class="squad-value{stats["val_class"]}" title="Total Squad Value">{stats["value_html"]}</div>'
                    html_out += '</div>' 
                    
                    html_out += '<div class="manager-stats-top">'
                    html_out += f'<span title="Total Picking Time">⏱️ {stats["time_html"]}</span>'
                    html_out += f'<span title="Number of Autopicks">🤖 {stats["auto_html"]}</span>'
                    html_out += '</div>'
                else:
                    html_out += '</div>' 
                
                for pos_id in [1, 2, 3, 4]:
                    pos_css_class = POS_CLASS_MAP[pos_id]
                    
                    if not merged_df.empty:
                        manager_pos_picks = merged_df[(merged_df["entry_name"] == m) & (merged_df["element_type"] == pos_id)]
                        picks_formatted = manager_pos_picks["player_name"].tolist()
                        picks_hover = manager_pos_picks["hover_name"].tolist()
                        pick_indices = manager_pos_picks["index"].tolist() 
                    else:
                        picks_formatted, picks_hover, pick_indices = [], [], []
                    
                    required_spots = ROSTER_LIMITS[pos_id]
                    
                    for i in range(required_spots):
                        if i < len(picks_formatted):
                            global_pick_idx = pick_indices[i]
                            is_round_one = global_pick_idx <= len(manager_order) 
                            is_last_picked = (global_pick_idx == display_picks)
                            
                            card_classes = f"player-card {pos_css_class}"
                            if is_round_one:
                                card_classes += " card-round-1"
                            if is_last_picked:
                                card_classes += " card-last-picked"
                                
                            html_out += f'<div class="{card_classes}" title="{picks_hover[i]} (Pick #{global_pick_idx})">{picks_formatted[i]}</div>'
                        else:
                            html_out += '<div class="empty-card">-</div>'
                    
                    if pos_id < 4:
                        html_out += '<div class="pos-divider"></div>'
                            
                html_out += '</div>' 
            html_out += '</div></div>'
            
            st.session_state.board_html = html_out
            st.session_state.picks_made = current_picks_made
            st.session_state.last_rendered_picks = display_picks

        draw_board_ui(display_picks, start_str, end_str, dur_str)
        
        if st.session_state.is_playing:
            time.sleep(0.8)
            st.rerun()

    render_live_draft_board()