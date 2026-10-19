# -*- coding: utf-8 -*-
P='public/app.js'; s=open(P,encoding='utf-8').read()
def rep(a,b,n=1):
    global s
    c=s.count(a); assert c==n, f"want {n} got {c}: {a[:90]!r}"; s=s.replace(a,b)

# Bug 1: a known scanned product's name is set in the draft, but render()'s
# value-preserving step overwrites the field back to blank. Re-apply it after render.
rep(
"""  S.lines=[{expiry:sc.expiry||'',qty:sc.qty||''}];
  render();
  if(!sc.ok){$('#scan_in')?.focus();return}""",
"""  S.lines=[{expiry:sc.expiry||'',qty:sc.qty||''}];
  render();
  {const pe=$('#lf_product');if(pe&&S.draft.product)pe.value=S.draft.product;}
  if(!sc.ok){$('#scan_in')?.focus();return}""")

# Bug 2: renaming a section must also rename it on every item that used it
# (items store the section by name), so the change shows everywhere.
rep("  if(d.secSave){const name=$('#sn_'+d.secSave).value.trim();if(name)quickWrite(updateDoc(doc(fs,'sections',d.secSave),{name}),'Section renamed');return}",
"""  if(d.secSave){
    const sec=S.sections.find(x=>x.id===d.secSave);const oldName=sec&&sec.name;const name=$('#sn_'+d.secSave).value.trim();
    if(!name||name===oldName)return;
    const b=writeBatch(fs);b.update(doc(fs,'sections',d.secSave),{name});
    const bb=by();const hit=S.items.filter(i=>i.location===oldName&&itemStore(i)===secStore(sec));
    hit.forEach(i=>b.update(doc(fs,'items',i.id),{location:name,lastAction:'edited',lastBy:bb.by,lastByName:bb.byName,lastAt:bb.at}));
    quickWrite(b.commit(),`Section renamed${hit.length?` · ${hit.length} item${hit.length===1?'':'s'} moved`:''}`);return;
  }""")

open(P,'w',encoding='utf-8').write(s); print("app.js v16 (autofill + section rename) patched OK")
