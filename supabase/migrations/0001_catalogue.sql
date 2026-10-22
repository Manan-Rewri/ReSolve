-- ReSolve: catalogue, practice state, and public profiles.
--
-- This is the schema the app actually uses. The catalogue is seeded from
-- `supabase/seed/`, and the practice state is written by the API with the
-- service-role key (the browser never talks to these tables directly).
--
-- Two axes stay separate, deliberately:
--
--   problems.difficulty  the community-wide tag: Easy, Medium, Hard
--   review_logs.rating   how that attempt felt for this user: medium, hard, extreme
--
-- `very easy` is not in `review_logs`: it is a decision not to schedule the
-- problem at all, so it removes the card instead of producing a review.

-- ---------------------------------------------------------------- catalogue

create table if not exists public.problems (
  id                 uuid primary key default gen_random_uuid(),
  slug               text not null unique,
  title              text not null,
  difficulty         text not null check (difficulty in ('Easy', 'Medium', 'Hard')),
  tags               text[] not null default '{}',
  statement          text not null,
  examples           jsonb not null default '[]',
  constraints        jsonb not null default '[]',

  -- The function the user has to write, and its parameters as [type, name].
  signature          text not null,
  params             jsonb not null default '[]',

  -- The C++ that goes around the user's function. The editor holds the
  -- function alone; the server splices it between these two.
  reference_solution text not null,
  prefix             text not null,
  suffix             text not null,
  editor_start       text not null,
  -- Set when the function returns nothing and this parameter holds the answer.
  print_param        text,

  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now()
);

comment on column public.problems.difficulty is
  'Community-wide tag. Never the user''s own sense of how hard it was.';

create table if not exists public.test_cases (
  id            uuid primary key default gen_random_uuid(),
  problem_id    uuid not null references public.problems (id) on delete cascade,
  position      int  not null,
  -- One C++ initialiser expression per parameter, in order.
  args          jsonb not null,
  -- What the reference solution printed. Measured, never predicted.
  expected      text not null,
  note          text not null default '',
  unique (problem_id, position)
);

create index if not exists test_cases_problem_idx
  on public.test_cases (problem_id, position);

-- A course: a named group of problems, in the order they should be done.
create table if not exists public.sheets (
  id          text primary key,
  name        text not null,
  blurb       text not null default '',
  tier        text not null default '',
  position    int  not null default 0,
  created_at  timestamptz not null default now()
);

create table if not exists public.sheet_problems (
  sheet_id      text not null references public.sheets (id) on delete cascade,
  problem_slug  text not null references public.problems (slug) on delete cascade,
  position      int  not null,
  primary key (sheet_id, problem_slug),
  unique (sheet_id, position)
);

create index if not exists sheet_problems_sheet_idx
  on public.sheet_problems (sheet_id, position);

-- ------------------------------------------------------------------- people

