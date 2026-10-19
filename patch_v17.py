# -*- coding: utf-8 -*-
P='public/app.js'; s=open(P,encoding='utf-8').read()
def rep(a,b,n=1):
    global s
    c=s.count(a); assert c==n, f"want {n} got {c}: {a[:90]!r}"; s=s.replace(a,b)

# remove qtyControl and its use on the card
rep(
"""function qtyControl(it,live){
  if(!live)return it.qty?`<span class="note">× ${esc(it.qty)}</span>`:'';
  return `<span class="qtywrap"><button type="button" class="qbtn" data-qtyminus="${it.id}" aria-label="Decrease count">&minus;</button><span class="qnum" data-qty="${it.id}">× ${esc(it.qty||0)}</span><button type="button" class="qbtn" data-qtyplus="${it.id}" aria-label="Increase count">+</button></span>`;
}
""","")
rep('    <div class="name">${esc(it.product)} ${qtyControl(it,live)}</div>',
    '    <div class="name">${esc(it.product)}</div>')

# scan readout: drop the Count line
rep("      ${sc.qty?`<span><b>Count</b>${esc(sc.qty)}</span>`:''}</div>",
    "      </div>")

# edit-item form: drop the Qty field
rep('      <label>Qty<input id="ei_qty_${it.id}" type="number" min="1" max="9999" value="${esc(it.qty||\'\')}" required></label>\n',"")

# date lines: no qty column
rep('      <div class="dl-head"><span>Use-by / best-before</span><span>Qty</span><span></span></div>',
    '      <div class="dl-head"><span>Use-by / best-before</span><span></span></div>')
rep(
"""function dlineRow(l,i,total){
  return `<div class="dline">
    <input class="dl-exp" type="date" value="${esc(l.expiry||'')}" min="2020-01-01" aria-label="Use-by date">
    <input class="dl-qty" type="number" min="1" max="9999" value="${esc(l.qty||'')}" placeholder="Qty" aria-label="Quantity">
    ${total>1?`<button type="button" class="btn small ghost" data-delline="${i}" aria-label="Remove date">&times;</button>`:'<span></span>'}
  </div>`;
}""",
"""function dlineRow(l,i,total){
  return `<div class="dline">
    <input class="dl-exp" type="date" value="${esc(l.expiry||'')}" min="2020-01-01" aria-label="Use-by date">
    ${total>1?`<button type="button" class="btn small ghost" data-delline="${i}" aria-label="Remove date">&times;</button>`:'<span></span>'}
  </div>`;
}""")
rep("  return dl.length?[...dl].map(r=>({expiry:r.querySelector('.dl-exp').value,qty:r.querySelector('.dl-qty').value})):[{expiry:'',qty:''}];}",
    "  return dl.length?[...dl].map(r=>({expiry:r.querySelector('.dl-exp').value})):[{expiry:''}];}")

# applyScan seed line
rep("  S.lines=[{expiry:sc.expiry||'',qty:sc.qty||''}];",
    "  S.lines=[{expiry:sc.expiry||''}];")

# remaining empty-line seeds
rep("{expiry:'',qty:''}","{expiry:''}",6)

# input listener no longer tracks qty
rep("  if(e.target.classList&&(e.target.classList.contains('dl-exp')||e.target.classList.contains('dl-qty')))S.lines=readLines();",
    "  if(e.target.classList&&e.target.classList.contains('dl-exp'))S.lines=readLines();")

# saveItemEdit: drop qty read, validation and write
rep("  const expiry=$('#ei_exp_'+id).value;const qv=$('#ei_qty_'+id).value;",
    "  const expiry=$('#ei_exp_'+id).value;")
rep("  if(!qv||Number(qv)<1){flash('Add a quantity');return}\n","")
rep("quickWrite(updateDoc(doc(fs,'items',id),{product,location,expiry,qty:Number(qv),lastAction:'edited'",
    "quickWrite(updateDoc(doc(fs,'items',id),{product,location,expiry,lastAction:'edited'")

# logForm: drop qty validation and qty on the written item
rep("    if(lines.some(l=>!l.qty||Number(l.qty)<1)){flash('Add a quantity for each date');return}\n","")
rep("      bch.set(ref,{product,gtin,batch,expiry:l.expiry,qty:l.qty?Number(l.qty):null,location,notes,store:curStore(),",
    "      bch.set(ref,{product,gtin,batch,expiry:l.expiry,location,notes,store:curStore(),")

# remove adjustQty and its click handlers
rep(
"""const qtyTimers={},qtyPending={};
function adjustQty(id,delta){
  const it=S.items.find(i=>i.id===id);if(!it)return;
  const base=qtyPending[id]!=null?qtyPending[id]:(Number(it.qty)||0);
  const next=Math.max(0,base+delta);qtyPending[id]=next;it.qty=next;
  const span=document.querySelector(`[data-qty="${id}"]`);if(span)span.textContent='× '+next;
  clearTimeout(qtyTimers[id]);
  qtyTimers[id]=setTimeout(()=>{const v=qtyPending[id];delete qtyPending[id];const b=by();
    quickWrite(updateDoc(doc(fs,'items',id),{qty:v,lastAction:'adjusted',lastBy:b.by,lastByName:b.byName,lastAt:b.at}),null);},700);
}
""","")
rep("  if(d.qtyplus){adjustQty(d.qtyplus,1);return}\n  if(d.qtyminus){adjustQty(d.qtyminus,-1);return}\n","")

open(P,'w',encoding='utf-8').write(s); print("app.js v17 (quantity removed) patched OK")
