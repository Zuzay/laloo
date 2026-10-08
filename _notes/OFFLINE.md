# Laloo çevrimdışı kayıtlar

Uygulama kurmadan, siteyi en az bir kez bağlantılı açıp service worker kurulduktan sonra ana sayfa bağlantısız açılabilir. İnternet yoksa `offline.html`, `offline.js` ve `offline.css` ile cihazda kaydedilen yerler gösterilir. Bu ekran CDN, harita, font veya Supabase gerektirmez. Mevcut `laloo_saved_places` kayıtları okunur; kullanıcı kayıtları değiştirilmez.

Harita, yön bulma, güncel yer bilgisi, üyelik, yönetim, yorum ve hikaye gönderimi internet gerektirir. Yerel kayıtlar diğer cihazlara aktarılmaz ve tarayıcı verileri temizlenirse kaybolur. Kayıtlı saatler ve erişim şartları güncel olmayabilir; çevrimdışı ekran bunları canlı bilgi gibi göstermez.

Service worker yalnızca belirtilen herkese açık statik dosyaları önbelleğe alır. Sayfa HTML'si, yetki belirteci taşıyan adresler, API yanıtları, harita döşemeleri ve POST istekleri önbelleğe girmez. Çevrimdışı yedek yalnızca `/`, `/index.html` ve `/offline.html` için vardır. Özel sayfalara çevrimdışı yedek verilmez.

Yeni sürüm, mevcut sekmeler kapanana kadar bekler. Temel çevrimdışı dosyalardan biri indirilemezse kurulum başarısız olur ve önceki çalışan worker korunur. Etkinleştirme yalnızca `laloo-` önekli eski önbellekleri temizler. Çevrimdışı dosyalar değiştiğinde `sw.js` içindeki VERSION da yükseltilmelidir.

`tests/browser-resilience.mjs` gerçek Chrome, gerçek service worker ve yerel HTTP sunucusuyla çalışır. İnternetteki API'ler engellenir; ana harita ekranı bağlantı dönüşünü kontrol etmek için fixture'dır. Testler haritanın bütün çevrimdışı çalıştığını iddia etmez. Kontroller: üçüncü taraflar kapalı kurulum, cihaz kayıtları ve güvenli metin gösterimi, beş dil, açık/koyu mobil görünüm, hatalı/dolu kayıt, koordinat sınırları, özel veri önbellek sınırı, canlıya geri dönüş, bekleyen güncelleme ve başarısız kurulum.

Ortam: `MS_PLAYWRIGHT_MODULE` Playwright modülünün mutlak yolu, `MS_CHROME_PATH` Chrome yolu, isteğe bağlı `MS_TEST_ARTIFACTS` ekran görüntüsü dizini. Çalıştır: `node tests/browser-resilience.mjs`.
