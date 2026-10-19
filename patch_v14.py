# -*- coding: utf-8 -*-
P='public/app.js'; s=open(P,encoding='utf-8').read()
def rep(a,b,n=1):
    global s
    c=s.count(a); assert c==n, f"want {n} got {c}: {a[:90]!r}"; s=s.replace(a,b)

# ---- state: stores + active store ----
rep("  staff:[], items:[], products:{}, settings:null, sections:[],",
    "  staff:[], items:[], products:{}, settings:null, sections:[], stores:[], storeId:null,")

# ---- store helpers + store-scoped liveItems ----
rep("const liveItems=()=>S.items.filter(i=>i.status==='active'||i.status==='reduced');",
"""const primaryStoreId=()=>S.settings?.primaryStore||(S.stores&&S.stores[0]&&S.stores[0].id)||null;
const curStore=()=>S.storeId||primaryStoreId();
const itemStore=i=>i.store||primaryStoreId();
const secStore=x=>x.storeId||primaryStoreId();
const staffStore=x=>x.storeId||primaryStoreId();
const activeStores=()=>(S.stores||[]).filter(x=>x.archived!==true).sort((a,b)=>(a.order??0)-(b.order??0)||a.name.localeCompare(b.name));
const activeStore=()=>(S.stores||[]).find(x=>x.id===curStore())||null;
const liveItems=()=>S.items.filter(i=>(i.status==='active'||i.status==='reduced')&&itemStore(i)===curStore());""")

# ---- director count is per-store ----
rep("const activeManagers=()=>S.staff.filter(s=>roleKey(s.role)==='director'&&s.active!==false);",
    "const activeManagers=()=>S.staff.filter(s=>roleKey(s.role)==='director'&&s.active!==false&&staffStore(s)===curStore());")

# ---- check times come from the active store ----
rep("const dueBy=round=>round==='morning'?(S.settings?.morningBy||'09:00'):(S.settings?.eveningBy||'20:00');",
    "const dueBy=round=>{const st=activeStore();return round==='morning'?(st?.morningBy||S.settings?.morningBy||'09:00'):(st?.eveningBy||S.settings?.eveningBy||'20:00');};")

# ---- sections are per-store ----
rep("const activeSections=()=>S.sections.filter(s=>s.archived!==true).sort((a,b)=>(a.order??0)-(b.order??0)||a.name.localeCompare(b.name));",
    "const activeSections=()=>S.sections.filter(s=>s.archived!==true&&secStore(s)===curStore()).sort((a,b)=>(a.order??0)-(b.order??0)||a.name.localeCompare(b.name));")

# ---- listen to stores ----
rep("  listen(collection(fs,'scores'),'scores',s=>{S.scores=s.docs.map(d=>({id:d.id,...d.data()})).sort((a,b)=>(b.score||0)-(a.score||0));if(document.getElementById('gameModal'))refreshBoard();});",
    "  listen(collection(fs,'scores'),'scores',s=>{S.scores=s.docs.map(d=>({id:d.id,...d.data()})).sort((a,b)=>(b.score||0)-(a.score||0));if(document.getElementById('gameModal'))refreshBoard();});\n"
    "  listen(collection(fs,'stores'),'stores',s=>{S.stores=s.docs.map(d=>({id:d.id,...d.data()}));if(!S.storeId)S.storeId=primaryStoreId();});")

# ---- resolveMe sets the viewer's store; add ensurePrimaryStore (one-time migration) ----
rep(
"""function resolveMe(){
  if(S.owner){S.me={id:'admin',name:'Boss',role:'director',owner:true};return}
  const st=S.member&&S.staff.find(x=>x.id===S.member.staffId);
  S.me=st&&st.active!==false?{...st,role:S.member.role}:null;
}""",
"""function resolveMe(){
  if(S.owner){S.me={id:'admin',name:'Boss',role:'director',owner:true};if(!S.storeId)S.storeId=primaryStoreId();return}
  const st=S.member&&S.staff.find(x=>x.id===S.member.staffId);
  S.me=st&&st.active!==false?{...st,role:S.member.role}:null;
  if(S.me)S.storeId=S.member.storeId||primaryStoreId();
}
// First time the Boss opens an old single-store app, turn its settings into a real store.
let _storeMig=false;
async function ensurePrimaryStore(){
  if(_storeMig)return;_storeMig=true;
  try{const now=Date.now();const ref=doc(collection(fs,'stores'));
    await setDoc(ref,{name:S.settings.store||'Store 1',morningBy:S.settings.morningBy||'09:00',eveningBy:S.settings.eveningBy||'20:00',order:0,archived:false,createdAt:now,createdBy:'Boss'});
    await updateDoc(doc(fs,'config','settings'),{primaryStore:ref.id});S.storeId=ref.id;
  }catch(e){_storeMig=false;}
}""")

