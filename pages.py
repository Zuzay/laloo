# Laloo şehir sayfaları üreticisi
# build.py her gece çağırır. Her şehir için 5 dilde düz, hızlı bir HTML sayfası yazar:
#   /<slug>/            (İngilizce)
#   /<lang>/<slug>/     (es, de, fr, tr)
# Ayrıca /cities/ listesi, sitemap.xml ve robots.txt üretir.
# Harita sayfası (index.html) bu dosyaları yüklemez, site yavaşlamaz.
import html, json, math, os, re, shutil, unicodedata
from datetime import datetime, timezone

SITE = "https://laloo.org"
LANGS = ["en", "es", "de", "fr", "tr"]
MIN_PLACES = 10          # bundan az yeri olan şehre sayfa yok (zayıf sayfa Google'da zarar)
PER_AREA = 25            # semt başına en fazla umumi tuvalet
MAX_MUNI = 20            # belediye grubunda en fazla
MAX_PUBLIC = 400         # sayfa başına en fazla umumi tuvalet
MANIFEST = "pages-manifest.json"
ABOUT = {"en": "About", "es": "Acerca de", "de": "Über uns", "fr": "À propos", "tr": "Hakkında"}
ROUTES_FILE = "routes.json"   # Loo Routes yazıları (Claude yazar, Uzay yükler)

# Hedef şehirlerin dillere göre adları (yoksa veritabanındaki ad kullanılır)
NAMES = {
  "istanbul": {"en": "Istanbul", "es": "Estambul", "de": "Istanbul", "fr": "Istanbul", "tr": "İstanbul"},
  "izmir": {"en": "Izmir", "es": "Esmirna", "de": "Izmir", "fr": "Izmir", "tr": "İzmir"},
  "amsterdam": {"en": "Amsterdam", "es": "Ámsterdam", "de": "Amsterdam", "fr": "Amsterdam", "tr": "Amsterdam"},
  "rotterdam": {"en": "Rotterdam", "es": "Róterdam", "de": "Rotterdam", "fr": "Rotterdam", "tr": "Rotterdam"},
  "warsaw": {"en": "Warsaw", "es": "Varsovia", "de": "Warschau", "fr": "Varsovie", "tr": "Varşova"},
  "brussels": {"en": "Brussels", "es": "Bruselas", "de": "Brüssel", "fr": "Bruxelles", "tr": "Brüksel"},
  "paris": {"en": "Paris", "es": "París", "de": "Paris", "fr": "Paris", "tr": "Paris"},
  "la": {"en": "Los Angeles", "es": "Los Ángeles", "de": "Los Angeles", "fr": "Los Angeles", "tr": "Los Angeles"},
  "bay": {"en": "San Francisco Bay Area", "es": "Área de la Bahía de San Francisco", "de": "San Francisco Bay Area", "fr": "Baie de San Francisco", "tr": "San Francisco Körfez Bölgesi"},
  "nyc": {"en": "New York City", "es": "Nueva York", "de": "New York City", "fr": "New York", "tr": "New York"},
  "miami": {"en": "Miami", "es": "Miami", "de": "Miami", "fr": "Miami", "tr": "Miami"},
}
SLUGS = {"la": "los-angeles", "bay": "san-francisco-bay-area", "nyc": "new-york"}

