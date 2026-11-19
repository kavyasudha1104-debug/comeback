# Product notes

The problem and the evidence are in the [README](../README.md) and [research.md](research.md). This page covers what Comeback does, why each rule is the way it is, and how I'd measure and test it.

## From a vague problem to something that ships

1. **Vague problem:** students drop off after missing a few days.
2. **What's actually happening:** the path resumes, but nothing says whether you'll still finish before Prelims, so a bad week turns into "I can't catch up".
3. **Smallest thing to ship:** an "on track?" card on My Progress, plus a plan after 2+ days off. Both use data SuperKalam already has.
4. **How we'd know it worked:** more students still studying in their second week back after a gap.

**Who it's for:** someone self-studying on SuperKalam's GS path with a Prelims date in mind, who sometimes misses days because of illness, a job, family or just a bad week.

## What it does

1. **On track?** One sentence answers it. For the sample month: "you'd finish 21 days after Prelims, with no time to revise." Below it you see your needed, normal and recent pace, and a chart.
2. **What to change if you're behind.** First the smallest change: a higher weekly target, within your catch-up limit. If that isn't enough, it suggests parking:
   - Mains-only subjects (SuperKalam tags these) until after Prelims, biggest first
   - then subjects you marked "can skim"
   - never subjects you marked "must finish"

   It only parks as much as it needs to. Every suggestion has a reason, you can switch any of them, and you rate how doable the plan feels (1 to 5).
3. **Coming back after 2+ days off.** A short welcome back. Missed news becomes one catch-up read (15 minutes per missed day, 30 to 60 in total). Missed practice and answers aren't made up.
4. **Logging and progress.** The same 18 subjects and 259 units as SuperKalam, +1/+2 unit buttons, the three daily habits, and a progress page that counts comebacks instead of streaks.

It has no AI in the planner: if an app tells you to drop something before UPSC, you should be able to see why. Progress is typed in here; inside SuperKalam it would be automatic.

## Why these rules

| Decision | Why |
|---|---|
| Measure against "revision starts", not Prelims day | The last weeks are for revision and tests. 30 days by default, adjustable |
| Catch-up limit of 30% | One prep guide suggests 20–25% of a day for backlog; I rounded up. A guess I'd tune |
| Mains-only subjects get parked first | Prelims doesn't test them, and SuperKalam already tags them |
| Must-finish subjects are never parked | The student decides what matters, not the app |
| It stops after can-skim | Deciding Geography matters less than History for someone would be a guess |
| One news catch-up read | Common advice is one compilation, not old papers. The 15 minutes is my estimate |
| Comebacks instead of streaks | A streak drops to zero exactly when someone needs help coming back |

## How I'd measure it

The queries are in [database/metrics.sql](../database/metrics.sql).

- **Recovery (main metric):** of people who come back after a 2-day gap, how many study on at least 3 days of their second week back.
- **Return (early signal):** of people who go 2 days without studying, how many are back within 3 days.
- **Plans kept, overrides per rule, doable rating:** is the plan realistic, and which rule is wrong?
- **Guardrail:** total units per week, so nobody "fits" by studying less.

### As an experiment inside SuperKalam

- **Test:** half of students who miss 2+ days see the welcome back and plan; half see today's app. Same for the "on track?" card on My Progress.
- **Events to track (PostHog):** `pace_viewed`, `plan_previewed`, `plan_applied` (with how many subjects were parked and overridden), `plan_rated`, and the existing study and habit events.
- **Decide on:** recovery. Watch return as the early read, total units per week as the guardrail, and SUPER conversion if the card is shown on the free plan.
- **Ship order:** the card first (no new decisions for the student, just information), then the plan once the card shows people want it.

## Risks

- "You'd finish after Prelims" could discourage people instead of motivating them. That's why it starts with a welcome back and the smallest change. It's the first thing I'd test.
- Units probably vary in length, so "units per day" is rough. Inside SuperKalam I'd use real time per unit.
- The paid Weekly Progress Report might already show pace. If so, the idea becomes showing it to everyone, at the moment someone comes back.

## How I'd test it next

1. Check the paid Weekly Progress Report.
2. Talk to 5 aspirants (at least 2 on SuperKalam) before showing them anything: when did you last miss 2+ days, what happened when you came back, and do you know if you'll finish before Prelims?
3. Watch them use it with their real progress: does the one-line answer motivate or discourage, which suggestions do they change, and do 30% and 30 days feel right?
4. A two-week pilot with 8–10 people, measured with the queries above.