# ---- header: store switcher for Boss, store name for staff ----
rep("  $('#storeName').textContent=S.settings.store||'';",
"""  if(!S.storeId)S.storeId=S.me.owner?primaryStoreId():(S.member?.storeId||primaryStoreId());
  if(S.me.owner&&S.loaded.stores&&(S.stores||[]).length===0&&S.settings&&!S.settings.primaryStore)ensurePrimaryStore();
  if(S.me.owner){const opts=activeStores().map(x=>`<option value="${x.id}" ${x.id===S.storeId?'selected':''}>${esc(x.name)}</option>`).join('');$('#storeName').innerHTML=opts?`<select id="storeSwitch" class="storesel" aria-label="Store">${opts}</select>`:'<span class="note">No stores yet</span>';}
  else $('#storeName').textContent=activeStore()?.name||S.settings.store||'';""")

# ---- All items scoped to the active store ----
rep("  if(q)arr=arr.filter(i=>(i.product+' '+(i.batch||'')+' '+(i.gtin||'')+' '+(i.location||'')+' '+i.loggedByName).toLowerCase().includes(q));",
    "  arr=arr.filter(i=>itemStore(i)===curStore());\n  if(q)arr=arr.filter(i=>(i.product+' '+(i.batch||'')+' '+(i.gtin||'')+' '+(i.location||'')+' '+i.loggedByName).toLowerCase().includes(q));")

# ---- staffView: scope staff list to store, add store picker per person, stores panel for Boss ----
rep("  const list=[...S.staff].sort((a,b)=>(a.active===false)-(b.active===false)||RANK[roleKey(b.role)]-RANK[roleKey(a.role)]||a.name.localeCompare(b.name));",
    "  const list=[...S.staff].filter(s=>staffStore(s)===curStore()).sort((a,b)=>(a.active===false)-(b.active===false)||RANK[roleKey(b.role)]-RANK[roleKey(a.role)]||a.name.localeCompare(b.name));")
rep("      ${lastMgr?`<div class=\"note\">${esc(s.name)} is the only Director, so their position can't change until someone else is made a Director.</div>`:''}",
    "      ${S.me.owner?`<label>Store<select id=\"store_${s.id}\">${activeStores().map(x=>`<option value=\"${x.id}\" ${x.id===staffStore(s)?'selected':''}>${esc(x.name)}</option>`).join('')}</select></label>`:''}\n"
    "      ${lastMgr?`<div class=\"note\">${esc(s.name)} is the only Director, so their position can't change until someone else is made a Director.</div>`:''}")
rep(
"""  <h2 style="margin-top:8px">Date checks</h2>
  <form class="panel" id="timesForm"><h3>Check times</h3>
    <div class="grid2"><label>Morning check due by<input id="st_morning" type="time" value="${esc(dueBy('morning'))}" required></label>
    <label>Evening check due by<input id="st_evening" type="time" value="${esc(dueBy('evening'))}" required></label></div>
    <button class="btn">Save times</button></form>""",
"""  ${S.me.owner?storesPanel():`<h2 style="margin-top:8px">Date checks</h2>
  <form class="panel" id="timesForm"><h3>Check times</h3>
    <div class="grid2"><label>Morning check due by<input id="st_morning" type="time" value="${esc(dueBy('morning'))}" required></label>
    <label>Evening check due by<input id="st_evening" type="time" value="${esc(dueBy('evening'))}" required></label></div>
    <button class="btn">Save times</button></form>`}""")

# ---- storesPanel() before staffView ----
rep("function staffView(){",
"""function storesPanel(){
  const ss=activeStores();
  return `<h2 style="margin-top:8px">Stores</h2>
  <div class="panel"><h3>Your stores</h3>
    <p class="note">Each person belongs to one store and sees only that store's items, sections and checks. Switch the store you're viewing from the picker in the top bar.</p>
    <div class="storelist">${ss.length?ss.map(x=>`<div class="storerow">
      <input class="stname" id="stn_${x.id}" value="${esc(x.name)}" maxlength="40" aria-label="Store name">
      <label class="tlab">Morning<input id="stm_${x.id}" type="time" value="${esc(x.morningBy||'09:00')}"></label>
      <label class="tlab">Evening<input id="ste_${x.id}" type="time" value="${esc(x.eveningBy||'20:00')}"></label>
      <button class="btn small primary" data-store-save="${x.id}">Save</button>
      ${ss.length>1?`<button class="btn small danger" data-store-archive="${x.id}">Remove</button>`:''}
    </div>`).join(''):'<div class="note">No stores yet.</div>'}</div>
    <form id="storeForm" class="secrow"><input id="store_new" required maxlength="40" placeholder="New store, e.g. Fresh Dundrum" aria-label="New store name"><button class="btn small primary">Add store</button></form>
  </div>`;
}
function staffView(){""")

