# -*- coding: utf-8 -*-
P='public/app.js'; s=open(P,encoding='utf-8').read()
def rep(a,b,n=1):
    global s
    c=s.count(a); assert c==n, f"want {n} got {c}: {a[:80]!r}"; s=s.replace(a,b)

# ---------- A. roles core ----------
rep(
"const ROLES={manager:'Manager',supervisor:'Supervisor',staff:'Floor staff'};\n"
"const RANK={staff:1,supervisor:2,manager:3};\n"
"const atLeast=r=>(RANK[S.me?.role]||1)>=RANK[r];\n"
"const isAdmin=()=>S.me?.role==='manager'; // managers, and the hidden owner who acts as one\n"
"const activeManagers=()=>S.staff.filter(s=>s.role==='manager'&&s.active!==false);",
"const ROLES={director:'Director',npc:'NPC'};\n"
"// Legacy data may still say manager/supervisor/staff; fold those into the new positions.\n"
"const roleKey=r=>(r==='manager'||r==='director')?'director':'npc';\n"
"const RANK={npc:1,director:2};\n"
"const myRole=()=>roleKey(S.me?.role);\n"
"const atLeast=r=>RANK[myRole()]>=RANK[r];\n"
"const isAdmin=()=>myRole()==='director'||!!S.me?.owner; // Directors manage; Boss (owner) is god mode\n"
"const canRestore=()=>isAdmin();                         // put items back: Director and Boss only\n"
"const activeManagers=()=>S.staff.filter(s=>roleKey(s.role)==='director'&&s.active!==false);")

# ---------- B. owner pseudo-member is a Director ----------
rep("  if(S.owner){S.me={id:'admin',name:'Admin',role:'manager',owner:true};return}",
    "  if(S.owner){S.me={id:'admin',name:'Boss',role:'director',owner:true};return}")

# ---------- C. tabs: Boss sees Log; Activity is Director+Boss ----------
rep("  const tabs=Object.keys(TABS).filter(t=>!(S.me.owner&&t==='log')&&!(t==='activity'&&!S.me.owner));",
    "  const tabs=Object.keys(TABS).filter(t=>!(t==='activity'&&!isAdmin()));")

# ---------- D. who's on shift label ----------
rep("  $('#whoName').textContent=S.me.name+' · '+ROLES[S.me.role||'staff'];updateThemeBtn();updatePhotoBtn();",
    "  $('#whoName').textContent=S.me.owner?'Boss':S.me.name+' · '+ROLES[myRole()];updateThemeBtn();updatePhotoBtn();")

# ---------- F. +Photo button available to everyone incl Boss ----------
rep("  if(S.me&&!S.me.owner) return `<button type=\"button\" class=\"btn small ghost photo-add\" data-addphoto=\"${esc(key)}\">+ Photo</button>`;",
    "  if(S.me) return `<button type=\"button\" class=\"btn small ghost photo-add\" data-addphoto=\"${esc(key)}\">+ Photo</button>`;")

# ---------- G. photo capture guard ----------
rep("  if(!f||!key||S.me.owner)return;flash('Processing photo…');",
    "  if(!f||!key)return;flash('Processing photo…');")

# ---------- H. photo author fallback ----------
rep("    quickWrite(setDoc(doc(fs,'photos',key),{data,byName:b.byName||'Owner',at:b.at}),'Photo added');",
    "    quickWrite(setDoc(doc(fs,'photos',key),{data,byName:b.byName||'Boss',at:b.at}),'Photo added');")

# ---------- I. qty steppers for everyone on live items ----------
rep("  if(!live||S.me.owner)return it.qty?`<span class=\"note\">× ${esc(it.qty)}</span>`:'';",
    "  if(!live)return it.qty?`<span class=\"note\">× ${esc(it.qty)}</span>`:'';")

# ---------- J. action buttons always shown (Boss god mode) ----------
rep("  const b=live?band(n):'';const acts=!S.me.owner;",
    "  const b=live?band(n):'';const acts=true;")

