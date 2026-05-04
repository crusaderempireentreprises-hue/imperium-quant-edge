if st.session_state.continuous:
    now = time.time()
    if now - st.session_state.last_cycle_time >= 10:
        execute_cycle()
        st.session_state.last_cycle_time = now

    st.rerun()