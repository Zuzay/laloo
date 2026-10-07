// Laloo service worker: cache the app shell only; map data and tiles stay live.
const V = "laloo-v4";
const CACHE_PREFIX = "laloo-";
const LOCAL_SHELL = [
  "./", "index.html", "logo-header.png", "favicon-32.png", "favicon-512.png",
  "apple-touch-icon.png", "icon-192.png", "icon-512.png", "icon-maskable-512.png"
];
const REMOTE_SHELL = [
  "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css",
  "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"
];

self.addEventListener("install", event => {
  event.waitUntil((async () => {
    const cache = await caches.open(V);
    // A third-party CDN outage should not prevent the local app shell installing.
    await cache.addAll(LOCAL_SHELL);
    await Promise.all(REMOTE_SHELL.map(async url => {
      try {
        const response = await fetch(url);
        if (response.ok) await cache.put(url, response);
      } catch (_) {}
    }));
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys
      .filter(key => key.startsWith(CACHE_PREFIX) && key !== V)
      .map(key => caches.delete(key)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", event => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  // Supabase, route services, map tiles and other sites always stay network-only.
  if (url.hostname.endsWith("supabase.co") || url.hostname.includes("openstreetmap") || url.pathname.endsWith("admin.html")) return;

  if (request.mode === "navigate") {
    // Only the map app entry point is cached; city pages and other routes are untouched.
    const isAppEntry = url.origin === self.location.origin &&
      (url.pathname === "/" || url.pathname.endsWith("/index.html") && url.pathname.split("/").length === 2);
    if (!isAppEntry) return;

    event.respondWith((async () => {
      const cache = await caches.open(V);
      try {
        const response = await fetch(request);
        if (response.ok) {
          try { await cache.put("index.html", response.clone()); } catch (_) {}
        }
        return response;
      } catch (_) {
        return await cache.match("index.html") || Response.error();
      }
    })());
    return;
  }

  const localShell = url.origin === self.location.origin && LOCAL_SHELL.some(path => {
    const shellUrl = new URL(path, self.registration.scope);
    return shellUrl.pathname === url.pathname;
  });
  const remoteShell = REMOTE_SHELL.includes(url.href);
  if (!localShell && !remoteShell) return;

  event.respondWith((async () => {
    const cache = await caches.open(V);
    const cached = await cache.match(request);
    if (cached) return cached;
    const response = await fetch(request);
    if (response.ok) {
      try { await cache.put(request, response.clone()); } catch (_) {}
    }
    return response;
  })());
});
