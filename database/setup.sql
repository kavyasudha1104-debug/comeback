-- Comeback: schema, access rules and server functions.
--
-- What it stores, mirroring SuperKalam's own structure:
--   * progress through SuperKalam's GS learning path: 18 subjects, 259 units
--   * a log of units studied each day, and the three daily habits
--     (Prelims practice, a Mains answer, News analysis)
--   * catch-up plans: which subjects were parked, and why
--
-- How access works:
--   * Every table has row level security. Signed-in users can SELECT only
--     their own rows. There are no INSERT/UPDATE/DELETE policies at all.
--   * Every write goes through a function below. They run as the owner,
--     take the user from auth.uid(), lock what they change, and check every
--     input. A user calling the API directly with their own token can't do
--     anything the app can't.
--   * Helpers and the subject catalog live in a "private" schema that
--     Supabase doesn't expose.
--   * Nothing is granted to anon. The service-role key is never used.
--
-- "Today" is always India time, decided by the server.

create schema if not exists private;
revoke all on schema private from public;

-- ---------------------------------------------------------------------------
-- helpers
-- ---------------------------------------------------------------------------

create or replace function private.uid() returns uuid
language plpgsql stable set search_path = '' as $$
declare u uuid := auth.uid();
begin
  if u is null then
    raise exception 'Your session ended. Press Start to begin again.' using hint = 'auth';
  end if;
  return u;
end $$;

create or replace function private.today() returns date
language sql stable set search_path = '' as $$
  select (now() at time zone 'Asia/Kolkata')::date
$$;

create or replace function private.fail(msg text, code text default 'invalid') returns void
language plpgsql set search_path = '' as $$
begin
  raise exception '%', msg using hint = code;
end $$;

-- SuperKalam's learning path (Learn page, 9 Nov 2026: 18 subjects, 259 units).
-- Must match comeback/catalog.py; a test checks they agree.
create table private.subjects (
  key        text primary key,
  units      int not null check (units > 0),
  mains_only boolean not null,
  position   int not null unique
);
insert into private.subjects (key, units, mains_only, position) values
  ('polity', 35, false, 1), ('economy', 18, false, 2), ('ir', 18, false, 3), ('social', 13, false, 4),
  ('governance', 5, true, 5), ('security', 6, true, 6), ('environment', 21, false, 7),
  ('indian_geo', 16, false, 8), ('physical_geo', 11, false, 9), ('scitech', 10, false, 10),
  ('world_geo', 5, false, 11), ('disaster', 4, true, 12), ('ancient', 13, false, 13),
  ('medieval', 23, false, 14), ('modern', 22, false, 15), ('art', 16, false, 16),
  ('world_history', 11, true, 17), ('ethics', 12, true, 18);

-- ---------------------------------------------------------------------------
-- tables
-- ---------------------------------------------------------------------------

create table public.profiles (
  user_id             uuid primary key references auth.users (id) on delete cascade,
  name                text not null default '' check (char_length(name) <= 60),
  exam_date           date not null,
  revision_days       int not null default 30 check (revision_days between 0 and 120),
  units_per_day       numeric(3,1) not null default 1.5 check (units_per_day between 0.5 and 10),
  study_days_per_week int not null default 6 check (study_days_per_week between 1 and 7),
  catchup_share       numeric(3,2) not null default 0.30 check (catchup_share between 0.10 and 0.50),
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);

create table public.plans (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references auth.users (id) on delete cascade,
  made_on         date not null,
  created_at      timestamptz not null default now(),
  status_before   text not null,
  status_after    text not null,
  needed_before   numeric(6,3) not null,
  needed_after    numeric(6,3) not null,
  parked_units    int not null,
  shortfall       int not null,
  overrides       int not null,
  weekly_target   int not null,
  rules           jsonb not null default '{}',
  doable          smallint check (doable between 1 and 5)
);
create index plans_user on public.plans (user_id, created_at desc);

