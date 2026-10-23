# -*- coding: utf-8 -*-
P='public/app.js'; s=open(P,encoding='utf-8').read()
def rep(a,b,n=1):
    global s
    c=s.count(a); assert c==n, f"want {n} got {c}: {a[:90]!r}"; s=s.replace(a,b)

# state: remember an item to jump to after a scan
rep("  loaded:{}, tab:'today', filter:{q:'',status:'active'}, scan:null, camOn:false,",
    "  loaded:{}, tab:'today', filter:{q:'',status:'active'}, scan:null, camOn:false, goto:null,")

# camera: scan the WHOLE frame (no cropped box) so a barcode reads at more distances
# and positions, and run a touch slower per frame since the detector now does more work.
rep("  const cfg={fps:15,qrbox:(w,h)=>({width:Math.min(320,Math.round(w*0.9)),height:Math.min(210,Math.round(h*0.55))})};",
    "  const cfg={fps:10};  // no qrbox = decode the full frame, which is what lets it catch a barcode held further away")

# manual-entry row: numeric keypad + a Go button; camera on its own row below
rep('''    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <input id="scan_in" autocomplete="off" placeholder="Scanner input, or type a barcode" aria-label="Barcode" style="flex:1 1 220px">
      <button type="button" class="btn primary" data-camera="1">${S.camOn?'Stop camera':'Scan with camera'}</button>
      ${S.camOn?`<button type="button" class="btn" data-torch="1">${torchOn?'Torch off':'Torch'}</button>`:''}
    </div>''',
'''    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <input id="scan_in" type="text" inputmode="numeric" pattern="[0-9]*" enterkeyhint="go" autocomplete="off" placeholder="Type or scan a barcode" aria-label="Barcode" style="flex:1 1 150px">
      <button type="button" class="btn primary" data-scango="1" style="flex:0 0 auto;min-width:64px">Go</button>
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <button type="button" class="btn" data-camera="1" style="flex:1 1 auto">${S.camOn?'Stop camera':'📷 Scan with camera'}</button>
      ${S.camOn?`<button type="button" class="btn" data-torch="1">${torchOn?'Torch off':'Torch'}</button>`:''}
    </div>''')

# softer camera hint (detection is more forgiving now)
rep('''    ${S.camOn?`<div class="note">Hold the barcode about <b>20&nbsp;cm</b> away (a hand's length), not right up against the lens — phone cameras can't focus that close. Keep steady; tap Torch in low light.</div>`:''}''',
    '''    ${S.camOn?`<div class="note">Point at the barcode and hold steady — it reads at most distances now. Tap Torch in low light. If a phone still struggles, typing the number or a Bluetooth scanner always works.</div>`:''}''')

# stock rows become tappable: jump straight to that item in All items
rep('''        ${onShelf.map(i=>{const n=daysLeft(i.expiry);return `<div class="stockrow">
          <span class="stockdate">${esc(fmtExp(i.expiry))}</span>
          <span class="pill ${band(n)}">${dueLabel(n)}</span>
          ${i.location?`<span class="stockloc">${esc(i.location)}</span>`:''}
        </div>`}).join('')}''',
'''        ${onShelf.map(i=>{const n=daysLeft(i.expiry);return `<button type="button" class="stockrow" data-gotoitem="${i.id}">
          <span class="stockdate">${esc(fmtExp(i.expiry))}</span>
          <span class="pill ${band(n)}">${dueLabel(n)}</span>
          ${i.location?`<span class="stockloc">${esc(i.location)}</span>`:''}
          <span class="chev" aria-hidden="true">&rsaquo;</span>
        </button>`}).join('')}''')

# give each item card an id so we can scroll to it
rep('''function itemCard(it){
  const n=daysLeft(it.expiry);const [y,m,d]=it.expiry.split('-');const live=it.status==='active'||it.status==='reduced';
  const b=live?band(n):'';const acts=true;
  return `<div class="item">''',
'''function itemCard(it){
  const n=daysLeft(it.expiry);const [y,m,d]=it.expiry.split('-');const live=it.status==='active'||it.status==='reduced';
  const b=live?band(n):'';const acts=true;
  return `<div class="item" id="it-${it.id}">''')

# after a render, scroll to and briefly highlight the item we jumped to
rep("  updateBadges();\n  if(!S.briefed){S.briefed=true;briefing()}",
    """  updateBadges();
  if(S.goto){const gid=S.goto;S.goto=null;const el=document.getElementById('it-'+gid);if(el){el.scrollIntoView({behavior:'smooth',block:'center'});el.classList.add('flash-item');setTimeout(()=>{el.classList.remove('flash-item')},1800);}}
  if(!S.briefed){S.briefed=true;briefing()}""")

# handlers: Go button, and tapping a stock row
rep("  if(d.camera){cam?stopCamera():startCamera();return}",
    """  if(d.camera){cam?stopCamera():startCamera();return}
  if(d.scango){const el=$('#scan_in');const v=el?el.value.trim():'';if(el)el.value='';if(v)applyScan(v);else el?.focus();return}
  if(d.gotoitem){if(cam)stopCamera();S.goto=d.gotoitem;S.tab='all';S.filter.status='active';S.filter.q='';window.scrollTo(0,0);render();return}""")

open(P,'w',encoding='utf-8').write(s); print("app.js v21 patched OK")
