import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timezone, timedelta

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Live FPL Draft Board", layout="wide", page_icon="⚽", initial_sidebar_state="collapsed")

# --- INITIALIZE SESSION STATE ---
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

# --- CUSTOM CSS FOR "ZOOM BROADCAST" UI WITH RESPONSIVE TEXT SCALING ---
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
    
    .draft-board-wrapper { width: 100%; overflow: hidden; margin-bottom: 20px;}
    .draft-container {
        display: flex; gap: 4px; width: 100%; height: calc(100vh - 200px); 
    }
    .manager-col {
        flex: 1 1 0; display: flex; flex-direction: column; 
        background-color: var(--secondary-background-color);
        border: 1px solid var(--border-color); border-radius: 4px; padding: 4px; overflow: hidden;
    }
    
    /* SCALABLE HEADER & TEAM NAMES */
    .manager-header {
        flex-shrink: 0; text-align: center; font-weight: 700; 
        font-size: clamp(0.8rem, 1.1vw, 1.2rem);
        margin-bottom: 4px; padding-bottom: 4px; border-bottom: 2px solid #00ff87; 
    }
    .manager-title-wrap {
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .team-name {
        font-size: clamp(0.7rem, 0.9vw, 1rem); 
        font-weight: 400; opacity: 0.7; display: block;
        margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    
    /* SCALABLE STATS UNDERNEATH TEAM NAMES */
    .manager-stats-top {
        display: flex; justify-content: space-evenly; gap: 4px;
        font-size: clamp(0.6rem, 0.75vw, 0.85rem);
        font-weight: normal; opacity: 0.9; margin-top: 6px; padding-top: 4px; 
        border-bottom: 4px solid transparent; /* adds a little spacing below stats since pos titles are gone */
        border-top: 1px dotted var(--border-color);
    }
    .manager-stats-top span {
        white-space: nowrap; 
    }
    
    /* SQUAD VALUE WITH RANKING */
    .manager-stats-bottom {
        flex-shrink: 0; text-align: center; font-weight: 700;
        font-size: clamp(0.75rem, 1vw, 1.1rem);
        margin-top: auto; padding-top: 4px; border-top: 2px solid #00ff87;
    }
    
    .rank-badge {
        font-size: clamp(0.6rem, 0.8vw, 0.9rem);
        opacity: 0.9;
        font-weight: 500;
        margin-left: 2px;
    }
    
    .time-slow { color: #ef4444; font-weight: 800; } /* Red */
    .auto-high { color: #ef4444; font-weight: 800; } /* Red */
    
    /* SCALABLE PLAYER CARDS */
    .player-card, .empty-card {
        flex: 1 1 0; display: flex; align-items: center; 
        background-color: var(--background-color); border: 1px solid var(--border-color);
        padding: 0 4px 0 8px; margin-bottom: 3px; border-radius: 3px;
        font-size: clamp(0.75rem, 0.95vw, 1.1rem);
        font-weight: 500; white-space: nowrap; overflow: hidden;
        text-overflow: ellipsis; box-shadow: 0 1px 2px rgba(0,0,0,0.05); position: relative; 
    }
    
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

def get_ordinal(n):
    if 11 <= (n % 100) <= 13:
        return f"{n}th"
    return f"{n}" + ["th", "st", "nd", "rd", "th"][min(n % 10, 4)]

# --- UI LAYOUT & SIDEBAR ---
st.sidebar.header("⚙️ Draft Settings")
league_id = st.sidebar.number_input("League ID", min_value=1, value=217, step=1)
refresh_seconds = st.sidebar.slider("Refresh Interval (Seconds)", min_value=3, max_value=30, value=5)

st.sidebar.markdown("---")
st.sidebar.toggle("⏸️ Pause Live Updates", key="pause_updates")

if st.sidebar.button("🔄 Manual Refresh", width="stretch"):
    st.session_state.picks_made = -1 
    st.session_state.draft_ended = False 
    st.cache_data.clear() 

POSITION_MAP = {1: "Goalkeepers", 2: "Defenders", 3: "Midfielders", 4: "Forwards"}
POS_CLASS_MAP = {1: "card-gk", 2: "card-def", 3: "card-mid", 4: "card-fwd"}
ROSTER_LIMITS = {1: 2, 2: 5, 3: 5, 4: 3} 

league_name, draft_start_dt = fetch_league_details(league_id)

is_paused = st.session_state.pause_updates or st.session_state.draft_ended
refresh_timer = None if is_paused else timedelta(seconds=refresh_seconds)

# --- AUTO-REFRESHING LIVE COMPONENT ---
@st.fragment(run_every=refresh_timer)
def render_live_draft_board():
        
    def draw_board_ui():
        col_title, col1, col2, col3 = st.columns([1.5, 1, 1.5, 1]) 
        with col_title:
            st.markdown(f"### ⚽ {league_name}") 

        with col1:
            st.metric("Total Picks", f"{max(0, st.session_state.picks_made)} / {st.session_state.total_picks}")
        
        with col2:
            if st.session_state.draft_ended:
                st.success("✅ Draft Complete!")
            elif st.session_state.pause_updates:
                st.warning("⏸️ Updates Paused")
            elif st.session_state.total_picks > 0:
                st.write("🚧 **Draft In Progress**")
                st.progress(st.session_state.picks_made / st.session_state.total_picks)
            else:
                st.info("🟡 Waiting for draft to begin...")
                
        with col3:
            now_bst = datetime.now(timezone.utc) + timedelta(hours=1)
            st.metric("Last Synced", now_bst.strftime("%H:%M:%S BST"))

        st.markdown("<hr style='margin: 0rem 0 0.5rem 0'>", unsafe_allow_html=True) 
        
        if st.session_state.board_html:
            st.markdown(st.session_state.board_html, unsafe_allow_html=True)

    players_df = fetch_players_data()
    if players_df.empty:
        st.toast("⚠️ Base player data unavailable. Retrying...")
        draw_board_ui()
        return

    choices_url = f"https://draft.premierleague.com/api/draft/{league_id}/choices"
    try:
        response = requests.get(choices_url, timeout=10)
        response.raise_for_status()
        choices_data = response.json()
    except Exception:
        st.toast("⚠️ FPL API blip. Keeping previous board on screen while retrying...")
        draw_board_ui()
        return

    if isinstance(choices_data, dict) and choices_data.get("detail") == "No League matches the given query.":
        st.error(f"❌ Invalid League ID: {league_id}. Please check the sidebar.")
        return

    choices = choices_data.get("choices", [])
    if not choices or pd.DataFrame(choices)["element"].isna().all():
        st.info("🟡 Draft room is open! Waiting for the first pick to be made...")
        return

    choices_df_raw = pd.DataFrame(choices)
    if "was_auto" not in choices_df_raw.columns:
        choices_df_raw["was_auto"] = False
        
    choices_df = choices_df_raw[["entry_name", "player_first_name", "player_last_name", "element", "index", "choice_time", "was_auto"]]
    made_picks_df = choices_df[choices_df["element"].notna()].copy()
    
    current_picks_made = len(made_picks_df)
    current_total_picks = len(choices_df)

    if current_total_picks > 0 and current_picks_made == current_total_picks:
        if not st.session_state.draft_ended:
            st.session_state.draft_ended = True
            st.rerun()

    if current_picks_made != st.session_state.picks_made or st.session_state.board_html == "":
        
        made_picks_df["player_display"] = made_picks_df["player_first_name"] + " " + made_picks_df["player_last_name"].str[0]
        merged_df = made_picks_df.merge(players_df, left_on="element", right_on="id", how="left")
        merged_df["position"] = merged_df["element_type"].map(POSITION_MAP)
        
        merged_df["player_name"] = merged_df["web_name"] + " <span class='pl-team'>(" + merged_df["team_name"] + ")</span>"
        merged_df["hover_name"] = merged_df["web_name"] + " (" + merged_df["team_name"] + ")"

        first_picks = merged_df.groupby("entry_name")["index"].min().sort_values()
        manager_order = first_picks.index.tolist()
        
        manager_names = (
            made_picks_df.drop_duplicates("entry_name")
            .set_index("entry_name")["player_display"]
            .reindex(manager_order)
            .fillna("Unknown")
            .to_dict()
        )
        
        manager_stats = {}
        if current_picks_made == current_total_picks and current_total_picks > 0:
            report_df = made_picks_df.sort_values("index").copy()
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

            # Pre-calculate to find min and max for highlighting
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
            
            # Sort valid values descending to determine rank
            valid_values_sorted = sorted([s["total_value"] for s in raw_stats.values() if s["total_value"] > 0], reverse=True)
            
            max_time = max(valid_times) if valid_times else -1
            max_auto = max(auto_counts) if auto_counts else -1

            for m in manager_order:
                t = raw_stats[m]["total_time"]
                v = raw_stats[m]["total_value"]
                a = raw_stats[m]["auto"]

                time_formatted = format_time(t)
                auto_formatted = str(int(a))

                # Highlight slowest time
                if t > 0 and t == max_time:
                    time_formatted = f'<span class="time-slow" title="Slowest Drafter...">{time_formatted}</span>'
                
                # Highlight most autopicks
                if a > 0 and a == max_auto:
                    auto_formatted = f'<span class="auto-high" title="Most Autopicks!">{auto_formatted}</span>'
                    
                # Rank squad values with Medals
                if v > 0:
                    rank = valid_values_sorted.index(v) + 1
                    if rank == 1:
                        rank_indicator = "🥇"
                    elif rank == 2:
                        rank_indicator = "🥈"
                    elif rank == 3:
                        rank_indicator = "🥉"
                    else:
                        rank_indicator = f"({get_ordinal(rank)})"
                        
                    val_formatted = f"£{v:.1f}m <span class='rank-badge'>{rank_indicator}</span>"
                else:
                    val_formatted = "N/A"

                manager_stats[m] = {
                    "value_html": val_formatted,
                    "time_html": time_formatted,
                    "auto_html": auto_formatted
                }

        merged_df = merged_df.sort_values(["element_type", "index"])

        # BUILD HTML
        html_out = '<div class="draft-board-wrapper"><div class="draft-container">'

        for m in manager_order:
            html_out += '<div class="manager-col">'
            html_out += f'<div class="manager-header" title="{manager_names[m]}">'
            html_out += f'<div class="manager-title-wrap">{manager_names[m]}</div>'
            html_out += f'<span class="team-name" title="{m}">{m}</span>'
            
            if m in manager_stats:
                stats = manager_stats[m]
                html_out += '<div class="manager-stats-top">'
                html_out += f'<span title="Total Picking Time">⏱️ {stats["time_html"]}</span>'
                html_out += f'<span title="Number of Autopicks">🤖 {stats["auto_html"]}</span>'
                html_out += '</div>'

            html_out += '</div>'
            
            for pos_id in [1, 2, 3, 4]:
                pos_css_class = POS_CLASS_MAP[pos_id]
                
                manager_pos_picks = merged_df[(merged_df["entry_name"] == m) & (merged_df["element_type"] == pos_id)]
                picks_formatted = manager_pos_picks["player_name"].tolist()
                picks_hover = manager_pos_picks["hover_name"].tolist()
                
                required_spots = ROSTER_LIMITS[pos_id]
                
                for i in range(required_spots):
                    if i < len(picks_formatted):
                        html_out += f'<div class="player-card {pos_css_class}" title="{picks_hover[i]}">{picks_formatted[i]}</div>'
                    else:
                        html_out += '<div class="empty-card">-</div>'
            
            if m in manager_stats:
                stats = manager_stats[m]
                html_out += f'<div class="manager-stats-bottom" title="Total Squad Value">💷 {stats["value_html"]}</div>'
                        
            html_out += '</div>' 
        html_out += '</div></div>'
        
        st.session_state.board_html = html_out
        st.session_state.picks_made = current_picks_made
        st.session_state.total_picks = current_total_picks

    draw_board_ui()

# --- INITIALIZE ---
render_live_draft_board()