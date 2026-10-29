# -*- coding: utf-8 -*-
P='public/app.js'; s=open(P,encoding='utf-8').read()
def rep(a,b,n=1):
    global s
    c=s.count(a); assert c==n, f"want {n} got {c}: {a[:90]!r}"; s=s.replace(a,b)

# ---- dedupe: one helper for "what of the scanned product is already on the shelf" ----
rep("function scanBox(){\n  const sc=S.scan;\n  const knownName=(sc&&sc.gtin&&S.products[sc.gtin]&&S.products[sc.gtin].name)||(S.draft&&S.draft.product)||'';\n  const onShelf=sc?liveItems().filter(i=>(sc.gtin&&i.gtin===sc.gtin)||(knownName&&i.product&&i.product.toLowerCase()===knownName.toLowerCase())):[];\n  onShelf.sort((a,b)=>a.expiry.localeCompare(b.expiry));",
"""// Live stock of whatever was just scanned, matched by barcode or by the product's known name.
function scanInStock(){
  const sc=S.scan;if(!sc)return [];
  const knownName=(sc.gtin&&S.products[sc.gtin]&&S.products[sc.gtin].name)||(S.draft&&S.draft.product)||'';
  return liveItems().filter(i=>(sc.gtin&&i.gtin===sc.gtin)||(knownName&&i.product&&i.product.toLowerCase()===knownName.toLowerCase()))
    .sort((a,b)=>a.expiry.localeCompare(b.expiry));
}
function scanBox(){
  const sc=S.scan;
  const onShelf=scanInStock();""")

# ---- stock card rows: tapping a date is now ONLY "change or remove this date" ----
# (adding dates moved to the clearly-labelled button below, so the two actions don't overlap)
rep('''        ${onShelf.map(i=>{const n=daysLeft(i.expiry);const open=S.editItem===i.id;return `<div class="stockitem">
          <button type="button" class="stockrow" data-edititem="${i.id}" aria-expanded="${open}">
            <span class="stockdate">${esc(fmtExp(i.expiry))}</span>
            <span class="pill ${band(n)}">${dueLabel(n)}</span>
            ${i.location?`<span class="stockloc">${esc(i.location)}</span>`:''}
            <span class="chev" aria-hidden="true">${open?'&#9662;':'&#9656;'}</span>
          </button>
          ${open?`<div class="stockedit">
            ${isAdmin()?editItemForm(i):''}
            <div class="actions">
              <button type="button" class="btn small danger" data-act="removed" data-id="${i.id}">Remove from shelf</button>
              <button type="button" class="btn small" data-act="sold" data-id="${i.id}">Sold through</button>
              <button type="button" class="btn small ghost" data-act="void" data-id="${i.id}">Delete entry</button>
              ${isAdmin()?'':'<button type="button" class="btn small ghost" data-editcancel="1">Close</button>'}
            </div>
          </div>`:''}
        </div>`}).join('')}
        <div class="note">Tap a date to edit it, add more dates for this product, or take it off the shelf.</div>
      </div>`:''}`''',
'''        ${onShelf.map(i=>{const n=daysLeft(i.expiry);const open=S.editItem===i.id;return `<div class="stockitem">
          <button type="button" class="stockrow" data-edititem="${i.id}" aria-expanded="${open}">
            <span class="stockdate">${esc(fmtExp(i.expiry))}</span>
            <span class="pill ${band(n)}">${dueLabel(n)}</span>
            ${i.location?`<span class="stockloc">${esc(i.location)}</span>`:''}
            <span class="chev" aria-hidden="true">${open?'&#9662;':'&#9656;'}</span>
          </button>
          ${open?`<form class="stockedit stockedit-form" data-stockdatesave="${i.id}">
            ${isAdmin()?`<label class="sd-lab">Use-by / best-before<input class="sd-exp" type="date" value="${esc(i.expiry)}" min="2020-01-01" required></label>
            <div class="actions"><button class="btn small primary">Save date</button>
              <button type="button" class="btn small ghost" data-editcancel="1">Cancel</button></div>`:''}
            <div class="actions srow-act">
              <button type="button" class="btn small danger" data-act="removed" data-id="${i.id}">Remove from shelf</button>
              <button type="button" class="btn small" data-act="sold" data-id="${i.id}">Sold through</button>
              <button type="button" class="btn small ghost" data-act="void" data-id="${i.id}">Delete</button>
              ${isAdmin()?'':'<button type="button" class="btn small ghost" data-editcancel="1">Close</button>'}
            </div>
          </form>`:''}
        </div>`}).join('')}
        <div class="note">Tap a date to change or remove it. To add another date for this product, use the button below.</div>
      </div>`:''}`''')

