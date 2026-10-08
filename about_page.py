# Laloo tanıtım sayfası (laloo.org/about/)
# pages.py her gece çağırır; rakamlar (şehir, tuvalet, yıldızlı yer, sayfa) canlı veriden gelir.
# Ekran görüntüleri gerçek sitenin canlı önizlemeleri (telefon çerçevesinde iframe), hep güncel kalır.
import html, json, os
esc = lambda s: html.escape(str(s if s is not None else ""), quote=True)

FOCUS = ["istanbul", "izmir", "amsterdam", "rotterdam", "warsaw", "brussels", "paris", "la", "bay", "nyc", "miami"]

CSS = """
:root{--navy:#10223d;--blue:#1c4fa0;--red:#e0453a;--line:#e6e1d4;--bg:#fefef8;--muted:#5f6b7d;--card:#fff;--tag:#e8f0fb;--green:#1b7a3a;--greenbg:#e3f6e8;--sand:#f6f1e4}
@media (prefers-color-scheme:dark){:root{--navy:#e9eef6;--blue:#8fb4ff;--line:#2a3445;--bg:#111722;--muted:#9aa6b8;--card:#172030;--tag:#1f2e48;--green:#7fd79a;--greenbg:#1d3326;--sand:#161e2b}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%;scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--navy);font:17px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--blue)}
header{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 16px;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--bg);z-index:5}
header img{height:34px;display:block;border-radius:8px}
@media (prefers-color-scheme:dark){header img{background:#fefef8;padding:2px 6px;height:38px}}
@media (prefers-color-scheme:dark){.phone{box-shadow:0 0 0 1px rgba(255,255,255,.14),0 18px 40px rgba(0,0,0,.5)}}
header nav{display:flex;gap:6px}
.pill{display:inline-block;text-decoration:none;font-weight:700;font-size:14px;padding:8px 12px;border-radius:999px;border:1px solid var(--line);color:var(--navy)}
.pill.p{background:#1c4fa0;border-color:#1c4fa0;color:#fff}
section{padding:56px 16px}section.alt{background:var(--sand)}
.wrap{max-width:1040px;margin:0 auto}
.eyebrow{font-size:13px;font-weight:800;letter-spacing:.14em;text-transform:uppercase;color:var(--red);margin:0 0 10px}
h1{font-size:clamp(40px,9vw,76px);line-height:.98;letter-spacing:-.02em;margin:0 0 16px}
h2{font-size:clamp(30px,6vw,48px);line-height:1.05;letter-spacing:-.015em;margin:0 0 14px}
h3{font-size:20px;margin:0 0 6px}
.lead{font-size:clamp(18px,2.6vw,21px);color:var(--muted);max-width:640px;margin:0 0 22px}
.hero{display:grid;grid-template-columns:1.1fr .9fr;gap:36px;align-items:center}
@media(max-width:820px){.hero{grid-template-columns:1fr}}
.live{display:inline-flex;align-items:center;gap:8px;font-weight:800;font-size:13px;letter-spacing:.1em;color:var(--green);background:var(--greenbg);padding:6px 12px;border-radius:999px;margin:0 0 16px}
.live i{width:9px;height:9px;border-radius:50%;background:#22a35a;box-shadow:0 0 0 0 rgba(34,163,90,.6);animation:pulse 1.8s infinite}
@keyframes pulse{70%{box-shadow:0 0 0 10px rgba(34,163,90,0)}100%{box-shadow:0 0 0 0 rgba(34,163,90,0)}}
.cta{display:flex;gap:10px;flex-wrap:wrap}
.btn{display:inline-block;text-decoration:none;font-weight:800;padding:14px 20px;border-radius:14px;background:#1c4fa0;color:#fff}
.btn.o{background:transparent;color:var(--navy);border:2px solid var(--line)}
.nums{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-top:34px}
@media(max-width:820px){.nums{grid-template-columns:repeat(2,1fr)}.nums div:last-child{grid-column:1/-1}}
.nums div{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px}
.nums b{display:block;font-size:clamp(28px,5vw,40px);line-height:1;letter-spacing:-.02em}
.nums span{font-size:13px;color:var(--muted);font-weight:600}
.phone{position:relative;width:300px;height:620px;border-radius:44px;background:#0d1522;padding:12px;box-shadow:0 18px 40px rgba(16,34,61,.25);flex:0 0 auto;margin:0 auto}
.phone .scr{width:100%;height:100%;border-radius:34px;overflow:hidden;background:#fefef8;position:relative;isolation:isolate}
.phone iframe{border:0;width:394px;height:846px;transform:scale(.7);transform-origin:0 0;position:absolute;top:0;left:0}
.phone .scr{padding-top:0}.phone .scr:before{content:"";display:block;height:26px;background:#fefef8}
.phone .scr iframe{top:26px}
.phone .notch{position:absolute;top:12px;left:50%;transform:translateX(-50%);width:110px;height:24px;background:#0d1522;border-radius:0 0 16px 16px;z-index:2}
.cap{text-align:center;font-weight:700;margin:12px 0 0}.cap small{display:block;color:var(--muted);font-weight:500}
.shots{display:flex;gap:28px;overflow-x:auto;scroll-snap-type:x mandatory;padding:8px 4px 18px;margin:26px -16px 0;padding-left:16px;padding-right:16px}
.shots>div{scroll-snap-align:center}
.steps{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:26px}
@media(max-width:820px){.steps{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:18px}
.num{display:inline-flex;width:34px;height:34px;border-radius:50%;background:#1c4fa0;color:#fff;font-weight:800;align-items:center;justify-content:center;margin-bottom:10px}
.mock{background:#fff;color:#10223d;border-radius:14px;padding:12px;margin-top:12px;box-shadow:0 4px 14px rgba(16,34,61,.12);font-size:15px}
.mock .t{display:inline-block;font-size:12px;font-weight:700;padding:2px 7px;border-radius:8px;margin:4px 4px 0 0;background:#e8f0fb;color:#1c4fa0}
.mock .t.f{background:#e3f6e8;color:#1b7a3a}.mock .t.c{background:#fff4df;color:#8a5a00}.mock .t.v{background:#e3f6e8;color:#1b7a3a}
.mock .go{display:inline-block;margin-top:10px;background:#1c4fa0;color:#fff;font-weight:700;border-radius:999px;padding:7px 12px;font-size:14px}
.mock .code{display:inline-block;margin-top:10px;border:2px dashed #e0453a;color:#e0453a;font-weight:800;border-radius:10px;padding:6px 10px;letter-spacing:.06em}
.chips{display:flex;gap:6px;flex-wrap:wrap}.chips span{background:#fff;color:#10223d;border:1px solid #d9dfe8;border-radius:999px;padding:6px 10px;font-weight:700;font-size:14px}
.chips span.on{background:#1c4fa0;color:#fff;border-color:#1c4fa0}
.big{font-size:clamp(34px,7vw,64px);line-height:1;letter-spacing:-.02em;font-weight:900;margin:0 0 16px}
.big em{font-style:normal;color:var(--red)}
.two{display:grid;grid-template-columns:1fr 1fr;gap:28px;align-items:center}
@media(max-width:820px){.two{grid-template-columns:1fr}}
.walk{position:relative;height:260px;background:var(--card);border:1px solid var(--line);border-radius:18px;overflow:hidden}
.walk svg{position:absolute;inset:0;width:100%;height:100%}
.walk .lbl{position:absolute;font-size:13px;font-weight:800;background:#fff;color:#10223d;border-radius:10px;padding:5px 8px;box-shadow:0 3px 10px rgba(16,34,61,.15)}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:22px}
.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:22px}@media(max-width:980px){.grid4{grid-template-columns:repeat(2,1fr)}}@media(max-width:560px){.grid4{grid-template-columns:1fr}}
@media(max-width:820px){.grid3{grid-template-columns:1fr}}
.feat{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px}
.feat .i{font-size:26px}.feat p{margin:4px 0 0;color:var(--muted);font-size:15px}
.world{position:relative;margin-top:24px;background:var(--card);border:1px solid var(--line);border-radius:18px;padding:12px}
.world .m{position:relative;width:100%;aspect-ratio:1000/402.8;background:url(/world-land.svg) center/100% 100% no-repeat}
.world .d{position:absolute;width:7px;height:7px;margin:-3.5px 0 0 -3.5px;border-radius:50%;background:#1c4fa0;opacity:.75}
.world .d.f{width:14px;height:14px;margin:-7px 0 0 -7px;background:#e0453a;opacity:1;box-shadow:0 0 0 4px rgba(224,69,58,.22)}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:14px;color:var(--muted);margin-top:8px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:0}
.cities{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:10px;margin-top:18px}
.cities a{display:block;text-decoration:none;color:var(--navy);background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px}
.cities a b{display:block;font-size:17px}.cities a span{font-size:13px;color:var(--muted)}
.road{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:22px}
@media(max-width:820px){.road{grid-template-columns:1fr}}
.road div{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px}
.road b{font-size:13px;letter-spacing:.12em;font-weight:900}.road .l{color:var(--green)}.road .n{color:var(--blue)}.road .t{color:var(--red)}
.road ul{margin:8px 0 0;padding-left:18px;color:var(--muted);font-size:15px}
.price{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:18px}@media(max-width:620px){.price{grid-template-columns:1fr}}
.langs{display:flex;gap:2px}.langs a{font-size:13px;font-weight:700;color:var(--muted);text-decoration:none;padding:6px 7px;border-radius:8px}.langs a.on{background:var(--tag);color:var(--blue)}
@media(max-width:560px){header nav .pill{display:none}}
footer{max-width:1040px;margin:0 auto;padding:22px 16px 44px;color:var(--muted);font-size:14px;border-top:1px solid var(--line)}
"""

