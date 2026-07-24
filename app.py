import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timezone, timedelta

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Live FPL Draft Board", layout="wide", page_icon="⚽", initial_sidebar_state="collapsed")

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
        transition: all 0.3s ease;
    }
    .manager-col.is-active {
        border: 1px solid #ff005a;
        background-color: rgba(255, 0, 90, 0.04);
    }
    .manager-col.is-next {
        border: 1px solid rgba(0, 170, 255, 0.4);
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
    .manager-header.is-active { border-bottom: 2px solid #ff005a; }
    .manager-header.is-next { border-bottom: 2px solid #00aaff; }
    
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
    
    .status-badge {
        display: block;
        font-size: 0.55rem;
        text-transform: uppercase;
        font-weight: 800;
        margin-top: 4px;
        letter-spacing: 0.5px;
    }
    .status-badge.active { 
        color: #ff005a; 
        animation: pulse-text 1.5s infinite; 
    }
    .status-badge.next { color: #00aaff; }
    
    @keyframes pulse-text {
        0% { opacity: 1; }
        50% { opacity: 0.4; }
        100% { opacity: 1; }
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
        padding: 0 4px; 
        margin-bottom: 3px;
        border-radius: 3px;
        font-size: 0.75rem; 
        font-weight: 500;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    .player-card.latest-pick {
        border: 1px solid #00ff87;
        background-color: rgba(0, 255, 135, 0.15);
        font-weight: 700;
    }
    
    .empty-card {
        background-color: transparent;
        border: 1px dashed var(--border-color);
        justify-content: center;
        opacity: 0.3;
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
        teams_dict = {t["id"]: t["short_name"] for t in data["teams"]}
        df = pd.DataFrame(data["elements"])[["id", "web_name", "element_type", "team"]]
        df["player_name"] = df["web_name"] + " (" + df["team"].map(teams_dict) + ")"
        return df[["id", "player_name", "element_type"]]
    except Exception as e:
        st.error(f"⚠️ Error fetching base player data: {e}")
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
pause_updates = st.sidebar.toggle("⏸️ Pause Live Updates", value=False)

POSITION_MAP = {1: "Goalkeepers", 2: "Defenders", 3: "Midfielders", 4: "Forwards"}
ROSTER_LIMITS = {1: 2, 2: 5, 3: 5, 4: 3} 

league_name = fetch_league_name(league_id)
refresh_timer = None if pause_updates else timedelta(seconds=refresh_seconds)

# --- AUTO-REFRESHING LIVE COMPONENT ---
@st.fragment(run_every=refresh_timer)
def render_live_draft_board():
    players_df = fetch_players_data()
    if players_df.empty:
        return

    choices_url = f"https://draft.premierleague.com/api/draft/{league_id}/choices"
    
    try:
        response = requests.get(choices_url, timeout=10)
        choices_data = response.json()
    except Exception as e:
        st.error(f"⚠️ Failed to connect to FPL API: {e}")
        return

    if isinstance(choices_data, dict) and choices_data.get("detail") == "No League matches the given query.":
        st.error(f"❌ Invalid League ID: {league_id}. Please check the sidebar.")
        return

    choices = choices_data.get("choices", [])
    if not choices:
        st.info("🟡 Draft has not started yet. Waiting for room creation...")
        return

    choices_df = pd.DataFrame(choices)[["entry_name", "player_first_name", "player_last_name", "element", "index", "choice_time"]]
    choices_df["player_display"] = choices_df["player_first_name"] + " " + choices_df["player_last_name"].str[0]

    num_managers = choices_df["entry_name"].nunique()
    manager_order = choices_df.sort_values("index").head(num_managers)["entry_name"].tolist()
    manager_names = choices_df.drop_duplicates("entry_name").set_index("entry_name")["player_display"].to_dict()

    made_picks_df = choices_df[choices_df["element"].notna()].copy()
    picks_made = len(made_picks_df)
    total_picks = len(choices_df)

    on_the_clock_manager = None
    next_up_manager = None

    if picks_made < total_picks and num_managers > 0:
        def get_manager_for_pick(pick_index):
            round_num = pick_index // num_managers
            pick_in_round = pick_index % num_managers
            idx = pick_in_round if round_num % 2 == 0 else (num_managers - 1 - pick_in_round)
            return manager_order[idx]

        on_the_clock_manager = get_manager_for_pick(picks_made)
        if picks_made + 1 < total_picks:
            next_up_manager = get_manager_for_pick(picks_made + 1)

    latest_pick_element = None
    if picks_made > 0:
        latest_pick_element = made_picks_df.sort_values("index").iloc[-1]["element"]

    # --- RENDER TOP METRICS & TITLE IN ONE ROW ---
    col_title, col1, col2, col3 = st.columns([1.5, 1, 1.5, 1]) 
    
    with col_title:
        st.markdown(f"### ⚽ {league_name}") 

    with col1:
        st.metric("Total Picks", f"{picks_made} / {total_picks}")
    
    with col2:
        if pause_updates:
            st.warning("⏸️ Updates Paused")
        elif picks_made == total_picks:
            st.success("✅ Draft Complete!")
        else:
            st.write("🚧 **Draft In Progress**")
            progress_val = min(picks_made / total_picks, 1.0) if total_picks > 0 else 0.0
            st.progress(progress_val)
            
    with col3:
        now_bst = datetime.now(timezone.utc) + timedelta(hours=1)
        st.metric("Last Synced", now_bst.strftime("%H:%M:%S BST"))

    st.markdown("<hr style='margin: 0rem 0 0.5rem 0'>", unsafe_allow_html=True) 

    if not made_picks_df.empty:
        merged_df = made_picks_df.merge(players_df, left_on="element", right_on="id", how="left")
        merged_df["position"] = merged_df["element_type"].map(POSITION_MAP)
    else:
        merged_df = pd.DataFrame(columns=["entry_name", "element", "element_type", "player_name"])

    # --- BUILD HTML DRAFT BOARD ---
    html_out = '<div class="draft-board-wrapper"><div class="draft-container">'

    for m in manager_order:
        col_class = ""
        header_class = ""
        badge_html = ""
        
        if m == on_the_clock_manager:
            col_class = "is-active"
            header_class = "is-active"
            badge_html = '<span class="status-badge active">▶ On The Clock</span>'
        elif m == next_up_manager:
            col_class = "is-next"
            header_class = "is-next"
            badge_html = '<span class="status-badge next">Next Up</span>'

        html_out += f'''
        <div class="manager-col {col_class}">
            <div class="manager-header {header_class}" title="{manager_names[m]}">
                {manager_names[m]}
                <span class="team-name" title="{m}">{m}</span>
                {badge_html}
            </div>
        '''
        
        for pos_id in [1, 2, 3, 4]:
            pos_name = POSITION_MAP[pos_id]
            html_out += f'<div class="pos-title">{pos_name}</div>'
            
            picks_data = merged_df[(merged_df["entry_name"] == m) & (merged_df["element_type"] == pos_id)][["player_name", "element"]].to_dict('records')
            required_spots = ROSTER_LIMITS[pos_id]
            
            for i in range(required_spots):
                if i < len(picks_data):
                    p = picks_data[i]
                    p_name = p["player_name"]
                    is_latest = (p["element"] == latest_pick_element)
                    latest_class = " latest-pick" if is_latest else ""
                    html_out += f'<div class="player-card{latest_class}" title="{p_name}">{p_name}</div>'
                else:
                    html_out += '<div class="empty-card">-</div>'
                    
        html_out += '</div>'

    html_out += '</div></div>'

    st.markdown(html_out, unsafe_allow_html=True)

# --- INITIALIZE ---
render_live_draft_board()