create table public.subject_progress (
  user_id        uuid not null references auth.users (id) on delete cascade,
  subject        text not null,
  done           int not null default 0 check (done >= 0),
  status         text not null default 'active' check (status in ('active', 'parked')),
  priority       text not null default 'normal' check (priority in ('must', 'normal', 'skim')),
  parked_rule    text,
  parked_reason  text check (char_length(parked_reason) <= 300),
  plan_id        uuid references public.plans (id) on delete set null,
  version        int not null default 1,
  updated_at     timestamptz not null default now(),
  primary key (user_id, subject)
);

create table public.study_log (
  id          bigint generated always as identity primary key,
  user_id     uuid not null references auth.users (id) on delete cascade,
  day         date not null,
  subject     text not null,
  units       int not null check (units between 1 and 10),
  created_at  timestamptz not null default now()
);
create index study_log_user_day on public.study_log (user_id, day);

create table public.habit_log (
  user_id     uuid not null references auth.users (id) on delete cascade,
  day         date not null,
  habit       text not null check (habit in ('prelims', 'mains', 'news')),
  created_at  timestamptz not null default now(),
  primary key (user_id, day, habit)
);

create table public.events (
  id       bigint generated always as identity primary key,
  user_id  uuid not null references auth.users (id) on delete cascade,
  name     text not null,
  props    jsonb not null default '{}' check (pg_column_size(props) <= 2048),
  at       timestamptz not null default now()
);
create index events_user_at on public.events (user_id, at);
create index events_name_at on public.events (name, at);

-- ---------------------------------------------------------------------------
-- access: read your own rows, write nothing directly
-- ---------------------------------------------------------------------------

alter table public.profiles         enable row level security;
alter table public.plans            enable row level security;
alter table public.subject_progress enable row level security;
alter table public.study_log        enable row level security;
alter table public.habit_log        enable row level security;
alter table public.events           enable row level security;

revoke all on public.profiles, public.plans, public.subject_progress, public.study_log, public.habit_log, public.events
  from public, anon, authenticated;
grant select on public.profiles, public.plans, public.subject_progress, public.study_log, public.habit_log, public.events
  to authenticated;

create policy "read own profile"  on public.profiles         for select to authenticated using (user_id = (select auth.uid()));
create policy "read own plans"    on public.plans            for select to authenticated using (user_id = (select auth.uid()));
create policy "read own progress" on public.subject_progress for select to authenticated using (user_id = (select auth.uid()));
create policy "read own log"      on public.study_log        for select to authenticated using (user_id = (select auth.uid()));
create policy "read own habits"   on public.habit_log        for select to authenticated using (user_id = (select auth.uid()));
create policy "read own events"   on public.events           for select to authenticated using (user_id = (select auth.uid()));

create or replace function private.log(u uuid, ev text, p jsonb default '{}') returns void
language sql set search_path = '' as $$
  insert into public.events (user_id, name, props) values (u, ev, coalesce(p, '{}'));
$$;

create or replace function private.subject(k text) returns private.subjects
language plpgsql stable set search_path = '' as $$
declare s private.subjects;
begin
  select * into s from private.subjects where key = k;
  if not found then perform private.fail('Unknown subject.'); end if;
  return s;
end $$;

-- ---------------------------------------------------------------------------
-- profile
-- ---------------------------------------------------------------------------

create or replace function public.server_today() returns date
language sql stable security definer set search_path = '' as $$
  select private.today()
$$;

create or replace function public.my_profile() returns jsonb
language sql stable security definer set search_path = '' as $$
  select to_jsonb(p) - 'user_id' from public.profiles p where p.user_id = private.uid()
$$;

create or replace function public.save_profile(p_name text, p_exam_date date, p_revision_days int,
                                               p_units_per_day double precision, p_days_per_week int,
                                               p_share double precision)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  u uuid := private.uid();
  r public.profiles;
  is_new boolean;
