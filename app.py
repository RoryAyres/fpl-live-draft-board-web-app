import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timezone, timedelta

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Live FPL Draft Board", layout="wide", page_icon="⚽", initial_sidebar_state="collapsed")

# --- CUSTOM CSS FOR "ZOOM BROADCAST" UI ---
st.markdown("""
    <style>
    /* 1. REMOVE PADDING BUT KEEP THE SIDEBAR TOGGLE VISIBLE */
    .block-container {
        padding-top: 2.5rem !important; 
        padding-bottom: 0rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        max-width: 100% !important;
    }
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;}
    
    /* 2. COMPACT TOP METRICS & TITLE */
    [data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.75rem !important;
    }
    h3 {
        margin-top: -15px !important;
        padding-bottom: 0px !important;
    }
    
    /* 3. RESPONSIVE, SHRINK-TO-FIT GRID */
    .draft-board-wrapper {
        width: 100%;
        overflow: hidden; 
    }
    .draft-container {
        display: flex;
        gap: 4px; 
        width: 100%;
        /* Dynamically calculates height: Full Screen MINUS headers and bottom button space */
        height: calc(100vh - 180px); 
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
    
    /* 4. STRETCHY PLAYER CARDS */
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
        df = pd.DataFrame(data["elements"])[["id", "web_name", "element_type"]]
        return df
    except Exception as e:
        st.error(f"⚠️ Error fetching base player data: {e}")
        return pd.DataFrame()

# --- UI LAYOUT & SIDEBAR ---
st.sidebar.header("⚙️ Draft Settings")
league_id = st.sidebar.number_input("League ID", min_value=1, value=217, step=1)
refresh_seconds = st.sidebar.slider("Refresh Interval (Seconds)", min_value=3, max_value=30, value=5)

POSITION_MAP = {1: "Goalkeepers", 2: "Defenders", 3: "Midfielders", 4: "Forwards"}

# --- AUTO-REFRESHING LIVE COMPONENT ---
@st.fragment(run_every=timedelta(seconds=refresh_seconds))
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
        st.info("🟡 Draft has not started yet. Waiting for the first pick...")
        return

    choices_df = pd.DataFrame(choices)[["entry_name", "player_first_name", "player_last_name", "element", "index", "choice_time"]]

    if choices_df["element"].isna().all():
        st.info("🟡 Draft room is open! Waiting for the first pick to be made...")
        return

    made_picks_df = choices_df[choices_df["element"].notna()].copy()
    picks_made = len(made_picks_df)
    total_picks = len(choices_df)

    # --- RENDER TOP METRICS & TITLE IN ONE ROW ---
    # Squeezing the title next to the metrics to save vertical real estate
    col_title, col1, col2, col3 = st.columns([1.5, 1, 1.5, 1]) 
    
    with col_title:
        st.markdown("### ⚽ Live FPL Draft") 

    with col1:
        st.metric("Total Picks", f"{picks_made} / {total_picks}")
    
    with col2:
        if picks_made == total_picks:
            st.success("✅ Draft Complete!")
        else:
            st.write("🚧 **Draft In Progress**")
            progress_val = min(picks_made / total_picks, 1.0) if total_picks > 0 else 0.0
            st.progress(progress_val)
            
    with col3:
        now_bst = datetime.now(timezone.utc) + timedelta(hours=1)
        st.metric("Last Synced", now_bst.strftime("%H:%M:%S BST"))

    st.markdown("<hr style='margin: 0rem 0 0.5rem 0'>", unsafe_allow_html=True) 

    # --- DATA PROCESSING ---
    made_picks_df["player_display"] = made_picks_df["player_first_name"] + " " + made_picks_df["player_last_name"].str[0]
    merged_df = made_picks_df.merge(players_df, left_on="element", right_on="id", how="left")
    merged_df["position"] = merged_df["element_type"].map(POSITION_MAP)
    merged_df["player_name"] = merged_df["web_name"]

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

    # --- BUILD HTML DRAFT BOARD ---
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
            html_out += f'<div class="pos-title">{pos_name}</div>'
            
            picks = merged_df[(merged_df["entry_name"] == m) & (merged_df["element_type"] == pos_id)]["player_name"].tolist()
            max_roster_spots = max([len(merged_df[(merged_df["entry_name"] == mgr) & (merged_df["element_type"] == pos_id)]) for mgr in manager_order], default=0)
            
            for i in range(max_roster_spots):
                if i < len(picks):
                    html_out += f'<div class="player-card" title="{picks[i]}">{picks[i]}</div>'
                else:
                    html_out += '<div class="empty-card">-</div>'
                    
        html_out += '</div>' 

    html_out += '</div></div>'

    st.markdown(html_out, unsafe_allow_html=True)

# --- INITIALIZE ---
render_live_draft_board()