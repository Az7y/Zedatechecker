# -*- coding: utf-8 -*-
P='public/app.js'; s=open(P,encoding='utf-8').read()
def rep(a,b,n=1):
    global s
    c=s.count(a); assert c==n, f"want {n} got {c}: {a[:90]!r}"; s=s.replace(a,b)

# A fresh scan is a fresh product. Previously S.draft.product was only SET when the
# barcode was already known, so an unknown next scan kept the last product's name —
# which autofilled the field and made the stock card show the old product's stock.
# Now clear the carried-over name/section/notes every scan, and set the name only
# when this barcode has a remembered one. Also always write the field (clearing it
# when empty) so render()'s value-preserving pass can't restore the stale name.
rep('''  const known=sc.gtin&&S.products[sc.gtin];
  if(known){S.draft.product=known.name;sc.image=known.image||null;}
  S.lines=[{expiry:sc.expiry||''}];
  render();
  {const pe=$('#lf_product');if(pe&&S.draft.product)pe.value=S.draft.product;}''',
'''  const known=sc.gtin&&S.products[sc.gtin];
  S.draft.product=known?known.name:'';S.draft.location='';S.draft.notes='';S.draft.addingSection=false;
  if(known)sc.image=known.image||null;
  S.lines=[{expiry:sc.expiry||''}];
  render();
  {const pe=$('#lf_product');if(pe)pe.value=S.draft.product||'';}''')

open(P,'w',encoding='utf-8').write(s); print("app.js v22 (stale scan draft) patched OK")