begin
  if p_exam_date is null or p_exam_date not between private.today() and private.today() + 1100 then
    perform private.fail('Prelims date should be within the next three years.');
  end if;
  if p_revision_days is null or p_revision_days not between 0 and 120 then
    perform private.fail('Revision time must be between 0 and 120 days.');
  end if;
  if p_units_per_day is null or p_units_per_day not between 0.5 and 10 then
    perform private.fail('Units per day must be between 0.5 and 10.');
  end if;
  if p_days_per_week is null or p_days_per_week not between 1 and 7 then
    perform private.fail('Study days per week must be between 1 and 7.');
  end if;
  if p_share is null or p_share not between 0.10 and 0.50 then
    perform private.fail('Catch-up limit must be between 10% and 50%.');
  end if;

  is_new := not exists (select 1 from public.profiles where user_id = u);
  insert into public.profiles as pr (user_id, name, exam_date, revision_days, units_per_day,
                                     study_days_per_week, catchup_share)
  values (u, left(btrim(coalesce(p_name, '')), 60), p_exam_date, p_revision_days,
          round(p_units_per_day::numeric, 1), p_days_per_week, round(p_share::numeric, 2))
  on conflict (user_id) do update
    set name = excluded.name, exam_date = excluded.exam_date, revision_days = excluded.revision_days,
        units_per_day = excluded.units_per_day, study_days_per_week = excluded.study_days_per_week,
        catchup_share = excluded.catchup_share, updated_at = now()
  returning * into r;

  insert into public.subject_progress (user_id, subject)
  select u, s.key from private.subjects s
  on conflict do nothing;

  perform private.log(u, case when is_new then 'profile_created' else 'profile_updated' end,
    jsonb_build_object('units_per_day', p_units_per_day, 'days_to_exam', p_exam_date - private.today(),
                       'revision_days', p_revision_days, 'share', p_share));
  return to_jsonb(r) - 'user_id';
end $$;

-- ---------------------------------------------------------------------------
-- reading everything the app needs, in one call
-- ---------------------------------------------------------------------------

create or replace function public.my_state(p_days int default 120) returns jsonb
language sql stable security definer set search_path = '' as $$
  with me as (select private.uid() as u, private.today() as t,
                     least(greatest(coalesce(p_days, 120), 7), 400) as n)
  select jsonb_build_object(
    'today', (select t from me),
    'subjects', coalesce((select jsonb_agg(to_jsonb(sp) - 'user_id' order by s.position)
                          from public.subject_progress sp
                          join private.subjects s on s.key = sp.subject, me
                          where sp.user_id = me.u), '[]'),
    'logs', coalesce((select jsonb_agg(jsonb_build_object('id', l.id, 'day', l.day, 'subject', l.subject,
                                                          'units', l.units) order by l.day, l.id)
                      from public.study_log l, me
                      where l.user_id = me.u and l.day >= me.t - me.n), '[]'),
    'habits', coalesce((select jsonb_agg(jsonb_build_object('day', h.day, 'habit', h.habit) order by h.day)
                        from public.habit_log h, me
                        where h.user_id = me.u and h.day >= me.t - me.n), '[]'),
    'plans', coalesce((select jsonb_agg(to_jsonb(p) - 'user_id' order by p.created_at desc)
                       from (select * from public.plans, me where user_id = me.u
                             order by created_at desc limit 20) p), '[]'))
$$;

-- ---------------------------------------------------------------------------
-- progress
-- ---------------------------------------------------------------------------

-- Set how many units of a subject are done (first-time setup, or a correction).
-- Doesn't count as studying today.
create or replace function public.set_done(p_subject text, p_done int, p_version int default null)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  u uuid := private.uid();
  s private.subjects := private.subject(p_subject);
  r public.subject_progress;
begin
  select * into r from public.subject_progress where user_id = u and subject = p_subject for update;
  if not found then perform private.fail('Set up your profile first.', 'gone'); end if;
  if p_version is not null and p_version <> r.version then
    perform private.fail('This changed in another tab. Refreshed it for you.', 'stale');
  end if;
  if p_done is null or p_done not between 0 and s.units then
    perform private.fail(format('Units done must be between 0 and %s.', s.units));
  end if;
  update public.subject_progress set done = p_done, version = version + 1, updated_at = now()
    where user_id = u and subject = p_subject returning * into r;
  perform private.log(u, 'progress_set', jsonb_build_object('subject', p_subject, 'done', p_done));
  return to_jsonb(r) - 'user_id';
