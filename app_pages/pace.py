import hashlib
import json
from datetime import timedelta

import altair as alt
import pandas as pd
import streamlit as st

from comeback import ui
from comeback.pace import RULES, make_plan, plan_payload

ui.show_flash()
store = ui.store()
S = ui.need_state()
s = ui.settings()
today = S.today

overrides: dict = st.session_state.setdefault("overrides", {})
plan = make_plan(S.subjects, s, today, overrides, S.unit_logs, S.active_days)
a = plan.before

if st.session_state.get("pace_viewed") != str(today):
    st.session_state.pace_viewed = str(today)
    store.log_event("pace_viewed", {"status": a.status, "days_off": a.days_off})

st.title("Are you on track?")
st.markdown(ui.status_chip(a.status), unsafe_allow_html=True)


def fmt(d):
    return f"{d.day} {d.strftime('%b')}"


# --- the answer, in one sentence ------------------------------------------------
if a.status == "done":
    st.markdown("### Every active subject is finished. Time to revise.")
elif a.status == "out_of_time":
    st.markdown(f"### Your revision time has started ({fmt(a.finish_by)}), with {ui.units(a.remaining)} still unstudied.")
else:
    when = fmt(a.projected_finish)
    after_exam = (a.projected_finish - s.exam_date).days if a.projected_finish else 0
    if after_exam > 0:
        st.markdown(f"### At {ui.units(s.units_per_day)} a day you'd finish on **{when}**: "
                    f"**{after_exam} days after Prelims**, with no time to revise "
                    f"(revision should start {fmt(a.finish_by)}).")
    elif a.late_by_days:
        st.markdown(f"### At {ui.units(s.units_per_day)} a day you'd finish on **{when}**, "
                    f"**{a.late_by_days} days** into your revision time (it starts {fmt(a.finish_by)}).")
    else:
        spare = (a.finish_by - a.projected_finish).days
        st.markdown(f"### At {ui.units(s.units_per_day)} a day you'll finish around **{when}**, "
                    f"{spare} days before your revision time starts ({fmt(a.finish_by)}).")
st.caption(f"{ui.exam_line()} · revision starts {s.revision_days} days before · "
           f"{s.study_days_per_week} study days a week. Change these in Settings.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Units left", a.remaining, help="In subjects you haven't parked.")
c2.metric("Needed pace", ui.pace(a.needed_pace), help="Units per study day to finish before revision starts.")
c3.metric("Your normal pace", ui.pace(a.normal_pace), help="What you said a normal day looks like.")
c4.metric("Last 2 weeks", ui.pace(a.recent_pace), help="What you actually logged, per study day.")

# --- the chart: where you are vs where you need to be -----------------------------
done_now = sum(x.done for x in S.subjects)
goal = done_now + a.remaining
start = today - timedelta(days=28)
hist = []
cum = done_now - sum(u for d, u in S.unit_logs if d >= start)
by_day = {}
for d, u in S.unit_logs:
    by_day[d] = by_day.get(d, 0) + u
d = start
while d <= today:
    cum += by_day.get(d, 0)
    hist.append({"date": d, "units": cum, "line": "Done so far"})
    d += timedelta(days=1)
lines = list(hist)
end = max(a.finish_by, a.projected_finish or a.finish_by)
if a.study_days_left > 0 and a.remaining:
    lines += [{"date": today, "units": done_now, "line": "Needed"}, {"date": a.finish_by, "units": goal, "line": "Needed"}]
if a.projected_finish and a.remaining:
    lines += [{"date": today, "units": done_now, "line": "Normal pace"},
              {"date": a.projected_finish, "units": goal, "line": "Normal pace"}]
df = pd.DataFrame(lines)
df["date"] = pd.to_datetime(df["date"])
colors = alt.Scale(domain=["Done so far", "Needed", "Normal pace"], range=["#2f6b4f", "#b04a2f", "#d9a441"])
chart = alt.Chart(df).mark_line(strokeWidth=3).encode(
    x=alt.X("date:T", title=None), y=alt.Y("units:Q", title="units done", scale=alt.Scale(zero=False)),
    color=alt.Color("line:N", scale=colors, legend=alt.Legend(orient="top", title=None)),
    strokeDash=alt.condition(alt.datum.line == "Done so far", alt.value([1, 0]), alt.value([6, 4])),
    tooltip=[alt.Tooltip("date:T"), "units", "line"])
marks = pd.DataFrame([{"date": pd.Timestamp(a.finish_by), "label": "Revision starts", "y": goal * 0.22},
                      {"date": pd.Timestamp(s.exam_date), "label": "Prelims", "y": goal * 0.06}])
rule = alt.Chart(marks).mark_rule(color="#888", strokeDash=[2, 3]).encode(x="date:T")
text = alt.Chart(marks).mark_text(align="right", dx=-4, color="#666").encode(
    x="date:T", y=alt.Y("y:Q", title="units done"), text="label:N")
st.altair_chart((chart + rule + text).properties(height=260), use_container_width=True)
st.caption("Solid: what you've done. Dashed red: the pace that finishes on time. Dashed yellow: your normal pace.")

# --- just applied: ask how it feels --------------------------------------------------
applied = st.session_state.get("applied_plan")
if applied:
    with st.container(border=True):
        st.markdown(f"**Plan saved.** {applied['summary']}")
        st.write("How doable does this feel?")
        rating = st.feedback("stars", key=f"rate_{applied['id']}")
        if rating is not None:
            ok, _ = ui.call(store.rate_plan, applied["id"], rating + 1)
            if ok:
                del st.session_state["applied_plan"]
                ui.flash("success", "Thanks for rating it.")
                st.rerun()

