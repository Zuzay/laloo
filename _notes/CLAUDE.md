# Laloo: Claude notları

Bu dosya Claude içindir. `_` ile başlayan klasör GitHub Pages'te yayınlanmaz (repoda .nojekyll yok, olursa bu dosya herkese açılır).
Her oturumda önce bu dosya okunur, sonra sadece ilgili dosyanın ilgili kısmı. İş kararları, fiyatlar, komisyonlar burada yok; onlar claude.ai projesindeki LALOO_PROJE.md'de.

## Kurallar
- Uzay dosyaları GitHub web'den yükler; Claude push yapmaz. Değişiklik = yüklemeye hazır tam dosya.
- SQL repoya konmaz; tek dosya olarak Supabase SQL Editor'e yapıştırılır.
- Kökte geçici/eski kopya dosya bırakılmaz (index_16.html, *.sql silindi, 2 Ekim).
- Her değişiklikte aşağıdaki "Değişiklik günlüğü"ne 1 satır eklenir.

## Dosya haritası
- index.html: Harita (MapLibre + OpenFreeMap, WebGL yoksa OSM). Pinler, filtreler, içme suyu, hikaye pinleri, puan ortalaması, rota (OSRM), arama (Photon), ?i= davet kodu, ?ref= ölçüm, erken üye sayacı. Supabase'e publishable key ile okur; sadece active=not.is.false yerler.
- admin.html: Yönetim paneli (Supabase girişi, admins tablosu). Sekmeler: Rakamlar, Yıldızlı yerler, İşletmeler, Belediyeler, Öneriler, Reddit, Hikayeler, Puanlar, Üyeler, Ayarlar (şehir linki + SVG QR).
- account.html: E-posta linkiyle giriş, işletme/belediye paneli. Erken üyeyi /join/'e yönlendirir. Oturum anahtarı laloo_acc.
- business.html: İşletme kaydı. terms.html: Koşullar.
- stories/index.html: Hikaye formu (ses ile yazma, önizleme, fotoğraf) + dinamik hikaye sayfası (?id=). Canonical'ı statik sayfaya çevirir.
- stories/<slug>-<id6>/ ve /<dil>/: pages.py üretir, elle dokunulmaz.
- rate/index.html: Puanlama (submit_review RPC, 250 m içindeki yerler, ?p=yer id).
- join/index.html: Erken üyelik (member_join RPC, e-posta linki, üye sayfası, davet linki/QR).
- tour/index.html: İki animasyon (?v=stories), ?lang=, ?rec=1. Fontlar tour/fonts, ses tour/audio/<a|b>-<dil>-<sahne>.mp3 (henüz yok).
- hosts/, about/, routes/, <şehir>/, tr/ es/ de/ fr/: pages.py / about_page.py çıktıları, elle dokunulmaz.
- build.py: Gece koşusu. OSM'den en eski 30 şehri günceller (osm_id upsert, silinen nokta active=false), adres bulur (450/koşu, bulamazsa "??"), Reddit tarar, sonra pages.generate çağırır.
- pages.py: Şehir sayfaları (10+ yer), Loo Routes (routes.json), hikaye statik sayfaları, sitemap.xml, llms.txt, cities.json, pages-manifest.json (eski sayfaları silmek için).
- about_page.py + about_i18n.json: /about/ 5 dilde.
- backup.py: Haftalık şifreli yedek (tablolar otomatik bulunur).
- .github/workflows/update.yml: Günde 2 koşu, timeout 150 dk. backup.yml: Pazar.
- sw.js, manifest.webmanifest, qrcode.js, ikonlar: PWA ve QR.

## Veritabanı (Supabase)
- Ziyaretçi yazmaları sadece RPC ile: submit_review, member_join, place_reviews, admin_delete_muni vb.
- Herkese açık view'lar: stories_public, reviews_public. Admin kuralı: laloo_is_admin().
- Fotoğraflar: story-photos deposu (pending/place-*.jpg dahil).

## Bilinen durumlar
- Hikaye statik sayfası yok çünkü yayında hikaye yok (2 Ekim). İlk yayından sonraki koşuda çıkmalı; çıkmazsa Actions logunda "stories fetch failed" aranır.
- Claude'un ortamından laloo.org ve Supabase'e erişim yok; repo herkese açık klonlanabiliyor.

## Değişiklik günlüğü
- 09-28: Güvenlik kontrolü, backup.py + backup.yml, içme suyu.
- 09-29: Blok 1 (rate, join, hikaye ses/önizleme/pin, foto zorunlu öneri, belediye silme, şikayet/küfür). laloo_fix2.sql: sayaç bekleyenleri sayar. account.html /join/ yönlendirmesi.
- 10-02: Blok 2a yüklendi (pages.py hikaye sayfaları + llms.txt + cities.json, build.py, admin şehir linki/QR, stories canonical, tour/). Koşu doğrulandı: llms.txt ve cities.json oluştu.
- 10-02: index_16.html ve laloo_blok1.sql repodan silindi. Bu not dosyası eklendi.

- 10-07: Harita yenilendi: yakın yer kartları, Keşfet/Kaydedilen sekmeleri, cihazda kayıt, su filtresi, mobil alt panel ve klavye erişimi; index.html, explore.css, sw.js.

- 10-07: Sol panelde üst alan sadeleştirildi, panel genişletildi, filtreler görünür satırlara alındı; liste alanı büyütüldü ve kısa ekranda tek kaydırma kullanıldı.

- 10-07: Tüm harita işaretleri resmî Phosphor SVG simgeleriyle yenilendi; ortak işaret sistemi, 44px dokunma alanı, seçili/odak/kapalı durumları, işletmeler ve konum noktası; yakın işaretlerde seçilebilir sayılı gruplar, bağımsız detay kutuları; simgeler ana dosyada, lisans dâhil.

- 10-07: Uzay bu oturumda onaylı tasarımın canlıya yüklenmesini istedi; bu yayın için GitHub ana dalının güncellenmesine açık izin verdi.

- 10-07: Mobil panel üçte bir yükseklikte başlar; gerçek tutamaçla sürükleme, kısa panjur geçişi, aramada açılma, klavye/iptal ve ekran değişimine uyum eklendi. Mobil harita merkez etiketi kaldırıldı; masaüstü paneli korunur.

- 10-08: Mr. Space ürün kredisi harita alt alanına 12 dilde ve Hakkında sayfalarına 5 dilde hazırlandı. about_page.py/sözlük de güncellendi. Ayrı inceleme dalı; bu çalışma yayın onayı vermiyor.

- 10-08: CDN bağımlılığı olmayan çevrimdışı Kaydedilen yerler ekranı, beş dil, özel veri ve harita önbelleği sınırları, sekme kapanışını bekleyen güvenli güncelleme ve gerçek tarayıcı testleri hazırlandı; PR 2 güncelleniyor.