end $$;

-- "I just finished N units of this subject."
create or replace function public.log_units(p_subject text, p_units int)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  u uuid := private.uid();
  s private.subjects := private.subject(p_subject);
  r public.subject_progress;
  add int;
begin
  if p_units is null or p_units not between 1 and 10 then
    perform private.fail('Log between 1 and 10 units at a time.');
  end if;
  select * into r from public.subject_progress where user_id = u and subject = p_subject for update;
  if not found then perform private.fail('Set up your profile first.', 'gone'); end if;
  if r.status = 'parked' then
    perform private.fail('This subject is parked. Bring it back first.');
  end if;
  add := least(p_units, s.units - r.done);
  if add <= 0 then perform private.fail('This subject is already complete.'); end if;
  insert into public.study_log (user_id, day, subject, units) values (u, private.today(), p_subject, add);
  update public.subject_progress set done = done + add, version = version + 1, updated_at = now()
    where user_id = u and subject = p_subject returning * into r;
  perform private.log(u, 'units_logged', jsonb_build_object('subject', p_subject, 'units', add));
  return to_jsonb(r) - 'user_id';
end $$;

-- Undo a log entry from today (a mis-tap).
create or replace function public.undo_log(p_id bigint) returns void
language plpgsql security definer set search_path = '' as $$
declare
  u uuid := private.uid();
  l public.study_log;
begin
  select * into l from public.study_log where id = p_id and user_id = u;
  if not found then perform private.fail('That entry no longer exists.', 'gone'); end if;
  if l.day <> private.today() then perform private.fail('Only today''s entries can be undone.'); end if;
  perform 1 from public.subject_progress where user_id = u and subject = l.subject for update;
  delete from public.study_log where id = l.id;
  update public.subject_progress set done = greatest(0, done - l.units), version = version + 1, updated_at = now()
    where user_id = u and subject = l.subject;
  perform private.log(u, 'units_undone', jsonb_build_object('subject', l.subject, 'units', l.units));
end $$;

create or replace function public.set_habit(p_habit text, p_done boolean) returns void
language plpgsql security definer set search_path = '' as $$
declare u uuid := private.uid();
begin
  if p_habit not in ('prelims', 'mains', 'news') then perform private.fail('Unknown habit.'); end if;
  if p_done then
    insert into public.habit_log (user_id, day, habit) values (u, private.today(), p_habit) on conflict do nothing;
  else
    delete from public.habit_log where user_id = u and day = private.today() and habit = p_habit;
  end if;
  perform private.log(u, case when p_done then 'habit_done' else 'habit_undone' end,
                      jsonb_build_object('habit', p_habit));
end $$;

create or replace function public.set_priority(p_subject text, p_priority text, p_version int default null)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  u uuid := private.uid();
  r public.subject_progress;
begin
  perform private.subject(p_subject);
  if p_priority not in ('must', 'normal', 'skim') then perform private.fail('Unknown priority.'); end if;
  select * into r from public.subject_progress where user_id = u and subject = p_subject for update;
  if not found then perform private.fail('Set up your profile first.', 'gone'); end if;
  if p_version is not null and p_version <> r.version then
    perform private.fail('This changed in another tab. Refreshed it for you.', 'stale');
  end if;
  update public.subject_progress set priority = p_priority, version = version + 1, updated_at = now()
    where user_id = u and subject = p_subject returning * into r;
  perform private.log(u, 'priority_set', jsonb_build_object('subject', p_subject, 'priority', p_priority));
  return to_jsonb(r) - 'user_id';
end $$;

create or replace function public.restore_subject(p_subject text) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  u uuid := private.uid();
  r public.subject_progress;