LANGS = ["en", "es", "de", "fr", "tr"]
try:
  TR = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "about_i18n.json"), encoding="utf-8"))
except Exception:
  TR = {}

# İngilizce sayfada: telefon dili es/de/fr/tr ise o dile geçer (kullanıcı dil seçtiyse dokunmaz)
AUTO = """<script>try{if(!localStorage.laloo_about_lang){var l=(navigator.language||"").slice(0,2).toLowerCase();if(["es","de","fr","tr"].indexOf(l)>-1)location.replace("/"+l+"/about/"+location.hash)}}catch(e){}</script>"""

def fmt(n, lang="en"):
  s = f"{n:,}"
  return s if lang == "en" else s.replace(",", "\u202f" if lang == "fr" else ".")

def lpath(lang, p):
  """/about/ -> /es/about/ ; / stays /"""
  return p if lang == "en" or p == "/" else f"/{lang}{p}"

def build(listed, routes, n_pages, names, city_url, now, site, lang="en", month=None):
  """listed: [(city_row, slug, n_tips, n_public)], routes: routes.json list.
  names(c, lang), city_url(slug, lang). Texts come from about_i18n.json (English is the key)."""
  D = TR.get(lang, {}) if lang != "en" else {}
  _ = lambda s: D.get(s) or s
  fm = lambda n: fmt(n, lang)
  n_cities = len(listed)
  n_pub = sum(x[3] for x in listed)
  n_tips = sum(x[2] for x in listed)
  total = n_pub + n_tips
  focus = [x for x in listed if x[0]["id"] in FOCUS]
  cu = lambda slug: city_url(slug, lang)
  route_url = lambda slug: lpath(lang, f"/routes/{slug}/")
  cities_url = lpath(lang, "/cities/")
  dots = []
  for c, slug, nt, npub in listed:
    lat = (c["min_lat"] + c["max_lat"]) / 2; lng = (c["min_lng"] + c["max_lng"]) / 2
    x = (lng + 180) / 360 * 100; y = (85 - max(-60, min(85, lat))) / 145 * 100
    f = c["id"] in FOCUS
    dots.append(f'<a class="d{" f" if f else ""}" href="{cu(slug)}" style="left:{x:.2f}%;top:{y:.2f}%" title="{esc(names(c, lang))}" aria-label="{esc(names(c, lang))}"></a>')
  line = _("{p} public restrooms · {t} hand-picked spots")
  focus_cards = "".join(
    f'<a href="{cu(slug)}"><b>{esc(names(c, lang))}</b><span>{esc(line.format(p=fm(npub), t=fm(nt)))}</span></a>'
    for c, slug, nt, npub in sorted(focus, key=lambda x: -(x[2] + x[3])))
  mine = [r for r in routes if lang in r["i18n"]]
  first_route = mine[0]["slug"] if mine else None
  route_list = "".join(
    f'<a href="{route_url(r["slug"])}"><b>{esc(r["i18n"][lang]["h1"])}</b><span>{esc(r["i18n"][lang]["desc"])}</span></a>'
    for r in mine)
  city_example = next((slug for c, slug, nt, npub in listed if c["id"] == "paris"), listed[0][1] if listed else "")
  month = month or now.strftime("%B %Y")
  city_url_ = cu

  body = f"""
<section>
 <div class="wrap hero">
  <div>
   <p class="live"><i></i>{_("LIVE NOW")} · {esc(month.upper())}</p>
   <h1>{_("Find a bathroom.")}<br>{_("Anywhere.")}</h1>
   <p class="lead">{_("The free map travelers open at the most urgent moment of their day. No app, no sign-up, one tap. Built on the Venice Beach boardwalk, now live in {n} cities.").format(n=fmt(n_cities))}</p>
   <div class="cta"><a class="btn" href="/?ref=about">📍 {_("Try it now")}</a><a class="btn o" href="#business">{_("For businesses")}</a><a class="btn o" href="#cities">{_("For cities")}</a><a class="btn o" href="/hosts/">{_("For hosts")}</a></div>
  </div>
  <div>
   <div class="phone"><div class="notch"></div><div class="scr"><iframe src="/?embed=1&amp;at=34.0006,-118.4846,15" title="{_("Laloo live map")}" loading="lazy"></iframe></div></div>
   <p class="cap">{_("The real map, live")}<small>{_("Santa Monica and Venice Beach")}</small></p>
  </div>
 </div>
 <div class="wrap nums">
  <div><b>{fm(n_cities)}</b><span>{_("cities live")}</span></div>
  <div><b>{fm(total)}</b><span>{_("places to go, mapped")}</span></div>
  <div><b>{fm(n_tips)}</b><span>{_("hand-picked spots")}</span></div>
  <div><b>12</b><span>{_("languages, set by the phone")}</span></div>
  <div><b>$0</b><span>{_("for every traveler, always")}</span></div>
 </div>
</section>

<section class="alt">
 <div class="wrap">
  <p class="eyebrow">{_("See it work")}</p>
  <h2>{_("Zero apps. Three taps. Relief.")}</h2>
  <div class="steps">
   <div class="card"><span class="num">1</span><h3>{_("Pick what you need")}</h3><p>{_("Public restrooms, cafés, or hand-picked spots we checked.")}</p>
    <div class="mock"><div class="chips"><span class="on">{_("All")}</span><span>🚻 {_("Public")}</span><span>☕ {_("Cafés")}</span><span>⭐ {_("Tips")}</span></div></div></div>
   <div class="card"><span class="num">2</span><h3>{_("Tap the closest pin")}</h3><p>{_("Free or paid, customers only or not, opening hours.")}</p>
    <div class="mock"><b>⭐ {_("Santa Monica Pier restrooms")}</b><br><span class="t f">{_("Free")}</span><span class="t">{_("Daytime")}</span><span class="t v">✓ {_("Verified by the city")}</span></div></div>
   <div class="card"><span class="num">3</span><h3>{_("Walk there")}</h3><p>{_("The route is drawn right on the map, with a one-tap handoff to Google Maps.")}</p>
    <div class="mock"><b>🚶 7 min · 525 m</b><br><span class="go">🚶 {_("Show route")}</span></div></div>
  </div>
  <div class="shots">
   <div><div class="phone"><div class="notch"></div><div class="scr"><iframe src="/?embed=1&amp;at=48.8606,2.3376,15" title="{_("Map in Paris")}" loading="lazy"></iframe></div></div><p class="cap">{_("Map")}<small>{_("Paris, around the Louvre")}</small></p></div>
   <div><div class="phone"><div class="notch"></div><div class="scr"><iframe src="{cu(city_example)}" title="{_("City pages")}" loading="lazy"></iframe></div></div><p class="cap">{_("City pages")}<small>{_("{n} cities, 5 languages").format(n=fmt(n_cities))}</small></p></div>
   {f'<div><div class="phone"><div class="notch"></div><div class="scr"><iframe src="{route_url(first_route)}" title="Loo Routes" loading="lazy"></iframe></div></div><p class="cap">Loo Routes<small>{_("Walks with every bathroom stop")}</small></p></div>' if first_route else ""}
   <div><div class="phone"><div class="notch"></div><div class="scr"><iframe src="/?embed=1&amp;at=41.0086,28.9760,15" title="{_("Map in Istanbul")}" loading="lazy"></iframe></div></div><p class="cap">{_("Map")}<small>{_("Istanbul, Sultanahmet")}</small></p></div>
  </div>
 </div>
</section>

<section>
 <div class="wrap two">
  <div>
   <p class="eyebrow">{_("The idea")}</p>
   <p class="big">{_("We don't sell bathrooms.")}<br><em>{_("We sell the walk.")}</em></p>
   <p class="lead">{_("Every walk to a bathroom passes shops, cafés and restaurants. Laloo lights up the right ones at the exact moment a traveler is looking at the map. Tourists, not locals: locals already know where to go.")}</p>
  </div>
  <div class="walk">
   <svg viewBox="0 0 400 260" aria-hidden="true"><path d="M40 210 C 120 200, 150 120, 220 120 S 330 60, 360 50" fill="none" stroke="#1c4fa0" stroke-width="6" stroke-linecap="round" stroke-dasharray="2 14"/></svg>
   <span class="lbl" style="left:14px;bottom:18px">📍 {_("You are here")}</span>
   <span class="lbl" style="left:44%;top:34%;background:#e0453a;color:#fff">👗 {_("Red pin on the way")} · {_("10% off")}</span>
   <span class="lbl" style="right:12px;top:10px">🚻 {_("Bathroom")} · 7 min</span>
  </div>
 </div>
</section>

<section class="alt">
 <div class="wrap">
  <p class="eyebrow">{_("Where we are")}</p>
  <h2>{_("{c} cities. {p} places.").format(c=fmt(n_cities), p=fmt(total))}</h2>
  <p class="lead">{_("Every dot is a city with its own page in five languages. The red ones are our focus cities, each with 100 hand-picked spots in the busiest tourist areas.")}</p>
  <div class="world"><div class="m">{"".join(dots)}</div>
   <div class="legend"><span><i style="background:#e0453a"></i>{_("Focus city")}</span><span><i style="background:#1c4fa0"></i>{_("Live city")}</span></div></div>
  <div class="cities">{focus_cards}</div>
  <p style="margin-top:14px"><a href="{cities_url}">{_("See all {n} cities").format(n=fmt(n_cities))} →</a></p>
 </div>
</section>

<section>
 <div class="wrap">
  <p class="eyebrow">{_("Built and live")}</p>
  <h2>{_("A working product, on the street today.")}</h2>
  <div class="grid3">
   <div class="feat"><div class="i">📍</div><h3>{_("Near me")}</h3><p>{_("One tap finds the traveler and shows the closest options.")}</p></div>
   <div class="feat"><div class="i">🚶</div><h3>{_("Route on the map")}</h3><p>{_("Walking time and distance in the page, plus Google Maps.")}</p></div>
   <div class="feat"><div class="i">⭐</div><h3>{_("Honest details")}</h3><p>{_("Free or customers only, hours, and what to expect inside.")}</p></div>
   <div class="feat"><div class="i">🌍</div><h3>{_("Speaks their language")}</h3><p>{_("12 languages, picked automatically from the phone.")}</p></div>
   <div class="feat"><div class="i">📱</div><h3>{_("Feels like an app")}</h3><p>{_("Add it to the home screen. No store, no account.")}</p></div>
   <div class="feat"><div class="i">➕</div><h3>{_("Anyone can add a place")}</h3><p>{_("Every suggestion is reviewed before it goes live.")}</p></div>
   <div class="feat"><div class="i">🏙️</div><h3>{_("City pages")}</h3><p>{_("{n} pages in 5 languages, updated every night.").format(n=fmt(n_pages))}</p></div>
   <div class="feat"><div class="i">📝</div><h3>Loo Routes</h3><p>{_("Walking guides with every bathroom stop on the way.")}</p></div>
   <div class="feat"><div class="i">📊</div><h3>{_("Real numbers")}</h3><p>{_("We measure returning visitors and taps on business pins.")}</p></div>
   <div class="feat"><div class="i">💧</div><h3>{_("Drinking water")}</h3><p>{_("Fountains and bottle refill spots, always on the map.")}</p></div>
   <div class="feat"><div class="i">📖</div><h3>{_("Laloo Stories")}</h3><p>{_("Travelers write about places only they know, with photos we pick by hand.")}</p></div>
   <div class="feat"><div class="i">🔒</div><h3>{_("Private by design")}</h3><p>{_("No account. We never store names or locations.")}</p></div>
  </div>
 </div>
</section>

<section class="alt" id="business">
 <div class="wrap two">
  <div>
   <p class="eyebrow">{_("For businesses")}</p>
   <h2>{_("Be the red pin on a tourist's walk.")}</h2>
   <p class="lead">{_("Your name, icon, hours and a discount code, shown on the route to the nearest bathroom. Then see exactly how many people saw you, tapped, asked for directions and copied your code.")}</p>
   <div class="price">
    <div class="card"><h3>{_("Free listing")}</h3><p>{_("A red pin with hours, description, website and a discount code. Keep it real with a window sticker photo now and then.")}</p></div>
    <div class="card"><h3>{_("Yearly plans")}</h3><p>{_("From about $20 to $89 a year for more visibility, deeper stats and a stop in our Loo Routes guides. The first businesses in each new city get year one free.")}</p></div>
   </div>
   <div class="cta" style="margin-top:18px"><a class="btn" href="/business.html">{_("Add your business, free")}</a><a class="btn o" href="/account.html">{_("Sign in")}</a></div>
  </div>
  <div>
   <div class="mock" style="max-width:360px;margin:0 auto">
    <b>👗 Heron CA</b><br><span class="t">{_("Local")}</span><span class="t">{_("10am to 7pm")}</span>
    <p style="margin:8px 0 0">{_("California coastal clothing, vintage and original designs on the Venice boardwalk.")}</p>
    <span class="code">{_("TAP TO COPY")} · LALOO10</span><br><span class="go">🚶 {_("Show route")}</span>
   </div>
   <div class="mock" style="max-width:360px;margin:14px auto 0">
    <b>{_("Last 30 days")}</b>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px">
     <div class="t" style="display:block;font-size:13px;padding:8px"><b style="font-size:22px;display:block">{fm(1240)}</b>{_("saw your pin")}</div>
     <div class="t" style="display:block;font-size:13px;padding:8px"><b style="font-size:22px;display:block">186</b>{_("opened it")}</div>
     <div class="t" style="display:block;font-size:13px;padding:8px"><b style="font-size:22px;display:block">74</b>{_("directions")}</div>
     <div class="t" style="display:block;font-size:13px;padding:8px"><b style="font-size:22px;display:block">39</b>{_("copied your code")}</div>
    </div>
    <p style="margin:8px 0 0;font-size:12px;color:#5f6b7d">{_("Example of the business dashboard.")}</p>
   </div>
  </div>
 </div>
</section>

<section id="cities">
 <div class="wrap two">
  <div>
   <p class="eyebrow">{_("For cities")}</p>
   <h2>{_("Your public toilets, in five languages, for free.")}</h2>
   <p class="lead">{_("We prepare a profile for each city from open data. The city claims it with an official email address, then marks toilets as closed, fixes hours and fees, and gets a “Verified by the city” badge. No fee, no contract, switch off any time.")}</p>
   <div class="cta"><a class="btn o" href="mailto:hello@laloo.org?subject=City%20profile">{_("Ask for your city's profile")}</a><a class="btn o" href="/terms.html#cities">{_("Terms for cities")}</a></div>
  </div>
  <div class="mock" style="max-width:360px;margin:0 auto">
   <b>🚻 {_("Public toilet")} · Centrum</b><br><span class="t v">✓ {_("Verified by the city")}</span><span class="t">{_("Paid")}</span><span class="t">{_("7am to 10pm")}</span>
   <p style="margin:8px 0 0">{_("Operated by the city. Contactless payment.")}</p>
   <span class="go">🚶 {_("Show route")}</span>
  </div>
 </div>
</section>

{f'<section class="alt"><div class="wrap"><p class="eyebrow">Loo Routes</p><h2>{_("Walks with every bathroom stop.")}</h2><p class="lead">{_("Travel guides centered on the walk, not on generic top-10 lists. Paying businesses appear as clearly labeled partner stops.")}</p><div class="cities">{route_list}</div></div></section>' if route_list else ""}

<section id="stories" style="border-top:1px solid var(--line)">
 <div class="wrap">
  <p class="eyebrow">{_("Laloo Stories")}</p>
  <h2>{_("Not AI. Real people, real experiences.")}</h2>
  <p class="lead">{_("Tired of travel tips that sound human but were written by a machine? On Laloo Stories, travelers and locals write about their neighborhood, the corners nobody knows and where to find a bathroom on the way. We share them in other languages, so one person's story can help someone on the other side of the world.")}</p>
  <div class="cta"><a class="btn" href="/stories/#write">{_("Share your story")}</a><a class="btn o" href="/stories/">{_("Read stories")}</a></div>
 </div>
</section>

<section>
 <div class="wrap">
  <p class="eyebrow">{_("Where we are going")}</p>
  <h2>{_("From one boardwalk to 150 tourist cities.")}</h2>
  <div class="road">
   <div><b class="l">{_("LIVE")}</b><ul><li>{_("Map, filters, routes, 12 languages")}</li><li>{_("{c} cities, {t} hand-picked spots").format(c=fmt(n_cities), t=fmt(n_tips))}</li><li>{_("City pages and Loo Routes in 5 languages")}</li><li>{_("Business pins, codes and sign-up")}</li><li>{_("Account panel for businesses and cities")}</li><li>{_("Laloo Stories, with photos")}</li><li>{_("Drinking water on the map")}</li></ul></div>
   <div><b class="n">{_("NEXT")}</b><ul><li>{_("City profiles claimed by municipalities")}</li><li>{_("Hostel and host QR packs")}</li><li>{_("“Was this helpful?” reviews")}</li><li>{_("Weekly Loo Routes")}</li></ul></div>
   <div><b class="t">{_("LATER")}</b><ul><li>{_("Moderated bathroom reviews")}</li><li>{_("Ambassador program at scale")}</li><li>{_("Bathroom access codes shared by businesses")}</li></ul></div>
  </div>
 </div>
</section>

<section class="alt">
 <div class="wrap">
  <h2>{_("Try it now. Then put your city on it.")}</h2>
  <div class="grid4">
   <div class="feat"><h3>{_("Travelers")}</h3><p>{_("Open laloo.org and tap “Near me”.")}</p><p><a href="/?ref=about">{_("Open the map")} →</a></p></div>
   <div class="feat"><h3>{_("Businesses")}</h3><p>{_("Free listing in minutes.")}</p><p><a href="/business.html">laloo.org/business.html →</a></p></div>
   <div class="feat"><h3>{_("Hosts and hostels")}</h3><p>{_("A free printable QR card for your guests.")}</p><p><a href="/hosts/">laloo.org/hosts →</a></p></div>
   <div class="feat"><h3>{_("Press, cities, investors")}</h3><p>{_("We'd love to talk.")}</p><p><a href="mailto:hello@laloo.org">hello@laloo.org</a> · Instagram <a href="https://instagram.com/loo.la.loo" rel="noopener">@loo.la.loo</a></p></div>
  </div>
 </div>
</section>
"""
  title = _("About Laloo · Find a bathroom anywhere")
  desc = _("Laloo is a free map that helps travelers find a bathroom in seconds. Live in {c} cities with {p} places. For travelers, businesses and cities.").format(c=n_cities, p=fm(total))
  canon = site + lpath(lang, "/about/")
  ab = {l: lpath(l, "/about/") for l in LANGS}
  alts = "".join(f'<link rel="alternate" hreflang="{l}" href="{site}{ab[l]}">' for l in LANGS) + f'<link rel="alternate" hreflang="x-default" href="{site}/about/">'
  langs = "".join(f'<a href="{ab[l]}" onclick="try{{localStorage.laloo_about_lang=\'{l}\'}}catch(e){{}}" class="{"on" if l == lang else ""}" lang="{l}">{l.upper()}</a>' for l in LANGS)
  return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canon}">
{alts}
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{site}/favicon-512.png">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#fefef8">
<style>{CSS}</style>
{AUTO if lang == "en" else ""}
</head>
<body>
<header><a href="/"><img src="/logo-header.png" alt="LALOO" width="120" height="34"></a>
<nav><span class="langs">{langs}</span><a class="pill p" href="/?ref=about">{_("Open the map")}</a></nav></header>
{body}
<footer><a href="https://mrspace.online/#laloo-project" target="_blank" rel="noopener">{_("A Mr. Space product")}</a> · laloo.org · {_("Made on the Venice Beach boardwalk")} · <a href="/terms.html">{_("Terms")}</a> · <a href="mailto:hello@laloo.org">hello@laloo.org</a><br>{_("Numbers updated automatically every night.")} {_("Map data © OpenStreetMap contributors.")}</footer>
</body>
</html>
"""
