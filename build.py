import json, sys, time, urllib.request, urllib.parse

BBOX = "33.70,-118.70,34.35,-117.90"
BRANDS = "Starbucks|McDonald's|Target|Whole Foods Market|Barnes & Noble|Panera Bread|In-N-Out Burger"
Q = f'''[out:json][timeout:180];
(
  nwr["amenity"="toilets"]({BBOX});
  nwr["toilets"="yes"]({BBOX});
  nwr["brand"~"^({BRANDS})$"]({BBOX});
);
out center tags;'''
SERVERS = [
  "https://overpass-api.de/api/interpreter",
  "https://overpass.private.coffee/api/interpreter",
  "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

data = None
for attempt in range(2):
  for s in SERVERS:
    try:
      req = urllib.request.Request(s, data=urllib.parse.urlencode({"data": Q}).encode(),
                                   headers={"User-Agent": "laloo.org updater"})
      with urllib.request.urlopen(req, timeout=300) as r:
        data = json.load(r)
      print("OK from", s); break
    except Exception as e:
      print("Failed", s, e)
  if data: break
  time.sleep(30)
if not data:
  sys.exit("All servers failed")

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
    "a": round(lat, 6), "o": round(lng, 6),
    "k": "public" if pub else "place",
    "n": t.get("name") or t.get("brand") or ("Public restroom" if pub else "Restroom"),
    "i": ", ".join(x for x in info if x),
  })

if len(out) < 50:
  sys.exit(f"Too few results ({len(out)}), not saving")
json.dump(out, open("toilets.json", "w"), separators=(",", ":"))
print("Saved", len(out), "places")
