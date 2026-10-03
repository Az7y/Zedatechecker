P='public/app.js'; s=open(P).read()
def rep(a,b,n=1):
    global s
    c=s.count(a); assert c==n, f"want {n} got {c}: {a[:70]!r}"; s=s.replace(a,b)

# imports: feedback config + deleteDoc
rep('import { firebaseConfig, OWNER_EMAIL } from "./firebase-config.js";',
    'import { firebaseConfig, OWNER_EMAIL, FEEDBACK_EMAIL, FEEDBACK_ENDPOINT } from "./firebase-config.js";')
rep("import { initializeFirestore, persistentLocalCache, persistentMultipleTabManager, collection, doc, onSnapshot, getDoc, setDoc, updateDoc, addDoc, writeBatch } from \"https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js\";",
    "import { initializeFirestore, persistentLocalCache, persistentMultipleTabManager, collection, doc, onSnapshot, getDoc, setDoc, updateDoc, addDoc, deleteDoc, writeBatch } from \"https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js\";")

# state: feedback
rep("  lines:[{expiry:'',qty:''}], offCache:{} };",
    "  lines:[{expiry:'',qty:''}], offCache:{}, feedback:[] };")

# photo button updater
rep("function updateThemeBtn(){const b=$('#themeBtn');if(!b)return;const cur=store.get('sdc_theme')||'system';b.textContent=cur==='light'?'\\u2600 Light':cur==='dark'?'\\u263e Dark':'\\u25d0 Auto';}",
    "function updateThemeBtn(){const b=$('#themeBtn');if(!b)return;const cur=store.get('sdc_theme')||'system';b.textContent=cur==='light'?'\\u2600 Light':cur==='dark'?'\\u263e Dark':'\\u25d0 Auto';}\nfunction updatePhotoBtn(){const b=$('#photoBtn');if(!b)return;b.textContent=photosOn()?'\\u25a3 Photos':'\\u25a2 Photos';b.setAttribute('aria-pressed',photosOn());}")

# feedback listener
rep("  listen(collection(fs,'sections'),'sections',s=>{S.sections=s.docs.map(d=>({id:d.id,...d.data()}))});",
    "  listen(collection(fs,'sections'),'sections',s=>{S.sections=s.docs.map(d=>({id:d.id,...d.data()}))});\n  listen(collection(fs,'feedback'),'feedback',s=>{S.feedback=s.docs.map(d=>({id:d.id,...d.data()})).sort((a,b)=>(b.at||0)-(a.at||0))});")

# render: refresh photo button too
rep("  $('#whoName').textContent=S.me.name+' \\u00b7 '+ROLES[S.me.role||'staff'];updateThemeBtn();",
    "  $('#whoName').textContent=S.me.name+' \\u00b7 '+ROLES[S.me.role||'staff'];updateThemeBtn();updatePhotoBtn();")

# replace displayPanel with feedback panel + list
rep("""function displayPanel(){
  return `<div class="panel" style="gap:8px"><h3>Display</h3>
    <label class="switch"><input type="checkbox" id="photoToggle" ${photosOn()?'checked':''}> Show product photos as thumbnails</label>
    <div class="note">Off shows a "Photo" link instead, lighter on data. Switch light/dark with the button in the top bar. Both are saved on this device only.</div></div>`;
}""",
"""function feedbackPanel(){
  return `<div class="panel" style="gap:8px"><h3>Suggest an improvement</h3>
    <div class="note">An idea to make the app easier to use? Send it to Oz7y.</div>
    <form id="feedbackForm" autocomplete="off" style="display:grid;gap:8px">
      <textarea id="fb_msg" rows="3" maxlength="1000" required placeholder="What would make this better?"></textarea>
      <div id="fbErr"></div>
      <div class="actions"><button class="btn primary">Send</button>
      ${FEEDBACK_EMAIL?`<button type="button" class="btn small" id="fbMail">Email instead</button>`:''}</div>
    </form></div>`;
}
function feedbackList(){
  if(!isAdmin()||!S.feedback.length)return '';
  return `<div class="panel"><h3>Suggestions (${S.feedback.length})</h3><div class="log">${S.feedback.slice(0,40).map(f=>`<div class="row"><span class="t">${fmtTime(f.at)}</span><span><b>${esc(f.byName||'Someone')}</b>${f.role?` <span class="note">(${esc(ROLES[f.role]||f.role)})</span>`:''} ${esc(f.message)} <button class="btn small" data-fbdel="${f.id}">Dismiss</button></span></div>`).join('')}</div></div>`;
}""")
rep("""    <div class="panel" style="gap:4px"><b>${esc(S.me.name)}</b><div class="note">@${esc(S.me.username)} \\u00b7 ${ROLES[S.me.role]}</div></div>
    ${displayPanel()}
    ${myPinForm()}</section>`;""",
"""    <div class="panel" style="gap:4px"><b>${esc(S.me.name)}</b><div class="note">@${esc(S.me.username)} \\u00b7 ${ROLES[S.me.role]}</div></div>
    ${feedbackPanel()}
    ${myPinForm()}</section>`;""")
rep("""  ${displayPanel()}
  ${S.me.owner?'':myPinForm()}
  </section>`;
}""",
"""  ${feedbackList()}
  ${feedbackPanel()}
  ${S.me.owner?'':myPinForm()}
  </section>`;
}""")

# click handler: photo toggle, email-instead, dismiss feedback
rep("  if(t.id==='themeBtn'){cycleTheme();return}",
"""  if(t.id==='themeBtn'){cycleTheme();return}
  if(t.id==='photoBtn'){store.set('sdc_photos',photosOn()?null:'1');render();return}
  if(t.id==='fbMail'){const m=$('#fb_msg')?.value||'';if(FEEDBACK_EMAIL)location.href=`mailto:${FEEDBACK_EMAIL}?subject=${encodeURIComponent('Shelf Date Check suggestion')}&body=${encodeURIComponent(m)}`;return}
  if(d.fbdel){if(isAdmin())quickWrite(deleteDoc(doc(fs,'feedback',d.fbdel)),'Dismissed');return}""")

# remove the old photoToggle change handler (no longer present)
rep("  if(e.target.id==='photoToggle'){store.set('sdc_photos',e.target.checked?'1':null);render()}\n", "")

# submit handler: feedback
rep("  if(f.id==='myPinForm'){",
"""  if(f.id==='feedbackForm'){
    const msg=$('#fb_msg').value.trim();if(!msg){$('#fbErr').innerHTML='<div class="errbox">Type your idea first.</div>';return}
    const b=by();
    quickWrite(addDoc(collection(fs,'feedback'),{message:msg.slice(0,1000),byName:b.byName||'Owner',role:S.me.role,at:b.at,version:'1.3'}),'Thanks, sent to Oz7y');
    if(FEEDBACK_ENDPOINT){try{fetch(FEEDBACK_ENDPOINT,{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json'},body:JSON.stringify({message:msg,from:b.byName||'Owner',role:S.me.role})}).catch(()=>{})}catch(e){}}
    $('#fb_msg').value='';$('#fbErr').innerHTML='';render();return;
  }
  if(f.id==='myPinForm'){""")

open(P,'w').write(s); print("app.js patched")
