from datetime import timedelta

import streamlit as st

from comeback import ui

ui.show_flash()
st.title("Comeback")
st.markdown("##### Missed a few days of UPSC prep? Find out if you'll still finish the syllabus before Prelims, and what to change if you won't.")

left, right = st.columns([1.15, 1], gap="large")

with left:
    st.markdown("""
When you miss days, your study plan resumes where you stopped, but your exam
date doesn't move. Comeback follows SuperKalam's GS learning path (18 subjects,
259 units) and tells you:

- **Whether you're on track** to finish before your revision months start
- **What each week needs to look like now**, within a pace you can actually keep
- **What to park if it won't fit**: Mains-only subjects wait until after Prelims, then anything you've marked can-skim
- **How to handle missed news**: one short catch-up read, not a pile of old papers

Every suggestion comes with a reason, and you decide.
""")

with right:
    st.markdown("**No sign-up needed.**")
    if st.button("Try it with a sample month", type="primary", use_container_width=True,
                 help="A student who studied for three weeks, then missed the last 5 days. Prelims is 150 days away."):
        store = ui.store()
        ok, _ = ui.call(store.start)
        if ok:
            today = ui.today_ist()
            ok, _ = ui.call(store.save_profile, "", (today + timedelta(days=150)).isoformat(), 30, 1.5, 6, 0.3)
            if ok:
                ok, _ = ui.call(store.load_sample)
            if ok:
                st.session_state.profile = store.my_profile()
                ui.flash("success", "Loaded a sample month: three weeks of steady study, then the last 5 days missed.")
            st.rerun()
    if st.button("Start with my own progress", use_container_width=True):
        ok, _ = ui.call(ui.store().start)
        if ok:
            st.rerun()

st.caption("Your data is private to you and kept only while this tab is open. "
           "Closing or refreshing the tab starts you fresh.")