T = {
 "en": {"title": "Public bathrooms in {c}: free toilets and where to go",
        "desc": "{n} public restrooms, free toilets and hand-picked spots in {c}. See fees and opening hours, then open the live map to find the nearest one. No app needed.",
        "h1": "Public bathrooms in {c}",
        "intro": "Laloo lists {n} places to use the bathroom in {c}: public restrooms, hand-picked spots and cafés. Open the live map to see the nearest one and walk there.",
        "open": "Open the map in {c}", "muni": "Run by the city",
        "muni_note": "Public toilets operated by the city or a public body. Information compiled by Laloo from open data.",
        "tips": "Hand-picked spots", "tips_note": "Checked and described by the Laloo team.",
        "pub": "Public restrooms by neighborhood", "more": "…and {k} more on the map.",
        "other": "Other areas", "free": "Free", "paid": "Paid", "cust": "Customers only", "ticket": "With ticket",
        "ask": "Ask inside, usually for customers", "upd": "Updated {d}.", "all": "All cities",
        "home": "Find a bathroom anywhere", "cities_t": "Public bathrooms by city", "cities_h1": "Find a bathroom in these cities",
        "cities_d": "Public restrooms, free toilets and hand-picked spots in {n} cities. Pick a city or open the live map.",
        "stat": "{p} public restrooms · {t} hand-picked spots", "src": "Map data © OpenStreetMap contributors.", "routes": "Loo Routes", "routes_city": "Walking routes in {c}", "routes_h1": "Loo Routes: walks with bathroom stops", "routes_d": "Walking routes through the world's busiest tourist spots, with every bathroom stop on the way.", "partner": "Laloo partner", "stops": "Bathroom stops", "open_route": "Open this area on the map", "pub_d": "Published {d}"},
 "es": {"title": "Baños públicos en {c}: aseos gratis y dónde ir",
        "desc": "{n} baños públicos, aseos gratuitos y lugares recomendados en {c}. Mira precios y horarios y abre el mapa en vivo para encontrar el más cercano. Sin descargar ninguna app.",
        "h1": "Baños públicos en {c}",
        "intro": "Laloo muestra {n} lugares para ir al baño en {c}: baños públicos, lugares recomendados y cafés. Abre el mapa en vivo para ver el más cercano y llegar caminando.",
        "open": "Abrir el mapa en {c}", "muni": "Gestionados por la ciudad",
        "muni_note": "Aseos públicos gestionados por el ayuntamiento o un organismo público. Información recopilada por Laloo a partir de datos abiertos.",
        "tips": "Lugares recomendados", "tips_note": "Revisados y descritos por el equipo de Laloo.",
        "pub": "Baños públicos por barrio", "more": "…y {k} más en el mapa.",
        "other": "Otras zonas", "free": "Gratis", "paid": "De pago", "cust": "Solo clientes", "ticket": "Con entrada",
        "ask": "Pregunta dentro, normalmente para clientes", "upd": "Actualizado: {d}.", "all": "Todas las ciudades",
        "home": "Encuentra un baño en cualquier lugar", "cities_t": "Baños públicos por ciudad", "cities_h1": "Encuentra un baño en estas ciudades",
        "cities_d": "Baños públicos, aseos gratuitos y lugares recomendados en {n} ciudades. Elige una ciudad o abre el mapa.",
        "stat": "{p} baños públicos · {t} lugares recomendados", "src": "Datos del mapa © colaboradores de OpenStreetMap.", "routes": "Loo Routes", "routes_city": "Rutas a pie en {c}", "routes_h1": "Loo Routes: paseos con paradas para ir al baño", "routes_d": "Rutas a pie por los lugares más turísticos del mundo, con cada parada para ir al baño en el camino.", "partner": "Socio de Laloo", "stops": "Paradas para ir al baño", "open_route": "Abrir esta zona en el mapa", "pub_d": "Publicado: {d}"},
 "de": {"title": "Öffentliche Toiletten in {c}: kostenlose WCs und wo man hingeht",
        "desc": "{n} öffentliche Toiletten, kostenlose WCs und ausgewählte Orte in {c}. Preise und Öffnungszeiten ansehen und auf der Live-Karte die nächste finden. Ohne App.",
        "h1": "Öffentliche Toiletten in {c}",
        "intro": "Laloo zeigt {n} Orte in {c}, an denen du auf die Toilette kannst: öffentliche Toiletten, ausgewählte Orte und Cafés. Öffne die Live-Karte, um die nächste zu finden.",
        "open": "Karte für {c} öffnen", "muni": "Von der Stadt betrieben",
        "muni_note": "Öffentliche Toiletten der Stadt oder einer öffentlichen Stelle. Von Laloo aus offenen Daten zusammengestellt.",
        "tips": "Ausgewählte Orte", "tips_note": "Vom Laloo-Team geprüft und beschrieben.",
        "pub": "Öffentliche Toiletten nach Stadtteil", "more": "…und {k} weitere auf der Karte.",
        "other": "Weitere Gegenden", "free": "Kostenlos", "paid": "Kostenpflichtig", "cust": "Nur für Kunden", "ticket": "Mit Eintritt",
        "ask": "Drinnen fragen, meist für Kunden", "upd": "Aktualisiert: {d}.", "all": "Alle Städte",
        "home": "Finde überall eine Toilette", "cities_t": "Öffentliche Toiletten nach Stadt", "cities_h1": "Finde eine Toilette in diesen Städten",
        "cities_d": "Öffentliche Toiletten, kostenlose WCs und ausgewählte Orte in {n} Städten. Wähle eine Stadt oder öffne die Karte.",
        "stat": "{p} öffentliche Toiletten · {t} ausgewählte Orte", "src": "Kartendaten © OpenStreetMap-Mitwirkende.", "routes": "Loo Routes", "routes_city": "Spaziergänge in {c}", "routes_h1": "Loo Routes: Spaziergänge mit Toilettenstopps", "routes_d": "Spaziergänge durch die beliebtesten Touristenorte der Welt, mit jedem Toilettenstopp unterwegs.", "partner": "Laloo-Partner", "stops": "Toilettenstopps", "open_route": "Diese Gegend auf der Karte öffnen", "pub_d": "Veröffentlicht: {d}"},
 "fr": {"title": "Toilettes publiques à {c} : WC gratuits et où aller",
        "desc": "{n} toilettes publiques, WC gratuits et bonnes adresses à {c}. Tarifs et horaires, puis la carte en direct pour trouver les plus proches. Sans application.",
        "h1": "Toilettes publiques à {c}",
        "intro": "Laloo recense {n} endroits où aller aux toilettes à {c} : toilettes publiques, bonnes adresses et cafés. Ouvrez la carte en direct pour trouver les plus proches.",
        "open": "Ouvrir la carte à {c}", "muni": "Gérées par la ville",
        "muni_note": "Toilettes publiques gérées par la ville ou un organisme public. Informations compilées par Laloo à partir de données ouvertes.",
        "tips": "Bonnes adresses", "tips_note": "Vérifiées et décrites par l'équipe Laloo.",
        "pub": "Toilettes publiques par quartier", "more": "…et {k} de plus sur la carte.",
        "other": "Autres quartiers", "free": "Gratuit", "paid": "Payant", "cust": "Réservé aux clients", "ticket": "Avec billet",
        "ask": "Demandez à l'intérieur, en général pour les clients", "upd": "Mis à jour : {d}.", "all": "Toutes les villes",
        "home": "Trouvez des toilettes partout", "cities_t": "Toilettes publiques par ville", "cities_h1": "Trouvez des toilettes dans ces villes",
        "cities_d": "Toilettes publiques, WC gratuits et bonnes adresses dans {n} villes. Choisissez une ville ou ouvrez la carte.",
        "stat": "{p} toilettes publiques · {t} bonnes adresses", "src": "Données cartographiques © contributeurs OpenStreetMap.", "routes": "Loo Routes", "routes_city": "Balades à {c}", "routes_h1": "Loo Routes : balades avec pauses toilettes", "routes_d": "Des balades dans les lieux les plus touristiques du monde, avec chaque pause toilettes sur le chemin.", "partner": "Partenaire Laloo", "stops": "Pauses toilettes", "open_route": "Ouvrir ce quartier sur la carte", "pub_d": "Publié : {d}"},
 "tr": {"title": "{c} umumi tuvaletleri: ücretsiz tuvaletler ve nereye gidilir",
        "desc": "{c} içinde {n} umumi tuvalet, ücretsiz WC ve seçilmiş yer. Ücret ve saatlere bak, canlı haritada en yakınını bul. Uygulama gerekmez.",
        "h1": "{c} umumi tuvaletleri",
        "intro": "Laloo, {c} içinde tuvalete gidebileceğin {n} yeri gösteriyor: umumi tuvaletler, seçilmiş yerler ve kafeler. En yakınını görmek için canlı haritayı aç.",
        "open": "{c} haritasını aç", "muni": "Belediyenin işlettiği",
        "muni_note": "Belediye ya da bir kamu kurumu tarafından işletilen tuvaletler. Bilgiler açık veriden Laloo tarafından derlendi.",
        "tips": "Seçilmiş yerler", "tips_note": "Laloo ekibi tarafından kontrol edildi ve anlatıldı.",
        "pub": "Semt semt umumi tuvaletler", "more": "…ve haritada {k} yer daha.",
        "other": "Diğer bölgeler", "free": "Ücretsiz", "paid": "Ücretli", "cust": "Sadece müşterilere", "ticket": "Biletle",
        "ask": "İçeride sor, genelde müşterilere", "upd": "Güncelleme: {d}.", "all": "Tüm şehirler",
        "home": "Her yerde tuvalet bul", "cities_t": "Şehir şehir umumi tuvaletler", "cities_h1": "Bu şehirlerde tuvalet bul",
        "cities_d": "{n} şehirde umumi tuvaletler, ücretsiz WC'ler ve seçilmiş yerler. Bir şehir seç ya da haritayı aç.",
        "stat": "{p} umumi tuvalet · {t} seçilmiş yer", "src": "Harita verisi © OpenStreetMap katkıcıları.", "routes": "Loo Routes", "routes_city": "{c} yürüyüş rotaları", "routes_h1": "Loo Routes: tuvalet molalı yürüyüşler", "routes_d": "Dünyanın en turistik yerlerinde, yol üstündeki her tuvalet molasıyla yürüyüş rotaları.", "partner": "Laloo partneri", "stops": "Tuvalet molaları", "open_route": "Bu bölgeyi haritada aç", "pub_d": "Yayın: {d}"},
}
MONTHS = {
 "en": "January February March April May June July August September October November December",
 "es": "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre",
 "de": "Januar Februar März April Mai Juni Juli August September Oktober November Dezember",
 "fr": "janvier février mars avril mai juin juillet août septembre octobre novembre décembre",
 "tr": "Ocak Şubat Mart Nisan Mayıs Haziran Temmuz Ağustos Eylül Ekim Kasım Aralık",
}
MUNI_RE = re.compile(r"\b(city|municipal|municipality|county|council|parks?|department|recreation|borough|state|public works|"
                     r"gemeente|stad|belediye|b\.?b\.?|İBB|İzBB|ville|mairie|commune|mairie de|ayuntamiento|stadt|miasto|"
                     r"urząd|zarząd|bruxelles|brussel|paris|nyc|mta|metro|transport for)\b", re.I)