# ---------- K. item card restore buttons: Director + Boss ----------
rep(
"      (it.status==='void'\n"
"        ? (atLeast('supervisor')?`<button class=\"btn small\" data-act=\"restored\" data-id=\"${it.id}\">Undo delete</button>`:'')\n"
"        : (atLeast('supervisor')?`<button class=\"btn small\" data-act=\"restored\" data-id=\"${it.id}\">Undo, put back on shelf</button>`:''))}</div>`:''}",
"      (it.status==='void'\n"
"        ? (canRestore()?`<button class=\"btn small\" data-act=\"restored\" data-id=\"${it.id}\">Undo delete</button>`:'')\n"
"        : (canRestore()?`<button class=\"btn small\" data-act=\"restored\" data-id=\"${it.id}\">Undo, put back on shelf</button>`:''))}</div>`:''}")

# ---------- L. section check input available to everyone incl Boss ----------
rep("        ${!c&&!S.me.owner?`<div class=\"actions\" style=\"padding-top:6px\">",
    "        ${!c?`<div class=\"actions\" style=\"padding-top:6px\">")

# ---------- M. Today reorder: expiry blocks on top, checks at the bottom ----------
rep(
"""function todayView(){
  const live=liveItems().sort((a,b)=>a.expiry.localeCompare(b.expiry));
  const exp=live.filter(i=>daysLeft(i.expiry)<0),soon=live.filter(i=>{const n=daysLeft(i.expiry);return n>=0&&n<=2}),week=live.filter(i=>{const n=daysLeft(i.expiry);return n>2&&n<=7});
  const round=currentRound();const hasSections=activeSections().length>0;
  const block=(t,arr,msg)=>`<div class="list"><h3>${t} (${arr.length})</h3>${arr.length?arr.map(itemCard).join(''):`<div class="empty">${msg}</div>`}</div>`;
  return `<section class="view">
    ${hasSections?roundPanel(round,true)+(round==='evening'?roundPanel('morning',false):'')
      :(isAdmin()?`<div class="empty">Add the sections you check (Dairy chiller, Bakery and so on) in the <b>Staff</b> tab, so everyone can tick them off each morning and evening.</div>`:'')}
    <div class="counts">
      <div class="count crit"><span class="n">${exp.length}</span><span class="l">Expired, pull now</span></div>
      <div class="count crit" style="opacity:.85"><span class="n">${soon.length}</span><span class="l">0–2 days</span></div>
      <div class="count warn"><span class="n">${week.length}</span><span class="l">3–7 days</span></div>
    </div>
    ${live.length===0?`<div class="empty">Nothing logged yet. Go to <b>Log product</b> and add the first item you check, with its batch code and use-by date.</div>`:''}
    ${(()=>{const blocks=[['Expired, pull from shelf',exp,'Nothing past its date.'],['Expiring in the next 2 days',soon,'Nothing due in the next 2 days.'],['Expiring this week',week,'Nothing else due this week.']];
      return [...blocks.filter(x=>x[1].length),...blocks.filter(x=>!x[1].length)].map(x=>block(x[0],x[1],x[2])).join('');})()}
  </section>`;
}""",
"""function todayView(){
  const live=liveItems().sort((a,b)=>a.expiry.localeCompare(b.expiry));
  const exp=live.filter(i=>daysLeft(i.expiry)<0),soon=live.filter(i=>{const n=daysLeft(i.expiry);return n>=0&&n<=2}),week=live.filter(i=>{const n=daysLeft(i.expiry);return n>2&&n<=7});
  const round=currentRound();const hasSections=activeSections().length>0;
  const block=(t,arr)=>`<div class="list"><h3>${t} (${arr.length})</h3>${arr.map(itemCard).join('')}</div>`;
  const blocks=[['Expired, pull from shelf',exp],['Expiring in the next 2 days',soon],['Expiring this week',week]].filter(x=>x[1].length);
  const checks=hasSections?roundPanel(round,true)+(round==='evening'?roundPanel('morning',false):'')
    :(isAdmin()?`<div class="empty">Add the sections you check (Dairy chiller, Bakery and so on) in the <b>Staff</b> tab, so everyone can tick them off each morning and evening.</div>`:'');
  return `<section class="view">
    <div class="counts">
      <div class="count crit"><span class="n">${exp.length}</span><span class="l">Expired, pull now</span></div>
      <div class="count crit" style="opacity:.85"><span class="n">${soon.length}</span><span class="l">0–2 days</span></div>
      <div class="count warn"><span class="n">${week.length}</span><span class="l">3–7 days</span></div>
    </div>
    ${live.length===0?`<div class="empty">Nothing logged yet. Go to <b>Log product</b> and add the first item you check, with its batch code and use-by date.</div>`
      :blocks.length?blocks.map(x=>block(x[0],x[1])).join(''):`<div class="okbox">Nothing due in the next 7 days. Nice.</div>`}
    ${checks}
  </section>`;
}""")

