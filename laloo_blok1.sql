-- =====================================================================
-- LALOO · BLOK 1 (29 Eylül 2026)
-- Puanlama + Erken üyelik + Şikayet/küfür kontrolü + Belediye silme
-- + Öneri fotoğrafları. Supabase SQL Editor'e tamamını yapıştır, Run.
-- Tekrar çalıştırılabilir (her şey "if not exists / or replace").
-- =====================================================================

-- ---------- 0) Yönetici kontrolü ----------
create or replace function public.laloo_is_admin() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.admins a
                 where lower(a.email) = lower(coalesce(auth.jwt() ->> 'email', '')));
$$;

-- ---------- 1) Küfür kontrolü (sadece işaretler, admin karar verir) ----------
create or replace function public.laloo_bad(t text) returns boolean
language sql immutable as $$
  select coalesce(t, '') ~* ('\m(' ||
    'fuck|shit|cunt|bitch|asshole|nigg|fagg|retard|whore|slut|' ||
    'amk|amın|amina|orospu|siktir|sikerim|sikeyim|yarrak|pezevenk|ibne|' ||
    'puta|mierda|coño|cabrón|cabron|gilipollas|maricón|' ||
    'scheiße|scheisse|fotze|hurensohn|wichser|arschloch|' ||
    'putain|connard|salope|enculé|encule|' ||
    'cazzo|stronzo|vaffanculo|caralho|porra|klootzak|kurwa|chuj|pierdol|' ||
    'хуй|пизд|бляд|сука)');
$$;

-- ---------- 2) Hikayeler: şikayet sayısı + küfür işareti ----------
alter table public.stories add column if not exists flag_count int not null default 0;
alter table public.stories add column if not exists bad_words boolean not null default false;

create or replace function public.laloo_story_bad() returns trigger
language plpgsql as $$
begin
  new.bad_words := public.laloo_bad(coalesce(new.title, '') || ' ' || coalesce(new.body, '') || ' ' || coalesce(new.nickname, ''));
  return new;
end $$;
drop trigger if exists laloo_story_bad on public.stories;
create trigger laloo_story_bad before insert on public.stories
  for each row execute function public.laloo_story_bad();

-- ---------- 3) Öneri formuna fotoğraf ----------
alter table public.suggestions add column if not exists photos jsonb;

-- ---------- 4) PUANLAMA ----------
create table if not exists public.reviews (
  id          bigint generated always as identity primary key,
  created_at  timestamptz not null default now(),
  place_id    bigint,
  place_name  text not null,
  city        text,
  stars       int  not null check (stars between 1 and 5),
  tags        text[] not null default '{}',
  comment     text,
  nickname    text,
  lang        text,
  ref         text,
  device      text,
  lat         double precision,
  lng         double precision,
  status      text not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
  bad_words   boolean not null default false,
  flag_count  int not null default 0
);
create index if not exists reviews_place_idx on public.reviews (place_id, status);
create index if not exists reviews_device_idx on public.reviews (device, created_at);
alter table public.reviews enable row level security;
drop policy if exists "reviews admin all" on public.reviews;
create policy "reviews admin all" on public.reviews for all to authenticated
  using (public.laloo_is_admin()) with check (public.laloo_is_admin());
revoke all on public.reviews from anon;

-- Herkese açık: sadece onaylılar, cihaz ve konum yok
create or replace view public.reviews_public as
  select id, place_id, place_name, city, stars, tags, comment, nickname, created_at
  from public.reviews where status = 'approved';
grant select on public.reviews_public to anon, authenticated;

-- Puan gönderme (tek kapı; tabloya doğrudan yazma yok)
create or replace function public.submit_review(
  p_place bigint, p_name text, p_stars int, p_tags text[], p_comment text,
  p_nick text, p_device text, p_ref text, p_lat double precision, p_lng double precision, p_lang text)
returns json language plpgsql security definer set search_path = public as $$
declare
  ok_tags text[] := array['clean','paper','soap','free','code','queue','accessible','baby','dirty','broken'];
  v_name text; v_lat double precision := p_lat; v_lng double precision := p_lng; v_city text; v_id bigint;
