import json
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from comeback import ui

ui.show_flash()
store = ui.store()
p = ui.profile() or {}
today = ui.today()

st.title("Settings and data")
st.caption("You're using Comeback as a guest. Your data is kept only while this tab is open.")

st.subheader("Your plan settings")
with st.form("settings"):
    name = st.text_input("Name", value=p.get("name") or "", max_chars=60)
    exam_saved = date.fromisoformat(p["exam_date"])
    exam = st.date_input("Prelims date", value=max(exam_saved, today), min_value=today,
                         max_value=today + timedelta(days=1100), format="DD/MM/YYYY")
    per_day = st.slider("GS units on a normal study day", 0.5, 6.0, float(p.get("units_per_day") or 1.5), 0.5)
    per_week = st.slider("Study days in a week", 1, 7, int(p.get("study_days_per_week") or 6))
    revision = st.slider("Stop new units this many days before Prelims", 0, 120, int(p.get("revision_days") or 30), 5)
    share = st.slider("Catch-up limit: go at most this much faster than normal", 10, 50,
                      int(round(float(p.get("catchup_share") or 0.3) * 100)), 5, format="%d%%")
    if st.form_submit_button("Save", type="primary"):
        ok, prof = ui.call(store.save_profile, name, exam.isoformat(), revision, per_day, per_week, share / 100)
        if ok:
            st.session_state.profile = prof
            ui.flash("success", "Saved.")
            st.rerun()

st.subheader("Try it with sample data")
st.write("Loads a sample month: three weeks of steady study, then the last few days missed, with Prelims in 150 days. "
         "**This replaces your progress and settings.**")
c1, c2 = st.columns(2)
if c1.button("Load sample month", use_container_width=True):
    ok, _ = ui.call(store.load_sample)
    if ok:
        st.session_state.profile = store.my_profile()
        st.session_state.overrides = {}
        ui.flash("success", "Sample loaded. Open Today, then On track?")
        st.rerun()
with c2.popover("Start fresh", use_container_width=True):
    st.write("Clears all your progress, logs and plans. Your settings stay.")
    if st.button("Yes, clear my progress", type="primary"):
        ok, _ = ui.call(store.reset_progress)
        if ok:
            st.session_state.overrides = {}
            ui.flash("success", "Progress cleared.")
            st.rerun()

st.subheader("Your data")
st.write("Everything you've entered belongs to you. Download it any time, or delete it.")
ok, data = ui.call(store.export_my_data)
if ok:
    a, b = st.columns(2)
    if a.download_button("Download everything (JSON)", json.dumps(data, indent=2, default=str),
                         file_name=f"comeback-{today}.json", mime="application/json", use_container_width=True):
        store.log_event("data_exported", {"format": "json"})
    if data.get("study_log"):
        csv = pd.DataFrame(data["study_log"])[["day", "subject", "units"]].to_csv(index=False)
        if b.download_button("Download study log (CSV)", csv, file_name=f"comeback-log-{today}.csv",
                             mime="text/csv", use_container_width=True):
            store.log_event("data_exported", {"format": "csv"})

with st.expander("Delete all my data"):
    st.write("This deletes your progress, logs, plans and settings. It can't be undone.")
    confirm = st.text_input('Type "delete" to confirm', key="confirm_delete")
    if st.button("Delete everything", disabled=confirm.strip().lower() != "delete"):
        ok, _ = ui.call(store.delete_my_data)
        if ok:
            ui.sign_out("All your data was deleted. You're back on a fresh sample month.")
            st.rerun()
