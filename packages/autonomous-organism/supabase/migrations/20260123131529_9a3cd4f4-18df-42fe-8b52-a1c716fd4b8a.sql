-- Core helper
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SET search_path = public;

-- Organizations
CREATE TABLE IF NOT EXISTS public.organizations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  owner_id uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_organizations_updated_at
BEFORE UPDATE ON public.organizations
FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- Profiles (maps auth user -> org + role)
CREATE TABLE IF NOT EXISTS public.profiles (
  user_id uuid PRIMARY KEY,
  organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  role text NOT NULL DEFAULT 'user' CHECK (role IN ('owner','user')),
  display_name text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_profiles_org ON public.profiles(organization_id);

CREATE TRIGGER trg_profiles_updated_at
BEFORE UPDATE ON public.profiles
FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- Secure helpers
CREATE OR REPLACE FUNCTION public.current_org_id()
RETURNS uuid AS $$
  SELECT organization_id FROM public.profiles WHERE user_id = auth.uid();
$$ LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public;

CREATE OR REPLACE FUNCTION public.is_org_member(org_id uuid)
RETURNS boolean AS $$
  SELECT EXISTS(
    SELECT 1 FROM public.profiles p
    WHERE p.user_id = auth.uid() AND p.organization_id = org_id
  );
$$ LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public;

CREATE OR REPLACE FUNCTION public.is_org_owner(org_id uuid)
RETURNS boolean AS $$
  SELECT EXISTS(
    SELECT 1
    FROM public.organizations o
    JOIN public.profiles p ON p.organization_id = o.id
    WHERE o.id = org_id AND p.user_id = auth.uid() AND p.role = 'owner'
  );
$$ LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public;

-- Sources (generic)
CREATE TABLE IF NOT EXISTS public.problem_sources (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  type text NOT NULL CHECK (type IN ('rss','hackernews')),
  name text NOT NULL,
  url text NOT NULL,
  enabled boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, type, url)
);

CREATE INDEX IF NOT EXISTS idx_problem_sources_org ON public.problem_sources(organization_id);

CREATE TRIGGER trg_problem_sources_updated_at
BEFORE UPDATE ON public.problem_sources
FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- Raw problems
CREATE TABLE IF NOT EXISTS public.problem_raw (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  source_id uuid REFERENCES public.problem_sources(id) ON DELETE SET NULL,
  external_id text,
  title text,
  url text,
  author text,
  published_at timestamptz,
  content text NOT NULL,
  content_hash text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, content_hash)
);

CREATE INDEX IF NOT EXISTS idx_problem_raw_org_created ON public.problem_raw(organization_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_problem_raw_source ON public.problem_raw(source_id);

-- Clean problems
CREATE TABLE IF NOT EXISTS public.problem_clean (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  raw_id uuid NOT NULL REFERENCES public.problem_raw(id) ON DELETE CASCADE,
  text_clean text NOT NULL,
  language text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, raw_id)
);

CREATE INDEX IF NOT EXISTS idx_problem_clean_org_created ON public.problem_clean(organization_id, created_at DESC);

-- Idea candidates
CREATE TABLE IF NOT EXISTS public.idea_candidates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  theme text NOT NULL,
  score numeric NOT NULL,
  summary text,
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_idea_candidates_org_score ON public.idea_candidates(organization_id, score DESC);

-- Runs & logs (scheduler/agents)
CREATE TABLE IF NOT EXISTS public.engine_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  engine text NOT NULL CHECK (engine IN ('sense','decision','factory','growth','memory','system')),
  status text NOT NULL CHECK (status IN ('running','success','failed','killed')),
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  meta jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_engine_runs_org_started ON public.engine_runs(organization_id, started_at DESC);

CREATE TABLE IF NOT EXISTS public.engine_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  run_id uuid REFERENCES public.engine_runs(id) ON DELETE CASCADE,
  level text NOT NULL CHECK (level IN ('info','success','warning','system','error')),
  source text NOT NULL,
  message text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_engine_logs_org_created ON public.engine_logs(organization_id, created_at DESC);

-- Scheduler config (guardrails + kill switch)
CREATE TABLE IF NOT EXISTS public.scheduler_config (
  organization_id uuid PRIMARY KEY REFERENCES public.organizations(id) ON DELETE CASCADE,
  enabled boolean NOT NULL DEFAULT false,
  kill_switch boolean NOT NULL DEFAULT false,
  max_iterations int NOT NULL DEFAULT 25,
  timeout_seconds int NOT NULL DEFAULT 60,
  error_threshold int NOT NULL DEFAULT 5,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_scheduler_config_updated_at
BEFORE UPDATE ON public.scheduler_config
FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- Enable RLS
ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.problem_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.problem_raw ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.problem_clean ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.idea_candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.engine_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.engine_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.scheduler_config ENABLE ROW LEVEL SECURITY;

-- Policies
-- organizations
CREATE POLICY "org_select_member" ON public.organizations
FOR SELECT USING (public.is_org_member(id));
CREATE POLICY "org_update_owner" ON public.organizations
FOR UPDATE USING (public.is_org_owner(id));

-- profiles
CREATE POLICY "profiles_select_self" ON public.profiles
FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "profiles_update_self" ON public.profiles
FOR UPDATE USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

-- sources
CREATE POLICY "sources_select_member" ON public.problem_sources
FOR SELECT USING (public.is_org_member(organization_id));
CREATE POLICY "sources_write_owner" ON public.problem_sources
FOR ALL USING (public.is_org_owner(organization_id)) WITH CHECK (public.is_org_owner(organization_id));

-- raw/clean
CREATE POLICY "raw_select_member" ON public.problem_raw
FOR SELECT USING (public.is_org_member(organization_id));
CREATE POLICY "clean_select_member" ON public.problem_clean
FOR SELECT USING (public.is_org_member(organization_id));

-- idea candidates
CREATE POLICY "ideas_select_member" ON public.idea_candidates
FOR SELECT USING (public.is_org_member(organization_id));
CREATE POLICY "ideas_write_owner" ON public.idea_candidates
FOR ALL USING (public.is_org_owner(organization_id)) WITH CHECK (public.is_org_owner(organization_id));

-- runs/logs
CREATE POLICY "runs_select_member" ON public.engine_runs
FOR SELECT USING (public.is_org_member(organization_id));
CREATE POLICY "runs_write_owner" ON public.engine_runs
FOR ALL USING (public.is_org_owner(organization_id)) WITH CHECK (public.is_org_owner(organization_id));

CREATE POLICY "logs_select_member" ON public.engine_logs
FOR SELECT USING (public.is_org_member(organization_id));
CREATE POLICY "logs_write_owner" ON public.engine_logs
FOR ALL USING (public.is_org_owner(organization_id)) WITH CHECK (public.is_org_owner(organization_id));

-- scheduler config
CREATE POLICY "sched_select_owner" ON public.scheduler_config
FOR SELECT USING (public.is_org_owner(organization_id));
CREATE POLICY "sched_write_owner" ON public.scheduler_config
FOR ALL USING (public.is_org_owner(organization_id)) WITH CHECK (public.is_org_owner(organization_id));
