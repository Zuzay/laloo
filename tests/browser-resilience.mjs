// Real service worker and offline Chrome. The online map is a fixture; no live APIs.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import {pathToFileURL} from 'node:url';
const root=path.resolve(import.meta.dirname,'..');
const {chromium}=await import(pathToFileURL(process.env.MS_PLAYWRIGHT_MODULE));
let oldWorker=false,failAsset=false;
const server=http.createServer((req,res)=>{
 const url=new URL(req.url,'http://local');
 if(url.pathname==='/sw.js' && oldWorker){res.writeHead(200,{'Content-Type':'text/javascript','Cache-Control':'no-store'}).end(`self.addEventListener('install',e=>e.waitUntil((async()=>{await caches.open('laloo-test-old');await caches.open('foreign-cache');})()));self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));`);return;}
 if(url.pathname==='/offline.css' && failAsset){res.writeHead(503).end();return;}
 if(url.pathname==='/__test__' || url.pathname==='/'){res.writeHead(200,{'Content-Type':'text/html','Cache-Control':'no-store'}).end('<!doctype html><title>Live map fixture</title><h1>Live map fixture</h1>');return;}
 if(['/admin.html','/account.html','/toilets.json','/test-tile.png'].includes(url.pathname)){res.writeHead(200,{'Content-Type':'text/plain'}).end('network-only fixture');return;}
 const file=path.resolve(root,'.'+url.pathname);if(!file.startsWith(root+path.sep)){res.writeHead(403).end();return;}
 try{const body=fs.readFileSync(file),type=({'.html':'text/html','.js':'text/javascript','.css':'text/css','.png':'image/png'})[path.extname(file)]||'application/octet-stream';res.writeHead(200,{'Content-Type':type,'Cache-Control':'no-store'}).end(body);}catch(_){res.writeHead(404).end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const origin='http://127.0.0.1:'+server.address().port;
const browser=await chromium.launch({executablePath:process.env.MS_CHROME_PATH,headless:true});
const artifacts=process.env.MS_TEST_ARTIFACTS||'/private/tmp/mrspace-validation';fs.mkdirSync(artifacts,{recursive:true});let passed=0;
async function test(name,fn){await fn();passed++;console.log('PASS '+name);}
async function fixture(lang='tr'){
 const context=await browser.newContext({viewport:{width:390,height:844},locale:lang,serviceWorkers:'allow'}),errors=[];
 await context.route('**/*',route=>new URL(route.request().url()).origin===origin?route.continue():route.abort());
 const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));await page.goto(origin+'/__test__');
 return {context,page,errors};
}
async function install(page){
 await page.evaluate(async()=>{
  await navigator.serviceWorker.register('/sw.js');await navigator.serviceWorker.ready;
  if(!navigator.serviceWorker.controller)await new Promise(resolve=>navigator.serviceWorker.addEventListener('controllerchange',resolve,{once:true}));
 });
}
const records=[{name:'Saved cafe',kind:'cafe',info:'12 Sample Street',lat:37.77,lng:-122.41,i18n:{tr:{info:'Örnek Sokak 12'}}},{name:'<img src=x onerror="window.injected=true">',info:'<script>window.injected=true</script>',lat:41,lng:29}];
try{
 await test('worker installs with every third-party request blocked and saved places open offline',async()=>{
  const f=await fixture();await install(f.page);await f.page.evaluate(records=>localStorage.setItem('laloo_saved_places',JSON.stringify(records)),records);await f.context.setOffline(true);await f.page.goto(origin+'/?ref=app');await f.page.locator('#places article').first().waitFor();assert.equal(await f.page.locator('#places article').count(),2);assert.match(await f.page.locator('#places').innerText(),/Örnek Sokak/);assert.equal(await f.page.locator('#places img,#places script').count(),0);assert.equal(await f.page.evaluate(()=>window.injected),undefined);assert.equal(await f.page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);assert.deepEqual(f.errors,[]);
  await f.page.screenshot({path:artifacts+'/laloo-offline-saved-mobile.png',fullPage:true});
  await f.context.setOffline(false);await f.page.getByRole('button',{name:'Yeniden bağlanmayı dene',exact:true}).click();await f.page.getByRole('heading',{name:'Live map fixture'}).waitFor();await f.context.close();
 });
 await test('five languages and both themes work offline without API or font dependencies',async()=>{
  const titles=['Your saved places','Kaydettiğin yerler','Tus lugares guardados','Deine gespeicherten Orte','Vos lieux enregistrés'];
  for(const [i,lang] of ['en','tr','es','de','fr'].entries()){
   const f=await fixture(lang);await install(f.page);await f.context.setOffline(true);await f.page.emulateMedia({colorScheme:i%2?'dark':'light'});await f.page.goto(origin+'/index.html?lang='+lang);await f.page.getByRole('heading',{name:titles[i],exact:true}).waitFor();assert.equal(await f.page.locator('#empty').isVisible(),true);assert.equal(await f.page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);assert.deepEqual(f.errors,[]);await f.context.close();
  }
 });
 await test('invalid JSON, oversized storage and invalid coordinates fail visibly without changing saved records',async()=>{
  for(const value of ['{',JSON.stringify({bad:true}),'x'.repeat(2000001),JSON.stringify([{lat:91,lng:0},{lat:0,lng:181},{lat:0,lng:0,name:'Valid'}])]){
   const f=await fixture();await install(f.page);await f.page.evaluate(v=>localStorage.setItem('laloo_saved_places',v),value);await f.context.setOffline(true);await f.page.goto(origin+'/');await f.page.locator('#retry').waitFor();assert.equal(await f.page.evaluate(()=>localStorage.getItem('laloo_saved_places')),value);assert.equal(await f.page.locator('#places article').count(),value.includes('Valid')?1:0);if(!value.includes('Valid'))assert.match(await f.page.locator('#notice').innerText(),/okunamadı/);assert.deepEqual(f.errors,[]);await f.context.close();
  }
 });
 await test('private pages, credentials, live data, map tiles and non-GET requests never enter cache',async()=>{
  const f=await fixture();await install(f.page);await f.page.evaluate(async()=>{
   for(const url of ['/admin.html','/account.html','/toilets.json?d=test','/test-tile.png','/icon-192.png?token=secret'])await fetch(url);
   await fetch('/admin.html',{method:'POST',body:'private'});
  });const cached=await f.page.evaluate(async()=>{const result=[];for(const name of await caches.keys())for(const req of await (await caches.open(name)).keys())result.push(req.url);return result;});
  assert.equal(cached.length,3);assert.equal(cached.some(u=>/admin|account|toilets|tile|secret/.test(u)),false);await f.context.setOffline(true);await assert.rejects(()=>f.page.goto(origin+'/admin.html'));await f.context.close();
 });
 await test('updates wait for old tabs; activation preserves unrelated caches',async()=>{
  oldWorker=true;const f=await fixture();await install(f.page);assert.ok((await f.page.evaluate(()=>caches.keys())).includes('laloo-test-old'));oldWorker=false;
  await f.page.evaluate(async()=>{const registration=await navigator.serviceWorker.getRegistration();await registration.update();});
  await f.page.waitForFunction(async()=>Boolean((await navigator.serviceWorker.getRegistration()).waiting));assert.ok((await f.page.evaluate(()=>caches.keys())).includes('laloo-test-old'));assert.ok((await f.page.evaluate(()=>caches.keys())).includes('foreign-cache'));
  await f.page.close();await new Promise(resolve=>setTimeout(resolve,700));const next=await f.context.newPage();await next.goto(origin+'/__test__');await next.waitForFunction(async()=>!(await caches.keys()).includes('laloo-test-old'));assert.ok((await next.evaluate(()=>caches.keys())).includes('foreign-cache'));assert.ok((await next.evaluate(()=>caches.keys())).includes('laloo-v9-saved-places'));await f.context.setOffline(true);await next.goto(origin+'/');await next.locator('#retry').waitFor();await f.context.close();
 });
 await test('incomplete fallback cannot activate a worker or discard the prior version',async()=>{
  oldWorker=true;const f=await fixture();await install(f.page);oldWorker=false;failAsset=true;await f.page.evaluate(async()=>{try{await (await navigator.serviceWorker.getRegistration()).update();}catch(_){}});await f.page.waitForTimeout(500);assert.ok((await f.page.evaluate(()=>caches.keys())).includes('laloo-test-old'));assert.equal(await f.page.evaluate(async()=>Boolean((await navigator.serviceWorker.getRegistration()).waiting)),false);failAsset=false;await f.context.close();
 });
 console.log(`${passed} Laloo offline groups passed; no live writes.`);
}finally{oldWorker=false;failAsset=false;await browser.close();await new Promise(resolve=>server.close(resolve));}