-- Mirrors auth.users. The API writes it with the service-role key.
create table if not exists public.profiles (
  id          uuid primary key references auth.users (id) on delete cascade,
  username    text not null default '',
  -- The share link is /p/<token>. Generated when the user asks for one.
  share_token text unique,
  is_public   boolean not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

-- ------------------------------------------------------------ practice state

-- One card per (user, problem). `stability_days` is the number of days until
-- predicted recall falls to 90%; `due_at` is when it comes back.
create table if not exists public.card_state (
  user_id           uuid not null references auth.users (id) on delete cascade,
  problem_slug      text not null references public.problems (slug) on delete cascade,
  state             text not null default 'learning'
                      check (state in ('new', 'learning', 'review', 'graduated')),
  stability_days    double precision not null check (stability_days >= 0),
  due_at            timestamptz not null,
  reps              int not null default 0 check (reps >= 0),
  lapses            int not null default 0 check (lapses >= 0),
  last_rating       text check (last_rating in ('medium', 'hard', 'extreme')),
  last_reviewed_at  timestamptz,
  updated_at        timestamptz not null default now(),
  primary key (user_id, problem_slug)
);

create index if not exists card_state_due_idx
  on public.card_state (user_id, due_at);

-- A problem the user got fully right. The tick in Learn reads this.
create table if not exists public.solved_problems (
  user_id       uuid not null references auth.users (id) on delete cascade,
  problem_slug  text not null references public.problems (slug) on delete cascade,
  solved_at     timestamptz not null default now(),
  primary key (user_id, problem_slug)
);

-- The review log. The dashboard and profile read it; the scheduler never does,
-- because a rating already carries everything it needs.
create table if not exists public.review_logs (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users (id) on delete cascade,
  problem_slug  text not null references public.problems (slug) on delete cascade,
  rating        text not null check (rating in ('medium', 'hard', 'extreme')),
  created_at    timestamptz not null default now()
);

create index if not exists review_logs_user_idx
  on public.review_logs (user_id, created_at desc);

-- ----------------------------------------------------------- write functions

-- Record a review and its resulting card in one transaction. The API calls
-- this with the service-role key; the browser never gets execute permission.
create or replace function public.record_review(
  p_user_id uuid,
  p_problem_slug text,
  p_rating text,
  p_state text,
  p_stability_days double precision,
  p_due_at timestamptz,
  p_reps int,
  p_lapses int,
  p_last_reviewed_at timestamptz
) returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  if p_rating not in ('medium', 'hard', 'extreme') then
    raise exception 'invalid rating: %', p_rating;
  end if;
  if p_state not in ('new', 'learning', 'review', 'graduated') then
    raise exception 'invalid card state: %', p_state;
  end if;

  insert into card_state (
    user_id, problem_slug, state, stability_days, due_at, reps, lapses,
    last_rating, last_reviewed_at, updated_at
  ) values (
    p_user_id, p_problem_slug, p_state, p_stability_days, p_due_at, p_reps, p_lapses,
    p_rating, p_last_reviewed_at, now()
  )
  on conflict (user_id, problem_slug) do update set
    state = excluded.state,
    stability_days = excluded.stability_days,
    due_at = excluded.due_at,
    reps = excluded.reps,
    lapses = excluded.lapses,
    last_rating = excluded.last_rating,
    last_reviewed_at = excluded.last_reviewed_at,
    updated_at = now();

  insert into review_logs (user_id, problem_slug, rating, created_at)
  values (p_user_id, p_problem_slug, p_rating, coalesce(p_last_reviewed_at, now()));
end;
$$;

-- One-time transfer of a browser's localStorage bucket. Refuses to run when
-- the user already has database state, so it cannot duplicate a review log.
create or replace function public.import_practice_state(
  p_user_id uuid,
  p_cards jsonb,
  p_solved jsonb,
  p_history jsonb
) returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  if exists (select 1 from card_state where user_id = p_user_id)
     or exists (select 1 from solved_problems where user_id = p_user_id)
     or exists (select 1 from review_logs where user_id = p_user_id) then
    raise exception 'practice state already exists for this user';
  end if;

  insert into card_state (
    user_id, problem_slug, state, stability_days, due_at, reps, lapses,
    last_rating, last_reviewed_at
  )
  select
    p_user_id,
    c->>'slug',
    coalesce(c->>'state', 'review'),
    (c->>'stability_days')::double precision,
    (c->>'due_at')::timestamptz,
    coalesce((c->>'reps')::int, 0),
    coalesce((c->>'lapses')::int, 0),
    nullif(c->>'last_rating', ''),
    nullif(c->>'last_reviewed_at', '')::timestamptz
  from jsonb_array_elements(p_cards) as c
  where exists (select 1 from problems p where p.slug = c->>'slug')
  on conflict do nothing;

  insert into solved_problems (user_id, problem_slug, solved_at)
  select p_user_id, s, now()
  from jsonb_array_elements_text(p_solved) as s
  where exists (select 1 from problems p where p.slug = s)
  on conflict do nothing;

  insert into review_logs (user_id, problem_slug, rating, created_at)
  select p_user_id, h->>'slug', h->>'rating',
         coalesce((h->>'at')::timestamptz, now())
  from jsonb_array_elements(p_history) as h
  where h->>'rating' in ('medium', 'hard', 'extreme')
    and exists (select 1 from problems p where p.slug = h->>'slug');
end;
$$;

revoke all on function public.record_review(
  uuid, text, text, text, double precision, timestamptz, int, int, timestamptz
) from public;
revoke all on function public.record_review(
  uuid, text, text, text, double precision, timestamptz, int, int, timestamptz
) from anon, authenticated;
grant execute on function public.record_review(
  uuid, text, text, text, double precision, timestamptz, int, int, timestamptz
) to service_role;

revoke all on function public.import_practice_state(uuid, jsonb, jsonb, jsonb)
  from public;
revoke all on function public.import_practice_state(uuid, jsonb, jsonb, jsonb)
  from anon, authenticated;
grant execute on function public.import_practice_state(uuid, jsonb, jsonb, jsonb)
  to service_role;

-- ----------------------------------------------------------- row level security

alter table public.problems         enable row level security;
alter table public.test_cases       enable row level security;
alter table public.sheets           enable row level security;
alter table public.sheet_problems   enable row level security;
alter table public.profiles         enable row level security;
alter table public.card_state       enable row level security;
alter table public.solved_problems  enable row level security;
alter table public.review_logs      enable row level security;

-- The catalogue is public.
drop policy if exists "catalogue problems are readable" on public.problems;
create policy "catalogue problems are readable"
  on public.problems for select using (true);

drop policy if exists "catalogue test cases are readable" on public.test_cases;
create policy "catalogue test cases are readable"
  on public.test_cases for select using (true);

drop policy if exists "sheets are readable" on public.sheets;
create policy "sheets are readable"
  on public.sheets for select using (true);

drop policy if exists "sheet problems are readable" on public.sheet_problems;
create policy "sheet problems are readable"
  on public.sheet_problems for select using (true);

-- Everything else belongs to its user. The API uses the service-role key, so
-- these policies are defence in depth; they also make the direct browser
-- client safe if it is ever pointed at these tables.
drop policy if exists "own profile" on public.profiles;
create policy "own profile"
  on public.profiles for all
  using (auth.uid() = id)
  with check (auth.uid() = id);

drop policy if exists "own card state" on public.card_state;
create policy "own card state"
  on public.card_state for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "own solved problems" on public.solved_problems;
create policy "own solved problems"
  on public.solved_problems for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "own review logs" on public.review_logs;
create policy "own review logs"
  on public.review_logs for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- -------------------------------------------------------------------- grants

grant usage on schema public to anon, authenticated;

grant select on public.problems, public.test_cases, public.sheets,
  public.sheet_problems to anon, authenticated;

grant select, insert, update, delete on public.profiles, public.card_state,
  public.solved_problems, public.review_logs to authenticated;

grant all on public.problems, public.test_cases, public.sheets,
  public.sheet_problems, public.profiles, public.card_state,
  public.solved_problems, public.review_logs to service_role;
