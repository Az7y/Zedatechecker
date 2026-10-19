# -*- coding: utf-8 -*-
P='public/app.js'; s=open(P,encoding='utf-8').read()
def rep(a,b,n=1):
    global s
    c=s.count(a); assert c==n, f"want {n} got {c}: {a[:90]!r}"; s=s.replace(a,b)

# state: track remote images that failed to load
rep("photos:{}, photoReq:{}, photoTarget:null };",
    "photos:{}, photoReq:{}, photoTarget:null, deadImg:{} };")

# ensurePhoto: use a cached copy if we have one; otherwise heal a scanned product's
# picture by downloading it once into our own database (Open Food Facts links rot).
rep(
"""function ensurePhoto(key){
  if(key in S.photos||S.photoReq[key])return;S.photoReq[key]=1;
  getDoc(doc(fs,'photos',key)).then(snap=>{S.photos[key]=snap.exists()?(snap.data().data||null):null;scheduleRender();}).catch(()=>{S.photos[key]=null;});
}""",
"""function cacheRemoteImage(url){
  return new Promise(res=>{
    if(!url||/^data:/.test(url)){res(null);return;}
    const img=new Image();img.crossOrigin='anonymous';
    img.onload=()=>{try{
      let w=img.naturalWidth||img.width,h=img.naturalHeight||img.height;if(!w||!h){res(null);return;}
      const sc=Math.min(1,480/Math.max(w,h));w=Math.max(1,Math.round(w*sc));h=Math.max(1,Math.round(h*sc));
      const cv=document.createElement('canvas');cv.width=w;cv.height=h;cv.getContext('2d').drawImage(img,0,0,w,h);
      let data=cv.toDataURL('image/jpeg',0.6);if(data.length>380000)data=cv.toDataURL('image/jpeg',0.4);
      res(data.length<=380000?data:null);
    }catch(e){res(null);}};
    img.onerror=()=>res(null);img.src=url;
  });
}
function ensurePhoto(key,it){
  if(key in S.photos||S.photoReq[key])return;S.photoReq[key]=1;
  getDoc(doc(fs,'photos',key)).then(async snap=>{
    if(snap.exists()&&snap.data().data){S.photos[key]=snap.data().data;scheduleRender();return;}
    S.photos[key]=null;scheduleRender();
    // Keep a permanent copy of a scanned product's picture, so it survives Open Food Facts link rot.
    const gtin=it&&it.gtin;const remote=it&&it.gtin&&S.products[it.gtin]&&S.products[it.gtin].image;
    if((remote||gtin)&&navigator.onLine){
      let data=remote?await cacheRemoteImage(remote):null;
      if(!data&&gtin){try{const r=await lookupName(String(gtin));if(r&&r.image)data=await cacheRemoteImage(r.image);}catch(e){}}
      if(data){S.photos[key]=data;scheduleRender();try{const b=by();await setDoc(doc(fs,'photos',key),{data,byName:b.byName||'auto',at:b.at});}catch(e){}}
    }
  }).catch(()=>{S.photos[key]=null;});
}"""
)

# itemPhoto: prefer the cached copy over a remote link, and drop links that fail to load
rep(
"""function itemPhoto(it){
  const prod=it.gtin?S.products[it.gtin]:S.products['n_'+slug(it.product)];
  const key=photoKeyFor(it);
  let src=prod&&prod.image;
  if(!src){ if(S.photos[key]===undefined){ensurePhoto(key);} else if(S.photos[key]){src=S.photos[key];} }
  if(src){""",
"""function itemPhoto(it){
  const prod=it.gtin?S.products[it.gtin]:S.products['n_'+slug(it.product)];
  const key=photoKeyFor(it);
  if(S.photos[key]===undefined)ensurePhoto(key,it);
  let src=S.photos[key]||(prod&&prod.image)||null;   // our own cached copy wins over a remote link
  if(src&&S.deadImg[src])src=null;                   // a remote link that already failed to load
  if(src){"""
)

# mark remote thumbnails that fail to load as dead, so they fall back to "+ Photo"
rep("boot();\n",
"""document.addEventListener('error',e=>{const t=e.target;if(t&&t.tagName==='IMG'&&t.closest&&t.closest('.thumb')){const u=t.getAttribute('src');if(u&&!/^data:/.test(u)){S.deadImg[u]=1;scheduleRender();}}},true);
boot();
""")

open(P,'w',encoding='utf-8').write(s); print("app.js v15 (permanent product photos) patched OK")
