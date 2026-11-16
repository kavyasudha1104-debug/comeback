"""Turns my_state() from the database into what the pace engine and the
Progress page need. All pure functions."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

from .pace import COMEBACK_GAP, Settings, SubjectState, all_subjects


def _d(v) -> date:
    return v if isinstance(v, date) else date.fromisoformat(str(v)[:10])


@dataclass
class State:
    today: date
    subjects: list[SubjectState]
    logs: list[dict] = field(default_factory=list)          # {id, day, subject, units}
    habits: dict[date, set[str]] = field(default_factory=dict)
    plans: list[dict] = field(default_factory=list)

    @property
    def unit_logs(self) -> list[tuple[date, int]]:
        return [(x["day"], x["units"]) for x in self.logs]

    @property
    def active_days(self) -> list[date]:
        """Days you logged units or ticked a habit."""
        return sorted({x["day"] for x in self.logs} | set(self.habits))

    @property
    def news_days(self) -> list[date]:
        return sorted(d for d, h in self.habits.items() if "news" in h)

    def today_logs(self) -> list[dict]:
        return [x for x in self.logs if x["day"] == self.today]

    def today_habits(self) -> set[str]:
        return self.habits.get(self.today, set())


def parse_state(raw: dict) -> State:
    rows = {r["subject"]: SubjectState(key=r["subject"], done=int(r["done"]), status=r["status"],
                                       priority=r["priority"], parked_reason=r.get("parked_reason"),
                                       version=int(r.get("version") or 1))
            for r in raw.get("subjects") or []}
    habits: dict[date, set[str]] = defaultdict(set)
    for h in raw.get("habits") or []:
        habits[_d(h["day"])].add(h["habit"])
    logs = [{"id": x["id"], "day": _d(x["day"]), "subject": x["subject"], "units": int(x["units"])}
            for x in raw.get("logs") or []]
    return State(today=_d(raw["today"]), subjects=all_subjects(rows), logs=logs,
                 habits=dict(habits), plans=raw.get("plans") or [])


def settings_from(profile: dict) -> Settings:
    return Settings(exam_date=_d(profile["exam_date"]), revision_days=int(profile["revision_days"]),
                    units_per_day=float(profile["units_per_day"]),
                    study_days_per_week=int(profile["study_days_per_week"]),
                    catchup_share=float(profile["catchup_share"]))


def comebacks(active: list[date], min_gap: int = COMEBACK_GAP) -> list[tuple[date, int]]:
    """(day you came back, days you'd been away) for each gap of min_gap+ days."""
    days = sorted(set(active))
    return [(cur, (cur - prev).days - 1) for prev, cur in zip(days, days[1:]) if (cur - prev).days - 1 >= min_gap]


def units_by_day(logs: list[tuple[date, int]], today: date, days: int = 28) -> list[tuple[date, int]]:
    totals = {today - timedelta(days=i): 0 for i in range(days)}
    for d, u in logs:
        if d in totals:
            totals[d] += u
    return sorted(totals.items())


def habit_days(habits: dict[date, set[str]], today: date, days: int = 14) -> dict[str, int]:
    start = today - timedelta(days=days - 1)
    out = {"prelims": 0, "mains": 0, "news": 0}
    for d, hs in habits.items():
        if start <= d <= today:
            for h in hs:
                out[h] += 1
    return out