begin
  perform private.subject(p_subject);
  select * into r from public.subject_progress where user_id = u and subject = p_subject for update;
  if not found or r.status <> 'parked' then
    perform private.fail('Only parked subjects can be brought back.', 'stale');
  end if;
  update public.subject_progress set status = 'active', parked_rule = null, parked_reason = null,
         version = version + 1, updated_at = now()
    where user_id = u and subject = p_subject returning * into r;
  perform private.log(u, 'subject_restored', jsonb_build_object('subject', p_subject, 'rule', r.parked_rule));
  return to_jsonb(r) - 'user_id';
end $$;

-- ---------------------------------------------------------------------------
-- catch-up plans
-- ---------------------------------------------------------------------------
-- The plan is worked out in Python so it can be previewed and changed. This
-- function trusts none of it: the plan must cover exactly the user's current
-- unfinished active subjects, nothing may have changed since the preview,
-- and every parking decision must follow the rule it claims.

create or replace function public.apply_plan(p_plan jsonb) returns uuid
language plpgsql security definer set search_path = '' as $$
declare
  u uuid := private.uid();
  today date := private.today();
  open_subjects text[];
  seen text[] := '{}';
  it jsonb;
  r public.subject_progress;
  s private.subjects;
  v_plan uuid;
  v_rule text;
  v_parked int := 0;
  v_overrides int := 0;
  v_target int;
  sm jsonb := coalesce(p_plan->'summary', '{}');
begin
  if coalesce(p_plan->>'today', '') <> today::text then
    perform private.fail('The day changed since this plan was made. Here''s a fresh one.', 'stale_plan');
  end if;
  begin
    v_target := (p_plan->>'weekly_target')::int;
  exception when others then
    perform private.fail('Bad weekly target.', 'stale_plan');
  end;
  if v_target is null or v_target not between 0 and 70 then
    perform private.fail('Bad weekly target.', 'stale_plan');
  end if;

  -- lock every subject row: a second tab applying at the same time waits,
  -- then finds the versions changed and is told to refresh
  select array_agg(subject order by subject) into open_subjects
  from (select sp.subject from public.subject_progress sp join private.subjects cat on cat.key = sp.subject
        where sp.user_id = u and sp.status = 'active' and sp.done < cat.units
        order by sp.subject for update of sp) x;
  if open_subjects is null then
    perform private.fail('Nothing left to plan.', 'stale_plan');
  end if;

  insert into public.plans (user_id, made_on, status_before, status_after, needed_before, needed_after,
                            parked_units, shortfall, overrides, weekly_target, rules)
  values (u, today, left(coalesce(sm->>'status_before', ''), 20), left(coalesce(sm->>'status_after', ''), 20),
          least(greatest(coalesce((sm->>'needed_before')::numeric, 0), 0), 999),
          least(greatest(coalesce((sm->>'needed_after')::numeric, 0), 0), 999),
          0, least(greatest(coalesce((sm->>'shortfall')::int, 0), 0), 10000), 0, v_target,
          case when jsonb_typeof(sm->'rules') = 'object' then sm->'rules' else '{}' end)
  returning id into v_plan;

  for it in select * from jsonb_array_elements(coalesce(p_plan->'keep', '[]'))
            union all select * from jsonb_array_elements(coalesce(p_plan->'park', '[]')) loop
    select * into r from public.subject_progress where user_id = u and subject = it->>'subject';
    if not found or r.status <> 'active' or r.version <> (it->>'version')::int then
      perform private.fail('Something changed since you opened this plan. Here''s a fresh one.', 'stale_plan');
    end if;
    if r.subject = any(seen) then perform private.fail('A subject appears twice in the plan.', 'stale_plan'); end if;
    seen := seen || r.subject;
  end loop;

  if (select array_agg(x order by x) from unnest(seen) x) is distinct from open_subjects then
    perform private.fail('Something changed since you opened this plan. Here''s a fresh one.', 'stale_plan');
  end if;

  for it in select * from jsonb_array_elements(coalesce(p_plan->'park', '[]')) loop
    select * into r from public.subject_progress where user_id = u and subject = it->>'subject';
    s := private.subject(r.subject);
    v_rule := it->>'rule';
    if v_rule = 'override' then
      v_overrides := v_overrides + 1;
    elsif v_rule = 'mains_only' then
      if not s.mains_only or r.priority = 'must' then
        perform private.fail('Only Mains-only subjects you haven''t marked must-finish can be parked by that rule.', 'stale_plan');
      end if;
    elsif v_rule = 'skim' then
      if r.priority <> 'skim' then
        perform private.fail('Only subjects marked can-skim can be parked by that rule.', 'stale_plan');
      end if;
    else
      perform private.fail('Unknown rule.', 'stale_plan');
    end if;
    update public.subject_progress
      set status = 'parked', parked_rule = v_rule, parked_reason = left(coalesce(it->>'reason', ''), 300),
          plan_id = v_plan, version = version + 1, updated_at = now()
      where user_id = u and subject = r.subject;
    v_parked := v_parked + (s.units - r.done);
  end loop;

  -- stamp the kept subjects too, so replaying this exact plan is refused as stale
  update public.subject_progress set plan_id = v_plan, version = version + 1, updated_at = now()
    where user_id = u and status = 'active' and subject = any(seen);

  update public.plans set parked_units = v_parked, overrides = v_overrides where id = v_plan;
  perform private.log(u, 'plan_applied', jsonb_build_object(
    'plan_id', v_plan, 'status_before', sm->>'status_before', 'status_after', sm->>'status_after',
    'parked_units', v_parked, 'overrides', v_overrides, 'weekly_target', v_target));
  return v_plan;