begin
  if p_stars is null or p_stars < 1 or p_stars > 5 then raise exception 'bad_stars'; end if;
  if coalesce(length(p_device), 0) < 8 then raise exception 'no_device'; end if;
  if p_place is not null then
    select name, lat, lng, city into v_name, v_lat, v_lng, v_city from places where id = p_place;
    if v_name is null then p_place := null; end if;
  end if;
  if v_name is null then v_name := left(trim(coalesce(p_name, '')), 120); end if;
  if length(v_name) < 2 then raise exception 'no_place'; end if;
  if (select count(*) from reviews where device = p_device and created_at > now() - interval '1 day') >= 5 then
    raise exception 'too_many'; end if;
  if exists (select 1 from reviews where device = p_device and created_at > now() - interval '1 day'
             and (place_id = p_place or (p_place is null and lower(place_name) = lower(v_name)))) then
    raise exception 'already'; end if;
  if v_city is null and v_lat is not null then
    select id into v_city from cities where v_lat between min_lat and max_lat and v_lng between min_lng and max_lng limit 1;
  end if;
  insert into reviews (place_id, place_name, city, stars, tags, comment, nickname, lang, ref, device, lat, lng, bad_words)
  values (p_place, v_name, v_city, p_stars,
          coalesce((select array_agg(t) from unnest(coalesce(p_tags, '{}')) t where t = any(ok_tags)), '{}'),
          nullif(left(trim(coalesce(p_comment, '')), 500), ''),
          nullif(left(trim(coalesce(p_nick, '')), 40), ''),
          left(p_lang, 8), left(p_ref, 60), left(p_device, 80),
          round(v_lat::numeric, 4), round(v_lng::numeric, 4),
          public.laloo_bad(coalesce(p_comment, '') || ' ' || coalesce(p_nick, '')))
  returning id into v_id;
  return json_build_object('ok', true, 'id', v_id);
end $$;

-- Haritadaki pencere için: ortalama, sayı, son 2 yorum
create or replace function public.place_reviews(p_id bigint) returns json
language sql stable security definer set search_path = public as $$
  select json_build_object(
    'n',   (select count(*) from reviews where place_id = p_id and status = 'approved'),
    'avg', (select round(avg(stars)::numeric, 1) from reviews where place_id = p_id and status = 'approved'),
    'last', coalesce((select json_agg(x) from (
        select id, stars, tags, comment, nickname, created_at from reviews
        where place_id = p_id and status = 'approved' and comment is not null
        order by created_at desc limit 2) x), '[]'::json));
$$;

-- ---------- 5) ŞİKAYET (3 farklı cihaz = otomatik askı) ----------
create table if not exists public.flags (
  id         bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  kind       text not null check (kind in ('story', 'review')),
  target     text not null,
  device     text not null,
  unique (kind, target, device)
);
alter table public.flags enable row level security;
drop policy if exists "flags admin all" on public.flags;
create policy "flags admin all" on public.flags for all to authenticated
  using (public.laloo_is_admin()) with check (public.laloo_is_admin());
revoke all on public.flags from anon;

create or replace function public.flag_content(p_kind text, p_id text, p_device text) returns json
language plpgsql security definer set search_path = public as $$
declare n int;
begin
  if p_kind not in ('story', 'review') or coalesce(length(p_device), 0) < 8 then raise exception 'bad'; end if;
  if (select count(*) from flags where device = p_device and created_at > now() - interval '1 day') >= 10 then
    return json_build_object('ok', true); end if;
  insert into flags (kind, target, device) values (p_kind, left(p_id, 64), left(p_device, 80)) on conflict do nothing;
  select count(*) into n from flags where kind = p_kind and target = p_id;
  if p_kind = 'story' then
    update stories set flag_count = n, status = case when n >= 3 and status = 'published' then 'pending' else status end
      where id::text = p_id;
  else
    update reviews set flag_count = n, status = case when n >= 3 and status = 'approved' then 'pending' else status end
      where id::text = p_id;
  end if;
  return json_build_object('ok', true);
end $$;

-- ---------- 6) ERKEN ÜYELİK ----------
create table if not exists public.members (
  id                uuid primary key default gen_random_uuid(),
  created_at        timestamptz not null default now(),
  email             text not null,
  nickname          text not null,
  city              text,
  lang              text,
  ref               text,
  invite_code       text not null unique,
  invited_by        uuid references public.members(id) on delete set null,
  devices           text[] not null default '{}',
  status            text not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
  seq               int unique,
  tier              int,
  approved_at       timestamptz,
  email_verified_at timestamptz,
  note              text
);
create unique index if not exists members_email_idx on public.members (lower(email));
alter table public.members enable row level security;
drop policy if exists "members admin all" on public.members;
create policy "members admin all" on public.members for all to authenticated
  using (public.laloo_is_admin()) with check (public.laloo_is_admin());
revoke all on public.members from anon;

-- Sıra numarasından rozet: 100 / 500 / 1000, sonrası 0 (standart)
create or replace function public.laloo_tier(n int) returns int language sql immutable as $$
  select case when n is null then null when n <= 100 then 100 when n <= 500 then 500 when n <= 1000 then 1000 else 0 end;
$$;

