import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timezone, timedelta

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Live FPL Draft Board", layout="wide", page_icon="⚽", initial_sidebar_state="collapsed")

# --- INITIALIZE SESSION STATE ---
if "picks_made" not in st.session_state:
    st.session_state.picks_made = 0
    st.session_state.total_picks = 0
    st.session_state.board_html = ""
if "pause_updates" not in st.session_state:
    st.session_state.pause_updates = False

# --- CUSTOM CSS FOR "ZOOM BROADCAST" UI ---
st.markdown("""
    <style>
    .block-container {
        padding-top: 3rem !important; 
        padding-bottom: 0rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        max-width: 100% !important;
    }
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;}
    
    [data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.75rem !important;
    }
    h3 {
        margin-top: 0px !important; 
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
    }
    
    .draft-board-wrapper {
        width: 100%;
        overflow: hidden; 
    }
    .draft-container {
        display: flex;
        gap: 4px; 
        width: 100%;
        height: calc(100vh - 200px); 
    }
    .manager-col {
        flex: 1 1 0; 
        display: flex;
        flex-direction: column; 
        background-color: var(--secondary-background-color);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        padding: 4px;
        overflow: hidden;
    }
    .manager-header {
        flex-shrink: 0; 
        text-align: center;
        font-weight: 700;
        font-size: 0.8rem;
        margin-bottom: 4px;
        padding-bottom: 4px;
        border-bottom: 2px solid #00ff87; 
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .team-name {
        font-size: 0.6rem;
        font-weight: 400;
        opacity: 0.7;
        display: block;
        margin-top: 2px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .pos-title {
        flex-shrink: 0;
        font-size: 0.55rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        opacity: 0.6;
        margin: 4px 0 2px 0;
        border-bottom: 1px solid var(--border-color);
        text-align: center;
    }
    
    .player-card, .empty-card {
        flex: 1 1 0; 
        display: flex;
        align-items: center; 
        background-color: var(--background-color);
        border: 1px solid var(--border-color);
        padding: 0 4px 0 8px; /* Slightly increased left padding for the inner indicator */
        margin-bottom: 3px;
        border-radius: 3px;
        font-size: 0.75rem; 
        font-weight: 500;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        position: relative; /* Required for the pseudo-element indicator */
    }
    
    /* SUBTLE & SHORTER POSITION COLOR CODING */
    .card-gk::before, .card-def::before, .card-mid::before, .card-fwd::before {
        content: "";
        position: absolute;
        left: 0;
        top: 20%;      /* Creates a gap at the top */
        bottom: 20%;   /* Creates a gap at the bottom */
        width: 3px;
        border-radius: 0 2px 2px 0;
        opacity: 0.55; /* Fades the color to make it softer */
    }
    .card-gk::before { background-color: #eab308; }  /* Yellow */
    .card-def::before { background-color: #3b82f6; } /* Blue */
    .card-mid::before { background-color: #22c55e; } /* Green */
    .card-fwd::before { background-color: #ef4444; } /* Red */
    
    .empty-card {
        background-color: transparent;
        border: 1px dashed var(--border-color);
        justify-content: center;
        opacity: 0.3;
        padding: 0 4px; /* Resets padding for empty boxes */
    }
    .pl-team {
        opacity: 0.5;
        font-size: 0.65rem;
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
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_league_name(league_id):
    league_details_url = f"https://draft.premierleague.com/api/league/{league_id}/details"
    try:
        response = requests.get(league_details_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("league", {}).get("name", f"League {league_id}")
    except Exception:
        return f"League {league_id}"

# --- UI LAYOUT & SIDEBAR ---
st.sidebar.header("⚙️ Draft Settings")
league_id = st.sidebar.number_input("League ID", min_value=1, value=217, step=1)
refresh_seconds = st.sidebar.slider("Refresh Interval (Seconds)", min_value=3, max_value=30, value=5)

st.sidebar.markdown("---")

st.sidebar.toggle("⏸️ Pause Live Updates", key="pause_updates")

if st.sidebar.button("🔄 Manual Refresh", use_container_width=True):
    st.session_state.picks_made = -1 
    st.cache_data.clear() 

POSITION_MAP = {1: "Goalkeepers", 2: "Defenders", 3: "Midfielders", 4: "Forwards"}
POS_CLASS_MAP = {1: "card-gk", 2: "card-def", 3: "card-mid", 4: "card-fwd"}
ROSTER_LIMITS = {1: 2, 2: 5, 3: 5, 4: 3} 

league_name = fetch_league_name(league_id)
refresh_timer = None if st.session_state.pause_updates else timedelta(seconds=refresh_seconds)

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
            if st.session_state.pause_updates:
                if st.session_state.total_picks > 0 and st.session_state.picks_made == st.session_state.total_picks:
                    st.success("✅ Draft Complete!")
                else:
                    st.warning("⏸️ Updates Paused")
            elif st.session_state.total_picks > 0 and st.session_state.picks_made == st.session_state.total_picks:
                st.success("✅ Draft Complete!")
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
    except Exception as e:
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

    choices_df = pd.DataFrame(choices)[["entry_name", "player_first_name", "player_last_name", "element", "index", "choice_time"]]
    made_picks_df = choices_df[choices_df["element"].notna()].copy()
    
    current_picks_made = len(made_picks_df)
    current_total_picks = len(choices_df)

    if current_total_picks > 0 and current_picks_made == current_total_picks:
        if not st.session_state.pause_updates:
            st.session_state.pause_updates = True
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
        
        merged_df = merged_df.sort_values(["element_type", "index"])

        html_out = '<div class="draft-board-wrapper"><div class="draft-container">'

        for m in manager_order:
            html_out += f'''
            <div class="manager-col">
                <div class="manager-header" title="{manager_names[m]}">
                    {manager_names[m]}
                    <span class="team-name" title="{m}">{m}</span>
                </div>
            '''
            
            for pos_id in [1, 2, 3, 4]:
                pos_name = POSITION_MAP[pos_id]
                pos_css_class = POS_CLASS_MAP[pos_id]
                html_out += f'<div class="pos-title">{pos_name}</div>'
                
                manager_pos_picks = merged_df[(merged_df["entry_name"] == m) & (merged_df["element_type"] == pos_id)]
                picks_formatted = manager_pos_picks["player_name"].tolist()
                picks_hover = manager_pos_picks["hover_name"].tolist()
                
                required_spots = ROSTER_LIMITS[pos_id]
                
                for i in range(required_spots):
                    if i < len(picks_formatted):
                        html_out += f'<div class="player-card {pos_css_class}" title="{picks_hover[i]}">{picks_formatted[i]}</div>'
                    else:
                        html_out += '<div class="empty-card">-</div>'
                        
            html_out += '</div>' 

        html_out += '</div></div>'
        
        st.session_state.board_html = html_out
        st.session_state.picks_made = current_picks_made
        st.session_state.total_picks = current_total_picks

    draw_board_ui()

# --- INITIALIZE ---
render_live_draft_board()