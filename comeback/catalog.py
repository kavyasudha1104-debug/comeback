"""SuperKalam's GS learning path, as SuperKalam shows it.

Subjects, unit counts and the "MAINS" labels are copied from SuperKalam's
Learn page (dashboard.superkalam.com/learn, seen 9 Nov 2026). The total,
259 units, matches the "0/259 Unit Completed" on the app's My Progress screen
(seen 10 Nov 2026). If SuperKalam changes its course, this list needs
updating; it is the only place it lives in Python (the database has a copy
it checks against).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Subject:
    key: str
    name: str
    units: int
    group: str
    mains_only: bool   # SuperKalam tags these "MAINS"


SUBJECTS: list[Subject] = [
    Subject("polity", "Indian Polity", 35, "Economy, Polity & Governance", False),
    Subject("economy", "Economy", 18, "Economy, Polity & Governance", False),
    Subject("ir", "International Relations", 18, "Economy, Polity & Governance", False),
    Subject("social", "Social Issues & Schemes", 13, "Economy, Polity & Governance", False),
    Subject("governance", "Governance", 5, "Economy, Polity & Governance", True),
    Subject("security", "Internal Security", 6, "Economy, Polity & Governance", True),
    Subject("environment", "Environment & Ecology", 21, "Geography, Environment & Science", False),
    Subject("indian_geo", "Indian Geography", 16, "Geography, Environment & Science", False),
    Subject("physical_geo", "Physical Geography", 11, "Geography, Environment & Science", False),
    Subject("scitech", "Science & Technology", 10, "Geography, Environment & Science", False),
    Subject("world_geo", "World Geography", 5, "Geography, Environment & Science", False),
    Subject("disaster", "Disaster Management", 4, "Geography, Environment & Science", True),
    Subject("ancient", "Ancient History", 13, "History & Culture", False),
    Subject("medieval", "Medieval History", 23, "History & Culture", False),
    Subject("modern", "Modern History", 22, "History & Culture", False),
    Subject("art", "Art & Culture", 16, "History & Culture", False),
    Subject("world_history", "World History", 11, "History & Culture", True),
    Subject("ethics", "Ethics", 12, "Society & Ethics", True),
]

BY_KEY = {s.key: s for s in SUBJECTS}
TOTAL_UNITS = sum(s.units for s in SUBJECTS)
PRELIMS_UNITS = sum(s.units for s in SUBJECTS if not s.mains_only)

HABITS = {
    "prelims": "Daily Prelims Practice",
    "mains": "Daily Mains Question",
    "news": "Daily News Analysis",
}

assert TOTAL_UNITS == 259 and PRELIMS_UNITS == 221
