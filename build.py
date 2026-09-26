# Laloo veri güncelleyici
# - Supabase'deki aktif şehirler için OSM'den tuvaletleri çeker ve places tablosuna yazar
# - LA için toilets.json yedek dosyasını da üretir
# SUPABASE_SECRET yoksa sadece toilets.json üretir (eski davranış)
import json, os, sys, time, urllib.request, urllib.parse
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
        with urllib.request.urlopen(req, timeout=300) as r:
          data = json.load(r)
        print("  OK from", s); return data
      except Exception as e:
        print("  Failed", s, e)
    time.sleep(30)
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

run = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
cities = sb("GET", "cities?select=*&active=eq.true", prefer="")
print("Cities:", [c["id"] for c in cities])
failed = []
for c in cities:
  print(f"== {c['id']}")
  data = overpass((c["min_lat"], c["min_lng"], c["max_lat"], c["max_lng"]))
  if not data: failed.append(c["id"]); continue
  pts = parse(data)
  if len(pts) < 20:
    print(f"  Too few results ({len(pts)}), skipping"); failed.append(c["id"]); continue
  rows = [dict(p, city=c["id"], source="osm", active=True, updated_at=run) for p in pts]
  for i in range(0, len(rows), 500):
    sb("POST", "places?on_conflict=osm_id", rows[i:i+500], prefer="resolution=merge-duplicates,return=minimal")
  # OSM'den silinen noktaları gizle
  sb("PATCH", f"places?source=eq.osm&city=eq.{c['id']}&updated_at=lt.{urllib.parse.quote(run)}", {"active": False})
  print(f"  Upserted {len(rows)}")
  if c["id"] == "la": save_json(pts)
  time.sleep(5)

if failed: sys.exit(f"Failed cities: {failed}")
