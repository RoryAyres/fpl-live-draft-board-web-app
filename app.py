import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timezone, timedelta

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Live FPL Draft Board", layout="wide", page_icon="⚽")

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

st.title("⚽ Live FPL Draft Board")

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

    # --- RENDER TOP METRICS ---
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Picks Made", f"{picks_made} / {total_picks}")
    
    with col2:
        if picks_made == total_picks:
            st.success("✅ Draft Complete!")
        else:
            st.info("🚧 Draft In Progress")
            
    with col3:
        now_bst = datetime.now(timezone.utc) + timedelta(hours=1)
        st.metric("Last Synced", now_bst.strftime("%H:%M:%S BST"))

    progress_val = min(picks_made / total_picks, 1.0) if total_picks > 0 else 0.0
    st.progress(progress_val)

    # --- DATA PROCESSING FOR BOARD ---
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

    column_headers = [f"{manager_names[m]}\n({m})" for m in manager_order]
    merged_df = merged_df.sort_values(["element_type", "index"])
    board_data = []

    for pos_id in [1, 2, 3, 4]:
        pos_name = POSITION_MAP[pos_id]
        board_data.append({header: f"— {pos_name.upper()} —" for header in manager_order})
        
        grouped_pos = merged_df[merged_df["element_type"] == pos_id].groupby("entry_name")["player_name"].apply(list).to_dict()
        max_roster_spots = max([len(grouped_pos.get(m, [])) for m in manager_order], default=0)
        
        for i in range(max_roster_spots):
            row_dict = {}
            for m in manager_order:
                picks = grouped_pos.get(m, [])
                row_dict[m] = picks[i] if i < len(picks) else ""
            board_data.append(row_dict)
            
        board_data.append({header: "" for header in manager_order})

    display_df = pd.DataFrame(board_data)
    display_df.columns = column_headers
    
    st.dataframe(display_df, use_container_width=True, hide_index=True, height=650)

# --- INITIALIZE ---
render_live_draft_board()