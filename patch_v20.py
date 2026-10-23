# -*- coding: utf-8 -*-
P='public/app.js'; s=open(P,encoding='utf-8').read()
def rep(a,b,n=1):
    global s
    c=s.count(a); assert c==n, f"want {n} got {c}: {a[:90]!r}"; s=s.replace(a,b)

# human date helper, next to fmtTime
rep("function fmtTime(ms){const d=new Date(ms);return `${pad(d.getDate())} ${MON[d.getMonth()]} ${pad(d.getHours())}:${pad(d.getMinutes())}`}",
    "function fmtTime(ms){const d=new Date(ms);return `${pad(d.getDate())} ${MON[d.getMonth()]} ${pad(d.getHours())}:${pad(d.getMinutes())}`}\nfunction fmtExp(exp){const [y,m,d]=exp.split('-').map(Number);return `${d} ${MON[m-1]} ${y}`}")

# match in-stock items by barcode OR by the product's known name (covers own-brand / renamed)
rep("  const sc=S.scan;const onShelf=sc&&sc.gtin?liveItems().filter(i=>i.gtin===sc.gtin):[];",
    """  const sc=S.scan;
  const knownName=(sc&&sc.gtin&&S.products[sc.gtin]&&S.products[sc.gtin].name)||(S.draft&&S.draft.product)||'';
  const onShelf=sc?liveItems().filter(i=>(sc.gtin&&i.gtin===sc.gtin)||(knownName&&i.product&&i.product.toLowerCase()===knownName.toLowerCase())):[];
  onShelf.sort((a,b)=>a.expiry.localeCompare(b.expiry));""")

# replace the plain warnbox with a proper stock card of the dates already on the shelf
rep("""      ${onShelf.length?`<div class="warnbox">Already on the list: ${onShelf.map(i=>`use-by ${esc(i.expiry)}`).join(', ')}</div>`:''}`""",
    """      ${onShelf.length?`<div class="stockcard">
        <div class="stockcard-h"><span>Already in stock</span><span class="stockcard-n">${onShelf.length} date${onShelf.length===1?'':'s'}</span></div>
        ${onShelf.map(i=>{const n=daysLeft(i.expiry);return `<div class="stockrow">
          <span class="stockdate">${esc(fmtExp(i.expiry))}</span>
          <span class="pill ${band(n)}">${dueLabel(n)}</span>
          ${i.location?`<span class="stockloc">${esc(i.location)}</span>`:''}
        </div>`}).join('')}
        <div class="note">These are already on the shelf. Only add a date below for stock with a different use-by.</div>
      </div>`:''}`""")

open(P,'w',encoding='utf-8').write(s); print("app.js v20 (scan stock card) patched OK")
