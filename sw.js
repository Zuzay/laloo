// Laloo service worker: uygulama kabuğunu saklar, veri ve harita her zaman canlı gelir
const V = "laloo-v7-modern-markers";
const SHELL = ["./", "index.html", "explore.css?v=7", "logo-header.png", "favicon-32.png", "icon-192.png", "icon-512.png",
  "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css",
  "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(V).then(c => c.addAll(SHELL)).catch(() => {}));
  self.skipWaiting();
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== V).map(k => caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener("fetch", e => {
  const r = e.request;
  if (r.method !== "GET") return;
  const u = new URL(r.url);
  // Supabase, rota servisi, harita karoları, admin: hiç dokunma
  if (u.hostname.endsWith("supabase.co") || u.hostname.includes("openstreetmap") || u.pathname.endsWith("admin.html")) return;
  // Sayfanın kendisi: önce internet (güncel kalsın), yoksa kayıtlı kopya
  if (r.mode === "navigate"){
    // Sadece harita sayfası önbelleğe yazılır; şehir sayfaları ve diğerleri normal yüklenir
    if (u.origin !== location.origin || !(u.pathname === "/" || u.pathname.endsWith("/index.html") && u.pathname.split("/").length === 2)) return;
    e.respondWith(fetch(r).then(res => { const c = res.clone(); caches.open(V).then(x => x.put("index.html", c)); return res; })
      .catch(() => caches.match("index.html")));
    return;
  }
  // Logo, ikon, Leaflet: önce kayıtlı kopya
  if (SHELL.some(s => r.url.endsWith(s.replace("./", "")) && s !== "./")){
    e.respondWith(caches.match(r).then(m => m || fetch(r)));
  }
});
