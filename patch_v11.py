# -*- coding: utf-8 -*-
P='public/app.js'; s=open(P,encoding='utf-8').read()
def rep(a,b,n=1):
    global s
    c=s.count(a); assert c==n, f"want {n} got {c}: {a[:80]!r}"; s=s.replace(a,b)

# ---- Boss activity is private: hide admin (Boss) actions from everyone but the Boss ----
rep("  for(const it of S.items)for(const h of (it.history||[]))if(h.byName){",
    "  for(const it of S.items)for(const h of (it.history||[]))if(h.byName&&!(h.by==='admin'&&!S.me.owner)){")
rep("  for(const s of S.sections)for(const h of (s.history||[]))if(h.byName)ev.push(",
    "  for(const s of S.sections)for(const h of (s.history||[]))if(h.byName&&!(h.by==='admin'&&!S.me.owner))ev.push(")

# ---- easter eggs: define the machinery right after stopCamera ----
rep("async function stopCamera(){const c=cam;cam=null;S.camOn=false;torchOn=false;if(c){try{await c.stop()}catch(e){}try{c.clear()}catch(e){}}render()}",
"""async function stopCamera(){const c=cam;cam=null;S.camOn=false;torchOn=false;if(c){try{await c.stop()}catch(e){}try{c.clear()}catch(e){}}render()}

/* ---------- hidden easter eggs (harmless, found by curious hands) ---------- */
const ASCII_BOOM=`     *   .   |   .   *
        .  -+-  .
   *  --( B O O M )--  *
        '  -+-  '
     *   .   |   .   *`;
const EGGS={oz7y:'Who is Oz7y',xyzzy:'The magic word',logo:'Logo tickler',sameer:'The idea guy'};
function eggsFound(){try{return JSON.parse(localStorage.getItem('sdc_eggs')||'[]')}catch(e){return[]}}
function eggModal(inner){
  let m=document.getElementById('eggModal');if(m)m.remove();
  m=document.createElement('div');m.id='eggModal';m.className='egg-modal';
  m.innerHTML=`<div class="egg-card">${inner}<button type="button" class="btn primary" data-eggclose="1">Nice</button></div>`;
  document.body.appendChild(m);
}
function foundEgg(id,title,body){
  const found=eggsFound();const isNew=!found.includes(id);
  if(isNew){found.push(id);try{localStorage.setItem('sdc_eggs',JSON.stringify(found))}catch(e){}}
  if(navigator.vibrate)navigator.vibrate([25,35,25]);
  const total=Object.keys(EGGS).length;
  eggModal(`<pre class="egg-boom">${ASCII_BOOM}</pre><h3>${esc(title)}</h3><p>${esc(body)}</p>
    <div class="egg-count">${isNew?'New secret unlocked · ':''}${found.length} of ${total} found</div>
    ${found.length>=total?'<div class="egg-all">🏆 Every secret found. Absolute legend.</div>':''}`);
}
function showTrophies(){
  const found=eggsFound();const total=Object.keys(EGGS).length;
  const rows=Object.entries(EGGS).map(([id,name])=>`<div class="egg-row">${found.includes(id)?'✅ '+esc(name):'🔒 • • •'}</div>`).join('');
  eggModal(`<h3>Secrets</h3><div class="egg-list">${rows}</div><div class="egg-count">${found.length} of ${total} found</div>
    ${found.length<total?'<p class="note">Keep poking around…</p>':''}`);
}
let eggCount={},eggResetT=null;
function tapEgg(which){
  clearTimeout(eggResetT);eggResetT=setTimeout(()=>{eggCount={}},3000);
  if(which==='oz7y'){
    eggCount.oz7y=(eggCount.oz7y||0)+1;const left=6-eggCount.oz7y;
    if(left>0){flash(`${left} more touch${left===1?'':'es'} to know who Oz7y is…`);return}
    eggCount={};foundEgg('oz7y','Oz7y, revealed','Oz7y is the one who dreamed up and built Zedatechecker — stacking shelves by day, writing code by night. Now you know. 👋');return;
  }
  if(which==='logo'){eggCount.logo=(eggCount.logo||0)+1;if(eggCount.logo>=3){eggCount={};foundEgg('logo','You tickled the logo','It giggled. ✨ Nothing else to see here… or is there?');}return;}
  if(which==='sameer'){eggCount.sameer=(eggCount.sameer||0)+1;if(eggCount.sameer>=3){eggCount={};foundEgg('sameer','The idea guy','Every good app starts with someone saying “what if…”. That was Sameer. 🌟');}return;}
  if(which==='ver'){showTrophies();return;}
}
const SECRET={
  'xyzzy':()=>foundEgg('xyzzy','Nothing happens.','…or does it? Any old-school adventurer would smile. You found a secret. 🕸️')
};"""
)

# ---- scan box: intercept magic words before treating input as a barcode ----
rep("function applyScan(raw){\n  if(!raw||!raw.trim())return;",
    "function applyScan(raw){\n  if(!raw||!raw.trim())return;\n  const _code=raw.trim().toLowerCase();if(SECRET[_code]){SECRET[_code]();return;}")

# ---- click handler: egg taps + modal close (before the button lookup) ----
rep("  const t=e.target.closest('button');if(!t)return;\n  const d=t.dataset;",
    "  if(e.target.id==='eggModal'){e.target.remove();return}\n"
    "  if(e.target.closest('[data-eggclose]')){document.getElementById('eggModal')?.remove();return}\n"
    "  const _eg=e.target.closest('[data-egg]');if(_eg){tapEgg(_eg.dataset.egg);return}\n"
    "  const t=e.target.closest('button');if(!t)return;\n  const d=t.dataset;")

open(P,'w',encoding='utf-8').write(s); print("app.js v11 (easter eggs + boss-private activity) patched OK")