end $$;

create or replace function public.rate_plan(p_id uuid, p_doable int) returns void
language plpgsql security definer set search_path = '' as $$
declare u uuid := private.uid();
begin
  if p_doable is null or p_doable not between 1 and 5 then perform private.fail('Rating must be 1 to 5.'); end if;
  update public.plans set doable = p_doable where id = p_id and user_id = u;
  if not found then perform private.fail('That plan no longer exists.', 'gone'); end if;
  perform private.log(u, 'plan_rated', jsonb_build_object('plan_id', p_id, 'doable', p_doable));
end $$;

-- ---------------------------------------------------------------------------
-- sample data, reset, events, your data
-- ---------------------------------------------------------------------------

-- A realistic month for trying the app: about 2 units a day for three weeks,
-- then the last five days missed. Exam in 150 days. Replaces your progress.
create or replace function public.load_sample() returns void
language plpgsql security definer set search_path = '' as $$
declare
  u uuid := private.uid();
  t date := private.today();
  d int;
  i int := 0;
  subj text;
  study_days int[] := array[30,28,27,26,25,23,22,21,20,18,17,16,15,13,12,11,10,8,7,6];
begin
  if not exists (select 1 from public.profiles where user_id = u) then
    perform private.fail('Set up your profile first.', 'gone');
  end if;
  delete from public.study_log where user_id = u;
  delete from public.habit_log where user_id = u;
  update public.subject_progress set done = 0, status = 'active', priority = 'normal', parked_rule = null,
         parked_reason = null, plan_id = null, version = version + 1, updated_at = now()
    where user_id = u;
  delete from public.plans where user_id = u;
  update public.profiles set exam_date = t + 150, revision_days = 30, units_per_day = 1.5,
         study_days_per_week = 6, catchup_share = 0.30, updated_at = now()
    where user_id = u;

  foreach d in array study_days loop
    i := i + 1;
    subj := case when i <= 10 then 'polity' when i <= 16 then 'modern' else 'economy' end;
    insert into public.study_log (user_id, day, subject, units) values (u, t - d, subj, 2);
    insert into public.habit_log (user_id, day, habit) values (u, t - d, 'prelims'), (u, t - d, 'news');
    if i % 2 = 0 then
      insert into public.habit_log (user_id, day, habit) values (u, t - d, 'mains');
    end if;
  end loop;
  update public.subject_progress sp set done = x.n, version = version + 1
    from (select subject, sum(units)::int n from public.study_log where user_id = u group by subject) x
    where sp.user_id = u and sp.subject = x.subject;
  update public.subject_progress set priority = 'skim', version = version + 1
    where user_id = u and subject in ('art', 'world_geo');
  update public.subject_progress set priority = 'must', version = version + 1
    where user_id = u and subject = 'polity';
  perform private.log(u, 'sample_loaded', '{}');