# ---- addStaff stamps the store ----
rep(
"""    const sref=doc(collection(fs,'staff'));const b=writeBatch(fs);
    b.set(sref,{name,username,role,active:true,authUid:uid,gen:1,createdAt:Date.now(),changes:[{text:`Added as ${ROLES[role]}`,...by()}]});
    b.set(doc(fs,'members',uid),{staffId:sref.id,role,username});""",
"""    const sref=doc(collection(fs,'staff'));const b=writeBatch(fs);const sid=curStore();
    b.set(sref,{name,username,role,active:true,storeId:sid,authUid:uid,gen:1,createdAt:Date.now(),changes:[{text:`Added as ${ROLES[role]}`,...by()}]});
    b.set(doc(fs,'members',uid),{staffId:sref.id,role,username,storeId:sid});""")

# ---- saveStaff: Boss can move someone to another store; keep storeId on member rewrites ----
rep("      if(s.active!==false)b.set(doc(fs,'members',uid),{staffId:s.id,role:patch.role||s.role,username:s.username});",
    "      if(s.active!==false)b.set(doc(fs,'members',uid),{staffId:s.id,role:patch.role||s.role,username:s.username,storeId:patch.storeId||s.storeId||primaryStoreId()});")
rep("  if(!notes.length){flash('Nothing changed');return}",
    "  if(S.me.owner){const nst=$('#store_'+id)?.value;if(nst&&nst!==staffStore(s)){patch.storeId=nst;notes.push('Moved store');if(s.active!==false)b.update(doc(fs,'members',s.authUid),{storeId:nst});}}\n"
    "  if(!notes.length){flash('Nothing changed');return}")

# ---- toggleStaff keeps storeId ----
rep("  if(reactivate)b.set(doc(fs,'members',s.authUid),{staffId:s.id,role:s.role,username:s.username});else b.delete(doc(fs,'members',s.authUid));",
    "  if(reactivate)b.set(doc(fs,'members',s.authUid),{staffId:s.id,role:s.role,username:s.username,storeId:s.storeId||primaryStoreId()});else b.delete(doc(fs,'members',s.authUid));")

# ---- first-run setup creates the first store ----
rep(
"""    try{const uid=await createLogin(username,1,pin);const sref=doc(collection(fs,'staff'));const now=Date.now();const b=writeBatch(fs);
      b.set(sref,{name,username,role:'director',active:true,authUid:uid,gen:1,createdAt:now,changes:[{text:'Added as Director',by:'admin',byName:'',at:now}]});
      b.set(doc(fs,'members',uid),{staffId:sref.id,role:'director',username});
      b.set(doc(fs,'logins',username),{gen:1});
      b.set(doc(fs,'config','settings'),{store:store_,morningBy:'09:00',eveningBy:'20:00',createdAt:now});
      // Starting sections for the store (every one is checked both morning and evening).
      ['Aisle 1','Fresh herbs','Pre-made sandwiches & sushi','Pizza fridge 1','Pizza fridge 2','Spider fridge','Bread']
        .forEach((secName,i)=>b.set(doc(collection(fs,'sections')),{name:secName,archived:false,order:i,createdAt:now,createdBy:name,history:[]}));""",
"""    try{const uid=await createLogin(username,1,pin);const sref=doc(collection(fs,'staff'));const storeRef=doc(collection(fs,'stores'));const now=Date.now();const b=writeBatch(fs);
      b.set(storeRef,{name:store_,morningBy:'09:00',eveningBy:'20:00',order:0,archived:false,createdAt:now,createdBy:name});
      b.set(sref,{name,username,role:'director',active:true,storeId:storeRef.id,authUid:uid,gen:1,createdAt:now,changes:[{text:'Added as Director',by:'admin',byName:'',at:now}]});
      b.set(doc(fs,'members',uid),{staffId:sref.id,role:'director',username,storeId:storeRef.id});
      b.set(doc(fs,'logins',username),{gen:1});
      b.set(doc(fs,'config','settings'),{store:store_,primaryStore:storeRef.id,morningBy:'09:00',eveningBy:'20:00',createdAt:now});
      ['Aisle 1','Fresh herbs','Pre-made sandwiches & sushi','Pizza fridge 1','Pizza fridge 2','Spider fridge','Bread']
        .forEach((secName,i)=>b.set(doc(collection(fs,'sections')),{name:secName,storeId:storeRef.id,archived:false,order:i,createdAt:now,createdBy:name,history:[]}));""")

