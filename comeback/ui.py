"""Shared Streamlit pieces: the visitor's store, error handling, data loading,
formatting and a little styling."""

from __future__ import annotations

import html
import time
from datetime import date, datetime, timedelta, timezone

import streamlit as st

from . import config
from .pace import Settings
from .stats import State, parse_state, settings_from
from .store import AuthRequired, BaseStore, ConnectionLost, StoreError

IST = timezone(timedelta(hours=5, minutes=30))


def today_ist() -> date:
    return datetime.now(IST).date()

CSS = """
<style>
.block-container {max-width: 900px; padding-top: 2rem;}
[data-testid="stHeaderActionElements"] {display: none;}
.cb-big {font-size: 2rem; font-weight: 650; line-height: 1.1; font-variant-numeric: tabular-nums;}
.cb-sub {opacity: .72; font-size: .92rem;}
.cb-title {font-weight: 550;}
.cb-tag {display: inline-block; font-size: .76rem; padding: .05rem .5rem; border-radius: .7rem;
         background: rgba(47,107,79,.11); margin: 0 .25rem .15rem 0; white-space: nowrap;}
.cb-tag.must {background: rgba(176,74,47,.14);}
.cb-tag.could {background: rgba(0,0,0,.06);}
.cb-tag.catch {background: rgba(217,164,65,.25);}
.cb-tag.park {background: rgba(0,0,0,.07);}
.cb-reason {font-size: .88rem; opacity: .8; margin-top: .15rem;}
.cb-done {text-decoration: line-through; opacity: .55;}
.cb-bar {height: .55rem; border-radius: .3rem; background: rgba(0,0,0,.07); overflow: hidden; display: flex; margin: .3rem 0 .2rem;}
.cb-bar span {display: block; height: 100%;}
.cb-bar .a {background: #8fb39f;} .cb-bar .b {background: #d9a441;} .cb-bar .c {background: #b04a2f;}
@media (max-width: 640px) {
  .block-container {padding-left: .9rem; padding-right: .9rem;}
  .cb-big {font-size: 1.6rem;}
}
</style>
"""


def style() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# store and errors
# ---------------------------------------------------------------------------

def store() -> BaseStore:
    """One store per browser session. Never shared between visitors,
    because it holds that visitor's guest session."""
    if "store" not in st.session_state:
        st.session_state.store = config.make_store()
    return st.session_state.store


def start_with_sample() -> None:
    """Start a guest session and load the sample month, so the app opens straight on Today."""
    s = store()
    s.start()
    exam = (today_ist() + timedelta(days=150)).isoformat()
    s.save_profile("", exam, 30, 1.5, 6, 0.3)
    s.load_sample()
    st.session_state.profile = s.my_profile()
    flash("info", "You're looking at a sample month: three weeks of study, then the last 5 days missed. "
                  "To use your own progress, go to Settings and press Start fresh.")


def sign_out(message: str | None = None) -> None:
    try:
        store().sign_out()
    except Exception:
        pass
    for k in [k for k in st.session_state.keys() if k != "store"]:
        del st.session_state[k]
    if message:
        flash("warning", message)


def flash(kind: str, message: str) -> None:
    """Show a message after the next rerun."""
    st.session_state.flash = (kind, message)


def show_flash() -> None:
    item = st.session_state.pop("flash", None)
    if item:
        getattr(st, item[0])(item[1])


def call(fn, *args, **kwargs):
    """Run a store call; show any failure on screen. Returns (ok, value)."""
    try:
        return True, fn(*args, **kwargs)
    except AuthRequired as e:
        sign_out(e.message)
        st.rerun()
    except ConnectionLost as e:
        st.warning(e.message, icon=":material/wifi_off:")
        return False, e
    except StoreError as e:
        if e.code in ("stale", "stale_plan", "gone"):
            refresh()
            flash("info", e.message)
            st.rerun()
        st.error(e.message)
        return False, e
    return False, None


# ---------------------------------------------------------------------------
# data for this run
# ---------------------------------------------------------------------------

def refresh() -> None:
    """Fetch fresh data on the next read. Called at the start of every run,
    so a change made in another tab or on the phone shows up on the next click."""
    st.session_state.pop("_state", None)


def today() -> date:
    """The server's idea of today (India time), so every device agrees.
    Re-checked every few minutes so a session left open past midnight moves on."""
    cached = st.session_state.get("_today")
    if not cached or time.monotonic() - cached[1] > 300:
        ok, v = call(store().server_today)
        st.session_state._today = (date.fromisoformat(v) if ok else today_ist(), time.monotonic())
    return st.session_state._today[0]


def state() -> State | None:
    if "_state" not in st.session_state:
        ok, raw = call(store().my_state, 120)
        if not ok:
            return None
        st.session_state._state = parse_state(raw)
    return st.session_state._state


def need_state() -> State:
    s = state()
    if s is None:
        if st.button("Try again", key="retry_load"):
            refresh()
            st.rerun()
        st.stop()
    return s


def profile() -> dict | None:
    return st.session_state.get("profile")


def settings() -> Settings:
    return settings_from(profile())


# ---------------------------------------------------------------------------
# formatting
# ---------------------------------------------------------------------------

def units(n: float) -> str:
    n = round(n, 1)
    txt = f"{n:g}"
    return f"{txt} unit" if n == 1 else f"{txt} units"


def pace(p: float | None) -> str:
    return "–" if p is None else f"{p:.1f}/day"


def mins(m: int) -> str:
    m = int(m)
    if m < 60:
        return f"{m} min"
    h, r = divmod(m, 60)
    return f"{h} h" if r == 0 else f"{h} h {r} min"


def day(d: date, ref: date | None = None) -> str:
    ref = ref or today()
    if d == ref:
        return "Today"
    if d == ref + timedelta(days=1):
        return "Tomorrow"
    if d == ref - timedelta(days=1):
        return "Yesterday"
    return f"{d.strftime('%a')} {d.day} {d.strftime('%b')}"


def esc(s: str) -> str:
    return html.escape(s or "")


def tag(text: str, cls: str = "") -> str:
    return f'<span class="cb-tag {cls}">{esc(text)}</span>'


def load_bar(limit: int, planned: int, extra: int = 0) -> str:
    """Planned (green), catch-up (amber), anything over the limit (red)."""
    total = max(limit, planned + extra, 1)
    over = max(planned + extra - limit, 0)
    a = min(planned, limit)
    b = max(min(planned + extra, limit) - a, 0)
    return (f'<div class="cb-bar"><span class="a" style="width:{a / total * 100:.1f}%"></span>'
            f'<span class="b" style="width:{b / total * 100:.1f}%"></span>'
            f'<span class="c" style="width:{over / total * 100:.1f}%"></span></div>')


def exam_line() -> str:
    s = settings()
    n = (s.exam_date - today()).days
    if n < 0:
        return "Prelims date has passed: update it in Settings"
    return f"{n} days to Prelims" if n != 1 else "Prelims tomorrow"


STATUS = {
    "on_track": ("On track", "#2f6b4f"),
    "stretch": ("Slightly behind", "#b7791f"),
    "behind": ("Behind", "#b04a2f"),
    "out_of_time": ("Out of time", "#b04a2f"),
    "done": ("Syllabus done", "#2f6b4f"),
}


def status_chip(status: str) -> str:
    label, color = STATUS[status]
    return (f'<span style="background:{color};color:white;border-radius:1rem;padding:.15rem .7rem;'
            f'font-weight:600;font-size:.9rem">{esc(label)}</span>')
