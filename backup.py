# Laloo haftalık veritabanı yedeği
# Tüm tabloları Supabase'den indirir, şifreli tek dosya yapar (backup.tar.gz.enc).
# Açmak için: openssl enc -d -aes-256-cbc -pbkdf2 -in backup.tar.gz.enc -out backup.tar.gz -pass pass:ŞİFREN
import json, os, sys, tarfile, urllib.request, datetime
SB_URL = os.environ.get("SUPABASE_URL", "https://tizfdnsjhhepxnqqrzuk.supabase.co")
KEY = os.environ.get("SUPABASE_SECRET", "")
if not KEY: sys.exit("SUPABASE_SECRET yok")
H = {"apikey": KEY, "User-Agent": "laloo.org backup"}
if not KEY.startswith("sb_"): H["Authorization"] = "Bearer " + KEY

def get(path, extra=None):
  req = urllib.request.Request(SB_URL + "/rest/v1/" + path, headers={**H, **(extra or {})})
  with urllib.request.urlopen(req, timeout=120) as r:
    return json.load(r)

spec = get("", {"Accept": "application/openapi+json"})
tables = sorted(p.strip("/") for p in spec.get("paths", {}) if p.count("/") == 1 and p != "/" and not p.startswith("/rpc/"))
day = datetime.date.today().isoformat()
os.makedirs("backup", exist_ok=True)
total = 0
failed = []
for t in tables:
  rows, off = [], 0
  try:
    while True:
      chunk = get(f"{t}?select=*&limit=1000&offset={off}")
      rows += chunk
      if len(chunk) < 1000: break
      off += 1000
  except Exception as ex:
    print("  FAILED", t, ex)
    failed.append(t)
    continue
  json.dump(rows, open(f"backup/{t}.json", "w"), ensure_ascii=False)
  print(f"  {t}: {len(rows)}"); total += len(rows)
if failed:
  sys.exit(f"Backup incomplete: could not export {len(failed)} table(s): {', '.join(failed)}")
with tarfile.open("backup.tar.gz", "w:gz") as tar: tar.add("backup", arcname=f"laloo-{day}")
print(f"Toplam {total} satır, {len(tables)} tablo")
