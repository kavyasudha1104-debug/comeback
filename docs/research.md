# Research

I did this on 9–10 November 2026. Next to each finding I've noted where it comes from:
- **seen**: in my own SuperKalam account (screenshots in `screenshots/superkalam/`)
- **source**: SuperKalam's own pages, its store listings, or another product's page (linked)
- **secondary**: a third-party blog or post
- **my guess**: my own reading, not evidence

## How the idea changed

My first idea was wrong, and finding that out is most of this research.

I first planned a catch-up planner for a pile of missed tasks: you miss three days, come back to all three days' targets on top of today's, and the app decides what to keep and what to drop.

Then I set up targets in the phone app. They turned out to be daily habits (Prelims practice, one Mains answer, news analysis) plus "add up to 5 GS units to complete next". When you miss a day, the habits just reset and the learning path resumes where you stopped. There's no pile, so the first idea solved a problem SuperKalam's design already avoids.

What's actually missing is this: resuming pushes your whole syllabus later, but Prelims doesn't move. My Progress shows units done (0/259), but not your pace, whether you'll finish before revision, or what to drop if you won't. That's what Comeback answers.

## What the app shows (seen, 10 Nov 2026)

| Screen | What's on it | Screenshot |
|---|---|---|
| Home, before targets | "My Targets: Set your targets anytime", an Add Targets button, "2979 completed their targets last week" | [home-before-targets](../screenshots/superkalam/home-before-targets.png) |
| My Targets | Four targets: Daily Prelims Practice, Daily Mains Questions ("write 1 answer daily"), Daily News Analysis, GS Learning ("step-by-step syllabus coverage") | [my-targets](../screenshots/superkalam/my-targets.png) |
| GS Learning target | "Add up to 5 units to complete next", then "Add GS units". You choose the units. No daily pace, no finish date, nothing tied to the exam date | [gs-learning-target](../screenshots/superkalam/gs-learning-target.jpg) |
| Home, after targets | Daily habits, and "Continue Learning: Indian Polity · Unit 1 · Resume" | [home-with-targets](../screenshots/superkalam/home-with-targets.png), [continue-learning](../screenshots/superkalam/continue-learning.png) |
| My Progress | 0/259 units completed, Prelims accuracy, MCQs attempted, Mains answers written, units per subject (Polity 0/35, Ancient History 0/13…). No pace, no projected finish, no exam timeline | [my-progress](../screenshots/superkalam/my-progress.png) |
| Website Learn page | 18 subjects with unit counts. Five are tagged MAINS: Governance, Internal Security, Disaster Management, World History and Ethics. The counts add up to 259, the same as My Progress | (seen 9 Nov; copied into `comeback/catalog.py`) |
| Website streak panel | 3 streak savers a month. A day counts if you do 1 lesson, 10 MCQs, 1 evaluation or the daily news test | (seen 9 Nov) |

I also asked SuperKalam's Ask AI about missed days and targets ([ask-ai-missed-days](../screenshots/superkalam/ask-ai-missed-days.png), [ask-ai-targets](../screenshots/superkalam/ask-ai-targets.png)). For missed days, it said its information doesn't explain how the app handles missed targets. For targets, it listed daily challenges, streaks and a progress dashboard, but found nothing about the app managing or adjusting a personal plan. That's the chatbot's answer, not proof, but it matches what I saw in the app.

