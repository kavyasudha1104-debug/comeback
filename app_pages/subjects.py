import pandas as pd
import streamlit as st

from comeback import ui
from comeback.catalog import TOTAL_UNITS

ui.show_flash()
store = ui.store()
S = ui.need_state()

done = sum(x.done for x in S.subjects)
st.title("Subjects")
st.caption(f"SuperKalam's GS learning path: 18 subjects, {TOTAL_UNITS} units. You've done {done}.")

st.markdown("**Update your progress** with the numbers from SuperKalam's My Progress screen, and mark which "
            "subjects must be finished before Prelims and which you could skim if time runs short.")

PRIO = {"must": "Must finish", "normal": "Normal", "skim": "Can skim"}
LABEL = {v: k for k, v in PRIO.items()}
df = pd.DataFrame([{
    "key": x.key, "Subject": x.subject.name + ("  (Mains)" if x.subject.mains_only else ""),
    "Done": x.done, "Units": x.subject.units, "Priority": PRIO[x.priority],
    "Status": "Parked" if x.status == "parked" else ("Finished" if x.remaining == 0 else "Active"),
} for x in S.subjects])
edited = st.data_editor(
    df, hide_index=True, use_container_width=True, key="subjects_editor", disabled=["Subject", "Units", "Status"],
    column_order=["Subject", "Done", "Units", "Priority", "Status"],
    column_config={
        "Done": st.column_config.NumberColumn(min_value=0, step=1, required=True,
                                              help="Units finished. Can't be more than the subject's units."),
        "Priority": st.column_config.SelectboxColumn(options=list(PRIO.values()), required=True),
    })

if st.button("Save changes", type="primary"):
    changed = 0
    for (_, old), (_, new), x in zip(df.iterrows(), edited.iterrows(), S.subjects):
        if int(new["Done"]) != int(old["Done"]):
            if not 0 <= int(new["Done"]) <= x.subject.units:
                st.error(f"{x.subject.name}: done must be between 0 and {x.subject.units}.")
                st.stop()
            ok, r = ui.call(store.set_done, x.key, int(new["Done"]), x.version)
            if not ok:
                st.stop()
            x.version = r["version"]
            changed += 1
        if new["Priority"] != old["Priority"]:
            ok, r = ui.call(store.set_priority, x.key, LABEL[new["Priority"]], x.version)
            if not ok:
                st.stop()
            x.version = r["version"]
            changed += 1
    ui.flash("success", f"Saved {changed} change{'s' if changed != 1 else ''}." if changed else "Nothing changed.")
    st.rerun()

parked = [x for x in S.subjects if x.status == "parked"]
if parked:
    st.subheader(f"Parked ({len(parked)})")
    st.caption("Parked subjects don't count towards your pace. Bring one back and it does again.")
    for x in parked:
        with st.container(border=True):
            left, right = st.columns([5, 1.6], vertical_alignment="center")
            left.markdown(f'<div class="cb-title">{ui.esc(x.subject.name)}</div>'
                          f'<div>{ui.tag(ui.units(x.remaining) + " left", "park")}</div>'
                          + (f'<div class="cb-reason">{ui.esc(x.parked_reason)}</div>' if x.parked_reason else ""),
                          unsafe_allow_html=True)
            if right.button("Bring back", key=f"restore_{x.key}", use_container_width=True):
                ok, _ = ui.call(store.restore_subject, x.key)
                if ok:
                    st.rerun()
