# Tech notes

## Stack

Everything is in Python, with no JavaScript.
- **Streamlit** runs the app.
- **Supabase** handles guest sessions (Auth) and the database (Postgres).

```
app.py                  opens a guest session with the sample month, page navigation
app_pages/              one file per screen
comeback/catalog.py     SuperKalam's 18 subjects and 259 units (from its Learn page)
comeback/pace.py        the maths and the rules: on track?, what to park, welcome back
comeback/stats.py       turns database rows into numbers for the pages
comeback/store.py       all database calls
comeback/ui.py          small shared helpers for the pages
database/setup.sql      tables, access rules and functions; run once in Supabase
database/metrics.sql    the metric queries
screenshots/            Comeback's screens, and SuperKalam screens from my research
```

`pace.py` has no database code, so the rules can be tested on their own. The main sum is simple: units left ÷ study days left before revision = the pace you need. That gets compared with your normal pace, and with your normal pace plus the catch-up limit.

## Data

| Table | What's in it |
|---|---|
| `profiles` | Prelims date, revision days, normal pace, study days a week, catch-up limit |
| `subject_progress` | One row per subject: units done, parked or not, priority, why it was parked |
| `study_log` | Units studied, by day and subject |
| `habit_log` | Which of the three habits were done each day |
| `plans` | Every plan applied: before and after, units parked, weekly target, the rating |
| `events` | Usage events for the metrics |

## Keeping each user's data private

- There's no sign-up. Opening the app creates a private guest session (Supabase anonymous sign-in), so each visitor still has their own user id.
- Row-level security is on for every table. Each visitor can only read their own rows.
- The data stays only while the tab is open. Refreshing or closing it starts a new guest.
- Nobody can write to a table directly. Every change (logging units, ticking a habit, applying a plan) goes through a SQL function. Each function checks who you are, locks the rows it changes, and checks the input: it must be a real subject, can't go past its units, and the plan can't be out of date.
- Applying a plan gets the most checks. It has to match your current progress exactly, and it can only park Mains subjects as Mains-only or your own can-skim subjects as can-skim. The same plan can't be applied twice.
- The app only uses Supabase's public (publishable or anon) key, and won't start if given the secret key.
- "Today" comes from the server in India time, so a wrong phone date can't mess up a plan.

What happens in a few tricky situations:

| Situation | What happens |
|---|---|
| The same plan applied from two tabs | One works; the other is refused and shows the fresh state |
| Units logged on the phone while a plan is open | Apply shows the new plan instead of the old one |
| Two quick taps on a subject's last unit | Only one counts |
| Server can't be reached | A message and a Try again button |
| Session expired | A new guest session with the sample month |

## What was checked

Each flow was run end to end: the sample month, starting from zero, entering progress from My Progress, applying a plan, bringing a parked subject back, and deleting data. Plus the tricky cases from the table above: two tabs, two quick taps, two visitors at once, and the server being down.

Bugs found and fixed along the way:
- The same plan could be applied twice when it didn't park anything. Every subject in an applied plan now gets stamped.
- The one-line answer said "51 days into your revision time" when the finish date was actually 21 days after Prelims. It now says that.
- After applying a plan, the page offered to apply again.
- On a phone, the chart labels overlapped.

## Running it

The live app is the easiest way to try it. To run your own copy: run `database/setup.sql` in a Supabase project, turn on anonymous sign-ins, put the project URL and publishable key in `.streamlit/secrets.toml`, then `pip install -r requirements.txt` and `streamlit run app.py`.
