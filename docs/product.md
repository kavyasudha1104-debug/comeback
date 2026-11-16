# Product notes

## The problem

When you miss days on SuperKalam, the GS learning path just picks up where you stopped. That's a good design, because a missed day doesn't leave you with a pile of work. But it also means your whole syllabus moves later, while Prelims stays where it is.

My Progress shows how many of the 259 units you've done. It doesn't show your pace, when you'd finish at that pace, or whether that's before Prelims. So after a bad week you can't tell from the app whether you're fine or quietly two months behind. SuperKalam's own blog says this "I can't catch up" feeling is when a lot of aspirants give up.

Other prep apps (Lighthouse Prep, upsc.ai, Proxy Gyan, SyncStudy, Poro) already show students whether they'll finish in time, so the idea itself isn't new. What's missing is that SuperKalam doesn't show it, even though it already has every input it needs: your exam year, a fixed 259-unit path, Mains tags on subjects and your daily progress. Evidence for all of this is in [research.md](research.md).

## Who it's for

Someone self-studying on SuperKalam's GS path with a Prelims date in mind, who misses days sometimes because of illness, a job, family or just a bad week.

## What Comeback does

1. **Setup.** You enter your Prelims date, how many units you do on a normal day, how many days a week you study, how long you keep for revision (30 days by default) and how much faster you're willing to go to catch up (30% by default). Then you can start from zero, copy your numbers from My Progress, or load a sample month.
2. **Progress.** It uses the same 18 subjects and 259 units as SuperKalam. You log units as you go (+1 or +2), and "next up" picks the same unit SuperKalam's Resume would. You can also tick the three daily habits.
3. **On track?** One sentence answers it. For example: "At 1.5 units a day you'd finish on 30 Apr: 21 days after Prelims, with no time to revise." Under it you see your needed, normal and recent pace, and a chart.
4. **What to change if you're behind.** First it tries the smallest change, which is a higher weekly target within your catch-up limit. If that isn't enough, it suggests parking subjects:
   - Mains-only subjects (SuperKalam tags these) wait until after Prelims, biggest first;
   - then subjects you marked "can skim";
   - subjects you marked "must finish" are never parked.

   It only parks as much as it needs to. If it still doesn't fit, it shows the gap and three ways to close it. Every suggestion has a reason, you can switch any of them, and you rate how doable the plan feels (1 to 5).
5. **Coming back after 2+ days off.** You get a short welcome back. Missed news becomes one catch-up read (15 minutes per missed day, 30 to 60 minutes in total). Missed practice and answers aren't made up, because today's are enough.
6. **Progress page.** It shows days studied, comebacks after a gap, units per day and habits. There are no streaks.
7. **Your data.** You can download it as JSON or CSV, start fresh, or delete everything.

What it doesn't do:
- It has no AI in the planner. If an app tells you to drop something before UPSC, you should be able to check why.
- It doesn't link to SuperKalam automatically. You type progress in from My Progress; inside SuperKalam this would be automatic.
- It has no content or reminders, because SuperKalam already does those well.

## Why these rules

| Decision | Why |
|---|---|
| Measure against "revision starts", not Prelims day | You need the last weeks for revision and tests. 30 days is a common buffer, and it's adjustable |
| Normal pace is what you say; recent pace is shown next to it | After a gap your recent pace is low, and new users have no history. Showing both makes the difference visible |
| Catch-up limit of 30% | One prep guide suggests 20–25% of a day for backlog work, so I rounded up. It's a guess I'd tune |
| Mains-only subjects get parked first | Prelims doesn't test them, and SuperKalam already tags them. Once Prelims is over they aren't parked any more |
| Must-finish subjects are never parked | You decide what matters, not the app |
| The app stops after can-skim | Deciding Geography matters less than History for someone would be a guess pretending to be advice |
| One news catch-up read | "Don't read every old paper, use one compilation" is common advice (sources in research.md). The 15 minutes is my estimate |
| Comebacks instead of streaks | A streak is zero exactly when someone needs help coming back |
| You only apply the plan you saw | If progress changed in another tab, the app shows the new plan instead of applying the old one |

## How I'd measure it

The queries are in [database/metrics.sql](../database/metrics.sql).

- **Recovery rate (main metric).** Of people who come back after a 2-day gap, how many are still studying on at least 3 days of their second week back.
- **Return rate (early read).** Of people who go 2 days without doing anything, how many are active again within 3 days. It's quick to read, but someone can come back for one day and disappear again, so it doesn't decide anything on its own.
- **Plans kept.** Was the weekly target met the week after the plan?
- **Overrides per rule.** If people keep un-parking Mains subjects, that rule is wrong.
- **Doable rating.** Does the plan feel possible?
- **Guardrail.** Total units per week, so nobody "fits" by quietly studying less.

Inside SuperKalam I'd A/B test an "on track?" card on My Progress, plus the plan after 2+ days off, and decide on recovery.

## Risks

- Hearing "you'd finish after Prelims" could discourage people instead of motivating them. That's why the page starts with a welcome back, suggests the smallest change first, and always ends with one weekly target. It's the first thing I'd test.
- Units probably aren't all the same length, so "units per day" is rough. It's the unit SuperKalam itself uses, but inside the company I'd use real time per unit.
- SuperKalam's paid Weekly Progress Report might already show pace. If it does, the idea becomes showing it to everyone, at the moment someone comes back.

## Validation plan (not done yet)

No aspirant has used Comeback. What I'd do next:

1. **Check the paid Weekly Progress Report**, to confirm the gap on every plan.
2. **Talk to 5 aspirants** (at least 2 on SuperKalam), 15 minutes each, before showing them anything:
   - When did you last miss 2+ days, and what happened when you came back?
   - Do you know if you'll finish the syllabus before Prelims? How?
   - Have you ever realised too late that you were behind? What did you drop?
   - Do you study Mains-only subjects before Prelims? Why?
3. **Watch them use it** with their real progress. I'd note whether the one-line answer motivates or discourages them, which suggestions they change and why, whether 30% and 30 days feel right, and what rating they give.
4. **Run a two-week pilot** with 8–10 people, measured with the queries above.

I wrote down what would count as a go before doing any of it:

| Signal | Go | Rethink |
|---|---|---|
| "Did that tell you something you didn't know?" | 3 of 5 say yes | 1 or fewer |
| Average doable rating | 4 or more | under 3 |
| Reaction to the one-line answer | mostly useful | mostly discouraging |
| Parking Mains-only before Prelims | most agree | most disagree (then that rule changes) |
