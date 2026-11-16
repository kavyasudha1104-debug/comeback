"""Are you on track for Prelims, and if not, what should give?

SuperKalam's own design already handles a missed day well in one way: daily
habits reset and the GS learning path resumes where you stopped. What a
missed week does is quieter. The learning path slides later, but the exam
date doesn't. This module answers the question nothing in SuperKalam answers
today:

    At the pace you can actually keep, will you finish the syllabus before
    you need to start revising? If not, what's the least painful thing to
    park, and what does each week need to look like now?

The rules, in order (the first that applies decides):

  0. You overruled it                 -> whatever you chose
  1. You marked a subject "must"      -> always kept
  2. Mains-only subject, Prelims next -> parked until after Prelims
     (SuperKalam itself tags these subjects "MAINS")
  3. You marked a subject "can skim"  -> parked, largest first
  4. Everything else                  -> kept; if it still doesn't fit, the
     shortfall is shown honestly with three ways to close it, rather than
     the app quietly deciding which of your subjects matters less

Parking only happens when the plan doesn't fit at your maximum pace
(normal pace + your catch-up share). If raising the pace a little is
enough, nothing is parked.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from datetime import date, timedelta

from .catalog import BY_KEY, SUBJECTS

RECENT_DAYS = 14      # "your recent pace" looks at the last two weeks
COMEBACK_GAP = 2      # days off before we say "welcome back"
NEWS_MIN, NEWS_MAX, NEWS_PER_DAY = 30, 60, 15

RULES = {
    "override": "You chose this",
    "must": "You marked it must-finish",
    "mains_only": "Mains-only, Prelims comes first",
    "skim": "You marked it can-skim",
    "keep": "Kept",
}


@dataclass
class Settings:
    exam_date: date
    revision_days: int = 30          # stop new units this many days before Prelims
    units_per_day: float = 1.5       # a normal study day
    study_days_per_week: int = 6
    catchup_share: float = 0.30      # how much faster than normal you're willing to go

    @property
    def max_pace(self) -> float:
        return self.units_per_day * (1 + self.catchup_share)

    def finish_by(self) -> date:
        return self.exam_date - timedelta(days=self.revision_days)


@dataclass
class SubjectState:
    key: str
    done: int = 0
    status: str = "active"           # active | parked
    priority: str = "normal"         # must | normal | skim
    parked_reason: str | None = None
    version: int = 1

    @property
    def subject(self):
        return BY_KEY[self.key]

    @property
    def remaining(self) -> int:
        return max(0, self.subject.units - self.done)


def all_subjects(states: dict[str, SubjectState] | None = None) -> list[SubjectState]:
    """Every catalog subject, in SuperKalam's order, with defaults for the missing ones."""
    states = states or {}
    return [states.get(s.key) or SubjectState(s.key) for s in SUBJECTS]


def study_days(start: date, end: date, per_week: int) -> float:
    """Study days from start up to (not including) end."""
    return max(0, (end - start).days) * per_week / 7


# ---------------------------------------------------------------------------
# where you stand
# ---------------------------------------------------------------------------

@dataclass
class Assessment:
    today: date
    finish_by: date
    days_to_finish_by: int
    study_days_left: float
    remaining: int
    parked_remaining: int
    normal_pace: float
    max_pace: float
    needed_pace: float | None        # None when there's no time left
    recent_pace: float | None        # None with no history
    status: str                      # done | on_track | stretch | behind | out_of_time
    projected_finish: date | None    # at your normal pace
    days_off: int | None

    @property
    def weekly_target(self) -> int:
        """Units to do this week to stay on the needed pace (never below normal)."""
        pace = max(self.needed_pace or 0, 0)
        return math.ceil(round(pace * self.per_week, 6)) if pace else 0

    per_week: int = 6

    @property
    def late_by_days(self) -> int:
        """How many days after finish_by you'd finish at your normal pace (0 if on time)."""
        if self.projected_finish is None:
            return 0
        return max(0, (self.projected_finish - self.finish_by).days)


def recent_pace(logs: list[tuple[date, int]], today: date, per_week: int) -> float | None:
    start = today - timedelta(days=RECENT_DAYS)
    in_window = [u for d, u in logs if start <= d < today]
    if not logs or min(d for d, _ in logs) >= today:
        return None
    return sum(in_window) / (RECENT_DAYS * per_week / 7)


