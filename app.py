if is_pre_draft:
            st.markdown(f"<h2 style='text-align: center; margin-top: 1rem; margin-bottom: 0.5rem;'>🏆 Welcome to the {league_name} Draft Room</h2>", unsafe_allow_html=True)

            now_utc = datetime.now(timezone.utc)
            if draft_start_dt:
                draft_time = pd.to_datetime(draft_start_dt)
                if draft_time > now_utc:
                    time_diff = draft_time - now_utc
                    days = time_diff.days
                    seconds = time_diff.seconds
                    hours = seconds // 3600
                    minutes = (seconds % 3600) // 60
                    
                    st.markdown(f"<p style='text-align: center; opacity: 0.8; margin-bottom: 1.5rem;'>Draft is scheduled for: <strong>{draft_time.strftime('%d %b %Y %H:%M')} (UTC)</strong></p>", unsafe_allow_html=True)
                    
                    # --- CUSTOM COUNTDOWN WIDGET ---
                    st.markdown("### ⏲️ Live Countdown")
                    col_d, col_h, col_m, _ = st.columns([1, 1, 1, 3])
                    col_d.metric("Days", days)
                    col_h.metric("Hours", hours)
                    col_m.metric("Minutes", minutes)
                    st.markdown("<hr style='margin: 1.5rem 0;'>", unsafe_allow_html=True)
                else:
                    st.info("🟡 Draft room is open! Waiting for the first pick to be made...")
                    st.markdown("<hr style='margin: 1.5rem 0;'>", unsafe_allow_html=True)
            
            # --- CUSTOM HTML MANAGER CARDS ---
            if league_entries:
                st.markdown("<h3 style='text-align: center; margin-bottom: 1rem;'>👥 Participating Teams</h3>", unsafe_allow_html=True)
                
                html_predraft = '<div style="display: flex; flex-wrap: wrap; gap: 12px; justify-content: center; margin-bottom: 2rem;">'
                for entry in league_entries:
                    mgr_name = f"{entry.get('player_first_name', '')} {entry.get('player_last_name', '')}".strip()
                    team_name = entry.get('entry_name', 'Unknown Team')
                    
                    # Reusing existing CSS classes for visual parity
                    html_predraft += f'''
                    <div class="manager-col" style="min-width: 160px; flex: 0 1 200px; padding: 12px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                        <div class="manager-header" style="border-color: var(--border-color); background-color: var(--background-color);">
                            <div class="manager-title-wrap" style="font-size: 1.1rem;">{mgr_name}</div>
                        </div>
                        <span class="team-name" style="font-size: 0.9rem; margin-top: 8px; opacity: 1.0; font-weight: 500;">{team_name}</span>
                    </div>
                    '''
                html_predraft += '</div>'
                st.markdown(html_predraft, unsafe_allow_html=True)
            
            return