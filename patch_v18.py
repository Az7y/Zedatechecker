# -*- coding: utf-8 -*-
P='public/app.js'; s=open(P,encoding='utf-8').read()
def rep(a,b,n=1):
    global s
    c=s.count(a); assert c==n, f"want {n} got {c}: {a[:90]!r}"; s=s.replace(a,b)

# ---- A. Multi-date editing in the edit-item form ----------------------------
# state slot
rep("  editStaff:null, editItem:null, showOwner:false,",
    "  editStaff:null, editItem:null, editLines:null, showOwner:false,")

# rebuild editItemForm with a date-lines block
rep(
'''function editItemForm(it){
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
    </div>
    <div class="actions"><button class="btn small primary">Save changes</button>
      <button type="button" class="btn small ghost" data-editcancel="1">Cancel</button></div>
  </form>`;
}''',
'''function editItemForm(it){
  const secs=activeSections();const known=secs.some(x=>x.name===it.location);
  const lines=S.editLines&&S.editLines.length?S.editLines:[{expiry:it.expiry||''}];
  return `<form class="panel edititem" id="editItemForm" data-editsave="${it.id}" style="grid-column:1/-1;gap:12px;margin-top:4px">
    <label>Product<input id="ei_prod_${it.id}" value="${esc(it.product)}" maxlength="80" required></label>
    <label>Section<select id="ei_loc_${it.id}" required>
      <option value="">— choose —</option>
      ${secs.map(x=>`<option ${x.name===it.location?'selected':''}>${esc(x.name)}</option>`).join('')}
      ${it.location&&!known?`<option selected>${esc(it.location)}</option>`:''}
    </select></label>
    <div class="datelines">
      <div class="dl-head"><span>Use-by / best-before</span><span></span></div>
      <div id="editLines">${lines.map((l,i)=>eilineRow(l,i,lines.length)).join('')}</div>
      <button type="button" class="btn small" data-eiaddline="1">+ Add another date</button>
      <div class="note">First row updates this entry. Extra dates are saved as new entries for the same product and section.</div>
    </div>
    <div class="actions"><button class="btn small primary">Save changes</button>
      <button type="button" class="btn small ghost" data-editcancel="1">Cancel</button></div>
  </form>`;
}
function eilineRow(l,i,total){
  return `<div class="dline">
    <input class="ei-exp" type="date" value="${esc(l.expiry||'')}" min="2020-01-01" aria-label="Use-by date">
    ${total>1?`<button type="button" class="btn small ghost" data-eidelline="${i}" aria-label="Remove date">&times;</button>`:'<span></span>'}
  </div>`;
}
function readEditLines(){const dl=document.querySelectorAll('#editLines .dline');
  return dl.length?[...dl].map(r=>({expiry:r.querySelector('.ei-exp').value})):[{expiry:''}];}''')

# saveItemEdit: first row updates, extra rows become new entries
rep(
'''function saveItemEdit(id){
  if(!isAdmin())return;const it=S.items.find(i=>i.id===id);if(!it)return;
  const product=$('#ei_prod_'+id).value.trim();const location=$('#ei_loc_'+id).value;
  const expiry=$('#ei_exp_'+id).value;
  if(!product){flash('Add a product name');return}
  if(!location){flash('Choose a section');return}
  if(!expiry){flash('Add a use-by date');return}
  const b=by();
  quickWrite(updateDoc(doc(fs,'items',id),{product,location,expiry,lastAction:'edited',lastBy:b.by,lastByName:b.byName,lastAt:b.at,history:[...(it.history||[]),{action:'edited',...b}].slice(-30)}),`${product} updated`);
  S.editItem=null;render();
}''',
'''function saveItemEdit(id){
  if(!isAdmin())return;const it=S.items.find(i=>i.id===id);if(!it)return;
  const product=$('#ei_prod_'+id).value.trim();const location=$('#ei_loc_'+id).value;
  const lines=readEditLines().filter(l=>l.expiry);
  if(!product){flash('Add a product name');return}
  if(!location){flash('Choose a section');return}
  if(!lines.length){flash('Add a use-by date');return}
  const b=by();const bch=writeBatch(fs);
  bch.update(doc(fs,'items',id),{product,location,expiry:lines[0].expiry,lastAction:'edited',lastBy:b.by,lastByName:b.byName,lastAt:b.at,history:[...(it.history||[]),{action:'edited',...b}].slice(-30)});
  const extra=lines.slice(1);
  for(const l of extra){const ref=doc(collection(fs,'items'));
    bch.set(ref,{product,gtin:it.gtin||null,batch:it.batch||'',expiry:l.expiry,location,notes:it.notes||'',store:itemStore(it),
      status:'active',loggedBy:b.by,loggedByName:b.byName,loggedAt:b.at,lastAction:'logged',lastBy:b.by,lastByName:b.byName,lastAt:b.at,
      history:[{action:'logged',...b}]});}
  quickWrite(bch.commit(),extra.length?`${product} updated · ${extra.length} more date${extra.length===1?'':'s'} added`:`${product} updated`);
  S.editItem=null;S.editLines=null;render();
}''')

