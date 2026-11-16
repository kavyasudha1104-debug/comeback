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
- The app only uses Supabase's public (anon) key, and won't start if given the secret key.
- "Today" comes from the server in India time, so a wrong phone date can't mess up a plan.

What happens in a few tricky situations:

| Situation | What happens |
|---|---|
| The same plan applied from two tabs | One works; the other is refused and shows the fresh state |
| Units logged on the phone while a plan is open | Apply shows the new plan instead of the old one |
| Two quick taps on a subject's last unit | Only one counts |
| Server can't be reached | A message and a Try again button |
| Session expired | A new guest session with the sample month |

## What I checked

I went through each flow myself: the sample month, starting from zero, entering progress from My Progress, applying a plan, bringing a parked subject back, and deleting data. I also checked the tricky cases from the table above: two tabs, two quick taps, two visitors at once, and the server being down.

Bugs I found and fixed along the way:
- The same plan could be applied twice when it didn't park anything. Every subject in an applied plan now gets stamped.
- The one-line answer said "51 days into your revision time" when the finish date was actually 21 days after Prelims. It now says that.
- After applying a plan, the page offered to apply again.
- On a phone, the chart labels overlapped.

Not tested: real users.

## Setting it up

1. **Supabase.** Create a project at [supabase.com](https://supabase.com).
   1. Open **SQL Editor → New query**, paste all of `database/setup.sql`, and click **Run**.
2. **Turn on guest access.** Under **Authentication → Sign In / Providers**, switch on **Allow anonymous sign-ins** and save. There's no sign-up: opening the app gives each visitor a private guest session.
3. **Keys.** From **Project Settings → API keys**, copy the Project URL and the anon (publishable) key into `.streamlit/secrets.toml`:
   ```toml
   SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
   SUPABASE_ANON_KEY = "your anon key"
   ```
   Never use the service_role or secret key.
4. **Run it.**
   ```bash
   pip install -r requirements.txt
   streamlit run app.py
   ```
5. **To put it online,** push the folder to GitHub (`secrets.toml` is in `.gitignore`), then create an app on [share.streamlit.io](https://share.streamlit.io) with main file `app.py`. Paste the two keys into its Secrets, and set the app's URL as the Site URL in Supabase under **Authentication → URL Configuration**.

Free plans sleep: Streamlit apps after a while without visitors, and Supabase projects after about a week of no activity.
