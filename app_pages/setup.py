from datetime import timedelta

import streamlit as st

from comeback import ui

st.title("A few quick questions")
st.write("These decide what \"on track\" means for you. You can change any of them later in Settings.")

today = ui.today_ist()
with st.form("setup"):
    name = st.text_input("What should I call you?", max_chars=60)
    exam = st.date_input("Your Prelims date", value=today + timedelta(days=200), min_value=today,
                         max_value=today + timedelta(days=1100), format="DD/MM/YYYY")
    per_day = st.slider("On a normal study day, how many SuperKalam GS units do you finish?", 0.5, 6.0, 1.5, 0.5,
                        help="Be honest rather than ambitious. Plans built on your real pace are the ones that last.")
    per_week = st.slider("Study days in a week", 1, 7, 6)
    revision = st.slider("Stop new units this many days before Prelims, to revise", 0, 120, 30, 5,
                         help="Most aspirants keep the last month or more for revision and tests.")
    share = st.slider("When catching up, go at most this much faster than normal", 10, 50, 30, 5, format="%d%%",
                      help="30% means a 1.5-units day can stretch to about 2. More than that rarely lasts.")
    start = st.radio("Where are you now?", [
        "Starting from zero",
        "I'll enter my SuperKalam progress next",
        "Load a sample month (to try the app)",
    ])
    if st.form_submit_button("Start", type="primary"):
        ok, prof = ui.call(ui.store().save_profile, name, exam.isoformat(), revision, per_day, per_week, share / 100)
        if ok:
            st.session_state.profile = prof
            if start.startswith("Load"):
                ok, _ = ui.call(ui.store().load_sample)
                if ok:
                    st.session_state.profile = ui.store().my_profile()
                    ui.flash("success", "Loaded a sample month: three weeks of steady study, then the last few days missed.")
            elif start.startswith("I'll"):
                ui.flash("info", "Enter how many units you've finished in each subject. "
                                 "The numbers are on SuperKalam's My Progress screen.")
                st.session_state.go_subjects = True
            st.rerun()
