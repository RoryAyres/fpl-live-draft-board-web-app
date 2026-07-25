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
        display: flex; justify-content: space-between; 
        font-size: clamp(0.65rem, 0.8vw, 0.9rem);
        font-weight: normal; opacity: 0.8; margin-top: 6px; padding-top: 4px; 
        border-top: 1px dotted var(--border-color);
    }
    .manager-stats-bottom {
        flex-shrink: 0; text-align: center; font-weight: 700;
        font-size: clamp(0.75rem, 1vw, 1.1rem);
        margin-top: auto; padding-top: 4px; border-top: 2px solid #00ff87;
    }
    
    /* SCALABLE POSITION TITLES */
    .pos-title {
        flex-shrink: 0; text-transform: uppercase; letter-spacing: 0.5px;
        font-size: clamp(0.55rem, 0.7vw, 0.8rem);
        opacity: 0.6; margin: 4px 0 2px 0; border-bottom: 1px solid var(--border-color); text-align: center;
    }
    
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
    
    /* SCALABLE PREMIER LEAGUE TEAM ABBREVIATIONS */
    .pl-team { 
        opacity: 0.5; 
        font-size: clamp(0.65rem, 0.8vw, 0.9rem); 
        margin-left: 4px; 
    }
    </style>
""", unsafe_allow_html=True)