esc = lambda s: html.escape(str(s or ""), quote=True)

def slugify(s):
  s = unicodedata.normalize("NFKD", s.replace("ı", "i").replace("İ", "I")).encode("ascii", "ignore").decode().lower()
  return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

def cname(c, lang):
  return NAMES.get(c["id"], {}).get(lang) or c["name"]

def month(lang, now):
  return f'{MONTHS[lang].split()[now.month - 1]} {now.year}'

def url(lang, slug):
  return f"{SITE}/{slug}/" if lang == "en" else f"{SITE}/{lang}/{slug}/"

def fee_tags(info, lang, fee=None):
  """OSM info metnini (Free, Customers only, saatler) dile göre etiket + saat olarak ayırır."""
  t = T[lang]; tags, rest = [], []
  if fee:
    tags.append({"Free": t["free"], "Paid": t["paid"], "Customers": t["cust"], "Ticket": t["ticket"]}.get(fee, fee))
  for part in [p.strip() for p in (info or "").split(",") if p.strip()]:
    m = {"Free": t["free"], "Paid": t["paid"], "Customers only": t["cust"], "Ask inside": t["ask"]}.get(part)
    if part.startswith("Ask inside"): m = t["ask"]
    if part == "usually for customers": continue
    (tags if m else rest).append(m or part)
  return tags, ", ".join(rest)