-- Sayaç (ana sayfa ve katılım sayfası)
create or replace function public.member_counter() returns json
language sql stable security definer set search_path = public as $$
  with a as (select count(*)::int n from members where status = 'approved'),
       p as (select count(*)::int n from members where status = 'pending')
  select json_build_object('approved', a.n, 'pending', p.n,
    'tier', public.laloo_tier(a.n + 1),
    'left', case public.laloo_tier(a.n + 1) when 0 then null else public.laloo_tier(a.n + 1) - a.n end)
  from a, p;
$$;

-- Davet eden kişinin rumuzu (davet linkiyle gelene gösterilir)
create or replace function public.invite_info(p_code text) returns json
language sql stable security definer set search_path = public as $$
  select json_build_object('nickname', nickname) from members
  where invite_code = lower(p_code) and status <> 'rejected' limit 1;
$$;

-- Katılım (herkese açık, aday olarak düşer)
create or replace function public.member_join(p_email text, p_nick text, p_city text, p_invite text,
  p_device text, p_lang text, p_ref text) returns json
language plpgsql security definer set search_path = public as $$
declare
  v_email text := lower(trim(coalesce(p_email, '')));
  v_nick text := left(trim(coalesce(p_nick, '')), 40);
  v_code text; v_inv uuid; v_pos int; m members;
  abc text := 'abcdefghjkmnpqrstuvwxyz23456789';
begin
  if v_email !~ '^[^@\s]+@[^@\s]+\.[^@\s]+$' then raise exception 'bad_email'; end if;
  if length(v_nick) < 2 then raise exception 'bad_nick'; end if;
  select * into m from members where lower(email) = v_email;
  if found then
    return json_build_object('ok', true, 'again', true, 'status', m.status);
  end if;
  if coalesce(length(p_device), 0) >= 8 and
     (select count(*) from members where p_device = any(devices) and created_at > now() - interval '1 day') >= 3 then
    raise exception 'too_many'; end if;
  select id into v_inv from members where invite_code = lower(coalesce(p_invite, '')) and status <> 'rejected';
  loop
    v_code := '';
    for i in 1..6 loop v_code := v_code || substr(abc, 1 + floor(random() * length(abc))::int, 1); end loop;
    exit when not exists (select 1 from members where invite_code = v_code);
  end loop;
  insert into members (email, nickname, city, lang, ref, invite_code, invited_by, devices)
  values (v_email, v_nick, nullif(left(trim(coalesce(p_city, '')), 80), ''), left(p_lang, 8), left(p_ref, 60),
          v_code, v_inv, case when coalesce(length(p_device), 0) >= 8 then array[left(p_device, 80)] else '{}' end);
  select (select count(*) from members where status in ('approved', 'pending'))::int into v_pos;
  return json_build_object('ok', true, 'position', v_pos, 'tier', public.laloo_tier(v_pos));
end $$;

-- Üyenin kendi sayfası (e-postadaki linkle giriş yaptıktan sonra)
create or replace function public.my_member(p_device text) returns json
language plpgsql security definer set search_path = public as $$
declare
  v_email text := lower(coalesce(auth.jwt() ->> 'email', '')); m members; v_pos int; v_inviter text;
begin
  if v_email = '' then raise exception 'not_signed_in'; end if;
  select * into m from members where lower(email) = v_email;
  if not found then return json_build_object('member', null, 'email', v_email); end if;
  update members set email_verified_at = coalesce(email_verified_at, now()),
    devices = case when coalesce(length(p_device), 0) >= 8 and not (left(p_device, 80) = any(devices)) and cardinality(devices) < 10
                   then devices || left(p_device, 80) else devices end
    where id = m.id returning * into m;
  if m.status = 'pending' then
    select (select count(*) from members where status = 'approved')
         + (select count(*) from members where status = 'pending' and created_at <= m.created_at) into v_pos;
  end if;
  select nickname into v_inviter from members where id = m.invited_by;
  return json_build_object('email', v_email, 'member', json_build_object(
    'nickname', m.nickname, 'city', m.city, 'status', m.status, 'seq', m.seq, 'tier', m.tier,
    'position', v_pos, 'position_tier', public.laloo_tier(v_pos),
    'invite_code', m.invite_code, 'invited_by', v_inviter, 'created_at', m.created_at),
    'stats', json_build_object(
      'invited',          (select count(*) from members where invited_by = m.id and status <> 'rejected'),
      'invited_approved', (select count(*) from members where invited_by = m.id and status = 'approved'),
      'stories',          (select count(*) from stories s where s.status = 'published'
                            and (lower(s.email) = v_email or s.device = any(m.devices))),
      'stories_pending',  (select count(*) from stories s where s.status = 'pending'
                            and (lower(s.email) = v_email or s.device = any(m.devices))),
      'reviews',          (select count(*) from reviews r where r.status = 'approved' and r.device = any(m.devices))));
