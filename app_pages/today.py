from datetime import timedelta

import streamlit as st

from comeback import ui
from comeback.catalog import BY_KEY, HABITS
from comeback.pace import assess, comeback_note, next_up

if st.session_state.pop("go_subjects", False):
    st.switch_page("app_pages/subjects.py")

ui.show_flash()
store = ui.store()
S = ui.need_state()
s = ui.settings()
today = S.today
name = (ui.profile() or {}).get("name") or ""
a = assess(S.subjects, s, today, S.unit_logs, S.active_days)

st.title(f"Today, {today.strftime('%a')} {today.day} {today.strftime('%b')}")
st.caption(ui.exam_line())

# --- coming back after days off ---------------------------------------------------
note = comeback_note(S.active_days, S.news_days, today)
if note:
    with st.container(border=True):
        st.markdown(f"**Welcome back{', ' + name if name else ''}. {note.days_off} days off happens to everyone.**")
        st.markdown(
            f"Your learning path picks up where you stopped, but Prelims hasn't moved, so your plan is "
            f"now {note.days_off} days tighter. Here's how to pick up without trying to make it all up today:")
        lines = []
        if note.missed_news_days:
            lines.append(f"- **News:** you missed {note.missed_news_days} day{'s' if note.missed_news_days != 1 else ''} "
                         f"of news analysis. Do **one {note.news_minutes}-minute read** of the main stories "
                         "(a weekly analysis is ideal), not every old day.")
        lines.append("- **Prelims practice and Mains answers:** don't make up missed days. Today's are enough.")
        lines.append("- **GS units:** see whether you're still on track, and what to change if you're not.")
        st.markdown("\n".join(lines))
        if st.button("Am I still on track?", type="primary", icon=":material/speed:"):
            st.switch_page("app_pages/pace.py")
elif a.status in ("behind", "out_of_time"):
    st.warning("At your normal pace you won't finish the syllabus before your revision time. "
               "Open **On track?** to see your options.", icon=":material/speed:")

# --- this week --------------------------------------------------------------------
week_start = today - timedelta(days=today.weekday())
this_week = sum(u for d, u in S.unit_logs if d >= week_start)
target = max(a.weekly_target, round(s.units_per_day * s.study_days_per_week))
c1, c2, c3 = st.columns(3)
c1.markdown(f'<div class="cb-big">{this_week}</div><div class="cb-sub">units this week</div>', unsafe_allow_html=True)
c2.markdown(f'<div class="cb-big">{target}</div><div class="cb-sub">weekly target</div>', unsafe_allow_html=True)
c3.markdown(f'<div class="cb-big">{a.remaining}</div><div class="cb-sub">units left before revision</div>',
            unsafe_allow_html=True)
st.progress(min(1.0, this_week / target) if target else 1.0)

# --- log a unit -------------------------------------------------------------------
st.subheader("Log your study")
nxt = next_up(S.subjects)


def log(subject, n):
    ok, _ = ui.call(store.log_units, subject, n)
    if ok:
        ui.flash("success", f"Logged {ui.units(n)} of {BY_KEY[subject].name}.")
        st.rerun()


if nxt:
    x, unit_no = nxt
    with st.container(border=True):
        left, right = st.columns([3, 2], vertical_alignment="center")
        left.markdown(f'<div class="cb-sub">Next up</div><div class="cb-title">{ui.esc(x.subject.name)} · '
                      f'Unit {unit_no}</div><div class="cb-sub">{x.done}/{x.subject.units} done</div>',
                      unsafe_allow_html=True)
        b1, b2 = right.columns(2)
        if b1.button("+1 unit", key="log1", type="primary", use_container_width=True):
            log(x.key, 1)
        if b2.button("+2 units", key="log2", use_container_width=True):
            log(x.key, 2)
else:
    st.success("Every active subject is finished.")

with st.expander("Log a different subject"):
    open_subjects = [x for x in S.subjects if x.status == "active" and x.remaining > 0]
    if open_subjects:
        with st.form("log_other", clear_on_submit=True):
            pick = st.selectbox("Subject", open_subjects, format_func=lambda x: f"{x.subject.name} ({x.done}/{x.subject.units})")
            n = st.number_input("Units", 1, 10, 1)
            if st.form_submit_button("Log", type="primary"):
                log(pick.key, int(n))

# --- daily habits -----------------------------------------------------------------
st.subheader("Daily habits")
done_today = S.today_habits()
cols = st.columns(3)
for col, (key, label) in zip(cols, HABITS.items()):
    with col:
        on = st.toggle(label, value=key in done_today, key=f"habit_{key}")
        if on != (key in done_today):
            ok, _ = ui.call(store.set_habit, key, on)
            if ok:
                st.rerun()

# --- today's log --------------------------------------------------------------------
entries = S.today_logs()
if entries:
    st.subheader("Logged today")
    for e in reversed(entries):
        left, right = st.columns([5, 1], vertical_alignment="center")
        left.markdown(f"{ui.units(e['units'])} of **{ui.esc(BY_KEY[e['subject']].name)}**")
        if right.button("", key=f"undo_{e['id']}", icon=":material/undo:", type="tertiary", help="Undo this entry"):
            ok, _ = ui.call(store.undo_log, e["id"])
            if ok:
                st.rerun()