def nearest_area(lat, lng, areas):
  best, bd = None, 1e9
  k = math.cos(math.radians(lat))
  for a in areas:
    d = (a["a"] - lat) ** 2 + ((a["o"] - lng) * k) ** 2
    if d < bd: best, bd = a["n"], d
  return best if bd < (0.03 ** 2) else None     # ~3 km'den uzaksa "Diğer bölgeler"

CSS = """:root{--navy:#10223d;--blue:#1c4fa0;--line:#e6e1d4;--bg:#fefef8;--muted:#5f6b7d;--card:#fff;--green:#1b7a3a;--greenbg:#e3f6e8;--amber:#8a5a00;--amberbg:#fff4df;--tag:#e8f0fb}
@media (prefers-color-scheme:dark){:root{--navy:#e9eef6;--blue:#8fb4ff;--line:#2a3445;--bg:#111722;--muted:#9aa6b8;--card:#172030;--green:#7fd79a;--greenbg:#1d3326;--amber:#f0c070;--amberbg:#3a2e17;--tag:#1f2e48}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--navy);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--blue)}
header{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 16px;border-bottom:1px solid var(--line)}
header img{height:34px;display:block;border-radius:8px}
@media (prefers-color-scheme:dark){header img{background:#fefef8;padding:2px 6px;height:38px}}
.langs{display:flex;gap:4px;flex-wrap:wrap;font-size:13px}.langs a{padding:3px 7px;border-radius:7px;text-decoration:none;color:var(--muted)}.langs a.on{background:var(--tag);color:var(--blue);font-weight:700}
main{max-width:760px;margin:0 auto;padding:18px 16px 40px}
h1{font-size:28px;line-height:1.2;margin:8px 0 10px}
h2{font-size:20px;margin:30px 0 6px}h3{font-size:16px;margin:18px 0 6px;color:var(--muted)}
.lead{font-size:17px;margin:0 0 6px}.stat{color:var(--muted);font-size:14px;margin:0 0 16px}
.cta{display:inline-block;background:#1c4fa0;color:#fff;font-weight:700;text-decoration:none;padding:12px 18px;border-radius:12px;margin:6px 0 4px}
.note{color:var(--muted);font-size:14px;margin:0 0 8px}
ul.pl{list-style:none;margin:0;padding:0}
ul.pl li{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 12px;margin:0 0 8px;overflow-wrap:anywhere}
ul.pl b{display:block}ul.pl p{margin:4px 0 0;font-size:14px}.h{color:var(--muted);font-size:13px}
.t{display:inline-block;font-size:12px;font-weight:700;padding:2px 7px;border-radius:8px;margin:4px 4px 0 0;background:var(--tag);color:var(--blue)}
.t.f{background:var(--greenbg);color:var(--green)}
ul.sm li{padding:7px 10px;margin:0 0 5px;border-radius:9px;font-size:15px}ul.sm b{display:inline;margin-right:6px}ul.sm .t{margin:0 4px 0 0}ul.sm .h{display:inline}.t.c{background:var(--amberbg);color:var(--amber)}
ul.cl{columns:2;gap:20px;padding-left:18px}@media(max-width:520px){ul.cl{columns:1}}
article p{margin:0 0 14px}.box{background:var(--tag);border-radius:12px;padding:12px 14px;margin:14px 0}
.stop{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin:0 0 12px;position:relative}
.stop .n{display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:50%;background:#1c4fa0;color:#fff;font-weight:700;font-size:13px;margin-right:8px;vertical-align:1px}
.stop .d{color:var(--muted);font-size:13px;margin:2px 0 6px}.stop.pt{border-color:#e0453a}.stop.pt .n{background:#e0453a}.t.p{background:#fde8e8;color:#b3261e}
.rl{list-style:none;padding:0;margin:0}.rl li{margin:0 0 10px}.rl a{font-weight:700}.rl span{display:block;color:var(--muted);font-size:14px}
footer{max-width:760px;margin:0 auto;padding:18px 16px 40px;border-top:1px solid var(--line);color:var(--muted);font-size:13px}"""

