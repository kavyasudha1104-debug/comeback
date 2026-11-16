from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

from comeback import ui
from comeback.catalog import HABITS
from comeback.pace import days_off
from comeback.stats import comebacks, habit_days, units_by_day

ui.show_flash()
S = ui.need_state()
today = S.today

st.title("Progress")
st.caption("No streaks here. After a bad week, what matters is whether you come back.")

active = S.active_days
recent = [d for d in active if (today - d).days < 14]
backs = comebacks(active)
off = days_off(active, today)
habits = habit_days(S.habits, today, 14)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Days studied", f"{len(recent)} / 14", help="Days in the last two weeks with a unit logged or a habit done.")
c2.metric("Comebacks", len(backs), help="Times you came back after 2 or more days off.")
c3.metric("Units, last 2 weeks", sum(u for d, u in S.unit_logs if (today - d).days < 14))
c4.metric("Days off now", "–" if off is None else off, help="Full days since you last did anything.")

if not active:
    st.info("Log units or tick a habit on the Today page and your progress shows up here.")
    st.stop()

if backs:
    last_day, gap = backs[-1]
    st.success(f"Last comeback: {ui.day(last_day, today)}, after {gap} days off. That's the part that counts.")

st.subheader("Units per day, last 4 weeks")
df = pd.DataFrame([{"day": d, "units": u} for d, u in units_by_day(S.unit_logs, today, 28)])
df["label"] = [f"{d.day} {d.strftime('%b')}" for d in df["day"]]
st.altair_chart(alt.Chart(df).mark_bar(color="#2f6b4f", cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
    x=alt.X("label:N", sort=None, title=None, axis=alt.Axis(labelAngle=-45)),
    y=alt.Y("units:Q", title="units"), tooltip=[alt.Tooltip("label:N", title="Day"), alt.Tooltip("units:Q", title="Units")]).properties(height=220),
    use_container_width=True)

st.subheader("Daily habits, last 2 weeks")
h1, h2, h3 = st.columns(3)
for col, (key, label) in zip((h1, h2, h3), HABITS.items()):
    col.metric(label, f"{habits[key]} / 14")

if S.plans:
    st.subheader("Catch-up plans")
    stars = {None: "", 1: "★", 2: "★★", 3: "★★★", 4: "★★★★", 5: "★★★★★"}
    status = {"on_track": "On track", "stretch": "Slightly behind", "behind": "Behind", "out_of_time": "Out of time",
              "done": "Done"}
    st.dataframe(pd.DataFrame([{
        "Made": ui.day(date.fromisoformat(p["made_on"]), today),
        "Was": status.get(p["status_before"], p["status_before"]),
        "Units parked": p["parked_units"],
        "Weekly target": p["weekly_target"],
        "You changed": p["overrides"],
        "Doable?": stars.get(p.get("doable"), ""),
    } for p in S.plans]), hide_index=True, use_container_width=True)