# ---------- N. All items: left section nav + collapsible groups ----------
rep(
"""  const body=arr.length?keys.map(k=>{
    const items=groups.get(k).slice().sort((a,b)=>a.expiry.localeCompare(b.expiry));
    return `<div class="list"><h3>${k?esc(k):'No section'} (${items.length})</h3>${items.map(itemCard).join('')}</div>`;
  }).join(''):'<div class="empty">No items match.</div>';
  return `<section class="view"><h2>All items</h2>
    <div class="filters"><input id="f_q" type="search" placeholder="Search product, batch, barcode, section or name" value="${esc(S.filter.q)}">
    <select id="f_status">${[['active','On shelf'],['removed','Removed'],['sold','Sold through'],['void','Deleted'],['all','Everything']].map(([v,l])=>`<option value="${v}" ${st===v?'selected':''}>${l}</option>`).join('')}</select></div>
    <div class="note">${arr.length} item${arr.length===1?'':'s'}</div>
    ${body}</section>`;
}""",
"""  const label=k=>k?esc(k):'No section';
  const nav=keys.length>1?`<div class="secnav" role="tablist">${keys.map((k,i)=>`<button type="button" class="secnav-item" data-gonav="${i}">${label(k)} <span class="cnt">${groups.get(k).length}</span></button>`).join('')}</div>`:'';
  const body=arr.length?`<div class="secbody">${keys.map((k,i)=>{
    const items=groups.get(k).slice().sort((a,b)=>a.expiry.localeCompare(b.expiry));
    return `<details class="grp" id="grp-${i}" open><summary><span>${label(k)}</span> <span class="cnt">${items.length}</span></summary><div class="list">${items.map(itemCard).join('')}</div></details>`;
  }).join('')}</div>`:'<div class="empty">No items match.</div>';
  return `<section class="view"><h2>All items</h2>
    <div class="filters"><input id="f_q" type="search" placeholder="Search product, batch, barcode, section or name" value="${esc(S.filter.q)}">
    <select id="f_status">${[['active','On shelf'],['removed','Removed'],['sold','Sold through'],['void','Deleted'],['all','Everything']].map(([v,l])=>`<option value="${v}" ${st===v?'selected':''}>${l}</option>`).join('')}</select></div>
    <div class="note">${arr.length} item${arr.length===1?'':'s'}</div>
    <div class="allwrap">${nav}${body}</div></section>`;
}""")

# ---------- O. Activity log: Director + Boss ----------
rep("  if(!S.me.owner)return `<section class=\"view\"><h2>Activity</h2><div class=\"empty\">The activity log is for the owner.</div></section>`;",
    "  if(!isAdmin())return `<section class=\"view\"><h2>Activity</h2><div class=\"empty\">The activity log is for Directors and the Boss.</div></section>`;")

# ---------- P. activity row restore (rename local to avoid shadowing canRestore()) ----------
rep("    const canRestore=['removed','sold','void'].includes(h.action)&&it.status===h.action&&it.lastAt===h.at&&atLeast('supervisor')&&!S.me.owner;",
    "    const canRestoreNow=['removed','sold','void'].includes(h.action)&&it.status===h.action&&it.lastAt===h.at&&canRestore();")
