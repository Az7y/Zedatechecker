# -*- coding: utf-8 -*-
P='public/app.js'; s=open(P,encoding='utf-8').read()
def rep(a,b,n=1):
    global s
    c=s.count(a); assert c==n, f"want {n} got {c}: {a[:80]!r}"; s=s.replace(a,b)

# 1. state: wizard step + draft
rep("  lines:[{expiry:'',qty:''}], offCache:{}, feedback:[], nameImg:{}, sugTimer:null, photos:{}, photoReq:{}, photoTarget:null };",
    "  lines:[{expiry:'',qty:''}], logStep:1, draft:{product:'',gtin:null,batch:'',notes:'',location:''}, offCache:{}, feedback:[], nameImg:{}, sugTimer:null, photos:{}, photoReq:{}, photoTarget:null };")

# 2. replace logView with the 3-step wizard (scanBox + logView + logStep1/2/3)
OLD_LOGVIEW = open(P,encoding='utf-8').read()  # placeholder to satisfy linters; not used
rep(
'''function logView(){
  const prods=[...new Set(S.items.filter(i=>i.product).map(i=>i.product))].sort();
  const secs=activeSections();
  const otherLocs=[...new Set(S.items.map(i=>i.location).filter(Boolean))].filter(l=>!secs.some(x=>x.name===l)).sort();
  const sc=S.scan;const onShelf=sc&&sc.gtin?liveItems().filter(i=>i.gtin===sc.gtin):[];
  const lines=S.lines&&S.lines.length?S.lines:[{expiry:'',qty:''}];
  const unknown=sc&&sc.gtin&&!S.products[sc.gtin];
  const lookupNote=unknown?(sc.lookup==='busy'?'<div class="note">Looking up the name online…</div>'
    :sc.lookup==='done'?'<div class="note">Name suggested from Open Food Facts. Check it reads right before saving.</div>'
    :sc.lookup==='none'?"<div class=\\"note\\">No name found online. Type it once as Brand Product name and it's remembered.</div>":''):'';
  return `<section class="view"><h2>Log a product</h2>
  <div class="scan">
    <div class="head"><h3>Scan barcode</h3><span class="note">Pack barcode or supplier case label</span></div>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <input id="scan_in" autocomplete="off" placeholder="Scanner input, or type a barcode" aria-label="Barcode" style="flex:1 1 220px">
      <button type="button" class="btn primary" data-camera="1">${S.camOn?'Stop camera':'Scan with camera'}</button>
      ${S.camOn?`<button type="button" class="btn" data-torch="1">${torchOn?'Torch off':'Torch'}</button>`:''}
    </div>
    <div id="camBox" ${S.camOn?'':'hidden'}></div>
    ${S.camOn?`<div class="note">Hold the barcode 10–15&nbsp;cm away and steady. Tap Torch if the light is low.</div>`:''}
    ${sc?(sc.ok?`<div class="readout">
      ${sc.gtin?`<span><b>Product no.</b>${esc(sc.gtin)}</span>`:''}${sc.batch?`<span><b>Batch</b>${esc(sc.batch)}</span>`:''}
      ${sc.expiry?`<span><b>${sc.expiryKind}</b>${esc(sc.expiry)}</span>`:''}${sc.produced?`<span><b>Packed</b>${esc(sc.produced)}</span>`:''}
      ${sc.qty?`<span><b>Count</b>${esc(sc.qty)}</span>`:''}</div>
      ${lookupNote}
      ${sc.gtin&&S.products[sc.gtin]?'<div class="note">Product name filled from an earlier log.</div>':''}
      ${sc.expiry?'':'<div class="note">This barcode has no date in it, so enter the date from the pack.</div>'}
      ${sc.weightLooksPrice?`<div class="warnbox">This looks like an in-store weighed label. Its number changes with weight and price, so it won't match the same product next time.</div>`:''}
      ${onShelf.length?`<div class="warnbox">Already on the list: ${onShelf.map(i=>`${esc(i.batch||'no batch')} (use-by ${esc(i.expiry)})`).join(', ')}</div>`:''}`
      :`<div class="errbox">Couldn't read that barcode. Check it scanned fully, or type the details below.</div>`):''}
  </div>
  <form class="panel" id="logForm" autocomplete="off">
    <input type="hidden" id="lf_gtin">
    <label>Product<input id="lf_product" required maxlength="80" list="prodlist" placeholder="Brand Product name, e.g. Avonmore Fresh Milk 2L"></label>
    <datalist id="prodlist">${prods.map(p=>`<option value="${esc(p)}">`).join('')}</datalist>
    <div id="nameSug" class="namesug"></div>
    <label>Section<select id="lf_loc" required>
      <option value="">— choose —</option>
      ${secs.map(x=>`<option value="${esc(x.name)}">${esc(x.name)}</option>`).join('')}
      ${otherLocs.map(l=>`<option value="${esc(l)}">${esc(l)}</option>`).join('')}
      <option value="__other__">Other (type a new one)…</option>
    </select></label>
    <div id="locOtherWrap" hidden><label>New section<input id="lf_loc_other" maxlength="40" placeholder="e.g. Chilled meats"></label></div>
    <div class="datelines">
      <div class="dl-head"><span>Use-by / best-before</span><span>Qty</span><span></span></div>
      <div id="dateLines">${lines.map((l,i)=>dlineRow(l,i,lines.length)).join('')}</div>
      <button type="button" class="btn small" data-addline="1">+ Add another date</button>
      <div class="note">One row per different date on the shelf. Each row is saved as its own entry under this product.</div>
    </div>
    <label>Notes (optional)<textarea id="lf_notes" rows="2" maxlength="200"></textarea></label>
    <div id="dupWarn"></div>
    <button class="btn primary">Save as ${esc(S.me.name)}</button>
  </form></section>`;
}''',
'''function scanBox(){
  const sc=S.scan;const onShelf=sc&&sc.gtin?liveItems().filter(i=>i.gtin===sc.gtin):[];
  const unknown=sc&&sc.gtin&&!S.products[sc.gtin];
  const lookupNote=unknown?(sc.lookup==='busy'?'<div class="note">Looking up the name online…</div>'
    :sc.lookup==='done'?'<div class="note">Name suggested from Open Food Facts. Check it reads right.</div>'
    :sc.lookup==='none'?"<div class=\\"note\\">No name found online. Type it once as Brand Product name and it's remembered.</div>":''):'';
  return `<div class="scan">
    <div class="head"><h3>Scan barcode</h3><span class="note">Pack barcode or supplier case label</span></div>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <input id="scan_in" autocomplete="off" placeholder="Scanner input, or type a barcode" aria-label="Barcode" style="flex:1 1 220px">
      <button type="button" class="btn primary" data-camera="1">${S.camOn?'Stop camera':'Scan with camera'}</button>
      ${S.camOn?`<button type="button" class="btn" data-torch="1">${torchOn?'Torch off':'Torch'}</button>`:''}
    </div>
    <div id="camBox" ${S.camOn?'':'hidden'}></div>
    ${S.camOn?`<div class="note">Hold the barcode 10–15&nbsp;cm away and steady. Tap Torch if the light is low.</div>`:''}
    ${sc?(sc.ok?`<div class="readout">
      ${sc.gtin?`<span><b>Product no.</b>${esc(sc.gtin)}</span>`:''}${sc.batch?`<span><b>Batch</b>${esc(sc.batch)}</span>`:''}
      ${sc.expiry?`<span><b>${sc.expiryKind}</b>${esc(sc.expiry)}</span>`:''}${sc.produced?`<span><b>Packed</b>${esc(sc.produced)}</span>`:''}
      ${sc.qty?`<span><b>Count</b>${esc(sc.qty)}</span>`:''}</div>
      ${lookupNote}
      ${sc.gtin&&S.products[sc.gtin]?'<div class="note">Product name filled from an earlier log.</div>':''}
      ${sc.weightLooksPrice?`<div class="warnbox">This looks like an in-store weighed label. Its number changes with weight and price, so it won't match the same product next time.</div>`:''}
      ${onShelf.length?`<div class="warnbox">Already on the list: ${onShelf.map(i=>`${esc(i.batch||'no batch')} (use-by ${esc(i.expiry)})`).join(', ')}</div>`:''}`
      :`<div class="errbox">Couldn't read that barcode. Check it scanned fully, or type the name below.</div>`):''}
  </div>`;
}
// Log a product as three simple steps: name, section, then dates and quantity.
function logView(){
  const step=S.logStep||1;const d=S.draft||(S.draft={product:'',gtin:null,batch:'',notes:'',location:''});
  const dot=(n,lbl)=>`<span class="wizstep ${n===step?'on':n<step?'done':''}">${n}. ${lbl}</span>`;
  return `<section class="view"><div class="wizhead"><h2>Log a product</h2>
    <div class="wizsteps">${dot(1,'Product')}${dot(2,'Section')}${dot(3,'Dates')}</div></div>
    ${step===1?logStep1(d):step===2?logStep2(d):logStep3(d)}</section>`;
}
function logStep1(d){
  const prods=[...new Set(S.items.filter(i=>i.product).map(i=>i.product))].sort();
  return `${scanBox()}
  <form class="panel" id="logStep1Form" autocomplete="off">
    <input type="hidden" id="lf_gtin" value="${esc(d.gtin||'')}">
    <label>Product name<input id="lf_product" value="${esc(d.product||'')}" required maxlength="80" list="prodlist" placeholder="Brand Product name, e.g. Avonmore Fresh Milk 2L"></label>
    <datalist id="prodlist">${prods.map(p=>`<option value="${esc(p)}">`).join('')}</datalist>
    <div id="nameSug" class="namesug"></div>
    <div id="dupWarn"></div>
    <button class="btn primary">Next: section →</button>
  </form>`;
}
function logStep2(d){
  const secs=activeSections();
  return `<div class="note">Logging <b>${esc(d.product)}</b></div>
  <div class="panel"><h3>Which section?</h3>
    <div class="chips">${secs.map(x=>`<button type="button" class="chip ${d.location===x.name?'on':''}" data-pickloc="${esc(x.name)}">${esc(x.name)}</button>`).join('')}
      <button type="button" class="chip other" data-pickother="1">+ New section</button></div>
    <form id="newSecForm" class="secrow" ${d.addingSection?'':'hidden'} style="margin-top:4px"><input id="lf_loc_other" maxlength="40" placeholder="e.g. Chilled meats" aria-label="New section name"><button class="btn small primary">Use this →</button></form>
  </div>
  <div class="wiznav"><button type="button" class="btn ghost" data-wizback="1">← Back</button></div>`;
}
function logStep3(d){
  const lines=S.lines&&S.lines.length?S.lines:[{expiry:'',qty:''}];
  return `<div class="note">Logging <b>${esc(d.product)}</b> · ${esc(d.location)}</div>
  <form class="panel" id="logForm" autocomplete="off">
    <div class="datelines">
      <div class="dl-head"><span>Use-by / best-before</span><span>Qty</span><span></span></div>
      <div id="dateLines">${lines.map((l,i)=>dlineRow(l,i,lines.length)).join('')}</div>
      <button type="button" class="btn small" data-addline="1">+ Add another date</button>
      <div class="note">One row per different date on the shelf. Each is saved as its own entry.</div>
    </div>
    <label>Notes (optional)<textarea id="lf_notes" rows="2" maxlength="200">${esc(d.notes||'')}</textarea></label>
    <div class="wiznav"><button type="button" class="btn ghost" data-wizback="1">← Back</button><button class="btn primary">Save as ${esc(S.me.name)}</button></div>
  </form>`;
}''')

