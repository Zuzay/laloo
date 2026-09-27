# Laloo veri güncelleyici
# - Supabase'deki aktif şehirler için OSM'den tuvaletleri çeker ve places tablosuna yazar
# - LA için toilets.json yedek dosyasını da üretir
# SUPABASE_SECRET yoksa sadece toilets.json üretir (eski davranış)
import json, os, shutil, sys, time, urllib.request, urllib.parse
sys.dont_write_bytecode = True                       # repoya __pycache__ yazılmasın
shutil.rmtree("__pycache__", ignore_errors=True)
from datetime import datetime, timezone

SB_URL = os.environ.get("SUPABASE_URL", "https://tizfdnsjhhepxnqqrzuk.supabase.co")
SB_SECRET = os.environ.get("SUPABASE_SECRET", "")
LA_BBOX = (33.70, -118.70, 34.35, -117.90)
BRANDS = "Starbucks|McDonald's|Target|Whole Foods Market|Barnes & Noble|Panera Bread|In-N-Out Burger"
SERVERS = [
  "https://overpass-api.de/api/interpreter",
  "https://overpass.private.coffee/api/interpreter",
  "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

def overpass(bbox):
  b = ",".join(str(x) for x in bbox)
  q = f'''[out:json][timeout:180];
(
  nwr["amenity"="toilets"]({b});
  nwr["toilets"="yes"]({b});
  nwr["brand"~"^({BRANDS})$"]({b});
);
out center tags;'''
  for attempt in range(2):
    for s in SERVERS:
      try:
        req = urllib.request.Request(s, data=urllib.parse.urlencode({"data": q}).encode(),
                                     headers={"User-Agent": "laloo.org updater"})
        with urllib.request.urlopen(req, timeout=200) as r:
          data = json.load(r)
        print("  OK from", s); return data
      except Exception as e:
        print("  Failed", s, e)
    time.sleep(30)
  return None

def areas(bbox):
  """Şehir sayfaları için semt adları (place=suburb/quarter/neighbourhood)."""
  b = ",".join(str(x) for x in bbox)
  q = f'[out:json][timeout:90];node["place"~"^(suburb|quarter|neighbourhood)$"]["name"]({b});out;'
  for s in SERVERS:
    try:
      req = urllib.request.Request(s, data=urllib.parse.urlencode({"data": q}).encode(), headers={"User-Agent": "laloo.org updater"})
      with urllib.request.urlopen(req, timeout=120) as r:
        els = json.load(r)["elements"]
      return [{"n": e["tags"].get("name:en") or e["tags"]["name"], "a": round(e["lat"], 5), "o": round(e["lon"], 5)} for e in els][:400]
    except Exception as e:
      print("  areas failed", s, e)
  return None

def parse(data):
  out, seen = [], set()
  for e in data["elements"]:
    t = e.get("tags", {})
    lat = e.get("lat") or e.get("center", {}).get("lat")
    lng = e.get("lon") or e.get("center", {}).get("lon")
    if lat is None: continue
    key = (round(lat, 5), round(lng, 5))
    if key in seen: continue
    pub = t.get("amenity") == "toilets"
    if pub and t.get("access") in ("private", "no"): continue
    if not pub and (t.get("toilets") == "no" or t.get("toilets:access") == "private"): continue
    seen.add(key)
    if pub:
      info = ["Free" if t.get("fee") == "no" else "Paid" if t.get("fee") == "yes" else "",
              "Customers only" if t.get("access") == "customers" else "",
              t.get("opening_hours", "")]
    else:
      info = ["Ask inside, usually for customers", t.get("opening_hours", "")]
    out.append({
      "osm_id": f'{e["type"]}/{e["id"]}',
      "lat": round(lat, 6), "lng": round(lng, 6),
      "kind": "public" if pub else "cafe",
      "name": t.get("name") or t.get("brand") or ("Public restroom" if pub else "Restroom"),
      "info": ", ".join(x for x in info if x),
      "operator": (t.get("operator") or "")[:120] or None,
      "charge": (t.get("charge") or "")[:60] or None,
    })
  return out

def sb(method, path, body=None, prefer="return=minimal"):
  req = urllib.request.Request(SB_URL + "/rest/v1/" + path, method=method,
    data=json.dumps(body).encode() if body is not None else None,
    headers={"apikey": SB_SECRET, "Content-Type": "application/json", "Prefer": prefer,
             "User-Agent": "laloo.org updater"})
  with urllib.request.urlopen(req, timeout=120) as r:
    txt = r.read().decode()
    return json.loads(txt) if txt else None

def save_json(points):
  small = [{"a": p["lat"], "o": p["lng"], "k": "public" if p["kind"] == "public" else "place",
            "n": p["name"], "i": p["info"]} for p in points]
  json.dump(small, open("toilets.json", "w"), separators=(",", ":"))
  print("Saved toilets.json:", len(small))

if not SB_SECRET:
  print("No SUPABASE_SECRET, only toilets.json for LA")
  data = overpass(LA_BBOX)
  if not data: sys.exit("All servers failed")
  pts = parse(data)
  if len(pts) < 50: sys.exit(f"Too few results ({len(pts)}), not saving")
  save_json(pts); sys.exit(0)

# ---------- 1) Adresle eklenen ipuçlarına koordinat bul (her gün) ----------
def nominatim(q):
  u = urllib.parse.urlencode({"q": q, "format": "json", "limit": 1})
  req = urllib.request.Request("https://nominatim.openstreetmap.org/search?" + u,
                               headers={"User-Agent": "laloo.org updater (hello@laloo.org)"})
  try:
    with urllib.request.urlopen(req, timeout=30) as r:
      res = json.load(r)
  except Exception as e:
    print("  error", q, e); res = []
  time.sleep(1.2)   # Nominatim kuralı: saniyede en fazla 1 istek
  return res[0] if res else None

def geocode():
  todo = sb("GET", "places?select=id,name,address,area,city&lat=is.null&address=not.is.null&address=not.like.%3F%3F*&order=id&limit=450", prefer="")
  names = {c["id"]: c["name"] for c in sb("GET", "cities?select=id,name", prefer="")}
  print(f"Geocoding {len(todo)} places")
  ok = miss = 0
  for p in todo:
    city = names.get(p["city"], "")
    # 1) adres  2) ad + semt + şehir  3) ad + şehir
    tries = [p["address"], ", ".join(x for x in (p["name"], p.get("area"), city) if x), ", ".join(x for x in (p["name"], city) if x)]
    hit = None
    for q in dict.fromkeys(tries):
      hit = nominatim(q)
      if hit: break
    if hit:
      sb("PATCH", f"places?id=eq.{p['id']}", {"lat": round(float(hit["lat"]), 6), "lng": round(float(hit["lon"]), 6), "active": True})
      ok += 1
    else:
      # Bulunamayanlar tekrar tekrar denenmesin: adresin başına işaret koy, admin panelinde düzeltilir
      sb("PATCH", f"places?id=eq.{p['id']}", {"address": "?? " + p["address"] if not p["address"].startswith("??") else p["address"]})
      print("  NOT FOUND", p["name"], "|", p["address"]); miss += 1
  print(f"  geocoded {ok}, not found {miss}")

# ---------- 2) İpucu notlarını çevir (DeepL, her gün) ----------
DEEPL_KEY = os.environ.get("DEEPL_KEY", "")
LANGS = {"tr":"TR", "es":"ES", "fr":"FR", "de":"DE", "it":"IT", "pt":"PT-BR", "nl":"NL", "pl":"PL", "ru":"RU", "zh":"ZH-HANS", "ja":"JA"}
def translate():
  if not DEEPL_KEY:
    print("No DEEPL_KEY, skipping translation"); return
  host = "https://api-free.deepl.com" if DEEPL_KEY.endswith(":fx") else "https://api.deepl.com"
  todo = sb("GET", "places?select=id,info,hours&kind=eq.tip&i18n=is.null&limit=200", prefer="")
  print(f"Translating {len(todo)} tips")
  if not todo: return
  out = {p["id"]: {} for p in todo}
  for code, dl in LANGS.items():
    for i in range(0, len(todo), 25):
      chunk = todo[i:i+25]
      texts = []
      for p in chunk: texts += [p["info"] or "", p["hours"] or ""]
      req = urllib.request.Request(host + "/v2/translate", method="POST",
        data=json.dumps({"text": texts, "source_lang": "EN", "target_lang": dl}).encode(),
        headers={"Authorization": "DeepL-Auth-Key " + DEEPL_KEY, "Content-Type": "application/json"})
      with urllib.request.urlopen(req, timeout=60) as r:
        tr = [t["text"] for t in json.load(r)["translations"]]
      for j, p in enumerate(chunk):
        out[p["id"]][code] = {"info": tr[2*j], "hours": tr[2*j+1]}
  for pid, d in out.items():
    sb("PATCH", f"places?id=eq.{pid}", {"i18n": d})
  print("  translated", len(out))

# ---------- 3) Reddit: şehir subreddit'lerinde tuvalet soruları (RSS, her gün) ----------
SUBS = {"la": ["LosAngeles", "AskLosAngeles", "santamonica"], "bay": ["sanfrancisco", "AskSF", "bayarea"],
        "nyc": ["AskNYC", "nyc", "NYCTravel"], "miami": ["Miami"], "paris": ["paris", "ParisTravelGuide"],
        "amsterdam": ["Amsterdam"], "rotterdam": ["Rotterdam"], "brussels": ["brussels"], "warsaw": ["warsaw"],
        "istanbul": ["istanbul"], "izmir": ["izmir"]}
def reddit():
  import xml.etree.ElementTree as ET
  ns = {"a": "http://www.w3.org/2005/Atom"}
  q = urllib.parse.quote("bathroom OR restroom OR toilet OR toilets OR wc OR tuvalet")
  found = []
  for city, subs in SUBS.items():
    for sub in subs:
      url = f"https://www.reddit.com/r/{sub}/search.rss?q={q}&restrict_sr=on&sort=new&t=week"
      try:
        req = urllib.request.Request(url, headers={"User-Agent": "laloo.org restroom helper (hello@laloo.org)"})
        with urllib.request.urlopen(req, timeout=30) as r:
          root = ET.fromstring(r.read())
        for e in root.findall("a:entry", ns):
          link = e.find("a:link", ns).get("href")
          title = (e.findtext("a:title", default="", namespaces=ns) or "").strip()
          found.append({"name": title[:120] or "Reddit post", "note": f"r/{sub}", "url": link,
                        "city": city, "source": "reddit", "status": "pending"})
      except Exception as ex:
        print("  reddit", sub, "failed:", ex)
      time.sleep(3)
  if found:
    sb("POST", "suggestions?on_conflict=url", found, prefer="resolution=ignore-duplicates,return=minimal")
  print(f"Reddit: {len(found)} posts checked")

for step in (geocode, translate, reddit):
  try: step()
  except Exception as ex: print(step.__name__, "failed:", ex)

# ---------- 4) OSM tuvaletleri (pazartesi ya da elle çalıştırınca) ----------
# Her koşuda en uzun süredir yenilenmeyen 30 şehir (186 şehir ~6 günde bir tur döner, Overpass'ı yormaz)
PER_RUN = int(os.environ.get("CITIES_PER_RUN", "30"))
run = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
cities = sb("GET", f"cities?select=*&active=eq.true&order=osm_updated.asc.nullsfirst&limit={PER_RUN}", prefer="")
print("Cities:", [c["id"] for c in cities])
failed = []
OSM_BUDGET = int(os.environ.get("OSM_MINUTES", "35")) * 60   # Overpass yavaşsa işi yarın bitir, sayfalar yine üretilsin
osm_start = time.time()
for c in cities:
  if time.time() - osm_start > OSM_BUDGET:
    print(f"Time budget reached, remaining cities tomorrow"); break
  print(f"== {c['id']}")
  data = overpass((c["min_lat"], c["min_lng"], c["max_lat"], c["max_lng"]))
  if not data: failed.append(c["id"]); continue
  pts = parse(data)
  if len(pts) < 5:
    print(f"  Too few results ({len(pts)}), skipping"); sb("PATCH", f"cities?id=eq.{c['id']}", {"osm_updated": run}); continue
  rows = [dict(p, city=c["id"], source="osm", active=True, updated_at=run) for p in pts]
  for i in range(0, len(rows), 500):
    sb("POST", "places?on_conflict=osm_id", rows[i:i+500], prefer="resolution=merge-duplicates,return=minimal")
  # OSM'den silinen noktaları gizle
  sb("PATCH", f"places?source=eq.osm&city=eq.{c['id']}&updated_at=lt.{urllib.parse.quote(run)}", {"active": False})
  sb("PATCH", f"cities?id=eq.{c['id']}", {"osm_updated": run})
  print(f"  Upserted {len(rows)}")
  time.sleep(4)   # Overpass'a nefes aldır (429 Too Many Requests olmasın)
  ar = areas((c["min_lat"], c["min_lng"], c["max_lat"], c["max_lng"]))
  if ar: sb("PATCH", f"cities?id=eq.{c['id']}", {"areas": ar}); print(f"  Areas {len(ar)}")
  if c["id"] == "la": save_json(pts)
  time.sleep(5)

if failed: print(f"WARNING: will retry tomorrow: {failed}")

# ---------- 5) Şehir sayfaları, sitemap.xml, robots.txt (her gece) ----------
def all_rows(path):
  out, off = [], 0
  while True:
    chunk = sb("GET", f"{path}&limit=1000&offset={off}", prefer="")
    out += chunk
    if len(chunk) < 1000: return out
    off += 1000

try:
  import pages
  all_cities = sb("GET", "cities?select=id,name,min_lat,min_lng,max_lat,max_lng,active,areas", prefer="")
  cols = "select=kind,name,info,area,fee,hours,lat,lng,i18n,operator"
  pages.generate(all_cities, lambda cid: all_rows(f"places?{cols}&city=eq.{cid}&active=eq.true&kind=in.(tip,public)&order=id"))
except Exception as ex:
  print("pages failed:", ex)
