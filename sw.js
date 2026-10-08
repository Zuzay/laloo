// Public static resources only. Private pages, APIs and map tiles stay network-only.
const VERSION = "laloo-v9-saved-places";
const PREFIX = "laloo-";
const FALLBACK = ["/offline.html", "/offline.css", "/offline.js"];
const PUBLIC_ASSETS = new Set([...FALLBACK, "/explore.css?v=8", "/logo-header.png", "/favicon-32.png", "/favicon-512.png", "/apple-touch-icon.png", "/icon-192.png", "/icon-512.png", "/icon-maskable-512.png"]);

self.addEventListener("install", event => {
  // No CDN dependency; an incomplete fallback must not replace a working worker.
  event.waitUntil(caches.open(VERSION).then(cache => cache.addAll(FALLBACK)));
  // Updates wait for existing tabs to close, keeping each tab on one version.
});
self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.filter(name => name.startsWith(PREFIX) && name !== VERSION).map(name => caches.delete(name)));
    await self.clients.claim();
  })());
});
self.addEventListener("fetch", event => {
  const request = event.request, url = new URL(request.url);
  if(request.method !== "GET" || url.origin !== self.location.origin) return;
  if(request.mode === "navigate") {
    if(!["/", "/index.html", "/offline.html"].includes(url.pathname)) return;
    event.respondWith((async () => {
      try {
        const response = await fetch(request);
        if(response.status < 500) return response;
      } catch (_) {}
      return await (await caches.open(VERSION)).match("/offline.html") || Response.error();
    })());
    return;
  }
  // Exact query matches prevent access-token URLs or unbounded variants entering cache.
  if(!PUBLIC_ASSETS.has(url.pathname + url.search)) return;
  event.respondWith((async () => {
    const cache = await caches.open(VERSION);
    // The essential fallback is versioned with the worker. Other assets stay fresh online.
    if(FALLBACK.includes(url.pathname)) {
      const cached = await cache.match(request); if(cached) return cached;
    }
    try {
      const response = await fetch(request);
      if(response.ok && response.type !== "opaque") {
        try { await cache.put(request, response.clone()); } catch (_) {}
      }
      return response;
    } catch (_) {
      return await cache.match(request) || Response.error();
    }
  })());
});
