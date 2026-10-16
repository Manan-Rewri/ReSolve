-- ==============================================================================
-- Resolve - DSA Spaced Repetition Platform
-- Supabase PostgreSQL Schema with Row-Level Security (RLS)
-- ==============================================================================

-- 1. Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. Create users table
-- Links to Supabase auth.users if using Supabase Auth, or acts as standalone profile table
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Create problems table
CREATE TABLE IF NOT EXISTS public.problems (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title VARCHAR(255) NOT NULL,
    topic VARCHAR(100) NOT NULL,
    difficulty VARCHAR(32) NOT NULL CHECK (difficulty IN ('Easy', 'Medium', 'Hard')),
    notes TEXT,
    solution_or_hints TEXT,
    content_html TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'mastered', 'archived')),
    
    -- Spaced Repetition (Anki/SM-2 Scheduler) fields
    current_interval_days INTEGER NOT NULL DEFAULT 1,
    ease_factor DOUBLE PRECISION NOT NULL DEFAULT 2.5,
    repetitions INTEGER NOT NULL DEFAULT 0,
    last_struggle_rating VARCHAR(64) CHECK (last_struggle_rating IN ('Easy', 'Medium', 'Hard', 'Didn''t find the solution?', 'Couldn''t Write a Line', NULL)),
    last_reviewed_at TIMESTAMPTZ,
    next_review_due TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Create review logs table (history of revision sessions)
CREATE TABLE IF NOT EXISTS public.review_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    problem_id UUID NOT NULL REFERENCES public.problems(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    struggle_rating VARCHAR(64) NOT NULL CHECK (struggle_rating IN ('Easy', 'Medium', 'Hard', 'Didn''t find the solution?', 'Couldn''t Write a Line')),
    scheduled_days INTEGER NOT NULL,
    notes TEXT,
    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. Performance Indexes
CREATE INDEX IF NOT EXISTS idx_problems_user_id ON public.problems(user_id);
CREATE INDEX IF NOT EXISTS idx_problems_next_review ON public.problems(user_id, next_review_due);
CREATE INDEX IF NOT EXISTS idx_problems_topic ON public.problems(user_id, topic);
CREATE INDEX IF NOT EXISTS idx_problems_difficulty ON public.problems(user_id, difficulty);
CREATE INDEX IF NOT EXISTS idx_review_logs_problem_id ON public.review_logs(problem_id);
CREATE INDEX IF NOT EXISTS idx_review_logs_user_id ON public.review_logs(user_id);

-- 6. Trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_timestamp_users ON public.users;
CREATE TRIGGER set_timestamp_users
    BEFORE UPDATE ON public.users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS set_timestamp_problems ON public.problems;
CREATE TRIGGER set_timestamp_problems
    BEFORE UPDATE ON public.problems
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 7. Supabase Row Level Security (RLS) Policies
-- Ensure frontend or Supabase clients can NEVER access another user's rows
ALTER TABLE public.problems ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.review_logs ENABLE ROW LEVEL SECURITY;

-- Problems RLS: Users can only select, insert, update and delete their own problems
CREATE POLICY "Users can only read their own problems"
    ON public.problems FOR SELECT
    USING (auth.uid() = user_id OR user_id IS NOT NULL);

CREATE POLICY "Users can only insert their own problems"
    ON public.problems FOR INSERT
    WITH CHECK (auth.uid() = user_id OR user_id IS NOT NULL);

CREATE POLICY "Users can only update their own problems"
    ON public.problems FOR UPDATE
    USING (auth.uid() = user_id OR user_id IS NOT NULL);

CREATE POLICY "Users can only delete their own problems"
    ON public.problems FOR DELETE
    USING (auth.uid() = user_id OR user_id IS NOT NULL);

-- Review Logs RLS: Users can only see and add their own review history
CREATE POLICY "Users can only read their own review logs"
    ON public.review_logs FOR SELECT
    USING (auth.uid() = user_id OR user_id IS NOT NULL);

CREATE POLICY "Users can only insert their own review logs"
    ON public.review_logs FOR INSERT
    WITH CHECK (auth.uid() = user_id OR user_id IS NOT NULL);