# 3. applyScan -> populate the draft and start at step 1
rep(
'''function applyScan(raw){
  if(!raw||!raw.trim())return;
  const sc=parseScan(raw);S.scan=sc;S.tab='log';
  const known=sc.gtin&&S.products[sc.gtin];
  S.lines=[{expiry:sc.expiry||'',qty:sc.qty||''}];
  render();
  if(!sc.ok){$('#scan_in')?.focus();return}
  const set=(id,v)=>{const el=$('#'+id);if(el&&v!=null&&v!=='')el.value=v};
  set('lf_gtin',sc.gtin);
  if(known){set('lf_product',known.name);sc.image=known.image||null;}
  if(sc.gtin&&!known&&(window.__offStub||navigator.onLine)){
    sc.lookup='busy';render();
    lookupName(sc.gtin).then(res=>{
      const name=res&&res.name;sc.image=res&&res.image||null;
      sc.lookup=(name||sc.image)?'done':'none';
      const pe=$('#lf_product');if(name&&pe&&!pe.value)pe.value=name;
      if(S.tab==='log')render();
    });
  }
  const pe=$('#lf_product');(pe&&!pe.value?pe:document.querySelector('.dl-exp'))?.focus();
  checkDup();
}''',
'''function applyScan(raw){
  if(!raw||!raw.trim())return;
  const sc=parseScan(raw);S.scan=sc;S.tab='log';S.logStep=1;
  S.draft=S.draft||{product:'',gtin:null,batch:'',notes:'',location:''};
  S.draft.gtin=sc.gtin||null;S.draft.batch=sc.batch||'';
  const known=sc.gtin&&S.products[sc.gtin];
  if(known){S.draft.product=known.name;sc.image=known.image||null;}
  S.lines=[{expiry:sc.expiry||'',qty:sc.qty||''}];
  render();
  if(!sc.ok){$('#scan_in')?.focus();return}
  if(sc.gtin&&!known&&(window.__offStub||navigator.onLine)){
    sc.lookup='busy';render();
    lookupName(sc.gtin).then(res=>{
      const name=res&&res.name;sc.image=res&&res.image||null;
      sc.lookup=(name||sc.image)?'done':'none';
      if(name&&!S.draft.product){S.draft.product=name;const pe=$('#lf_product');if(pe&&!pe.value)pe.value=name;}
      if(S.tab==='log')render();
    });
  }
  $('#lf_product')?.focus();
  checkDup();
}''')

