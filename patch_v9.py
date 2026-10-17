# -*- coding: utf-8 -*-
P='public/app.js'; s=open(P,encoding='utf-8').read()
def rep(a,b,n=1):
    global s
    c=s.count(a); assert c==n, f"want {n} got {c}: {a[:80]!r}"; s=s.replace(a,b)

# 1. ACTION: add 'edited'
rep("const ACTION={logged:'logged',reduced:'reduced',removed:'removed from shelf',sold:'marked sold through',restored:'put back on shelf',void:'deleted (mistake)',adjusted:'changed the count'};",
    "const ACTION={logged:'logged',reduced:'reduced',removed:'removed from shelf',sold:'marked sold through',restored:'put back on shelf',void:'deleted (mistake)',edited:'edited the details',adjusted:'changed the count'};")

# 2. state: editItem
rep("  editStaff:null, showOwner:false, ownerTaps:0, error:null, briefed:false,",
    "  editStaff:null, editItem:null, showOwner:false, ownerTaps:0, error:null, briefed:false,")

# 3. itemCard: Edit button (Director/Boss) + inline edit form
rep(
"""    ${acts?`<div class="actions" style="grid-column:1/-1">${live?`
      <button class="btn small danger" data-act="removed" data-id="${it.id}">Remove from shelf</button>
      <button class="btn small" data-act="sold" data-id="${it.id}">Sold through</button>
      <button class="btn small ghost" data-act="void" data-id="${it.id}">Delete entry</button>`:
      (it.status==='void'
        ? (canRestore()?`<button class="btn small" data-act="restored" data-id="${it.id}">Undo delete</button>`:'')
        : (canRestore()?`<button class="btn small" data-act="restored" data-id="${it.id}">Undo, put back on shelf</button>`:''))}</div>`:''}
  </div>`;
}""",
"""    ${acts?`<div class="actions" style="grid-column:1/-1">${live?`
      <button class="btn small danger" data-act="removed" data-id="${it.id}">Remove from shelf</button>
      <button class="btn small" data-act="sold" data-id="${it.id}">Sold through</button>
      <button class="btn small ghost" data-act="void" data-id="${it.id}">Delete entry</button>
      ${isAdmin()?`<button class="btn small" data-edititem="${it.id}">${S.editItem===it.id?'Close':'Edit'}</button>`:''}`:
      (it.status==='void'
        ? (canRestore()?`<button class="btn small" data-act="restored" data-id="${it.id}">Undo delete</button>`:'')
        : (canRestore()?`<button class="btn small" data-act="restored" data-id="${it.id}">Undo, put back on shelf</button>`:''))}</div>`:''}
    ${live&&isAdmin()&&S.editItem===it.id?editItemForm(it):''}
  </div>`;
}
// Directors and the Boss can fix a logged entry: name, section (for items logged with none), date, qty.
function editItemForm(it){
  const secs=activeSections();const known=secs.some(x=>x.name===it.location);
  return `<form class="panel edititem" id="editItemForm" data-editsave="${it.id}" style="grid-column:1/-1;gap:10px;margin-top:4px">
    <label>Product<input id="ei_prod_${it.id}" value="${esc(it.product)}" maxlength="80" required></label>
    <div class="grid2">
      <label>Section<select id="ei_loc_${it.id}" required>
        <option value="">— choose —</option>
        ${secs.map(x=>`<option ${x.name===it.location?'selected':''}>${esc(x.name)}</option>`).join('')}
        ${it.location&&!known?`<option selected>${esc(it.location)}</option>`:''}
      </select></label>
      <label>Use-by<input id="ei_exp_${it.id}" type="date" value="${esc(it.expiry)}" min="2020-01-01" required></label>
      <label>Qty<input id="ei_qty_${it.id}" type="number" min="1" max="9999" value="${esc(it.qty||'')}" required></label>
    </div>
    <div class="actions"><button class="btn small primary">Save changes</button>
      <button type="button" class="btn small ghost" data-editcancel="1">Cancel</button></div>
  </form>`;
}""")

# 4. allView: jump-to-section dropdown instead of the chip rail
rep("  const nav=keys.length>1?`<div class=\"secnav\" role=\"tablist\">${keys.map((k,i)=>`<button type=\"button\" class=\"secnav-item\" data-gonav=\"${i}\">${label(k)} <span class=\"cnt\">${groups.get(k).length}</span></button>`).join('')}</div>`:'';",
    "  const nav=keys.length>1?`<label class=\"jumpsec\"><span>Jump to section</span><select id=\"secjump\"><option value=\"\">All sections</option>${keys.map((k,i)=>`<option value=\"${i}\">${label(k)} (${groups.get(k).length})</option>`).join('')}</select></label>`:'';")
rep("    <div class=\"allwrap\">${nav}${body}</div></section>`;",
    "    ${nav}\n    ${body}</section>`;")

# 5. click handler: drop gonav, add edit toggle/cancel
rep("  if(d.gonav!==undefined){const el=document.getElementById('grp-'+d.gonav);if(el){el.open=true;el.scrollIntoView({behavior:'smooth',block:'start'})}return}",
    "  if(d.edititem){S.editItem=S.editItem===d.edititem?null:d.edititem;render();return}\n  if(d.editcancel){S.editItem=null;render();return}")

# 6. change handler: section jump dropdown
rep("  if(e.target.id==='f_status'){S.filter.status=e.target.value;render()}\n  if(e.target.id==='lf_loc'){",
    "  if(e.target.id==='f_status'){S.filter.status=e.target.value;render()}\n  if(e.target.id==='secjump'){const v=e.target.value;if(v!==''){const el=document.getElementById('grp-'+v);if(el){el.open=true;el.scrollIntoView({behavior:'smooth',block:'start'})}}return}\n  if(e.target.id==='lf_loc'){")