rep("    ev.push({at:h.at,byName:h.byName,restoreId:canRestore?it.id:null,html:",
    "    ev.push({at:h.at,byName:h.byName,restoreId:canRestoreNow?it.id:null,html:")

# ---------- Q. suggestions: drop the "Email instead" button ----------
rep(
"      <div class=\"actions\"><button class=\"btn primary\">Send</button>\n"
"      ${FEEDBACK_EMAIL?`<button type=\"button\" class=\"btn small\" id=\"fbMail\">Email instead</button>`:''}</div>",
"      <div class=\"actions\"><button class=\"btn primary\">Send</button></div>")

# ---------- R. suggestions list: normalise role label ----------
rep("${f.role?` <span class=\"note\">(${esc(ROLES[f.role]||f.role)})</span>`:''}",
    "${f.role?` <span class=\"note\">(${esc(ROLES[roleKey(f.role)]||f.role)})</span>`:''}")

# ---------- S. staff view: my-account role label ----------
rep("    <div class=\"panel\" style=\"gap:4px\"><b>${esc(S.me.name)}</b><div class=\"note\">@${esc(S.me.username)} · ${ROLES[S.me.role]}</div></div>\n    ${feedbackPanel()}",
    "    <div class=\"panel\" style=\"gap:4px\"><b>${esc(S.me.name)}</b><div class=\"note\">@${esc(S.me.username)} · ${ROLES[myRole()]}</div></div>\n    ${feedbackPanel()}")

# ---------- S2. staff list sort by normalised rank ----------
rep("  const list=[...S.staff].sort((a,b)=>(a.active===false)-(b.active===false)||RANK[b.role||'staff']-RANK[a.role||'staff']||a.name.localeCompare(b.name));",
    "  const list=[...S.staff].sort((a,b)=>(a.active===false)-(b.active===false)||RANK[roleKey(b.role)]-RANK[roleKey(a.role)]||a.name.localeCompare(b.name));")

# ---------- S3. staff card role + last-director guard ----------
rep("    const role=s.role||'staff';const open=S.editStaff===s.id;const lastMgr=role==='manager'&&s.active!==false&&activeManagers().length<=1;",
    "    const role=roleKey(s.role);const open=S.editStaff===s.id;const lastMgr=role==='director'&&s.active!==false&&activeManagers().length<=1;")
rep("      <span class=\"pill ${role==='manager'?'ok':role==='supervisor'?'warn':'done'}\">${ROLES[role]}</span>",
    "      <span class=\"pill ${role==='director'?'ok':'done'}\">${ROLES[role]}</span>")
rep("      ${lastMgr?`<div class=\"note\">${esc(s.name)} is the only manager, so their position can't change until someone else is made manager.</div>`:''}",
    "      ${lastMgr?`<div class=\"note\">${esc(s.name)} is the only Director, so their position can't change until someone else is made a Director.</div>`:''}")

# ---------- S4. "what each position can do" panel ----------
rep(
"""  <div class="panel" style="gap:6px"><h3>What each position can do</h3>
    <div class="note"><b>Floor staff:</b> do the morning and evening checks, log products, remove from shelf, mark sold through.</div>
    <div class="note"><b>Supervisor:</b> all of that, plus undo a removal or sale made by mistake.</div>
    <div class="note"><b>Manager:</b> all of that, plus this Staff page: add people, change positions, reset PINs, deactivate staff, and set up sections and check times.</div>
    <div class="note">Floor staff and supervisors only see "Change my PIN" here.</div></div>""",
"""  <div class="panel" style="gap:6px"><h3>What each position can do</h3>
    <div class="note"><b>NPC:</b> morning and evening checks, log products, remove from shelf, mark sold through, delete a mistaken entry, change their own PIN.</div>
    <div class="note"><b>Director:</b> everything an NPC can, plus put items back on the shelf, see the activity log, and this Staff page: add people, change positions, reset PINs, deactivate staff, reorder sections and set check times.</div>
    <div class="note"><b>Boss:</b> full access to everything, including the suggestions inbox.</div>
    <div class="note">NPCs only see "Change my PIN" here.</div></div>""")