def tag_html(tags, lang):
  t = T[lang]; out = []
  for g in tags:
    cls = "f" if g == t["free"] else "c" if g in (t["cust"], t["ask"]) else ""
    out.append(f'<span class="t {cls}">{esc(g)}</span>')
  return "".join(out)

def page(lang, title, desc, canon, alts, body, slug_for_lang):
  links = "".join(f'<link rel="alternate" hreflang="{l}" href="{esc(u)}">' for l, u in alts)
  links += f'<link rel="alternate" hreflang="x-default" href="{esc(dict(alts)["en"])}">'
  langs = "".join(f'<a href="{esc(slug_for_lang(l))}" class="{"on" if l == lang else ""}" lang="{l}">{l.upper()}</a>' for l in LANGS)
  return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(canon)}">
{links}
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(canon)}">
<meta property="og:image" content="{SITE}/favicon-512.png">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#fefef8">
<style>{CSS}</style>
</head>
<body>
<header><a href="/"><img src="/logo-header.png" alt="LALOO" width="120" height="34"></a><nav class="langs">{langs}</nav></header>
<main>
{body}
</main>
<footer><a href="/">laloo.org · {esc(T[lang]["home"])}</a> · <a href="{'/cities/' if lang == 'en' else f'/{lang}/cities/'}">{esc(T[lang]["all"])}</a> · <a href="{'/about/' if lang == 'en' else f'/{lang}/about/'}">{esc(ABOUT[lang])}</a> · <a href="https://www.trustpilot.com/review/laloo.org" rel="noopener">Trustpilot</a><br>{esc(T[lang]["src"])}</footer>
</body>
</html>
"""

def li(name, tags, hours, info, lang):
  s = f'<li><b>{esc(name)}</b>{tag_html(tags, lang)}'
  if hours: s += f'<div class="h">{esc(hours)}</div>'
  if info: s += f'<p>{esc(info)}</p>'
  return s + "</li>"

def city_body(c, lang, tips, pubs, areas, now):
  t = T[lang]; cn = cname(c, lang)
  n = len(tips) + len(pubs)
  lat = (c["min_lat"] + c["max_lat"]) / 2; lng = (c["min_lng"] + c["max_lng"]) / 2
  if tips:  # haritayı yıldızlı yerlerin ortasında aç
    lat = sorted(x["lat"] for x in tips)[len(tips) // 2]; lng = sorted(x["lng"] for x in tips)[len(tips) // 2]
  cta = f'<a class="cta" href="/?at={lat:.4f},{lng:.4f},14&amp;ref=city-{esc(c["id"])}">📍 {esc(t["open"].format(c=cn))}</a>'
  b = [f'<h1>{esc(t["h1"].format(c=cn))}</h1>',
       f'<p class="lead">{esc(t["intro"].format(c=cn, n=n))}</p>',
       f'<p class="stat">{esc(t["stat"].format(p=len(pubs), t=len(tips)))} · {esc(t["upd"].format(d=month(lang, now)))}</p>', cta]
  muni = [p for p in pubs if p.get("operator") and MUNI_RE.search(p["operator"])]
  if muni:
    b.append(f'<h2>{esc(t["muni"])}</h2><p class="note">{esc(t["muni_note"])}</p><ul class="pl">')
    for p in sorted(muni, key=lambda p: (nearest_area(p["lat"], p["lng"], areas) or "~", p["name"], p["lat"]))[:MAX_MUNI]:
      tags, hours = fee_tags(p.get("info"), lang)
      where = nearest_area(p["lat"], p["lng"], areas)
      b.append(li(p["name"], tags, hours, " · ".join(x for x in (where, p.get("operator")) if x), lang))
    b.append("</ul>")
    if len(muni) > MAX_MUNI: b.append(f'<p class="note">{esc(t["more"].format(k=len(muni) - MAX_MUNI))}</p>')
  if tips:
    b.append(f'<h2>{esc(t["tips"])}</h2><p class="note">{esc(t["tips_note"])}</p>')
    groups = {}
    for x in tips: groups.setdefault(x.get("area") or t["other"], []).append(x)
    for area in sorted(groups, key=lambda a: (-len(groups[a]), a)):
      b.append(f'<h3>{esc(area)}</h3><ul class="pl">')
      for x in sorted(groups[area], key=lambda x: x["name"]):
        info = ((x.get("i18n") or {}).get(lang) or {}).get("info") or x.get("info")
        hours = ((x.get("i18n") or {}).get(lang) or {}).get("hours") or x.get("hours")
        tags, _ = fee_tags("", lang, x.get("fee"))
        b.append(li(x["name"], tags, hours, info, lang))
      b.append("</ul>")
  mids = {id(p) for p in muni}
  rest = [p for p in pubs if id(p) not in mids]
  if rest:
    b.append(f'<h2>{esc(t["pub"])}</h2>')
    groups = {}
    for p in rest: groups.setdefault(nearest_area(p["lat"], p["lng"], areas) or t["other"], []).append(p)
    order = sorted(groups, key=lambda a: (a == t["other"], -len(groups[a]), a))
    shown = 0
    for area in order:
      if shown >= MAX_PUBLIC: break
      items = sorted(groups[area], key=lambda p: (p["name"] in ("Public restroom", "Restroom"), p["name"], p["lat"]))
      b.append(f'<h3>{esc(area)} · {len(items)}</h3><ul class="pl sm">')
      for p in items[:PER_AREA]:
        tags, hours = fee_tags(p.get("info"), lang)
        b.append(li(p["name"], tags, hours, "", lang)); shown += 1
      b.append("</ul>")
      if len(items) > PER_AREA: b.append(f'<p class="note">{esc(t["more"].format(k=len(items) - PER_AREA))}</p>')
  b.append(cta)
  return "\n".join(b), n

def md(text):
  """Düz metin: **kalın** desteklenir, geri kalan her şey kaçışlanır."""
  return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", esc(text))

def route_body(r, lang, now):
  t = T[lang]; d = r["i18n"][lang]
  b = [f'<p class="note">{esc(t["routes"])} · {esc(t["pub_d"].format(d=month(lang, datetime.fromisoformat(r["date"]))))}</p>',
       f'<h1>{esc(d["h1"])}</h1><article>']
  k = 0
  for blk in d["body"]:
    if "p" in blk: b.append(f'<p>{md(blk["p"])}</p>')
    elif "h2" in blk: b.append(f'<h2>{esc(blk["h2"])}</h2>')
    elif "box" in blk: b.append(f'<div class="box">{md(blk["box"])}</div>')
    elif "stop" in blk:
      st = blk["stop"]; pt = st.get("partner")
      k += 0 if pt else 1
      num = "★" if pt else str(k)
      tags = (f'<span class="t p">{esc(t["partner"])}</span>' if pt else "") + tag_html(fee_tags("", lang, st.get("fee"))[0], lang)
      name = esc(st["name"])
      if st.get("url"): name = f'<a href="{esc(st["url"])}" rel="{"sponsored noopener" if pt else "noopener"}">{name}</a>'
      b.append(f'<div class="stop{" pt" if pt else ""}"><b><span class="n">{num}</span>{name}</b> {tags}'
               + (f'<div class="d">{esc(st["where"])}</div>' if st.get("where") else "") + f'<div>{md(st["text"])}</div></div>')
  b.append("</article>")
  b.append(f'<a class="cta" href="/?at={r["lat"]:.4f},{r["lng"]:.4f},15&amp;ref=route-{esc(r["slug"])}">📍 {esc(t["open_route"])}</a>')
  return "\n".join(b)

def write(path, text):
  os.makedirs(os.path.dirname(path), exist_ok=True)
  old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
  if old != text:
    open(path, "w", encoding="utf-8").write(text)

def generate(cities, places_for, root=".", now=None):
  """cities: cities tablosu satırları. places_for(city_id) -> o şehrin aktif yerleri (tip + osm)."""
  now = now or datetime.now(timezone.utc)
  old = set(json.load(open(os.path.join(root, MANIFEST)))) if os.path.exists(os.path.join(root, MANIFEST)) else set()
  made, listed = [], []
  used = set()
  routes = json.load(open(os.path.join(root, ROUTES_FILE), encoding="utf-8")) if os.path.exists(os.path.join(root, ROUTES_FILE)) else []
  rpath = lambda l, slug: f"/routes/{slug}/" if l == "en" else f"/{l}/routes/{slug}/"
  for c in sorted(cities, key=lambda c: c["name"]):
    if not c.get("active", True): continue
    slug = SLUGS.get(c["id"]) or slugify(NAMES.get(c["id"], {}).get("en") or c["name"]) or c["id"]
    if slug in used or slug in ("cities", "admin", *LANGS): slug = f'{slug}-{c["id"]}'
    used.add(slug)
    rows = places_for(c["id"])
    tips = [r for r in rows if r.get("kind") == "tip" and r.get("lat") is not None]
    pubs = [r for r in rows if r.get("kind") == "public" and r.get("lat") is not None]
    if len(tips) + len(pubs) < MIN_PLACES: continue
    areas = c.get("areas") or []
    alts = [(l, url(l, slug)) for l in LANGS]
    for lang in LANGS:
      body, n = city_body(c, lang, tips, pubs, areas, now)
      mine = [r for r in routes if r["city"] == c["id"] and lang in r["i18n"]]
      if mine:
        body = body.replace('<h2>', f'<h2>{esc(T[lang]["routes_city"].format(c=cname(c, lang)))}</h2><ul class="rl">' + "".join(
          f'<li><a href="{rpath(lang, r["slug"])}">{esc(r["i18n"][lang]["h1"])}</a><span>{esc(r["i18n"][lang]["desc"])}</span></li>' for r in mine) + '</ul><h2>', 1)
      cn = cname(c, lang); t = T[lang]
      rel = f"{slug}/index.html" if lang == "en" else f"{lang}/{slug}/index.html"
      write(os.path.join(root, rel), page(lang, t["title"].format(c=cn), t["desc"].format(c=cn, n=n), url(lang, slug), alts, body,
                                          lambda l, s=slug: f"/{s}/" if l == "en" else f"/{l}/{s}/"))
      made.append(rel)
    listed.append((c, slug, len(tips), len(pubs)))
  # Loo Routes yazıları ve /routes/ listesi
  for r in routes:
    langs = [l for l in LANGS if l in r["i18n"]]
    alts = [(l, SITE + rpath(l, r["slug"])) for l in langs]
    if "en" not in langs: continue
    for lang in langs:
      d = r["i18n"][lang]
      rel = rpath(lang, r["slug"]).strip("/") + "/index.html"
      write(os.path.join(root, rel), page(lang, d["title"], d["desc"], SITE + rpath(lang, r["slug"]), alts, route_body(r, lang, now),
                                          lambda l, s=r["slug"], ls=langs: rpath(l, s) if l in ls else ("/" if l == "en" else f"/{l}/cities/")))
      made.append(rel)
  if routes:
    for lang in LANGS:
      t = T[lang]; mine = [r for r in sorted(routes, key=lambda r: r["date"], reverse=True) if lang in r["i18n"]]
      body = [f'<h1>{esc(t["routes_h1"])}</h1><p class="lead">{esc(t["routes_d"])}</p><ul class="rl">']
      body += [f'<li><a href="{rpath(lang, r["slug"])}">{esc(r["i18n"][lang]["h1"])}</a><span>{esc(r["i18n"][lang]["desc"])}</span></li>' for r in mine]
      body.append("</ul>")
      rel = "routes/index.html" if lang == "en" else f"{lang}/routes/index.html"
      write(os.path.join(root, rel), page(lang, t["routes_h1"], t["routes_d"], SITE + rpath(lang, "").replace("//", "/").rstrip("/") + "/",
                                          [(l, SITE + ("/routes/" if l == "en" else f"/{l}/routes/")) for l in LANGS], "\n".join(body),
                                          lambda l: "/routes/" if l == "en" else f"/{l}/routes/"))
      made.append(rel)
  # /cities/ listeleri
  for lang in LANGS:
    t = T[lang]
    items = sorted(listed, key=lambda x: slugify(cname(x[0], lang)))
    body = [f'<h1>{esc(t["cities_h1"])}</h1><p class="lead">{esc(t["cities_d"].format(n=len(items)))}</p>',
            f'<a class="cta" href="/?ref=cities">📍 {esc(t["home"])}</a><ul class="cl">']
    for c, slug, nt, npub in items:
      href = f"/{slug}/" if lang == "en" else f"/{lang}/{slug}/"
      body.append(f'<li><a href="{href}">{esc(cname(c, lang))}</a></li>')
    body.append("</ul>")
    rel = "cities/index.html" if lang == "en" else f"{lang}/cities/index.html"
    alts = [(l, url(l, "cities")) for l in LANGS]
    write(os.path.join(root, rel), page(lang, t["cities_t"] + " · Laloo", t["cities_d"].format(n=len(items)), url(lang, "cities"), alts,
                                        "\n".join(body), lambda l: "/cities/" if l == "en" else f"/{l}/cities/"))
    made.append(rel)
  # Artık sayfası olmayan eski dosyaları sil
  for rel in old - set(made):
    p = os.path.join(root, rel)
    if os.path.exists(p): os.remove(p)
    d = os.path.dirname(p)
    while d and d != root and os.path.isdir(d) and not os.listdir(d):
      os.rmdir(d); d = os.path.dirname(d)
  # Tanıtım sayfası (laloo.org/about/ + /<dil>/about/): canlı rakamlarla, 5 dilde
  try:
    import about_page
    n_pages = len(made) + len(LANGS)
    for lang in LANGS:
      rel = "about/index.html" if lang == "en" else f"{lang}/about/index.html"
      write(os.path.join(root, rel), about_page.build(listed, routes, n_pages, lambda c, l: cname(c, l),
                                                      lambda slug, l: url(l, slug).replace(SITE, ""), now, SITE, lang,
                                                      month(lang, now)))
      made.append(rel)
  except Exception as ex:
    print("about page failed:", ex)
  json.dump(sorted(made), open(os.path.join(root, MANIFEST), "w"), indent=0)
  # sitemap.xml ve robots.txt
  urls = [f"{SITE}/"] + [SITE + "/" + rel[:-len("index.html")] for rel in sorted(made)]
  for extra in ("hosts/index.html", "stories/index.html"):          # elle yüklenen sabit sayfalar
    if os.path.exists(os.path.join(root, extra)): urls.append(SITE + "/" + extra[:-len("index.html")])
  sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
  sm += [f"  <url><loc>{esc(u)}</loc></url>" for u in urls]
  sm.append("</urlset>")
  write(os.path.join(root, "sitemap.xml"), "\n".join(sm) + "\n")
  write(os.path.join(root, "robots.txt"), f"User-agent: *\nDisallow: /admin.html\nSitemap: {SITE}/sitemap.xml\n")
  print(f"Pages: {len(listed)} cities, {len(made)} files")
  return listed