end $$;

create or replace function public.reset_progress() returns void
language plpgsql security definer set search_path = '' as $$
declare u uuid := private.uid();
begin
  delete from public.study_log where user_id = u;
  delete from public.habit_log where user_id = u;
  update public.subject_progress set done = 0, status = 'active', priority = 'normal', parked_rule = null,
         parked_reason = null, plan_id = null, version = version + 1, updated_at = now()
    where user_id = u;
  delete from public.plans where user_id = u;
  perform private.log(u, 'progress_reset', '{}');
end $$;

-- Events the browser may report. Everything important is logged by the
-- functions above instead, because those can't be faked or skipped.
create or replace function public.log_event(p_name text, p_props jsonb default '{}') returns void
language plpgsql security definer set search_path = '' as $$
declare u uuid := private.uid();
begin
  if p_name not in ('plan_previewed', 'decision_changed', 'data_exported', 'pace_viewed') then
    perform private.fail('Unknown event.');
  end if;
  if jsonb_typeof(coalesce(p_props, '{}')) <> 'object' or pg_column_size(p_props) > 1024 then
    perform private.fail('Event details too large.');
  end if;
  if (select count(*) from public.events where user_id = u and at > now() - interval '1 day') >= 500 then
    return;   -- quietly drop; never break the app over analytics
  end if;
  perform private.log(u, p_name, p_props);
end $$;

create or replace function public.export_my_data() returns jsonb
language sql stable security definer set search_path = '' as $$
  select jsonb_build_object(
    'profile',  (select to_jsonb(p) - 'user_id' from public.profiles p where user_id = private.uid()),
    'subjects', coalesce((select jsonb_agg(to_jsonb(s) - 'user_id' order by subject)
                          from public.subject_progress s where user_id = private.uid()), '[]'),
    'study_log', coalesce((select jsonb_agg(to_jsonb(l) - 'user_id' order by day, id)
                           from public.study_log l where user_id = private.uid()), '[]'),
    'habits',   coalesce((select jsonb_agg(to_jsonb(h) - 'user_id' order by day)
                          from public.habit_log h where user_id = private.uid()), '[]'),
    'plans',    coalesce((select jsonb_agg(to_jsonb(p) - 'user_id' order by created_at)
                          from public.plans p where user_id = private.uid()), '[]'))
$$;

create or replace function public.delete_my_data() returns void
language plpgsql security definer set search_path = '' as $$
declare u uuid := private.uid();
begin
  delete from public.study_log where user_id = u;
  delete from public.habit_log where user_id = u;
  delete from public.subject_progress where user_id = u;
  delete from public.plans where user_id = u;
  delete from public.events where user_id = u;
  delete from public.profiles where user_id = u;
end $$;

-- ---------------------------------------------------------------------------
-- who can call what
-- ---------------------------------------------------------------------------

-- private helpers are only ever called from inside the functions above,
-- which run as the owner. Nobody else gets to see or call them.
revoke all on all functions in schema private from public, anon, authenticated;
revoke all on all tables in schema private from public, anon, authenticated;

do $$
declare f text;
begin
  foreach f in array array[
    'server_today()', 'my_profile()', 'save_profile(text,date,int,double precision,int,double precision)',
    'my_state(int)', 'set_done(text,int,int)', 'log_units(text,int)', 'undo_log(bigint)',
    'set_habit(text,boolean)', 'set_priority(text,text,int)', 'restore_subject(text)',
    'apply_plan(jsonb)', 'rate_plan(uuid,int)', 'load_sample()', 'reset_progress()',
    'log_event(text,jsonb)', 'export_my_data()', 'delete_my_data()']
  loop
    execute format('revoke all on function public.%s from public, anon', f);
    execute format('grant execute on function public.%s to authenticated', f);
  end loop;
end $$;