# ---------- S5. sections list: reorder arrows + note ----------
rep("    <p class=\"note\">Every section is ticked off in both the morning and evening check. Anyone can also add a new section while logging a product, by choosing \"Other\" for the section.</p>",
    "    <p class=\"note\">Every section is ticked off in both the morning and evening check. Use the ▲▼ arrows to set the order staff see them in. Anyone can also add a new section while logging a product, by choosing \"Other\" for the section.</p>")
rep(
"    ${secs.length?`<div class=\"seclist\">${secs.map(s=>`<div class=\"secrow\"><input id=\"sn_${s.id}\" value=\"${esc(s.name)}\" maxlength=\"40\" aria-label=\"Section name\">\n      <button class=\"btn small\" data-sec-save=\"${s.id}\">Rename</button><button class=\"btn small danger\" data-sec-archive=\"${s.id}\">Remove</button></div>`).join('')}</div>`:'<div class=\"note\">No sections yet.</div>'}",
"    ${secs.length?`<div class=\"seclist\">${secs.map((s,i)=>`<div class=\"secrow\"><span class=\"secmove\"><button class=\"btn small ghost\" data-sec-up=\"${s.id}\" ${i===0?'disabled':''} aria-label=\"Move up\">▲</button><button class=\"btn small ghost\" data-sec-down=\"${s.id}\" ${i===secs.length-1?'disabled':''} aria-label=\"Move down\">▼</button></span><input id=\"sn_${s.id}\" value=\"${esc(s.name)}\" maxlength=\"40\" aria-label=\"Section name\">\n      <button class=\"btn small\" data-sec-save=\"${s.id}\">Rename</button><button class=\"btn small danger\" data-sec-archive=\"${s.id}\">Remove</button></div>`).join('')}</div>`:'<div class=\"note\">No sections yet.</div>'}")

# ---------- T. camera: hi-res + torch, iOS-friendly ----------
rep(
"""async function startCamera(){
  if(!window.Html5Qrcode){flash('Camera scanner didn\\'t load. Check the connection.');return}
  S.camOn=true;render();
  const F=Html5QrcodeSupportedFormats;
  cam=new Html5Qrcode('camBox',{formatsToSupport:[F.EAN_13,F.EAN_8,F.UPC_A,F.UPC_E,F.CODE_128,F.DATA_MATRIX,F.QR_CODE,F.ITF],useBarCodeDetectorIfSupported:true,verbose:false});
  try{await cam.start({facingMode:'environment'},{fps:12,qrbox:(w,h)=>({width:Math.min(300,w*0.85),height:Math.min(180,h*0.5)})},
      text=>{stopCamera();if(navigator.vibrate)navigator.vibrate(60);applyScan(text)},()=>{})}
  catch(e){S.camOn=false;cam=null;render();flash('Camera blocked. Allow camera access for this site in the browser settings.')}
}
async function stopCamera(){const c=cam;cam=null;S.camOn=false;if(c){try{await c.stop()}catch(e){}try{c.clear()}catch(e){}}render()}""",
"""let torchOn=false;
async function startCamera(){
  if(!window.Html5Qrcode){flash('Camera scanner didn\\'t load. Check the connection.');return}
  S.camOn=true;torchOn=false;render();
  const F=Html5QrcodeSupportedFormats;
  cam=new Html5Qrcode('camBox',{formatsToSupport:[F.EAN_13,F.EAN_8,F.UPC_A,F.UPC_E,F.CODE_128,F.DATA_MATRIX,F.QR_CODE,F.ITF],useBarCodeDetectorIfSupported:true,verbose:false});
  const onHit=text=>{stopCamera();if(navigator.vibrate)navigator.vibrate(60);applyScan(text)};
  // Tighter box and a higher-resolution stream so the barcode is readable before the lens finishes focusing.
  const cfg={fps:15,qrbox:(w,h)=>({width:Math.min(320,Math.round(w*0.9)),height:Math.min(210,Math.round(h*0.55))})};
  const hi={facingMode:'environment',width:{ideal:1920},height:{ideal:1080},advanced:[{focusMode:'continuous'}]};
  try{await cam.start(hi,cfg,onHit,()=>{})}
  catch(e){
    try{await cam.start({facingMode:'environment'},cfg,onHit,()=>{})}
    catch(e2){S.camOn=false;cam=null;render();flash('Camera blocked. Allow camera access for this site in the browser settings.')}
  }
}
// Torch helps a lot on iPhones, where the browser gives little focus control. No-op where unsupported.
async function toggleTorch(){
  if(!cam)return;torchOn=!torchOn;
  try{await cam.applyVideoConstraints({advanced:[{torch:torchOn}]});render();}
  catch(e){torchOn=false;flash('This phone doesn\\'t allow the torch from the browser');}
}
async function stopCamera(){const c=cam;cam=null;S.camOn=false;torchOn=false;if(c){try{await c.stop()}catch(e){}try{c.clear()}catch(e){}}render()}""")