# ---- save handler for the compact date edit ----
rep('''function setItemStatus(id,act){''',
'''function saveStockDate(id){
  if(!isAdmin())return;const it=S.items.find(i=>i.id===id);if(!it)return;
  const el=document.querySelector('.stockedit-form[data-stockdatesave="'+id+'"] .sd-exp');
  const expiry=el?el.value:'';
  if(!expiry){flash('Add a use-by date');return}
  const b=by();
  quickWrite(updateDoc(doc(fs,'items',id),{expiry,lastAction:'edited',lastBy:b.by,lastByName:b.byName,lastAt:b.at,history:[...(it.history||[]),{action:'edited',...b}].slice(-30)}),`${it.product} date updated`);
  S.editItem=null;render();
}
function setItemStatus(id,act){''')

# ---- logStep1: label the add button clearly when the product is already in stock ----
rep("""function logStep1(d){
  const prods=[...new Set(S.items.filter(i=>i.product).map(i=>i.product))].sort();
  return `${scanBox()}""",
"""function logStep1(d){
  const prods=[...new Set(S.items.filter(i=>i.product).map(i=>i.product))].sort();
  const inStock=scanInStock().length>0;
  return `${scanBox()}""")
rep('    <button class="btn primary">Next: section →</button>',
    '    <button class="btn primary">${inStock?\'Add another date →\':\'Next: section →\'}</button>')

# ---- logStep3: let the section be changed from the dates step ----
rep('  return `<div class="note">Logging <b>${esc(d.product)}</b> · ${esc(d.location)}</div>',
    '  return `<div class="note">Logging <b>${esc(d.product)}</b> · <button type="button" class="linklike" data-wizback="1">${esc(d.location)} (change)</button></div>')

# ---- logStep1 submit: in stock + one section -> jump straight to the dates step ----
rep('''  if(f.id==='logStep1Form'){
    S.draft=S.draft||{};S.draft.product=$('#lf_product').value.trim();  // keep S.draft.gtin from the scan (the hidden field can be blanked by re-render)
    if(!S.draft.product){flash('Add a product name');return}
    if(cam)stopCamera();S.logStep=2;render();return;
  }''',
'''  if(f.id==='logStep1Form'){
    S.draft=S.draft||{};S.draft.product=$('#lf_product').value.trim();  // keep S.draft.gtin from the scan (the hidden field can be blanked by re-render)
    if(!S.draft.product){flash('Add a product name');return}
    if(cam)stopCamera();
    const stock=scanInStock();const secs=[...new Set(stock.map(i=>i.location).filter(Boolean))];
    if(stock.length&&secs.length===1){S.draft.location=secs[0];S.logStep=3;}  // already in one section: go straight to dates
    else S.logStep=2;
    render();return;
  }''')

# route the compact edit form's submit
rep("  if(f.id==='editItemForm'){saveItemEdit(f.dataset.editsave);return}",
    "  if(f.id==='editItemForm'){saveItemEdit(f.dataset.editsave);return}\n  if(f.dataset&&f.dataset.stockdatesave){saveStockDate(f.dataset.stockdatesave);return}")

# ---- remove dead 'jump to item in All items' code (stock rows now edit in place) ----
rep("  loaded:{}, tab:'today', filter:{q:'',status:'active'}, scan:null, camOn:false, goto:null,",
    "  loaded:{}, tab:'today', filter:{q:'',status:'active'}, scan:null, camOn:false,")
rep("  updateBadges();\n  if(S.goto){const gid=S.goto;S.goto=null;const el=document.getElementById('it-'+gid);if(el){el.scrollIntoView({behavior:'smooth',block:'center'});el.classList.add('flash-item');setTimeout(()=>{el.classList.remove('flash-item')},1800);}}\n  if(!S.briefed){S.briefed=true;briefing()}",
    "  updateBadges();\n  if(!S.briefed){S.briefed=true;briefing()}")
rep('  return `<div class="item" id="it-${it.id}">','  return `<div class="item">')
rep('  if(d.gotoitem){if(cam)stopCamera();S.goto=d.gotoitem;S.tab=\'all\';S.filter.status=\'active\';S.filter.q=\'\';window.scrollTo(0,0);render();return}\n',"")

open(P,'w',encoding='utf-8').write(s); print("app.js v24 (scan cleanup) patched OK")
