# -*- coding: utf-8 -*-
P='public/app.js'; s=open(P,encoding='utf-8').read()
def rep(a,b,n=1):
    global s
    c=s.count(a); assert c==n, f"want {n} got {c}: {a[:90]!r}"; s=s.replace(a,b)

# 1. item card meta: drop the batch / "no batch" chip
rep('''    <div class="meta">${it.batch?`<span class="batch">${esc(it.batch)}</span>`:'<span class="nobatch">no batch</span>'}${it.location?`<span>${esc(it.location)}</span>`:''}''',
    '''    <div class="meta">${it.location?`<span>${esc(it.location)}</span>`:''}''')

# 2. empty-today copy: no more "batch code"
rep("add the first item you check, with its batch code and use-by date.",
    "add the first item you check, with its use-by date.")

# 3. scan readout: drop the Batch line
rep("${sc.gtin?`<span><b>Product no.</b>${esc(sc.gtin)}</span>`:''}${sc.batch?`<span><b>Batch</b>${esc(sc.batch)}</span>`:''}",
    "${sc.gtin?`<span><b>Product no.</b>${esc(sc.gtin)}</span>`:''}")

# 4. duplicate warning: list by use-by date, not batch
rep("${onShelf.length?`<div class=\"warnbox\">Already on the list: ${onShelf.map(i=>`${esc(i.batch||'no batch')} (use-by ${esc(i.expiry)})`).join(', ')}</div>`:''}",
    "${onShelf.length?`<div class=\"warnbox\">Already on the list: ${onShelf.map(i=>`use-by ${esc(i.expiry)}`).join(', ')}</div>`:''}")

# 5. search placeholder: drop "batch"
rep('placeholder="Search product, batch, barcode, section or name — any words"',
    'placeholder="Search product, barcode, section or name — any words"')

# 6. activity log line: drop the batch chip after the product name
rep("html:`${esc(ACTION[h.action]||h.action)} <b>${esc(it.product)}</b> <span class=\"batch\">${esc(it.batch||'no batch')}</span>`});",
    "html:`${esc(ACTION[h.action]||h.action)} <b>${esc(it.product)}</b>`});")

open(P,'w',encoding='utf-8').write(s); print("app.js v19 (batch mentions removed) patched OK")