# ---------- T2. camera controls in the log view: torch button + steadiness hint ----------
rep(
"""      <input id="scan_in" autocomplete="off" placeholder="Scanner input, or type a barcode" aria-label="Barcode" style="flex:1 1 220px">
      <button type="button" class="btn primary" data-camera="1">${S.camOn?'Stop camera':'Scan with camera'}</button>
    </div>
    <div id="camBox" ${S.camOn?'':'hidden'}></div>""",
"""      <input id="scan_in" autocomplete="off" placeholder="Scanner input, or type a barcode" aria-label="Barcode" style="flex:1 1 220px">
      <button type="button" class="btn primary" data-camera="1">${S.camOn?'Stop camera':'Scan with camera'}</button>
      ${S.camOn?`<button type="button" class="btn" data-torch="1">${torchOn?'Torch off':'Torch'}</button>`:''}
    </div>
    <div id="camBox" ${S.camOn?'':'hidden'}></div>
    ${S.camOn?`<div class="note">Hold the barcode 10–15&nbsp;cm away and steady. Tap Torch if the light is low.</div>`:''}""")

# ---------- U. first-run setup creates a Director ----------
rep(
"      b.set(sref,{name,username,role:'manager',active:true,authUid:uid,gen:1,createdAt:now,changes:[{text:'Added as Manager',by:'admin',byName:'',at:now}]});\n"
"      b.set(doc(fs,'members',uid),{staffId:sref.id,role:'manager',username});",
"      b.set(sref,{name,username,role:'director',active:true,authUid:uid,gen:1,createdAt:now,changes:[{text:'Added as Director',by:'admin',byName:'',at:now}]});\n"
"      b.set(doc(fs,'members',uid),{staffId:sref.id,role:'director',username});")

# ---------- V. setItemStatus: drop owner block, Director/Boss restore ----------
rep(
"  const it=S.items.find(i=>i.id===id);if(!it||S.me.owner)return;\n"
"  if(act==='restored'&&!atLeast('supervisor')){flash('Ask a supervisor or manager to undo this');return}",
"  const it=S.items.find(i=>i.id===id);if(!it)return;\n"
"  if(act==='restored'&&!canRestore()){flash('Only a Director or the Boss can put items back');return}")

# ---------- W. adjustQty guard ----------
rep("  const it=S.items.find(i=>i.id===id);if(!it||S.me.owner)return;\n  const base=qtyPending[id]",
    "  const it=S.items.find(i=>i.id===id);if(!it)return;\n  const base=qtyPending[id]")

# ---------- X. checkSection guard ----------
rep("  const s=S.sections.find(x=>x.id===id);if(!s||S.me.owner)return;",
    "  const s=S.sections.find(x=>x.id===id);if(!s)return;")