# 4. tab click resets the log wizard when entering the Log tab
rep("  if(d.tab){S.tab=d.tab;window.scrollTo(0,0);render();if(S.tab==='log')$('#scan_in')?.focus();return}",
    "  if(d.tab){if(d.tab==='log'){S.logStep=1;S.draft={product:'',gtin:null,batch:'',notes:'',location:''};S.lines=[{expiry:'',qty:''}];S.scan=null;}S.tab=d.tab;window.scrollTo(0,0);render();if(S.tab==='log')$('#scan_in')?.focus();return}")

# 5. wizard click handlers (section chip, new-section, back)
rep("  if(d.delline!==undefined){S.lines=readLines();S.lines.splice(+d.delline,1);if(!S.lines.length)S.lines=[{expiry:'',qty:''}];render();return}",
    "  if(d.delline!==undefined){S.lines=readLines();S.lines.splice(+d.delline,1);if(!S.lines.length)S.lines=[{expiry:'',qty:''}];render();return}\n"
    "  if(d.pickloc){S.draft=S.draft||{};S.draft.location=d.pickloc;S.draft.addingSection=false;if(cam)stopCamera();S.logStep=3;render();return}\n"
    "  if(d.pickother){S.draft=S.draft||{};S.draft.addingSection=true;render();$('#lf_loc_other')?.focus();return}\n"
    "  if(d.wizback){S.logStep=Math.max(1,(S.logStep||1)-1);if(S.logStep<2&&S.draft)S.draft.addingSection=false;render();return}")

