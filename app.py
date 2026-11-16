"""Comeback: are you still on track for UPSC Prelims after missing days?

Run:  streamlit run app.py
Setup and deployment: docs/tech.md
"""

import logging

import streamlit as st

from comeback import ui

st.set_page_config(page_title="Comeback", page_icon=":material/restart_alt:", layout="centered")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
ui.style()
ui.refresh()          # every run reads fresh data once; pages share it

try:
    store = ui.store()
except RuntimeError as e:
    st.error(f"The app isn't set up yet: {e}")
    st.stop()

if not store.signed_in:
    # No sign-up: every visitor gets a private guest session with a sample month
    # already loaded, and lands straight on Today.
    with st.spinner("Opening Comeback..."):
        ok, _ = ui.call(ui.start_with_sample)
    if not ok:
        if st.button("Try again"):
            st.rerun()
        st.stop()

if "profile" not in st.session_state:
    ok, prof = ui.call(store.my_profile)
    if not ok:
        if st.button("Try again"):
            st.rerun()
        st.stop()
    st.session_state.profile = prof

if st.session_state.profile is None:
    st.navigation([st.Page("app_pages/setup.py", title="Set up", url_path="setup", default=True)],
                  position="hidden").run()
    st.stop()

st.navigation([
    st.Page("app_pages/today.py", title="Today", icon=":material/today:", url_path="today", default=True),
    st.Page("app_pages/pace.py", title="On track?", icon=":material/speed:", url_path="pace"),
    st.Page("app_pages/subjects.py", title="Subjects", icon=":material/menu_book:", url_path="subjects"),
    st.Page("app_pages/progress.py", title="Progress", icon=":material/insights:", url_path="progress"),
    st.Page("app_pages/settings.py", title="Settings", icon=":material/settings:", url_path="settings"),
], position="top").run()