What I couldn't see is the paid plan's Weekly Progress Report. The [help page](https://superkalam.com/help-and-support) says SUPER includes a weekly progress report to find strengths and weaknesses. I found nothing saying it covers pace or a finish date, but I haven't seen one.

## What SuperKalam says publicly (source)

- A SuperKalam article from Feb 2025 says that if you miss a session, the AI recalculates and adjusts your future sessions. It doesn't say how. ([article](https://superkalam.com/upsc-preparation/strategy/time-management-app-for-ias-preparation))
- A Play Store review from Aug 2026 (4 stars) says the app "fixes my timetable when I miss a day". ([Play Store](https://play.google.com/store/apps/details?id=com.superkalam&hl=en_IN))
- The app is pitched as a personal timetable, daily targets, reminders and streaks, with a learning path set by the exam year you choose at signup. ([Play Store](https://play.google.com/store/apps/details?id=com.superkalam&hl=en_IN), [homepage](https://superkalam.com/))
- Their own blog says one missed day creates a backlog, the backlog causes stress, and many aspirants stop because they feel they can't catch up. ([blog](https://superkalam.com/upsc-preparation/tips/how-to-be-consistent-in-upsc-preparation-tips-by-toppers))
- The paid FOCUS batch has a fixed timetable with milestones like "this completes the entire Prelims syllabus", plus weekend backlog days. That's a pace plan, but for a whole batch rather than one person. ([FOCUS page](https://superkalam.com/focus-batch-2026-working-professional), [FOCUS 2025 schedule](https://superkalam-public-v2.s3.ap-south-1.amazonaws.com/web/pdfs/FOCUS-2025-Complete-Schedule.pdf))

My guess is that "fixes my timetable" means the path carrying on from where you stopped, which matches what I saw. The paid plan might do more.

## Other apps already do this (source, checked 10 Nov 2026)

That's why I'm not claiming the idea is new.

| Product | What it does |
|---|---|
| [Poro](https://poroapp.com/syllabus-tracker/) | General study app. Says whether you'll finish each subject at your pace ("On track", "Tight", "Short") and how many days late |
| [Lighthouse Prep](https://lighthouseprep.in/study-planner/upsc) | UPSC planner. Plans back from the exam date and cuts the routine down when you fall behind |
| [upsc.ai](https://upsc.ai/tools/upsc-progress-tracker) | UPSC tracker. Advertises an adaptive timetable with "auto slip recovery" |
| [Proxy Gyan](https://www.proxygyan.com/upsc-timetable) | UPSC timetable. Says it tells you when you'll finish each subject |
| [SyncStudy](https://www.syncstudy.in/tools/free-study-timetable-generator) | UPSC timetable. Shifts forward when you miss a day, keeping the exam deadline |

So the gap is inside SuperKalam. Other apps answer "will I finish in time?", and SuperKalam already has what it needs to answer it (exam year, a fixed 259-unit path, daily progress), but it doesn't. Comeback builds the answer on SuperKalam's own structure: its 18 subjects and 259 units, its Mains tags (to decide what can wait) and its three daily habits.

## What users and aspirants say

From SuperKalam reviews (source):
- People mostly praise the discipline features: daily targets, reminders and nudges keep them consistent. ([App Store](https://apps.apple.com/in/app/superkalam-crack-upsc-ias/id6747128599?see-all=reviews&platform=ipad), [Play Store](https://play.google.com/store/apps/details?id=com.superkalam&hl=en_IN))
- The complaints are about crashes, no search or bookmarks in current affairs, some MCQs outside the syllabus, test-series communication, and a power cut during an All-India test being flagged as tab-switching.

On falling behind (secondary):
- A first-person Medium post, "Reasons why I left UPSC": the author couldn't clear a backlog after missing classes and gave up. ([Medium](https://medium.com/being/reasons-why-i-left-upsc-c8c5d0548ac3))
- A UPSC educator suggests keeping buffer days, and striking off a backlog that's become overwhelming rather than chasing it. ([X thread](https://x.com/krishna_tupe/status/1578997344737013760))
- On old newspapers, three sources say much the same thing: chasing a news backlog creates more backlog ([Quora](https://www.quora.com/How-can-I-cover-up-backlog-newspaper-reading-of-5-months-while-preparing-for-UPSC-CSE-2017)), students facing months of it feel like giving up ([Plutus IAS](https://plutusias.com/how-many-months-of-current-affairs-are-enough-for-upsc-prelims/)), so use one compilation ([Raj IAS](https://rajiasacademy.com/upsc-current-affairs-how-much-is-enough/)).
- A coaching guide recommends a priority order when you fall behind, rather than trying to recover everything. ([The Prayas India](https://theprayasindia.com/how-to-manage-time-during-upsc-preparation/))

What this supports:
- The "behind and can't catch up" moment is real. How common it is, only SuperKalam's data could show.
- One catch-up read for missed news is standard advice, not my invention.
- Choosing what to drop is what educators recommend. Apps don't usually do it with reasons.

## What I still don't know

- Does the paid Weekly Progress Report show pace or a finish date?
- How many SuperKalam users have multi-day gaps, and how many stop afterwards?
- Would "you'd finish after Prelims" motivate aspirants or discourage them?
- Does parking Mains-only subjects before Prelims match how they actually study? Some do GS2/GS3 alongside Prelims on purpose.
- Is "units per day" a fair measure, given that units probably vary in length?
