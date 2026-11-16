-- Comeback pilot metrics. Run in the Supabase SQL editor (it runs as the
-- project owner, so it sees everyone's rows). Every query is aggregate only:
-- no names or emails come out. Explained in docs/product.md.

-- name: return_rate
-- Early signal. A "gap" starts when someone who studied goes 2 full days
-- without logging a unit or ticking a habit. Did they do anything within
-- the next 3 days? Only gaps whose 3-day window is over are counted.
with days as (
  select user_id, day as d from public.study_log
  union select user_id, day from public.habit_log
),
gaps as (
  select a.user_id, a.d as last_active
  from days a
  where not exists (select 1 from days b where b.user_id = a.user_id and b.d between a.d + 1 and a.d + 2)
    and a.d + 5 < (now() at time zone 'Asia/Kolkata')::date
)
select count(*) as gaps,
       count(*) filter (where exists (select 1 from days b where b.user_id = g.user_id
                                      and b.d between g.last_active + 3 and g.last_active + 5)) as came_back,
       round(100.0 * count(*) filter (where exists (select 1 from days b where b.user_id = g.user_id
                                      and b.d between g.last_active + 3 and g.last_active + 5))
             / nullif(count(*), 0), 1) as return_rate_pct
from gaps g;

-- name: recovery
-- The decision metric. Of people who came back within 3 days of a gap, how
-- many were still studying a week later: active on at least 3 of the 7
-- days in their second week back? Only counts returns whose second week is over.
with days as (
  select user_id, day as d from public.study_log
  union select user_id, day from public.habit_log
),
gaps as (
  select a.user_id, a.d as last_active from days a
  where not exists (select 1 from days b where b.user_id = a.user_id and b.d between a.d + 1 and a.d + 2)
),
returns as (
  select g.user_id, (select min(b.d) from days b where b.user_id = g.user_id
                     and b.d between g.last_active + 3 and g.last_active + 5) as back
  from gaps g
)
select count(*) as returns,
       count(*) filter (where (select count(*) from days b where b.user_id = r.user_id
                               and b.d between r.back + 7 and r.back + 13) >= 3) as still_studying_week_2,
       round(100.0 * count(*) filter (where (select count(*) from days b where b.user_id = r.user_id
                               and b.d between r.back + 7 and r.back + 13) >= 3) / nullif(count(*), 0), 1)
         as recovery_rate_pct
from returns r
where r.back is not null and r.back + 13 < (now() at time zone 'Asia/Kolkata')::date;

-- name: plan_kept
-- Was the plan realistic? Of plans whose first week is over, how many had
-- at least their weekly target of units logged in the 7 days after.
select count(*) as plans_with_week_over,
       count(*) filter (where coalesce(u.units, 0) >= p.weekly_target) as target_met,
       round(100.0 * count(*) filter (where coalesce(u.units, 0) >= p.weekly_target) / nullif(count(*), 0), 1)
         as plan_kept_pct
from public.plans p
left join lateral (select sum(units) as units from public.study_log l
                   where l.user_id = p.user_id and l.day between p.made_on and p.made_on + 6) u on true
where p.made_on + 6 < (now() at time zone 'Asia/Kolkata')::date and p.weekly_target > 0;

-- name: override_rate
-- How often people disagree with the parking rules.
select count(*) as plans,
       sum(overrides) as subjects_parked_by_choice,
       count(*) filter (where overrides > 0) as plans_with_a_change,
       round(avg(parked_units), 1) as avg_units_parked
from public.plans;

-- name: overrides_by_rule
-- Which rule people overrule most: the one to look at first.
select props->>'rule' as rule, props->>'to' as changed_to, count(*) as times
from public.events where name = 'decision_changed'
group by 1, 2 order by times desc;

-- name: doable_rating
select count(doable) as rated, round(avg(doable), 2) as avg_doable,
       count(*) filter (where doable >= 4) as rated_4_or_5,
       count(*) filter (where doable <= 2) as rated_1_or_2
from public.plans;

-- name: status_when_planning
-- How far behind people are when they ask for a plan.
select status_before, count(*) as plans, round(avg(needed_before), 2) as avg_needed_pace
from public.plans group by 1 order by 2 desc;

-- name: funnel
-- People who looked at the pace page -> saw a plan -> applied one.
select
  (select count(distinct user_id) from public.events where name = 'pace_viewed') as viewed_pace,
  (select count(distinct user_id) from public.events where name = 'plan_previewed') as previewed_plan,
  (select count(distinct user_id) from public.events where name = 'plan_applied') as applied_plan;
