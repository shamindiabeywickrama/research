-- Run this in Supabase SQL Editor (Project -> SQL Editor -> New query)

create table if not exists predictions (
    id bigint generated always as identity primary key,
    date date not null,
    hour int not null,
    predicted_occupancy_percent numeric not null,
    predicted_occupancy_count int not null,
    is_exam_period boolean default false,
    is_semester_break boolean default false,
    is_weekend boolean default false,
    created_at timestamptz default now()
);

-- Helpful index for history queries ordered by recency
create index if not exists idx_predictions_created_at on predictions (created_at desc);

-- Enable Row Level Security (recommended)
alter table predictions enable row level security;

-- Allow the backend (using anon or service key) to insert/select.
-- For a quick prototype, this policy allows all operations.
-- Tighten this before going to production.
create policy "Allow all access to predictions"
    on predictions
    for all
    using (true)
    with check (true);