# ---------- Y. by(): label Boss actions ----------
rep("const by=()=>S.me.owner?{by:'admin',byName:'',at:Date.now()}:{by:S.me.id,byName:S.me.name,at:Date.now()};",
    "const by=()=>S.me.owner?{by:'admin',byName:'Boss',at:Date.now()}:{by:S.me.id,byName:S.me.name,at:Date.now()};")

# ---------- Z. applyScan: Boss can scan too ----------
rep("  if(!raw||!raw.trim()||S.me?.owner)return;",
    "  if(!raw||!raw.trim())return;")

# ---------- AA. addphoto click: everyone incl Boss ----------
rep("  if(d.addphoto){if(!S.me.owner)pickPhoto(d.addphoto);return}",
    "  if(d.addphoto){pickPhoto(d.addphoto);return}")

# ---------- AB. remove fbMail click handler ----------
rep("  if(t.id==='fbMail'){const m=$('#fb_msg')?.value||'';if(FEEDBACK_EMAIL)location.href=`mailto:${FEEDBACK_EMAIL}?subject=${encodeURIComponent('Shelf Date Check suggestion')}&body=${encodeURIComponent(m)}`;return}\n",
    "")

# ---------- AC. new click handlers: section jump, torch, reorder ----------
rep("  if(d.restore){setItemStatus(d.restore,'restored');return}",
    "  if(d.gonav!==undefined){const el=document.getElementById('grp-'+d.gonav);if(el){el.open=true;el.scrollIntoView({behavior:'smooth',block:'start'})}return}\n"
    "  if(d.torch){toggleTorch();return}\n"
    "  if(d.secUp){moveSection(d.secUp,-1);return}\n"
    "  if(d.secDown){moveSection(d.secDown,1);return}\n"
    "  if(d.restore){setItemStatus(d.restore,'restored');return}")

# ---------- AD. moveSection (renormalise order) ----------
rep("const logChange=(s,text)=>[...(s.changes||[]),{text,...by()}].slice(-20);",
    "const logChange=(s,text)=>[...(s.changes||[]),{text,...by()}].slice(-20);\n"
    "// Reorder sections: renumber them 0..n in the new arrangement, writing only what moved.\n"
    "function moveSection(id,dir){\n"
    "  if(!isAdmin())return;\n"
    "  const secs=activeSections();const i=secs.findIndex(x=>x.id===id);if(i<0)return;const j=i+dir;if(j<0||j>=secs.length)return;\n"
    "  const arr=secs.slice();const [m]=arr.splice(i,1);arr.splice(j,0,m);\n"
    "  const b=writeBatch(fs);let changed=0;arr.forEach((x,idx)=>{if((x.order)!==idx){b.update(doc(fs,'sections',x.id),{order:idx});changed++}});\n"
    "  if(changed)quickWrite(b.commit(),'Sections reordered');\n"
    "}")

# ---------- AE. saveStaff: normalised role compare + Director wording ----------
rep(
"  if(newRole!==(s.role||'staff')){\n"
"    if(s.role==='manager'&&activeManagers().length<=1){flash('Keep at least one active manager');return}\n"
"    patch.role=newRole;notes.push(`Position changed from ${ROLES[s.role||'staff']} to ${ROLES[newRole]}`);",
"  if(newRole!==roleKey(s.role)){\n"
"    if(roleKey(s.role)==='director'&&activeManagers().length<=1){flash('Keep at least one active Director');return}\n"
"    patch.role=newRole;notes.push(`Position changed from ${ROLES[roleKey(s.role)]} to ${ROLES[newRole]}`);")

# ---------- AF. toggleStaff: normalised role + Director wording ----------
rep("  if(s.active!==false&&s.role==='manager'&&activeManagers().length<=1){flash('Keep at least one active manager');return}",
    "  if(s.active!==false&&roleKey(s.role)==='director'&&activeManagers().length<=1){flash('Keep at least one active Director');return}")

open(P,'w',encoding='utf-8').write(s); print("app.js patched OK")
