/* The fallback has no map, CDN or API dependency. Saved records stay on this device. */
(() => {
  'use strict';
  const LANGS = ['en','tr','es','de','fr'];
  const copy = {
    credit:['A Mr. Space product','Bir Mr. Space ürünü','Un producto de Mr. Space','Ein Produkt von Mr. Space','Un produit de Mr. Space'],
    languageLabel:['Language','Dil','Idioma','Sprache','Langue'],
    connection:['Offline','Çevrimdışı','Sin conexión','Offline','Hors connexion'],
    title:['Your saved places','Kaydettiğin yerler','Tus lugares guardados','Deine gespeicherten Orte','Vos lieux enregistrés'],
    description:['Places saved on this device are available here. The map and live information need a connection.','Bu cihazda kaydettiğin yerleri burada görebilirsin. Harita ve güncel bilgiler için bağlantı gerekir.','Aquí están los lugares guardados en este dispositivo. El mapa y la información actual requieren conexión.','Hier findest du die auf diesem Gerät gespeicherten Orte. Karte und aktuelle Informationen benötigen eine Verbindung.','Les lieux enregistrés sur cet appareil sont disponibles ici. La carte et les informations à jour nécessitent une connexion.'],
    retry:['Try connecting again','Yeniden bağlanmayı dene','Intentar conectar de nuevo','Verbindung erneut versuchen','Réessayer la connexion'],
    empty:['No places saved on this device yet. Save a place with the bookmark button when you reconnect.','Bu cihazda henüz kayıtlı yer yok. Bağlantı geldiğinde yerleri yer imi düğmesiyle kaydedebilirsin.','Aún no hay lugares guardados en este dispositivo. Guárdalos con el botón de marcador al reconectar.','Noch keine Orte auf diesem Gerät gespeichert. Speichere Orte nach dem Verbinden mit der Lesezeichen-Schaltfläche.','Aucun lieu enregistré sur cet appareil. Enregistrez des lieux avec le bouton de signet une fois reconnecté.'],
    freshness:['Saved details may have changed. Check opening hours and access when you reconnect.','Kayıtlı bilgiler değişmiş olabilir. Bağlantı geldiğinde saatleri ve erişim koşullarını kontrol et.','Los datos guardados pueden haber cambiado. Comprueba horarios y acceso al reconectar.','Gespeicherte Angaben können sich geändert haben. Prüfe Öffnungszeiten und Zugang nach dem Verbinden.','Les informations enregistrées peuvent avoir changé. Vérifiez horaires et accès après reconnexion.'],
    unavailable:['Device storage could not be read. Your saved records have not been changed.','Cihaz kayıtları okunamadı. Kayıtlı yerlerin değiştirilmedi.','No se pudo leer el almacenamiento. Tus registros no se han modificado.','Gerätespeicher konnte nicht gelesen werden. Deine Einträge wurden nicht geändert.','Impossible de lire le stockage. Vos enregistrements n’ont pas été modifiés.'],
    connected:['Connection detected. Try again to open the live map.','Bağlantı algılandı. Güncel haritayı açmak için yeniden dene.','Conexión detectada. Reintenta para abrir el mapa actual.','Verbindung erkannt. Versuche erneut, die aktuelle Karte zu öffnen.','Connexion détectée. Réessayez pour ouvrir la carte à jour.'],
    count:['{n} places saved on this device','Bu cihazda {n} kayıtlı yer','{n} lugares guardados en este dispositivo','{n} Orte auf diesem Gerät gespeichert','{n} lieux enregistrés sur cet appareil'],
    unnamed:['Saved place','Kaydedilen yer','Lugar guardado','Gespeicherter Ort','Lieu enregistré'],
    coordinates:['Coordinates','Koordinatlar','Coordenadas','Koordinaten','Coordonnées']
  };
  let lang = new URLSearchParams(location.search).get('lang');
  try { lang ||= localStorage.getItem('laloo_lang') || localStorage.getItem('lang'); } catch (_) {}
  if(!LANGS.includes(lang)) lang = (navigator.language || 'en').split('-')[0];
  if(!LANGS.includes(lang)) lang = 'en';
  let places=[],storageError=false;
  const text = v => typeof v === 'string' ? v.slice(0,1500) : '';
  try {
    const raw=localStorage.getItem('laloo_saved_places');
    if(raw && raw.length > 2000000) throw new Error('too_large');
    const records=JSON.parse(raw || '[]');
    if(!Array.isArray(records)) throw new Error('invalid');
    places=records.filter(p=>p && typeof p==='object' && Number.isFinite(p.lat) && Number.isFinite(p.lng) && Math.abs(p.lat)<=90 && Math.abs(p.lng)<=180).slice(0,100);
  } catch(_){storageError=true;}
  function draw(){
    const li=LANGS.indexOf(lang), t=k=>copy[k][li];
    document.documentElement.lang=lang;document.title=t('title')+' · Laloo';
    Object.keys(copy).forEach(k=>{const el=document.getElementById(k);if(el)el.textContent=t(k);});
    document.getElementById('language').value=lang;
    document.getElementById('count').textContent=t('count').replace('{n}',places.length);
    document.getElementById('empty').hidden=places.length>0 || storageError;
    document.getElementById('notice').textContent=storageError?t('unavailable'):navigator.onLine?t('connected'):'';
    const list=document.getElementById('places');list.replaceChildren();
    places.forEach(p=>{
      const card=document.createElement('article'), name=document.createElement('h2'), loc=p.i18n?.[lang];
      name.textContent=text(loc?.name || p.name)||t('unnamed');card.append(name);
      [text(loc?.info || p.info),text(p.address)].filter(Boolean).forEach(value=>{const line=document.createElement('p');line.textContent=value;card.append(line);});
      const coordinates=document.createElement('p');coordinates.className='coordinates';coordinates.textContent=t('coordinates')+': '+p.lat.toFixed(6)+', '+p.lng.toFixed(6);card.append(coordinates);list.append(card);
    });
  }
  document.getElementById('language').onchange=e=>{lang=e.target.value;try{localStorage.setItem('laloo_lang',lang);}catch(_){}draw();};
  document.getElementById('retry').onclick=()=>{
    if(location.pathname==='/offline.html')location.assign('/?lang='+encodeURIComponent(lang));else location.reload();
  };
  addEventListener('online',draw);addEventListener('offline',draw);addEventListener('storage',e=>{if(e.key==='laloo_saved_places')location.reload();});draw();
})();
