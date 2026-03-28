-- =============================================================================
-- Newton Smart Home – Production schema for Supabase (PostgreSQL)
-- Single migration: auth, profiles, core tables, RLS, indexes, seed trigger
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. AUTH EXTENSION & PROFILES
-- -----------------------------------------------------------------------------

-- Profiles linked to Supabase Auth (auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
  id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name text,
  role text NOT NULL DEFAULT 'customer' CHECK (role IN ('admin', 'technician', 'customer')),
  phone text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Auto-create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.profiles (id, full_name, role)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1)),
    COALESCE(NEW.raw_user_meta_data->>'role', 'customer')
  );
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- -----------------------------------------------------------------------------
-- 2. CORE TABLES (UUID PKs, timestamps, FKs)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.homes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  name text NOT NULL,
  address text,
  city text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.rooms (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  home_id uuid NOT NULL REFERENCES public.homes(id) ON DELETE CASCADE,
  name text NOT NULL,
  floor int,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.hubs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  home_id uuid NOT NULL REFERENCES public.homes(id) ON DELETE CASCADE,
  serial_number text NOT NULL UNIQUE,
  status text NOT NULL DEFAULT 'offline' CHECK (status IN ('online', 'offline')),
  firmware_version text,
  last_seen timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.devices (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  home_id uuid NOT NULL REFERENCES public.homes(id) ON DELETE CASCADE,
  room_id uuid REFERENCES public.rooms(id) ON DELETE CASCADE,
  hub_id uuid REFERENCES public.hubs(id) ON DELETE SET NULL,
  type text NOT NULL CHECK (type IN ('light', 'ac', 'camera', 'lock', 'sensor')),
  name text NOT NULL,
  status text NOT NULL DEFAULT 'off' CHECK (status IN ('on', 'off', 'standby')),
  metadata jsonb DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.automations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  home_id uuid NOT NULL REFERENCES public.homes(id) ON DELETE CASCADE,
  name text NOT NULL,
  trigger jsonb NOT NULL DEFAULT '{}',
  actions jsonb NOT NULL DEFAULT '[]',
  enabled boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.device_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id uuid NOT NULL REFERENCES public.devices(id) ON DELETE CASCADE,
  event_type text NOT NULL,
  payload jsonb DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- 3. INDEXES (FKs, lookups, performance)
-- -----------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_homes_owner_id ON public.homes(owner_id);
CREATE INDEX IF NOT EXISTS idx_rooms_home_id ON public.rooms(home_id);
CREATE INDEX IF NOT EXISTS idx_hubs_home_id ON public.hubs(home_id);
CREATE INDEX IF NOT EXISTS idx_hubs_serial_number ON public.hubs(serial_number);
CREATE INDEX IF NOT EXISTS idx_devices_home_id ON public.devices(home_id);
CREATE INDEX IF NOT EXISTS idx_devices_room_id ON public.devices(room_id);
CREATE INDEX IF NOT EXISTS idx_devices_hub_id ON public.devices(hub_id);
CREATE INDEX IF NOT EXISTS idx_automations_home_id ON public.automations(home_id);
CREATE INDEX IF NOT EXISTS idx_device_logs_device_id ON public.device_logs(device_id);
CREATE INDEX IF NOT EXISTS idx_device_logs_created_at ON public.device_logs(created_at DESC);

-- -----------------------------------------------------------------------------
-- 4. ROW LEVEL SECURITY (RLS)
-- -----------------------------------------------------------------------------

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.homes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rooms ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.hubs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.automations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.device_logs ENABLE ROW LEVEL SECURITY;

-- Helper: true if current user is admin
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.profiles
    WHERE id = auth.uid() AND role = 'admin'
  );
$$;

-- Profiles: users see/edit own; admin full access
DROP POLICY IF EXISTS "profiles_select_own" ON public.profiles;
CREATE POLICY "profiles_select_own" ON public.profiles FOR SELECT USING (id = auth.uid() OR public.is_admin());
DROP POLICY IF EXISTS "profiles_update_own" ON public.profiles;
CREATE POLICY "profiles_update_own" ON public.profiles FOR UPDATE USING (id = auth.uid() OR public.is_admin());
DROP POLICY IF EXISTS "profiles_insert_admin" ON public.profiles;
CREATE POLICY "profiles_insert_admin" ON public.profiles FOR INSERT WITH CHECK (public.is_admin());
DROP POLICY IF EXISTS "profiles_delete_admin" ON public.profiles;
CREATE POLICY "profiles_delete_admin" ON public.profiles FOR DELETE USING (public.is_admin());

-- Homes: owner CRUD; admin full access
DROP POLICY IF EXISTS "homes_select_owner" ON public.homes;
CREATE POLICY "homes_select_owner" ON public.homes FOR SELECT USING (owner_id = auth.uid() OR public.is_admin());
DROP POLICY IF EXISTS "homes_insert_owner" ON public.homes;
CREATE POLICY "homes_insert_owner" ON public.homes FOR INSERT WITH CHECK (owner_id = auth.uid() OR public.is_admin());
DROP POLICY IF EXISTS "homes_update_owner" ON public.homes;
CREATE POLICY "homes_update_owner" ON public.homes FOR UPDATE USING (owner_id = auth.uid() OR public.is_admin());
DROP POLICY IF EXISTS "homes_delete_owner" ON public.homes;
CREATE POLICY "homes_delete_owner" ON public.homes FOR DELETE USING (owner_id = auth.uid() OR public.is_admin());

-- Rooms: home owner CRUD; admin full access
DROP POLICY IF EXISTS "rooms_select_owner" ON public.rooms;
CREATE POLICY "rooms_select_owner" ON public.rooms FOR SELECT USING (
  home_id IN (SELECT id FROM public.homes WHERE owner_id = auth.uid()) OR public.is_admin()
);
DROP POLICY IF EXISTS "rooms_insert_owner" ON public.rooms;
CREATE POLICY "rooms_insert_owner" ON public.rooms FOR INSERT WITH CHECK (
  home_id IN (SELECT id FROM public.homes WHERE owner_id = auth.uid()) OR public.is_admin()
);
DROP POLICY IF EXISTS "rooms_update_owner" ON public.rooms;
CREATE POLICY "rooms_update_owner" ON public.rooms FOR UPDATE USING (
  home_id IN (SELECT id FROM public.homes WHERE owner_id = auth.uid()) OR public.is_admin()
);
DROP POLICY IF EXISTS "rooms_delete_owner" ON public.rooms;
CREATE POLICY "rooms_delete_owner" ON public.rooms FOR DELETE USING (
  home_id IN (SELECT id FROM public.homes WHERE owner_id = auth.uid()) OR public.is_admin()
);

-- Hubs: home owner CRUD; admin full access
DROP POLICY IF EXISTS "hubs_select_owner" ON public.hubs;
CREATE POLICY "hubs_select_owner" ON public.hubs FOR SELECT USING (
  home_id IN (SELECT id FROM public.homes WHERE owner_id = auth.uid()) OR public.is_admin()
);
DROP POLICY IF EXISTS "hubs_insert_owner" ON public.hubs;
CREATE POLICY "hubs_insert_owner" ON public.hubs FOR INSERT WITH CHECK (
  home_id IN (SELECT id FROM public.homes WHERE owner_id = auth.uid()) OR public.is_admin()
);
DROP POLICY IF EXISTS "hubs_update_owner" ON public.hubs;
CREATE POLICY "hubs_update_owner" ON public.hubs FOR UPDATE USING (
  home_id IN (SELECT id FROM public.homes WHERE owner_id = auth.uid()) OR public.is_admin()
);
DROP POLICY IF EXISTS "hubs_delete_owner" ON public.hubs;
CREATE POLICY "hubs_delete_owner" ON public.hubs FOR DELETE USING (
  home_id IN (SELECT id FROM public.homes WHERE owner_id = auth.uid()) OR public.is_admin()
);

-- Devices: home owner CRUD; admin full access
DROP POLICY IF EXISTS "devices_select_owner" ON public.devices;
CREATE POLICY "devices_select_owner" ON public.devices FOR SELECT USING (
  home_id IN (SELECT id FROM public.homes WHERE owner_id = auth.uid()) OR public.is_admin()
);
DROP POLICY IF EXISTS "devices_insert_owner" ON public.devices;
CREATE POLICY "devices_insert_owner" ON public.devices FOR INSERT WITH CHECK (
  home_id IN (SELECT id FROM public.homes WHERE owner_id = auth.uid()) OR public.is_admin()
);
DROP POLICY IF EXISTS "devices_update_owner" ON public.devices;
CREATE POLICY "devices_update_owner" ON public.devices FOR UPDATE USING (
  home_id IN (SELECT id FROM public.homes WHERE owner_id = auth.uid()) OR public.is_admin()
);
DROP POLICY IF EXISTS "devices_delete_owner" ON public.devices;
CREATE POLICY "devices_delete_owner" ON public.devices FOR DELETE USING (
  home_id IN (SELECT id FROM public.homes WHERE owner_id = auth.uid()) OR public.is_admin()
);

-- Automations: home owner CRUD; admin full access
DROP POLICY IF EXISTS "automations_select_owner" ON public.automations;
CREATE POLICY "automations_select_owner" ON public.automations FOR SELECT USING (
  home_id IN (SELECT id FROM public.homes WHERE owner_id = auth.uid()) OR public.is_admin()
);
DROP POLICY IF EXISTS "automations_insert_owner" ON public.automations;
CREATE POLICY "automations_insert_owner" ON public.automations FOR INSERT WITH CHECK (
  home_id IN (SELECT id FROM public.homes WHERE owner_id = auth.uid()) OR public.is_admin()
);
DROP POLICY IF EXISTS "automations_update_owner" ON public.automations;
CREATE POLICY "automations_update_owner" ON public.automations FOR UPDATE USING (
  home_id IN (SELECT id FROM public.homes WHERE owner_id = auth.uid()) OR public.is_admin()
);
DROP POLICY IF EXISTS "automations_delete_owner" ON public.automations;
CREATE POLICY "automations_delete_owner" ON public.automations FOR DELETE USING (
  home_id IN (SELECT id FROM public.homes WHERE owner_id = auth.uid()) OR public.is_admin()
);

-- Device logs: readable (and insertable) by home owner; admin full access
DROP POLICY IF EXISTS "device_logs_select_owner" ON public.device_logs;
CREATE POLICY "device_logs_select_owner" ON public.device_logs FOR SELECT USING (
  device_id IN (
    SELECT id FROM public.devices
    WHERE home_id IN (SELECT id FROM public.homes WHERE owner_id = auth.uid())
  ) OR public.is_admin()
);
DROP POLICY IF EXISTS "device_logs_insert_owner" ON public.device_logs;
CREATE POLICY "device_logs_insert_owner" ON public.device_logs FOR INSERT WITH CHECK (
  device_id IN (
    SELECT id FROM public.devices
    WHERE home_id IN (SELECT id FROM public.homes WHERE owner_id = auth.uid())
  ) OR public.is_admin()
);

-- -----------------------------------------------------------------------------
-- 5. SEED DATA – auto-create example home/room/hub/device for new profiles
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.seed_example_home_for_new_profile()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  new_home_id uuid;
  new_room_id uuid;
  new_hub_id uuid;
BEGIN
  INSERT INTO public.homes (owner_id, name, address, city)
  VALUES (NEW.id, 'My Home', NULL, NULL)
  RETURNING id INTO new_home_id;

  INSERT INTO public.rooms (home_id, name, floor)
  VALUES (new_home_id, 'Living Room', 1)
  RETURNING id INTO new_room_id;

  INSERT INTO public.hubs (home_id, serial_number, status, firmware_version)
  VALUES (new_home_id, 'HUB-' || replace(gen_random_uuid()::text, '-', '')::text, 'offline', '1.0.0')
  RETURNING id INTO new_hub_id;

  INSERT INTO public.devices (home_id, room_id, hub_id, type, name, status, metadata)
  VALUES (
    new_home_id,
    new_room_id,
    new_hub_id,
    'light',
    'Living Room Light',
    'off',
    '{"brand": "Newton"}'::jsonb
  );

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_profile_created_seed_home ON public.profiles;
CREATE TRIGGER on_profile_created_seed_home
  AFTER INSERT ON public.profiles
  FOR EACH ROW EXECUTE FUNCTION public.seed_example_home_for_new_profile();

-- -----------------------------------------------------------------------------
-- 6. UPDATED_AT TRIGGER (optional but best practice)
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS set_updated_at ON public.profiles;
CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.profiles FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
DROP TRIGGER IF EXISTS set_updated_at ON public.homes;
CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.homes FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
DROP TRIGGER IF EXISTS set_updated_at ON public.rooms;
CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.rooms FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
DROP TRIGGER IF EXISTS set_updated_at ON public.hubs;
CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.hubs FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
DROP TRIGGER IF EXISTS set_updated_at ON public.devices;
CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.devices FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
DROP TRIGGER IF EXISTS set_updated_at ON public.automations;
CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.automations FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