end $$;

-- Admin listesi (sayılarla birlikte)
create or replace function public.admin_members() returns json
language plpgsql stable security definer set search_path = public as $$
begin
  if not public.laloo_is_admin() then raise exception 'not_admin'; end if;
  return coalesce((select json_agg(x order by x.seq nulls last, x.created_at) from (
    select m.id, m.created_at, m.email, m.nickname, m.city, m.lang, m.ref, m.invite_code, m.status, m.seq, m.tier,
           m.approved_at, m.email_verified_at, m.note,
           (select nickname from members i where i.id = m.invited_by) as invited_by,
           (select count(*) from members i where i.invited_by = m.id and i.status <> 'rejected') as invited,
           (select count(*) from stories s where lower(s.email) = lower(m.email) or s.device = any(m.devices)) as stories,
           (select count(*) from reviews r where r.device = any(m.devices)) as reviews
    from members m) x), '[]'::json);
end $$;

-- Onayla / reddet (onayda sıra numarası ve rozet verilir)
create or replace function public.admin_member_set(p_id uuid, p_status text) returns json
language plpgsql security definer set search_path = public as $$
declare m members; v_seq int;
begin
  if not public.laloo_is_admin() then raise exception 'not_admin'; end if;
  if p_status not in ('approved', 'rejected', 'pending') then raise exception 'bad_status'; end if;
  perform pg_advisory_xact_lock(424242);
  select * into m from members where id = p_id;
  if not found then raise exception 'not_found'; end if;
  if p_status = 'approved' and m.seq is null then
    select coalesce(max(seq), 0) + 1 into v_seq from members;
    update members set status = 'approved', seq = v_seq, tier = public.laloo_tier(v_seq), approved_at = now() where id = p_id;
  else
    update members set status = p_status where id = p_id;
  end if;
  select * into m from members where id = p_id;
  return json_build_object('ok', true, 'seq', m.seq, 'tier', m.tier);
end $$;

-- ---------- 7) BELEDİYE PROFİLİ SİLME ----------
create or replace function public.admin_delete_muni(p_id bigint) returns json
language plpgsql security definer set search_path = public as $$
declare n int := 0; r record;
begin
  if not public.laloo_is_admin() then raise exception 'not_admin'; end if;
  -- Bağlı tuvaletler haritada kalır, sadece rozet ve bağlantı kalkar
  if exists (select 1 from information_schema.columns where table_schema = 'public' and table_name = 'places'
             and column_name = 'verified' and is_generated = 'NEVER') then
    execute 'update public.places set muni_id = null, verified = false where muni_id = $1' using p_id;
  else
    execute 'update public.places set muni_id = null where muni_id = $1' using p_id;
  end if;
  get diagnostics n = row_count;
  -- Profile bağlı başka ne varsa (hesaplar vb.) bağlantısını kopar
  for r in select c.conrelid::regclass as tbl, a.attname as col
           from pg_constraint c join pg_attribute a on a.attrelid = c.conrelid and a.attnum = c.conkey[1]
           where c.contype = 'f' and c.confrelid = 'public.muni_profiles'::regclass
             and c.conrelid <> 'public.places'::regclass loop
    execute format('update %s set %I = null where %I = $1', r.tbl, r.col, r.col) using p_id;
  end loop;
  delete from public.muni_profiles where id = p_id;
  return json_build_object('ok', true, 'places', n);
end $$;

-- ---------- 8) Yetkiler ----------
revoke all on function public.admin_members() from public, anon;
revoke all on function public.admin_member_set(uuid, text) from public, anon;
revoke all on function public.admin_delete_muni(bigint) from public, anon;
revoke all on function public.my_member(text) from public, anon;
grant execute on function public.admin_members() to authenticated;
grant execute on function public.admin_member_set(uuid, text) to authenticated;
grant execute on function public.admin_delete_muni(bigint) to authenticated;
grant execute on function public.my_member(text) to authenticated;
grant execute on function public.submit_review(bigint, text, int, text[], text, text, text, text, double precision, double precision, text) to anon, authenticated;
grant execute on function public.place_reviews(bigint) to anon, authenticated;
grant execute on function public.flag_content(text, text, text) to anon, authenticated;
grant execute on function public.member_counter() to anon, authenticated;
grant execute on function public.invite_info(text) to anon, authenticated;
grant execute on function public.member_join(text, text, text, text, text, text, text) to anon, authenticated;

-- ---------- 9) Kontrol ----------
select 'reviews' as tablo, count(*) from public.reviews
union all select 'members', count(*) from public.members
union all select 'flags', count(*) from public.flags;