if a.status in ("on_track", "done") and not overrides:
    if a.status == "on_track":
        st.success(f"You're on track. About {max(a.weekly_target, round(s.units_per_day * s.study_days_per_week))} "
                   "units a week keeps you there.")
    st.stop()

# --- the plan -------------------------------------------------------------------------
latest = S.plans[0] if S.plans else None
if (latest and latest["made_on"] == today.isoformat() and not plan.parked and not overrides
        and a.status == "stretch"):
    st.info(f"Your plan from today: **{latest['weekly_target']} units a week**"
            + (f", with {ui.units(latest['parked_units'])} parked until later." if latest["parked_units"] else ".")
            + " Parked subjects are on the Subjects page.", icon=":material/check_circle:")
    st.stop()

st.divider()
st.subheader("What to change")
after = plan.after
body = plan_payload(plan, today)
shown_before = st.session_state.get("shown_plan")
this_plan = hashlib.sha1(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
st.session_state.shown_plan = this_plan
if st.session_state.get("previewed") != this_plan:
    st.session_state.previewed = this_plan
    store.log_event("plan_previewed", {"status": a.status, "parked_units": plan.parked_units})

if not plan.parked and after.needed_pace is not None:
    st.markdown(f"**Raise your pace from {ui.pace(s.units_per_day)} to {ui.pace(after.needed_pace)}**: "
                f"about **{after.weekly_target} units a week** instead of "
                f"{round(s.units_per_day * s.study_days_per_week)}. That's within your {round(s.catchup_share * 100)}% "
                "catch-up limit, so nothing needs parking.")
elif plan.parked:
    st.markdown(f"Even at your top pace ({ui.pace(s.max_pace)}) not everything fits. "
                f"Park **{ui.units(plan.parked_units)}** for now, and do **{after.weekly_target} units a week** "
                f"({ui.pace(after.needed_pace)}).")

if plan.shortfall:
    st.error(f"Even after parking, about **{ui.units(plan.shortfall)}** won't fit before revision. "
             "The app won't decide which of your subjects matters less. Pick one:")
    for w in plan.ways_to_fit:
        st.markdown(f"- {w}")


def choice(dcs):
    current = "Park" if dcs.action == "park" else "Keep"
    pick = st.segmented_control("Decision", ["Keep", "Park"], default=current, key=f"ov_{dcs.key}_{current}",
                                label_visibility="collapsed")
    if pick and pick != current:
        overrides[dcs.key] = pick.lower()
        store.log_event("decision_changed", {"rule": dcs.rule, "to": pick.lower(), "subject": dcs.key})
        st.rerun()


if plan.parked:
    st.markdown("**Parked for now** (not deleted; bring any back from Subjects):")
for dcs in plan.parked:
    with st.container(border=True):
        left, right = st.columns([5, 1.6], vertical_alignment="center")
        left.markdown(f'<div class="cb-title">{ui.esc(dcs.name)}</div>'
                      f'<div>{ui.tag(ui.units(dcs.remaining) + " left", "park")}</div>'
                      f'<div class="cb-reason">{ui.esc(dcs.reason)}</div>', unsafe_allow_html=True)
        with right:
            choice(dcs)

kept = [d for d in plan.decisions if d.action == "keep"]
with st.expander(f"Kept ({len(kept)} subjects, {ui.units(sum(d.remaining for d in kept))})", expanded=bool(overrides)):
    for dcs in kept:
        left, right = st.columns([5, 1.6], vertical_alignment="center")
        left.markdown(f'**{ui.esc(dcs.name)}** · {ui.units(dcs.remaining)} left<div class="cb-reason">'
                      f'{ui.esc(dcs.reason)}</div>', unsafe_allow_html=True)
        with right:
            choice(dcs)

with st.expander("How these suggestions are made"):
    st.markdown(f"""
In order; the first rule that applies decides:

1. **You chose**: your Keep/Park choice always wins.
2. **Must-finish** subjects (set on the Subjects page) are never parked.
3. **Mains-only subjects** wait until after Prelims. SuperKalam itself tags Governance, Internal Security,
   Disaster Management, World History and Ethics as Mains.
4. **Can-skim** subjects (your choice, on the Subjects page) are parked next, largest first.
5. Everything else is **kept**. If it still doesn't fit, you're shown the gap and three ways to close it.
   The app never decides on its own that one of your subjects matters less.

Subjects are parked only when the plan doesn't fit at your top pace: your normal
{ui.pace(s.units_per_day)} plus your {round(s.catchup_share * 100)}% catch-up limit = {ui.pace(s.max_pace)}.
Only as much is parked as needed.
""")
    st.caption("Rules used here: " + ", ".join(sorted({RULES[d.rule] for d in plan.decisions})))

a1, a2 = st.columns([1.2, 2])
if a1.button("Apply this plan", type="primary", icon=":material/check:", use_container_width=True):
    if shown_before != this_plan:
        ui.flash("info", "Something changed since you opened this plan. Here's a fresh one.")
        st.rerun()
    ok, plan_id = ui.call(store.apply_plan, body)
    if ok:
        st.session_state.overrides = {}
        st.session_state.applied_plan = {
            "id": plan_id,
            "summary": (f"{after.weekly_target} units a week from now"
                        + (f"; {ui.units(plan.parked_units)} parked until later." if plan.parked else "."))}
        st.rerun()
if overrides and a2.button("Undo my changes"):
    st.session_state.overrides = {}
    st.rerun()