def days_off(active: list[date], today: date) -> int | None:
    """Full days since you last did anything, not counting today. None if never."""
    if not active:
        return None
    last = max(active)
    return 0 if last >= today else (today - last).days - 1


def assess(states: list[SubjectState], s: Settings, today: date,
           logs: list[tuple[date, int]] | None = None,
           active: list[date] | None = None) -> Assessment:
    logs = logs or []
    finish_by = s.finish_by()
    left = study_days(today, finish_by, s.study_days_per_week)
    remaining = sum(x.remaining for x in states if x.status == "active")
    parked = sum(x.remaining for x in states if x.status == "parked")
    needed = remaining / left if left > 0 else None

    if remaining == 0:
        status = "done"
    elif needed is None:
        status = "out_of_time"
    elif needed <= s.units_per_day + 1e-9:
        status = "on_track"
    elif needed <= s.max_pace + 1e-9:
        status = "stretch"
    else:
        status = "behind"

    projected = None
    if remaining and s.units_per_day > 0:
        projected = today + timedelta(days=math.ceil(remaining / s.units_per_day * 7 / s.study_days_per_week))

    return Assessment(today=today, finish_by=finish_by, days_to_finish_by=(finish_by - today).days,
                      study_days_left=left, remaining=remaining, parked_remaining=parked,
                      normal_pace=s.units_per_day, max_pace=s.max_pace, needed_pace=needed,
                      recent_pace=recent_pace(logs, today, s.study_days_per_week),
                      status=status, projected_finish=projected,
                      days_off=days_off(active or [d for d, _ in logs], today),
                      per_week=s.study_days_per_week)


# ---------------------------------------------------------------------------
# what to do about it
# ---------------------------------------------------------------------------

@dataclass
class Decision:
    key: str
    name: str
    remaining: int
    action: str          # keep | park
    rule: str
    reason: str
    version: int = 1


@dataclass
class Plan:
    before: Assessment
    after: Assessment
    decisions: list[Decision]
    shortfall: int                         # units that still don't fit at max pace
    ways_to_fit: list[str] = field(default_factory=list)

    @property
    def parked(self) -> list[Decision]:
        return [d for d in self.decisions if d.action == "park"]

    @property
    def parked_units(self) -> int:
        return sum(d.remaining for d in self.parked)


def make_plan(states: list[SubjectState], s: Settings, today: date,
              overrides: dict[str, str] | None = None,
              logs: list[tuple[date, int]] | None = None,
              active: list[date] | None = None) -> Plan:
    overrides = overrides or {}
    active_states = [x for x in states if x.status == "active" and x.remaining > 0]
    before = assess(states, s, today, logs, active)
    left = before.study_days_left
    capacity = s.max_pace * left                      # units you can still do before finish_by
    prelims_next = s.exam_date > today

    decisions: dict[str, Decision] = {}

    def decide(x: SubjectState, action: str, rule: str, reason: str):
        decisions[x.key] = Decision(x.key, x.subject.name, x.remaining, action, rule, reason, x.version)

    # 0 and 1: fixed decisions
    for x in active_states:
        o = overrides.get(x.key)
        if o in ("keep", "park"):
            decide(x, o, "override", "You chose to keep this." if o == "keep" else "You chose to park this.")
        elif x.priority == "must":
            decide(x, "keep", "must", "You marked this must-finish, so it's never parked.")

    def load() -> int:
        return sum(x.remaining for x in active_states
                   if decisions.get(x.key) is None or decisions[x.key].action == "keep")

    # 2 and 3: park only while the plan doesn't fit at your max pace
    if before.status in ("behind", "out_of_time"):
        mains = sorted([x for x in active_states if x.key not in decisions
                        and x.subject.mains_only and prelims_next], key=lambda x: -x.remaining)
        skims = sorted([x for x in active_states if x.key not in decisions
                        and x.priority == "skim"], key=lambda x: -x.remaining)
        for x in mains:
            if load() <= capacity:
                break
            decide(x, "park", "mains_only",
                   f"SuperKalam marks {x.subject.name} as a Mains subject; it isn't tested in Prelims. "
                   f"Parked until after Prelims ({x.remaining} units).")
        for x in skims:
            if load() <= capacity:
                break
            decide(x, "park", "skim",
                   f"You marked {x.subject.name} as can-skim. Parked so your must-finish subjects fit "
                   f"({x.remaining} units). Bring it back any time.")

    for x in active_states:
        if x.key not in decisions:
            decide(x, "keep", "keep", "Fits in your plan." if load() <= capacity
                   else "Kept. You haven't marked it can-skim, so the app won't drop it for you.")

    after_states = [replace(x, status="parked") if decisions.get(x.key) and decisions[x.key].action == "park"
                    else x for x in states]
    after = assess(after_states, s, today, logs, active)
    shortfall = max(0, math.ceil(after.remaining - capacity - 1e-9)) if left > 0 else after.remaining

    ways: list[str] = []
    if shortfall:
        need_days = after.remaining / s.max_pace * 7 / s.study_days_per_week
        fit_revision = (s.exam_date - today).days - math.ceil(need_days)
        if 0 <= fit_revision < s.revision_days:
            ways.append(f"Cut your revision buffer from {s.revision_days} to {fit_revision} days.")
        if left > 0:
            need_upd = after.remaining / left / (1 + s.catchup_share)
            if need_upd <= 10:
                ways.append(f"Raise your normal pace from {s.units_per_day:g} to {math.ceil(need_upd * 10) / 10:g} units a day.")
        ways.append(f"Mark more subjects can-skim on the Subjects page (about {shortfall} units need to go).")

    order = {"park": 1, "keep": 0}
    out = sorted(decisions.values(), key=lambda d: (order[d.action], [x.key for x in states].index(d.key)))
    return Plan(before=before, after=after, decisions=out, shortfall=shortfall, ways_to_fit=ways)


