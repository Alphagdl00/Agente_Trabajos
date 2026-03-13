create table if not exists users (
    id uuid primary key,
    email text unique not null,
    full_name text default '',
    created_at timestamptz not null default now()
);

create table if not exists user_profiles (
    id uuid primary key,
    user_id uuid not null references users(id) on delete cascade,
    display_name text not null default 'Default',
    practices text[] not null default '{}',
    seniority_levels text[] not null default '{}',
    preferred_regions text[] not null default '{}',
    preferred_countries text[] not null default '{}',
    preferred_work_modes text[] not null default '{}',
    preferred_companies text[] not null default '{}',
    keywords text[] not null default '{}',
    is_default boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists companies (
    id bigserial primary key,
    company_name text not null,
    industry text not null default '',
    region text not null default '',
    country text not null default '',
    priority text not null default '',
    international_hiring text not null default '',
    profile_fit text not null default '',
    salary_band text not null default '',
    ats text not null default '',
    career_url text not null,
    is_active boolean not null default true,
    created_at timestamptz not null default now()
);

create unique index if not exists companies_company_url_idx
    on companies (company_name, career_url);

create table if not exists job_runs (
    id bigserial primary key,
    run_type text not null default 'scheduled',
    started_at timestamptz not null default now(),
    finished_at timestamptz,
    status text not null default 'running',
    profile_scope text[] not null default '{}',
    region_scope text[] not null default '{}',
    country_scope text[] not null default '{}',
    total_companies integer not null default 0,
    total_jobs integer not null default 0,
    notes text not null default ''
);

create table if not exists jobs (
    id bigserial primary key,
    job_key text not null,
    company_id bigint references companies(id) on delete set null,
    company_name text not null default '',
    title text not null default '',
    location text not null default '',
    region text not null default '',
    country text not null default '',
    work_mode text not null default '',
    seniority_level text not null default '',
    ats text not null default '',
    department text not null default '',
    priority text not null default '',
    global_signal boolean not null default false,
    posted_date text not null default '',
    description_snippet text not null default '',
    source_url text not null default '',
    apply_url text not null default '',
    first_seen_at timestamptz not null default now(),
    last_seen_at timestamptz not null default now()
);

create unique index if not exists jobs_job_key_idx
    on jobs (job_key);

create table if not exists run_jobs (
    id bigserial primary key,
    run_id bigint not null references job_runs(id) on delete cascade,
    job_id bigint not null references jobs(id) on delete cascade,
    score integer not null default 0,
    score_band text not null default 'Bajo',
    score_reasons text[] not null default '{}',
    has_keyword_match boolean not null default false,
    is_new_today boolean not null default false
);

create unique index if not exists run_jobs_run_job_idx
    on run_jobs (run_id, job_id);

create table if not exists user_job_actions (
    id bigserial primary key,
    user_id uuid not null references users(id) on delete cascade,
    profile_id uuid references user_profiles(id) on delete set null,
    job_id bigint not null references jobs(id) on delete cascade,
    action_type text not null,
    notes text not null default '',
    created_at timestamptz not null default now()
);

create index if not exists user_job_actions_user_idx
    on user_job_actions (user_id, created_at desc);

create index if not exists jobs_country_region_idx
    on jobs (country, region);