# ---- log an item: stamp the store ----
rep("      bch.set(ref,{product,gtin,batch,expiry:l.expiry,qty:l.qty?Number(l.qty):null,location,notes,\n        status:'active',loggedBy:b.by,loggedByName:b.byName,loggedAt:b.at,lastAction:'logged',lastBy:b.by,lastByName:b.byName,lastAt:b.at,",
    "      bch.set(ref,{product,gtin,batch,expiry:l.expiry,qty:l.qty?Number(l.qty):null,location,notes,store:curStore(),\n        status:'active',loggedBy:b.by,loggedByName:b.byName,loggedAt:b.at,lastAction:'logged',lastBy:b.by,lastByName:b.byName,lastAt:b.at,")

# ---- new section while logging: stamp the store ----
rep("      bch.set(doc(collection(fs,'sections')),{name:location,archived:false,order:Date.now(),createdAt:b.at,createdBy:b.byName||'staff',history:[]});",
    "      bch.set(doc(collection(fs,'sections')),{name:location,storeId:curStore(),archived:false,order:Date.now(),createdAt:b.at,createdBy:b.byName||'staff',history:[]});")

# ---- section added from Staff tab: stamp the store ----
rep("    quickWrite(addDoc(collection(fs,'sections'),{name,archived:false,order:Date.now(),createdAt:Date.now(),history:[]}),`${name} added`);",
    "    quickWrite(addDoc(collection(fs,'sections'),{name,storeId:curStore(),archived:false,order:Date.now(),createdAt:Date.now(),history:[]}),`${name} added`);")

# ---- check times write to the store ----
rep(
"""  if(f.id==='timesForm'){
    const m=$('#st_morning').value,ev=$('#st_evening').value;if(!m||!ev)return;
    quickWrite(updateDoc(doc(fs,'config','settings'),{morningBy:m,eveningBy:ev}),'Check times saved');return;
  }""",
"""  if(f.id==='timesForm'){
    const m=$('#st_morning').value,ev=$('#st_evening').value;if(!m||!ev)return;
    if(activeStore())quickWrite(updateDoc(doc(fs,'stores',curStore()),{morningBy:m,eveningBy:ev}),'Check times saved');
    else quickWrite(updateDoc(doc(fs,'config','settings'),{morningBy:m,eveningBy:ev}),'Check times saved');return;
  }
  if(f.id==='storeForm'){
    const name=$('#store_new').value.trim();if(!name)return;
    if(activeStores().some(x=>x.name.toLowerCase()===name.toLowerCase())){flash('There is already a store with that name');return}
    const now=Date.now();const b=writeBatch(fs);const storeRef=doc(collection(fs,'stores'));
    b.set(storeRef,{name,morningBy:'09:00',eveningBy:'20:00',order:(S.stores?.length||0),archived:false,createdAt:now,createdBy:S.me.name||'Boss'});
    ['Aisle 1','Fresh herbs','Pre-made sandwiches & sushi','Pizza fridge 1','Pizza fridge 2','Spider fridge','Bread']
      .forEach((secName,i)=>b.set(doc(collection(fs,'sections')),{name:secName,storeId:storeRef.id,archived:false,order:i,createdAt:now,createdBy:S.me.name||'Boss',history:[]}));
    quickWrite(b.commit(),`${name} added`);$('#store_new').value='';S.storeId=storeRef.id;return;
  }""")

# ---- click handlers: store save / archive ----
rep("  if(d.secArchive){const s=S.sections.find(x=>x.id===d.secArchive);quickWrite(updateDoc(doc(fs,'sections',d.secArchive),{archived:true}),`${s?.name||'Section'} removed`);return}",
    "  if(d.secArchive){const s=S.sections.find(x=>x.id===d.secArchive);quickWrite(updateDoc(doc(fs,'sections',d.secArchive),{archived:true}),`${s?.name||'Section'} removed`);return}\n"
    "  if(d.storeSave){const nm=$('#stn_'+d.storeSave)?.value.trim(),mm=$('#stm_'+d.storeSave)?.value,ee=$('#ste_'+d.storeSave)?.value;if(nm)quickWrite(updateDoc(doc(fs,'stores',d.storeSave),{name:nm,morningBy:mm,eveningBy:ee}),'Store saved');return}\n"
    "  if(d.storeArchive){const x=S.stores.find(s=>s.id===d.storeArchive);quickWrite(updateDoc(doc(fs,'stores',d.storeArchive),{archived:true}),`${x?.name||'Store'} removed`);if(S.storeId===d.storeArchive)S.storeId=primaryStoreId();return}")

# ---- change handler: Boss store switcher ----
rep("  if(e.target.id==='f_status'){S.filter.status=e.target.value;render()}",
    "  if(e.target.id==='f_status'){S.filter.status=e.target.value;render()}\n  if(e.target.id==='storeSwitch'){S.storeId=e.target.value;render();return}")

open(P,'w',encoding='utf-8').write(s); print("app.js v14 (multi-store) patched OK")