# ---------------------------------------------------------------------------
# coming back after days off
# ---------------------------------------------------------------------------

@dataclass
class ComebackNote:
    days_off: int
    missed_news_days: int
    news_minutes: int


def comeback_note(active: list[date], news_days: list[date], today: date) -> ComebackNote | None:
    """After 2+ days off: how to handle the daily habits you missed.

    SuperKalam's daily habits reset each day, and that's right for practice
    and answer writing: doing three days of MCQs today doesn't help. News
    is different: what you missed can matter in the exam, but reading old
    daily analyses one by one is the backlog that makes people give up.
    So the missed news days become one summary read of 30-60 minutes.
    """
    off = days_off(active, today)
    if off is None or off < COMEBACK_GAP:
        return None
    gap_start = today - timedelta(days=off)
    missed = sum(1 for i in range(off) if gap_start + timedelta(days=i) not in set(news_days))
    minutes = max(NEWS_MIN, min(NEWS_MAX, NEWS_PER_DAY * missed)) if missed else 0
    return ComebackNote(days_off=off, missed_news_days=missed, news_minutes=minutes)


def next_up(states: list[SubjectState]) -> tuple[SubjectState, int] | None:
    """Where SuperKalam's 'Resume' would put you: the subject you've started,
    else the first one not finished, in the Learn page's order."""
    active = [x for x in states if x.status == "active" and x.remaining > 0]
    started = [x for x in active if x.done > 0]
    pick = (started or active or [None])[0]
    return (pick, pick.done + 1) if pick else None


def plan_payload(plan: Plan, today: date) -> dict:
    """What gets sent to the database when the plan is applied. The server re-checks it."""
    return {
        "today": today.isoformat(),
        "park": [{"subject": d.key, "rule": d.rule, "reason": d.reason, "version": d.version}
                 for d in plan.parked],
        "keep": [{"subject": d.key, "version": d.version} for d in plan.decisions if d.action == "keep"],
        "weekly_target": plan.after.weekly_target,
        "summary": {
            "status_before": plan.before.status, "status_after": plan.after.status,
            "needed_before": round(plan.before.needed_pace or 0, 3),
            "needed_after": round(plan.after.needed_pace or 0, 3),
            "parked_units": plan.parked_units, "shortfall": plan.shortfall,
            "overrides": sum(1 for d in plan.decisions if d.rule == "override"),
            "rules": {r: sum(1 for d in plan.decisions if d.rule == r) for r in RULES},
        },
    }