# 7. logView: drop batch field, section required
rep(
"""    <div class="grid2">
      <label>Batch / lot code (optional)<input id="lf_batch" class="mono" maxlength="40" placeholder="L2731"></label>
      <label>Section<select id="lf_loc">
        <option value="">— choose —</option>
        ${secs.map(x=>`<option value="${esc(x.name)}">${esc(x.name)}</option>`).join('')}
        ${otherLocs.map(l=>`<option value="${esc(l)}">${esc(l)}</option>`).join('')}
        <option value="__other__">Other (type a new one)…</option>
      </select></label>
    </div>""",
"""    <label>Section<select id="lf_loc" required>
      <option value="">— choose —</option>
      ${secs.map(x=>`<option value="${esc(x.name)}">${esc(x.name)}</option>`).join('')}
      ${otherLocs.map(l=>`<option value="${esc(l)}">${esc(l)}</option>`).join('')}
      <option value="__other__">Other (type a new one)…</option>
    </select></label>""")

# 7b. date lines: make the qty column read as required
rep('<div class="dl-head"><span>Use-by / best-before</span><span>Qty</span><span></span></div>',
    '<div class="dl-head"><span>Use-by / best-before</span><span>Qty</span><span></span></div>')  # unchanged anchor (kept for clarity)

# 8. checkDup: product-only (batch field is gone)
rep(
"""function checkDup(){
  const pe=$('#lf_product'),be=$('#lf_batch'),dw=$('#dupWarn');if(!pe||!be||!dw)return;
  const p=pe.value.trim().toLowerCase(),b=be.value.trim().toUpperCase();
  const dup=p&&b&&liveItems().find(i=>i.product.toLowerCase()===p&&(i.batch||'')===b);
  dw.innerHTML=dup?`<div class="warnbox">This batch is already on the list, logged by ${esc(dup.loggedByName)} on ${fmtTime(dup.loggedAt)}, use-by ${esc(dup.expiry)}. Save anyway only if it's separate stock.</div>`:'';
}""",
"""function checkDup(){
  const pe=$('#lf_product'),dw=$('#dupWarn');if(!pe||!dw)return;
  const p=pe.value.trim().toLowerCase();
  const dups=p?liveItems().filter(i=>i.product.toLowerCase()===p):[];
  dw.innerHTML=dups.length?`<div class="warnbox">${esc(pe.value.trim())} is already on the list (${dups.map(i=>'use-by '+esc(i.expiry)).join(', ')}). Add again only if it's separate stock.</div>`:'';
}""")

# 9. input listener: lf_batch gone
rep("  if(e.target.id==='lf_product'||e.target.id==='lf_batch')checkDup();",
    "  if(e.target.id==='lf_product')checkDup();")

# 10. submit editItemForm handler
rep("  if(f.id==='logForm'){\n    const product=$('#lf_product').value.trim();",
    "  if(f.id==='editItemForm'){saveItemEdit(f.dataset.editsave);return}\n  if(f.id==='logForm'){\n    const product=$('#lf_product').value.trim();")

# 11. logForm: batch from scan, require section + qty
rep(
"""    const batch=$('#lf_batch').value.trim().toUpperCase();const notes=$('#lf_notes').value.trim();const gtin=$('#lf_gtin').value||null;
    const lines=readLines().filter(l=>l.expiry);
    if(!product){flash('Add a product name');return}
    if(!lines.length){flash('Add at least one use-by date');return}""",
"""    const batch=((S.scan&&S.scan.batch)||'').toUpperCase();const notes=$('#lf_notes').value.trim();const gtin=$('#lf_gtin').value||null;
    const lines=readLines().filter(l=>l.expiry);
    if(!product){flash('Add a product name');return}
    if(!location){flash('Choose a section');return}
    if(!lines.length){flash('Add at least one use-by date');return}
    if(lines.some(l=>!l.qty||Number(l.qty)<1)){flash('Add a quantity for each date');return}""")

# 12. logForm reset: drop lf_batch
rep("    ['lf_product','lf_gtin','lf_batch','lf_notes'].forEach(id=>{const el=$('#'+id);if(el)el.value=''});",
    "    ['lf_product','lf_gtin','lf_notes'].forEach(id=>{const el=$('#'+id);if(el)el.value=''});")

# 13. saveItemEdit function (Director/Boss only)
rep("const UNDOABLE=['removed','sold','void'];",
    "const UNDOABLE=['removed','sold','void'];\n"
    "function saveItemEdit(id){\n"
    "  if(!isAdmin())return;const it=S.items.find(i=>i.id===id);if(!it)return;\n"
    "  const product=$('#ei_prod_'+id).value.trim();const location=$('#ei_loc_'+id).value;\n"
    "  const expiry=$('#ei_exp_'+id).value;const qv=$('#ei_qty_'+id).value;\n"
    "  if(!product){flash('Add a product name');return}\n"
    "  if(!location){flash('Choose a section');return}\n"
    "  if(!expiry){flash('Add a use-by date');return}\n"
    "  if(!qv||Number(qv)<1){flash('Add a quantity');return}\n"
    "  const b=by();\n"
    "  quickWrite(updateDoc(doc(fs,'items',id),{product,location,expiry,qty:Number(qv),lastAction:'edited',lastBy:b.by,lastByName:b.byName,lastAt:b.at,history:[...(it.history||[]),{action:'edited',...b}].slice(-30)}),`${product} updated`);\n"
    "  S.editItem=null;render();\n"
    "}")

open(P,'w',encoding='utf-8').write(s); print("app.js v9 patched OK")