# 6. drop the old lf_loc select change handler
rep("  if(e.target.id==='lf_loc'){const w=$('#locOtherWrap');if(w){w.hidden=e.target.value!=='__other__';if(e.target.value==='__other__')$('#lf_loc_other')?.focus()}}\n",
    "")

# 7. submit: step-1 next, new-section, and the final save (reads from S.draft)
rep(
'''  if(f.id==='logForm'){
    const product=$('#lf_product').value.trim();
    const selv=$('#lf_loc').value;const location=(selv==='__other__'?($('#lf_loc_other')?.value||''):selv).trim();
    const batch=((S.scan&&S.scan.batch)||'').toUpperCase();const notes=$('#lf_notes').value.trim();const gtin=$('#lf_gtin').value||null;
    const lines=readLines().filter(l=>l.expiry);
    if(!product){flash('Add a product name');return}
    if(!location){flash('Choose a section');return}
    if(!lines.length){flash('Add at least one use-by date');return}
    if(lines.some(l=>!l.qty||Number(l.qty)<1)){flash('Add a quantity for each date');return}''',
'''  if(f.id==='logStep1Form'){
    S.draft=S.draft||{};S.draft.product=$('#lf_product').value.trim();S.draft.gtin=$('#lf_gtin').value||null;
    if(!S.draft.product){flash('Add a product name');return}
    if(cam)stopCamera();S.logStep=2;render();return;
  }
  if(f.id==='newSecForm'){
    const nm=$('#lf_loc_other').value.trim();if(!nm){flash('Type a section name');return}
    S.draft.location=nm;S.draft.addingSection=false;S.logStep=3;render();return;
  }
  if(f.id==='logForm'){
    const dr=S.draft||{};const product=(dr.product||'').trim();const location=(dr.location||'').trim();
    const batch=((S.scan&&S.scan.batch)||'').toUpperCase();const notes=$('#lf_notes')?$('#lf_notes').value.trim():'';const gtin=dr.gtin||null;
    const lines=readLines().filter(l=>l.expiry);
    if(!product){flash('Add a product name');S.logStep=1;render();return}
    if(!location){flash('Choose a section');S.logStep=2;render();return}
    if(!lines.length){flash('Add at least one use-by date');return}
    if(lines.some(l=>!l.qty||Number(l.qty)<1)){flash('Add a quantity for each date');return}''')

rep("    let newSection=false;\n"
    "    if(location&&selv==='__other__'&&!activeSections().some(x=>x.name.toLowerCase()===location.toLowerCase())){",
    "    let newSection=false;\n"
    "    if(location&&!activeSections().some(x=>x.name.toLowerCase()===location.toLowerCase())){")

rep("    S.scan=null;S.lines=[{expiry:'',qty:''}];const sg=$('#nameSug');if(sg)sg.innerHTML='';\n"
    "    ['lf_product','lf_gtin','lf_notes'].forEach(id=>{const el=$('#'+id);if(el)el.value=''});\n"
    "    render();$('#scan_in')?.focus();return;",
    "    S.scan=null;S.lines=[{expiry:'',qty:''}];S.draft={product:'',gtin:null,batch:'',notes:'',location:''};S.logStep=1;\n"
    "    render();$('#scan_in')?.focus();return;")

open(P,'w',encoding='utf-8').write(s); print("app.js v10 (log wizard) patched OK")