# edit open/close seeds and clears the date rows
rep("  if(d.edititem){S.editItem=S.editItem===d.edititem?null:d.edititem;render();return}",
    "  if(d.edititem){const op=S.editItem===d.edititem?null:d.edititem;S.editItem=op;if(op){const it=S.items.find(i=>i.id===op);S.editLines=[{expiry:(it&&it.expiry)||''}];}else S.editLines=null;render();return}")
rep("  if(d.editcancel){S.editItem=null;render();return}",
    "  if(d.editcancel){S.editItem=null;S.editLines=null;render();return}")

# add/remove edit date rows
rep("  if(d.delline!==undefined){S.lines=readLines();S.lines.splice(+d.delline,1);if(!S.lines.length)S.lines=[{expiry:''}];render();return}",
    "  if(d.delline!==undefined){S.lines=readLines();S.lines.splice(+d.delline,1);if(!S.lines.length)S.lines=[{expiry:''}];render();return}\n  if(d.eiaddline){S.editLines=readEditLines();S.editLines.push({expiry:''});render();return}\n  if(d.eidelline!==undefined){S.editLines=readEditLines();S.editLines.splice(+d.eidelline,1);if(!S.editLines.length)S.editLines=[{expiry:''}];render();return}")

# input listener tracks edit date rows too
rep("  if(e.target.classList&&e.target.classList.contains('dl-exp'))S.lines=readLines();",
    "  if(e.target.classList&&e.target.classList.contains('dl-exp'))S.lines=readLines();\n  if(e.target.classList&&e.target.classList.contains('ei-exp'))S.editLines=readEditLines();")

# ---- B. ASCII boom redraw (cleaner, centred) --------------------------------
rep(
'''const ASCII_BOOM=`     *   .   |   .   *
        .  -+-  .
   *  --( B O O M )--  *
        '  -+-  '
     *   .   |   .   *`;''',
'''const ASCII_BOOM=`.   *   |   *   .
  *  --=+=--  *
--=[ B O O M ]=--
  *  --=+=--  *
.   *   |   *   .`;''')

# ---- C. Token search on All items -------------------------------------------
rep("  if(q)arr=arr.filter(i=>(i.product+' '+(i.batch||'')+' '+(i.gtin||'')+' '+(i.location||'')+' '+i.loggedByName).toLowerCase().includes(q));",
    "  if(q){const toks=q.split(/\\s+/).filter(Boolean);arr=arr.filter(i=>{const hay=(i.product+' '+(i.batch||'')+' '+(i.gtin||'')+' '+(i.location||'')+' '+i.loggedByName).toLowerCase();return toks.every(t=>hay.includes(t));});}")
rep('placeholder="Search product, batch, barcode, section or name"',
    'placeholder="Search product, batch, barcode, section or name — any words"')

open(P,'w',encoding='utf-8').write(s); print("app.js v18 patched OK")
