import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import { getAuth, onAuthStateChanged, signInWithEmailAndPassword, createUserWithEmailAndPassword, signOut, updatePassword, reauthenticateWithCredential, EmailAuthProvider } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";
import { initializeFirestore, persistentLocalCache, persistentMultipleTabManager, collection, doc, onSnapshot, getDoc, setDoc, updateDoc, addDoc, deleteDoc, writeBatch } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";
import { firebaseConfig, OWNER_EMAIL, FEEDBACK_EMAIL, FEEDBACK_ENDPOINT } from "./firebase-config.js";

const fbApp = initializeApp(firebaseConfig);
const auth = getAuth(fbApp);
// Offline cache: works on patchy shop Wi-Fi and syncs when the connection comes back.
const fs = initializeFirestore(fbApp, { localCache: persistentLocalCache({ tabManager: persistentMultipleTabManager() }) });

// Each staff member is a real Firebase login behind the scenes. The username and PIN make the password;
// the PIN itself is never stored in the database.
const STAFF_DOMAIN = 'staff.shelf-date-check.app';
const staffEmail = (username, gen) => `${username}.${gen}@${STAFF_DOMAIN}`;
const staffPassword = (username, pin) => `sdc-${pin}-${username}`;
const USERNAME_RE = /^[a-z0-9][a-z0-9._-]{1,19}$/;
const PIN_RE = /^\d{4,6}$/;

// A second Firebase app, used only to create logins without signing the current person out.
let creatorAuth = null;
function getCreatorAuth(){ if(!creatorAuth) creatorAuth = getAuth(initializeApp(firebaseConfig, 'creator')); return creatorAuth; }
async function createLogin(username, gen, pin){
  const ca = getCreatorAuth();
  const cred = await createUserWithEmailAndPassword(ca, staffEmail(username, gen), staffPassword(username, pin));
  const uid = cred.user.uid; await signOut(ca); return uid;
}

const S = { authUser:null, authChecked:false, owner:false, member:null, me:null,
  staff:[], items:[], products:{}, settings:null, sections:[],
  loaded:{}, tab:'today', filter:{q:'',status:'active'}, scan:null, camOn:false,
  editStaff:null, showOwner:false, ownerTaps:0, error:null, briefed:false,
  lines:[{expiry:'',qty:''}], offCache:{}, feedback:[], nameImg:{}, sugTimer:null, photos:{}, photoReq:{}, photoTarget:null };

/* GS1 barcode parsing. Handles plain EAN/UPC, and GS1-128 / DataMatrix / QR element strings
   (with or without brackets, with or without the group separator a scanner sends). */
const GS='\x1d';
const AI_FIXED={'00':18,'01':14,'02':14,'11':6,'12':6,'13':6,'15':6,'16':6,'17':6,'20':2};
const AI_VAR={'10':20,'21':20,'22':20,'30':8,'37':8,'240':30,'241':30,'90':30,'91':90,'92':90,'93':90,'94':90,'95':90,'96':90,'97':90,'98':90,'99':90};
function gs1Date(s){const yy=+s.slice(0,2),mm=+s.slice(2,4);let dd=+s.slice(4,6);
  if(mm<1||mm>12)return null;const now=new Date().getFullYear()%100;let y=2000+yy;if(yy-now>50)y-=100;if(yy-now<-49)y+=100;
  if(dd===0)dd=new Date(Date.UTC(y,mm,0)).getUTCDate();
  return `${y}-${String(mm).padStart(2,'0')}-${String(dd).padStart(2,'0')}`}
function parseScan(raw){
  let s=String(raw).replace(/[\r\n]/g,'').trim();
  s=s.replace(/^\][A-Za-z]\d/,'');                       // symbology prefix like ]C1 ]d2 ]Q3
  s=s.replace(/<GS>|\{GS\}|\^\]|~1/g,GS);                 // separator written out by some scanners
  const out={raw:String(raw).trim(),fields:{}};
  if(/^https?:\/\//i.test(s)){                            // GS1 Digital Link QR code
    try{const u=new URL(s);const parts=u.pathname.split('/').filter(Boolean);
      for(let k=0;k<parts.length-1;k++)if(/^\d{2,4}$/.test(parts[k])&&(AI_FIXED[parts[k]]!==undefined||AI_VAR[parts[k]]!==undefined)){out.fields[parts[k]]=decodeURIComponent(parts[k+1]);k++}
      u.searchParams.forEach((v,k)=>{if(/^\d{2,4}$/.test(k))out.fields[k]=v});}catch(e){}
  }else if(/^\(\d{2,4}\)/.test(s)){                       // bracketed human-readable form
    for(const m of s.matchAll(/\((\d{2,4})\)([^(]*)/g))out.fields[m[1]]=m[2].trim();
  }else if(/^\d{8}$|^\d{12,14}$/.test(s)){                // plain retail barcode
    out.fields['01']=s.padStart(14,'0');out.plain=true;
  }else{
    let i=0,guard=0;
    while(i<s.length&&guard++<20){
      if(s[i]===GS){i++;continue}
      let ai=null;
      for(const len of [2,3,4]){const c=s.slice(i,i+len);if(AI_FIXED[c]!==undefined||AI_VAR[c]!==undefined){ai=c;break}}
      if(!ai&&/^3[1-6]\d\d/.test(s.slice(i,i+4))){ai=s.slice(i,i+4);i+=4;out.fields[ai]=s.slice(i,i+6);i+=6;continue}
      if(!ai)break;
      i+=ai.length;
      if(AI_FIXED[ai]!==undefined){out.fields[ai]=s.slice(i,i+AI_FIXED[ai]);i+=AI_FIXED[ai]}
      else{let end=s.indexOf(GS,i);if(end<0)end=s.length;end=Math.min(end,i+AI_VAR[ai]);out.fields[ai]=s.slice(i,end);i=end}
    }
  }
  const f=out.fields;
  out.gtin=(f['01']||f['02']||'').replace(/^0+(?=\d{13}$)/,'')||null;  // store as 13 digits where possible
  out.batch=f['10']||null;
  out.expiry=f['17']?gs1Date(f['17']):f['15']?gs1Date(f['15']):f['16']?gs1Date(f['16']):null;
  out.expiryKind=f['17']?'Use by':f['15']?'Best before':f['16']?'Sell by':null;
  out.produced=f['11']?gs1Date(f['11']):null;
  out.qty=f['37']?Number(f['37']):f['30']?Number(f['30']):null;
  out.weightLooksPrice=out.gtin&&/^2/.test(out.gtin)&&out.plain;
  out.ok=!!(out.gtin||out.batch||out.expiry);
  return out;
}

const $ = s => document.querySelector(s);
const esc = v => String(v ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const store = {get(k){try{return localStorage.getItem(k)}catch(e){return null}},set(k,v){try{v==null?localStorage.removeItem(k):localStorage.setItem(k,v)}catch(e){}}};
// Per-device preferences
const photosOn=()=>store.get('sdc_photos')==='1';
function updatePhotoBtn(){const b=document.getElementById('photoBtn');if(!b)return;b.textContent=photosOn()?'▣ Photos':'▢ Photos';b.setAttribute('aria-pressed',photosOn());}
function applyTheme(){const t=store.get('sdc_theme');const r=document.documentElement;if(t==='light'||t==='dark')r.dataset.theme=t;else r.removeAttribute('data-theme');}
function cycleTheme(){const order=['system','light','dark'];const cur=store.get('sdc_theme')||'system';const next=order[(order.indexOf(cur)+1)%3];store.set('sdc_theme',next==='system'?null:next);applyTheme();updateThemeBtn();}
function updateThemeBtn(){const b=$('#themeBtn');if(!b)return;const cur=store.get('sdc_theme')||'system';b.textContent=cur==='light'?'☀ Light':cur==='dark'?'☾ Dark':'◐ Auto';}
function flash(msg){const f=$('#flash');clearTimeout(flash.t);clearTimeout(undo.t);clearInterval(undo.i);f.textContent=msg;f.hidden=false;flash.t=setTimeout(()=>f.hidden=true,3000)}
const undo={t:null,i:null};
// A 10-second window to undo the action just taken.
function showUndo(msg,revertFn){
  const f=$('#flash');clearTimeout(flash.t);clearTimeout(undo.t);clearInterval(undo.i);
  let left=10;const paint=()=>{f.innerHTML=`<span>${esc(msg)}</span><button type="button" class="undo-btn">Undo (${left})</button>`;};
  paint();f.hidden=false;
  undo.i=setInterval(()=>{left--;if(left<=0){clearInterval(undo.i)}else paint()},1000);
  undo.t=setTimeout(()=>{f.hidden=true;clearInterval(undo.i)},10000);
  const btn=f.querySelector('.undo-btn');if(btn)btn.onclick=()=>{clearTimeout(undo.t);clearInterval(undo.i);f.hidden=true;revertFn()};
}
const MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
function daysLeft(exp){const [y,m,d]=exp.split('-').map(Number);const t=new Date();const a=Date.UTC(y,m-1,d),b=Date.UTC(t.getFullYear(),t.getMonth(),t.getDate());return Math.round((a-b)/86400000)}
function band(n){return n<=2?'crit':n<=7?'warn':'ok'}
function dueLabel(n){return n<0?`Expired ${-n} day${n===-1?'':'s'} ago`:n===0?'Expires today':n===1?'Expires tomorrow':`${n} days left`}
const pad=n=>String(n).padStart(2,'0');
function fmtTime(ms){const d=new Date(ms);return `${pad(d.getDate())} ${MON[d.getMonth()]} ${pad(d.getHours())}:${pad(d.getMinutes())}`}
const clock=ms=>{const d=new Date(ms);return `${pad(d.getHours())}:${pad(d.getMinutes())}`};
const STATUS={active:'On shelf',reduced:'On shelf',removed:'Removed',sold:'Sold through',void:'Deleted'};
const ACTION={logged:'logged',reduced:'reduced',removed:'removed from shelf',sold:'marked sold through',restored:'put back on shelf',void:'deleted (mistake)',adjusted:'changed the count'};
const ROLES={manager:'Manager',supervisor:'Supervisor',staff:'Floor staff'};
const RANK={staff:1,supervisor:2,manager:3};
const atLeast=r=>(RANK[S.me?.role]||1)>=RANK[r];
const isAdmin=()=>S.me?.role==='manager'; // managers, and the hidden owner who acts as one
const activeManagers=()=>S.staff.filter(s=>s.role==='manager'&&s.active!==false);
const liveItems=()=>S.items.filter(i=>i.status==='active'||i.status==='reduced');
const errText=e=>e?.code==='permission-denied'?'Your position doesn\'t allow that.':e?.code==='unavailable'||e?.code==='auth/network-request-failed'?'No connection. Try again when online.':'Something went wrong. Try again.';

/* ---------- morning and evening date checks ---------- */
// The day splits at 2pm: before that it's the morning check, after it the evening check.
const SPLIT_HOUR=14;
const ROUND={morning:'Morning check',evening:'Evening check'};
const currentRound=()=>new Date().getHours()<SPLIT_HOUR?'morning':'evening';
function roundWindow(round){const s=new Date();s.setHours(round==='morning'?0:SPLIT_HOUR,0,0,0);const e=new Date();e.setHours(round==='morning'?SPLIT_HOUR:24,0,0,0);return [s.getTime(),e.getTime()]}
const dueBy=round=>round==='morning'?(S.settings?.morningBy||'09:00'):(S.settings?.eveningBy||'20:00');
function roundCheck(s,round){const [a,b]=roundWindow(round);const h=(s.history||[]).filter(x=>x.at>=a&&x.at<b);return h[h.length-1]||null}
function pastDue(round){const [h,m]=dueBy(round).split(':').map(Number);const n=new Date();return n.getHours()*60+n.getMinutes()>h*60+m}
const activeSections=()=>S.sections.filter(s=>s.archived!==true).sort((a,b)=>(a.order??0)-(b.order??0)||a.name.localeCompare(b.name));
function roundState(round){const secs=activeSections();const rows=secs.map(s=>({s,c:roundCheck(s,round)}));return {rows,done:rows.filter(r=>r.c).length,total:rows.length}}
function updateBadges(){
  if(!S.me){document.title='Zedatechecker';return}
  const r=roundState(currentRound());const left=r.total-r.done;const exp=liveItems().filter(i=>daysLeft(i.expiry)<0).length;const total=left+exp;
  document.title=(total?`(${total}) `:'')+'Zedatechecker';
  try{total?navigator.setAppBadge?.(total):navigator.clearAppBadge?.()}catch(e){}
}

/* ---------- auth and data ---------- */
let unsubs=[];
function stopListeners(){unsubs.forEach(u=>{try{u()}catch(e){}});unsubs=[]}
function listen(ref,key,map){
  unsubs.push(onSnapshot(ref,snap=>{map(snap);S.loaded[key]=true;render()},err=>{
    if(err.code==='permission-denied'&&!S.owner)return;
    S.error='Lost connection to the list. Reload the page to reconnect.';render()}));
}
function startData(){
  listen(collection(fs,'staff'),'staff',s=>{S.staff=s.docs.map(d=>({id:d.id,...d.data()}));resolveMe()});
  listen(collection(fs,'items'),'items',s=>{S.items=s.docs.map(d=>({id:d.id,...d.data()}))});
  listen(collection(fs,'products'),'products',s=>{const m={};s.docs.forEach(d=>m[d.id]=d.data());S.products=m});
  listen(collection(fs,'sections'),'sections',s=>{S.sections=s.docs.map(d=>({id:d.id,...d.data()}))});
  listen(collection(fs,'feedback'),'feedback',s=>{S.feedback=s.docs.map(d=>({id:d.id,...d.data()})).sort((a,b)=>(b.at||0)-(a.at||0))});
}
function resolveMe(){
  if(S.owner){S.me={id:'admin',name:'Admin',role:'manager',owner:true};return}
  const st=S.member&&S.staff.find(x=>x.id===S.member.staffId);
  S.me=st&&st.active!==false?{...st,role:S.member.role}:null;
}
function boot(){
  applyTheme();
  if(location.hash==='#owner')S.showOwner=true;
  onAuthStateChanged(auth,u=>{
    stopListeners();Object.assign(S,{authUser:u,authChecked:true,owner:false,member:null,me:null,error:null,loaded:{},briefed:false,settings:null});
    if(!u){render();return}
    S.owner=!!OWNER_EMAIL&&u.email===OWNER_EMAIL.toLowerCase();
    unsubs.push(onSnapshot(doc(fs,'config','settings'),s=>{S.settings=s.exists()?s.data():null;S.loaded.settings=true;
      if(S.settings&&!S.loaded.started){S.loaded.started=true;startData()}render()},
      e=>{S.loaded.settings=true;S.error=e.code==='permission-denied'?'This login has been deactivated. Ask a manager to reactivate you.':'Could not reach the list. Check the connection and reload.';render()}));
    if(!S.owner){
      unsubs.push(onSnapshot(doc(fs,'members',u.uid),s=>{S.member=s.exists()?s.data():null;S.loaded.member=true;
        if(!S.member)S.error='This login has been deactivated. Ask a manager to reactivate you.';
        else if(S.error&&S.error.startsWith('This login'))S.error=null;
        resolveMe();render()},()=>{S.loaded.member=true;S.error='This login has been deactivated. Ask a manager to reactivate you.';render()}));
    }else{S.loaded.member=true;resolveMe()}
  });
  const net=()=>{const el=$('#netState');if(el)el.hidden=navigator.onLine};
  addEventListener('online',net);addEventListener('offline',net);net();
  setInterval(()=>{const a=document.activeElement;if(S.me&&!(a&&a.matches('input,textarea,select'))&&!cam)render()},60000);
}

/* ---------- render ---------- */
const TABS={today:'Today',log:'Log product',all:'All items',activity:'Activity',staff:'Staff'};
function render(){
  if(cam&&S.camOn&&S.tab==='log'&&document.getElementById('camBox'))return;
  const app=$('#app');
  const keep={};document.querySelectorAll('#app input,#app select,#app textarea').forEach(el=>{if(el.id&&el.type!=='password')keep[el.id]=el.value});
  const focused=document.activeElement&&document.activeElement.id;
  const top=$('#top');
  if(!S.authChecked)return;
  if(!S.authUser){top.hidden=true;app.innerHTML=loginView();restore(keep,focused);return}
  if(S.error){top.hidden=true;app.innerHTML=`<section class="view">${brand()}<div class="errbox">${esc(S.error)}</div><div><button class="btn" data-signout="1">Sign out</button></div></section>`;return}
  if(!S.loaded.settings||!S.loaded.member){app.innerHTML=`<section class="view">${brand()}<div class="empty">Loading…</div></section>`;return}
  if(!S.settings){top.hidden=true;app.innerHTML=S.owner?setupView():`<section class="view">${brand()}<div class="empty">The app hasn't been set up for this store yet. Ask your manager.</div><div><button class="btn" data-signout="1">Sign out</button></div></section>`;restore(keep,focused);return}
  if(!S.loaded.staff||!S.loaded.items||!S.loaded.sections||!S.me){app.innerHTML=`<section class="view">${brand()}<div class="empty">Loading the store's list…</div></section>`;return}
  top.hidden=false;
  const tabs=Object.keys(TABS).filter(t=>!(S.me.owner&&t==='log'));
  if(!tabs.includes(S.tab))S.tab='today';
  $('#tabs').innerHTML=tabs.map(t=>`<button role="tab" data-tab="${t}" aria-selected="${t===S.tab}">${TABS[t]}</button>`).join('');
  $('#whoName').textContent=S.me.name+' · '+ROLES[S.me.role||'staff'];updateThemeBtn();updatePhotoBtn();
  $('#storeName').textContent=S.settings.store||'';
  app.innerHTML={today:todayView,log:logView,all:allView,activity:activityView,staff:staffView}[S.tab]();
  restore(keep,focused);
  const lsel=$('#lf_loc');if(lsel&&lsel.value==='__other__'){const w=$('#locOtherWrap');if(w)w.hidden=false}
  updateBadges();
  if(!S.briefed){S.briefed=true;briefing()}
}
function restore(keep,focused){for(const id in keep){const el=document.getElementById(id);if(el)el.value=keep[id]}if(focused){const el=document.getElementById(focused);if(el)el.focus()}}
const LOGO='<svg class="mark" viewBox="0 0 32 32" aria-hidden="true"><rect y="3" width="32" height="29" rx="7" fill="var(--accent)"/><rect x="9" y="0.5" width="2.6" height="7" rx="1.3" fill="var(--accent)"/><rect x="20.4" y="0.5" width="2.6" height="7" rx="1.3" fill="var(--accent)"/><path d="M10 19 l4 4 l9 -10" fill="none" stroke="var(--accent-fg)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>';
const brand=()=>`<div class="brand"><span class="mark-wrap" data-stamp="1">${LOGO}</span> Zedatechecker</div>`;
function briefing(){
  if(S.me.owner)return;
  const round=currentRound(),r=roundState(round),exp=liveItems().filter(i=>daysLeft(i.expiry)<0).length;
  const parts=[];if(r.total-r.done)parts.push(`${r.total-r.done} section${r.total-r.done===1?'':'s'} left in the ${round} check`);if(exp)parts.push(`${exp} item${exp===1?'':'s'} to pull`);
  if(parts.length)flash(parts.join(', '));
}

/* ---------- views ---------- */
function loginView(){
  let recent=[];try{recent=JSON.parse(store.get('sdc_recent')||'[]')}catch(e){}
  if(S.showOwner)return `<section class="view">${brand()}
  <form class="panel" id="ownerForm"><label>Email<input id="ow_email" type="email" autocomplete="username" required></label>
    <label>Password<input id="ow_pass" type="password" autocomplete="current-password" required></label>
    <div id="loginErr"></div><button class="btn primary">Sign in</button></form>
  <div><button class="btn small" data-owner-close="1">Back</button></div></section>`;
  return `<section class="view">${brand()}
  <p class="note">Sign in with the username and PIN your manager gave you.</p>
  ${recent.length?`<div class="staffpick">${recent.map(u=>`<button type="button" data-recent="${esc(u)}">${esc(u)}</button>`).join('')}</div>`:''}
  <form class="panel" id="loginForm" autocomplete="off">
    <label>Username<input id="li_user" autocapitalize="none" autocorrect="off" spellcheck="false" required maxlength="20"></label>
    <label>PIN<input id="li_pin" type="password" class="pin" inputmode="numeric" maxlength="6" required autocomplete="off"></label>
    <div id="loginErr"></div><button class="btn primary">Sign in</button></form></section>`;
}
function setupView(){
  return `<section class="view">${brand()}
  <p class="note">First-time setup. Name the store and create the first manager login.</p>
  <form class="panel" id="setupForm" autocomplete="off">
    <label>Store name<input id="su_store" required maxlength="60" placeholder="e.g. Stepaside"></label>
    <div class="grid2">
      <label>Manager's name<input id="su_name" required maxlength="40"></label>
      <label>Username<input id="su_user" required maxlength="20" autocapitalize="none" placeholder="e.g. joel"></label>
      <label>PIN (4 to 6 digits)<input id="su_pin" type="password" class="pin" inputmode="numeric" maxlength="6" required></label>
    </div>
    <div id="suErr"></div><button class="btn primary">Create store and manager</button>
  </form>
  <div><button class="btn small" data-signout="1">Sign out</button></div></section>`;
}
function photoKeyFor(it){return it.gtin?String(it.gtin):('n_'+slug(it.product));}
function ensurePhoto(key){
  if(key in S.photos||S.photoReq[key])return;S.photoReq[key]=1;
  getDoc(doc(fs,'photos',key)).then(snap=>{S.photos[key]=snap.exists()?(snap.data().data||null):null;scheduleRender();}).catch(()=>{S.photos[key]=null;});
}
let _srt=null;function scheduleRender(){clearTimeout(_srt);_srt=setTimeout(()=>{if(!(cam&&S.camOn))render();},150);}
function itemPhoto(it){
  const prod=it.gtin?S.products[it.gtin]:S.products['n_'+slug(it.product)];
  const key=photoKeyFor(it);
  let src=prod&&prod.image;
  if(!src){ if(S.photos[key]===undefined){ensurePhoto(key);} else if(S.photos[key]){src=S.photos[key];} }
  if(src){
    return photosOn()
      ?`<a class="thumb" href="${esc(src)}" target="_blank" rel="noopener"><img src="${esc(src)}" alt="photo" loading="lazy"></a>`
      :`<a class="plink" href="${esc(src)}" target="_blank" rel="noopener">Photo</a>`;
  }
  if(S.me&&!S.me.owner) return `<button type="button" class="btn small ghost photo-add" data-addphoto="${esc(key)}">+ Photo</button>`;
  return '';
}
// Camera / file photo, shrunk on the device and stored in Firestore (no Firebase Storage needed).
let _fileInput=null;
function pickPhoto(key){
  S.photoTarget=key;
  if(!_fileInput){_fileInput=document.createElement('input');_fileInput.type='file';_fileInput.accept='image/*';_fileInput.setAttribute('capture','environment');_fileInput.style.display='none';_fileInput.addEventListener('change',onPhotoPicked);document.body.appendChild(_fileInput);}
  _fileInput.click();
}
function onPhotoPicked(e){
  const f=e.target.files&&e.target.files[0];e.target.value='';const key=S.photoTarget;
  if(!f||!key||S.me.owner)return;flash('Processing photo…');
  const img=new Image();const url=URL.createObjectURL(f);
  img.onerror=()=>{URL.revokeObjectURL(url);flash('Could not read that photo');};
  img.onload=()=>{URL.revokeObjectURL(url);
    const max=480;let w=img.width,h=img.height;const sc=Math.min(1,max/Math.max(w,h));w=Math.max(1,Math.round(w*sc));h=Math.max(1,Math.round(h*sc));
    const cv=document.createElement('canvas');cv.width=w;cv.height=h;cv.getContext('2d').drawImage(img,0,0,w,h);
    let data;try{data=cv.toDataURL('image/jpeg',0.6);}catch(err){flash('Could not process that photo');return;}
    if(data.length>380000){try{data=cv.toDataURL('image/jpeg',0.4);}catch(e){}}
    if(data.length>380000){flash('Photo too large, try a plainer shot');return;}
    S.photos[key]=data;const b=by();
    quickWrite(setDoc(doc(fs,'photos',key),{data,byName:b.byName||'Owner',at:b.at}),'Photo added');
    render();
  };
  img.src=url;
}
function qtyControl(it,live){
  if(!live||S.me.owner)return it.qty?`<span class="note">× ${esc(it.qty)}</span>`:'';
  return `<span class="qtywrap"><button type="button" class="qbtn" data-qtyminus="${it.id}" aria-label="Decrease count">&minus;</button><span class="qnum" data-qty="${it.id}">× ${esc(it.qty||0)}</span><button type="button" class="qbtn" data-qtyplus="${it.id}" aria-label="Increase count">+</button></span>`;
}
function itemCard(it){
  const n=daysLeft(it.expiry);const [y,m,d]=it.expiry.split('-');const live=it.status==='active'||it.status==='reduced';
  const b=live?band(n):'';const acts=!S.me.owner;
  return `<div class="item">
    <div class="datebox ${b==='ok'?'':b}"><div class="d">${+d}</div><div class="m">${MON[+m-1]} ${y.slice(2)}</div></div>
    <div class="name">${esc(it.product)} ${qtyControl(it,live)}</div>
    <div class="meta">${it.batch?`<span class="batch">${esc(it.batch)}</span>`:'<span class="nobatch">no batch</span>'}${it.location?`<span>${esc(it.location)}</span>`:''}
      ${itemPhoto(it)}
      ${live?`<span class="pill ${band(n)}">${dueLabel(n)}</span>`:`<span class="pill done">${STATUS[it.status]}</span>`}</div>
    <div class="meta"><span>Logged by ${esc(it.loggedByName)} · ${fmtTime(it.loggedAt)}</span>
      ${it.lastAction&&it.lastAction!=='logged'&&it.lastByName?`<span>Last: ${esc(it.lastByName)} ${ACTION[it.lastAction]||''} · ${fmtTime(it.lastAt)}</span>`:''}</div>
    ${it.notes?`<div class="note" style="grid-column:2">${esc(it.notes)}</div>`:''}
    ${acts?`<div class="actions" style="grid-column:1/-1">${live?`
      <button class="btn small danger" data-act="removed" data-id="${it.id}">Remove from shelf</button>
      <button class="btn small" data-act="sold" data-id="${it.id}">Sold through</button>
      <button class="btn small ghost" data-act="void" data-id="${it.id}">Delete entry</button>`:
      (it.status==='void'
        ? (atLeast('supervisor')?`<button class="btn small" data-act="restored" data-id="${it.id}">Undo delete</button>`:'')
        : (atLeast('supervisor')?`<button class="btn small" data-act="restored" data-id="${it.id}">Undo, put back on shelf</button>`:''))}</div>`:''}
  </div>`;
}
function roundPanel(round,active){
  const r=roundState(round);const late=pastDue(round);
  const pct=r.total?Math.round(r.done/r.total*100):0;const complete=r.total&&r.done===r.total;
  const sum=`<summary class="round-sum"><div class="round-head"><div><h2>${ROUND[round]}</h2><div class="note">${round==='morning'?'Before opening':'Before closing'}, due by ${esc(dueBy(round))}</div></div>
    <div class="round-count ${complete?'ok':late?'crit':'warn'}"><b>${r.done}</b>/${r.total}</div></div>
    <div class="meter" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100"><span style="width:${pct}%"></span></div></summary>`;
  if(!active){
    const missed=r.rows.filter(x=>!x.c).map(x=>x.s.name);
    return `<details class="panel round past">${sum}<div class="round-body"><div class="note">${complete?'All sections were checked.':`Not checked: ${missed.map(esc).join(', ')}`}</div></div></details>`;
  }
  return `<details class="panel round" ${complete?'':'open'}>${sum}
    <div class="round-body">
    ${complete?`<div class="okbox">All sections checked. Nice work.</div>`:''}
    <div class="checklist">${r.rows.map(({s,c})=>`<div class="check-row ${c?'done':late?'late':''}">
      <span class="tick" aria-hidden="true">${c?'&#10003;':''}</span>
      <div class="check-body"><b>${esc(s.name)}</b>
        <div class="note">${c?`Checked by ${esc(c.byName)} at ${clock(c.at)}${c.note?` · ${esc(c.note)}`:''}`:late?`Not checked, was due by ${esc(dueBy(round))}`:'Not checked yet'}</div>
        ${!c&&!S.me.owner?`<div class="actions" style="padding-top:6px">
          <input id="cn_${s.id}" placeholder="Note (optional), e.g. 2 pulled" maxlength="80" class="note-in">
          <button class="btn small primary" data-check="${s.id}">Checked</button></div>`:''}
      </div></div>`).join('')}</div></div>
  </details>`;
}
function todayView(){
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
    ${block('Expired, pull from shelf',exp,'Nothing past its date.')}
    ${block('Expiring in the next 2 days',soon,'Nothing due in the next 2 days.')}
    ${block('Expiring this week',week,'Nothing else due this week.')}
  </section>`;
}
function logView(){
  const prods=[...new Set(S.items.filter(i=>i.product).map(i=>i.product))].sort();
  const secs=activeSections();
  const otherLocs=[...new Set(S.items.map(i=>i.location).filter(Boolean))].filter(l=>!secs.some(x=>x.name===l)).sort();
  const sc=S.scan;const onShelf=sc&&sc.gtin?liveItems().filter(i=>i.gtin===sc.gtin):[];
  const lines=S.lines&&S.lines.length?S.lines:[{expiry:'',qty:''}];
  const unknown=sc&&sc.gtin&&!S.products[sc.gtin];
  const lookupNote=unknown?(sc.lookup==='busy'?'<div class="note">Looking up the name online…</div>'
    :sc.lookup==='done'?'<div class="note">Name suggested from Open Food Facts. Check it reads right before saving.</div>'
    :sc.lookup==='none'?"<div class=\"note\">No name found online. Type it once as Brand Product name and it's remembered.</div>":''):'';
  return `<section class="view"><h2>Log a product</h2>
  <div class="scan">
    <div class="head"><h3>Scan barcode</h3><span class="note">Pack barcode or supplier case label</span></div>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <input id="scan_in" autocomplete="off" placeholder="Scanner input, or type a barcode" aria-label="Barcode" style="flex:1 1 220px">
      <button type="button" class="btn primary" data-camera="1">${S.camOn?'Stop camera':'Scan with camera'}</button>
    </div>
    <div id="camBox" ${S.camOn?'':'hidden'}></div>
    ${sc?(sc.ok?`<div class="readout">
      ${sc.gtin?`<span><b>Product no.</b>${esc(sc.gtin)}</span>`:''}${sc.batch?`<span><b>Batch</b>${esc(sc.batch)}</span>`:''}
      ${sc.expiry?`<span><b>${sc.expiryKind}</b>${esc(sc.expiry)}</span>`:''}${sc.produced?`<span><b>Packed</b>${esc(sc.produced)}</span>`:''}
      ${sc.qty?`<span><b>Count</b>${esc(sc.qty)}</span>`:''}</div>
      ${lookupNote}
      ${sc.gtin&&S.products[sc.gtin]?'<div class="note">Product name filled from an earlier log.</div>':''}
      ${sc.expiry?'':'<div class="note">This barcode has no date in it, so enter the date from the pack.</div>'}
      ${sc.weightLooksPrice?`<div class="warnbox">This looks like an in-store weighed label. Its number changes with weight and price, so it won't match the same product next time.</div>`:''}
      ${onShelf.length?`<div class="warnbox">Already on the list: ${onShelf.map(i=>`${esc(i.batch||'no batch')} (use-by ${esc(i.expiry)})`).join(', ')}</div>`:''}`
      :`<div class="errbox">Couldn't read that barcode. Check it scanned fully, or type the details below.</div>`):''}
  </div>
  <form class="panel" id="logForm" autocomplete="off">
    <input type="hidden" id="lf_gtin">
    <label>Product<input id="lf_product" required maxlength="80" list="prodlist" placeholder="Brand Product name, e.g. Avonmore Fresh Milk 2L"></label>
    <datalist id="prodlist">${prods.map(p=>`<option value="${esc(p)}">`).join('')}</datalist>
    <div id="nameSug" class="namesug"></div>
    <div class="grid2">
      <label>Batch / lot code (optional)<input id="lf_batch" class="mono" maxlength="40" placeholder="L2731"></label>
      <label>Section<select id="lf_loc">
        <option value="">— choose —</option>
        ${secs.map(x=>`<option value="${esc(x.name)}">${esc(x.name)}</option>`).join('')}
        ${otherLocs.map(l=>`<option value="${esc(l)}">${esc(l)}</option>`).join('')}
        <option value="__other__">Other (type a new one)…</option>
      </select></label>
    </div>
    <div id="locOtherWrap" hidden><label>New section<input id="lf_loc_other" maxlength="40" placeholder="e.g. Chilled meats"></label></div>
    <div class="datelines">
      <div class="dl-head"><span>Use-by / best-before</span><span>Qty</span><span></span></div>
      <div id="dateLines">${lines.map((l,i)=>dlineRow(l,i,lines.length)).join('')}</div>
      <button type="button" class="btn small" data-addline="1">+ Add another date</button>
      <div class="note">One row per different date on the shelf. Each row is saved as its own entry under this product.</div>
    </div>
    <label>Notes (optional)<textarea id="lf_notes" rows="2" maxlength="200"></textarea></label>
    <div id="dupWarn"></div>
    <button class="btn primary">Save as ${esc(S.me.name)}</button>
  </form></section>`;
}
function dlineRow(l,i,total){
  return `<div class="dline">
    <input class="dl-exp" type="date" value="${esc(l.expiry||'')}" min="2020-01-01" aria-label="Use-by date">
    <input class="dl-qty" type="number" min="1" max="9999" value="${esc(l.qty||'')}" placeholder="Qty" aria-label="Quantity">
    ${total>1?`<button type="button" class="btn small ghost" data-delline="${i}" aria-label="Remove date">&times;</button>`:'<span></span>'}
  </div>`;
}
function readLines(){const dl=document.querySelectorAll('#dateLines .dline');
  return dl.length?[...dl].map(r=>({expiry:r.querySelector('.dl-exp').value,qty:r.querySelector('.dl-qty').value})):[{expiry:'',qty:''}];}
function allView(){
  const q=S.filter.q.trim().toLowerCase();const st=S.filter.status;
  let arr=S.items.filter(i=>{
    if(st==='active')return i.status==='active'||i.status==='reduced';
    if(st==='void')return i.status==='void';
    if(st==='all')return i.status!=='void';
    return i.status===st;
  });
  if(q)arr=arr.filter(i=>(i.product+' '+(i.batch||'')+' '+(i.gtin||'')+' '+(i.location||'')+' '+i.loggedByName).toLowerCase().includes(q));
  const order=new Map(activeSections().map((x,idx)=>[x.name,idx]));
  const groups=new Map();
  for(const it of arr){const key=it.location||'';if(!groups.has(key))groups.set(key,[]);groups.get(key).push(it)}
  const keys=[...groups.keys()].sort((a,b)=>{
    const oa=order.has(a)?order.get(a):(a?1000:2000),ob=order.has(b)?order.get(b):(b?1000:2000);
    return oa-ob||a.localeCompare(b);
  });
  const body=arr.length?keys.map(k=>{
    const items=groups.get(k).slice().sort((a,b)=>a.expiry.localeCompare(b.expiry));
    return `<div class="list"><h3>${k?esc(k):'No section'} (${items.length})</h3>${items.map(itemCard).join('')}</div>`;
  }).join(''):'<div class="empty">No items match.</div>';
  return `<section class="view"><h2>All items</h2>
    <div class="filters"><input id="f_q" type="search" placeholder="Search product, batch, barcode, section or name" value="${esc(S.filter.q)}">
    <select id="f_status">${[['active','On shelf'],['removed','Removed'],['sold','Sold through'],['void','Deleted'],['all','Everything']].map(([v,l])=>`<option value="${v}" ${st===v?'selected':''}>${l}</option>`).join('')}</select></div>
    <div class="note">${arr.length} item${arr.length===1?'':'s'}</div>
    ${body}</section>`;
}
function activityView(){
  const ev=[];
  for(const it of S.items)for(const h of (it.history||[]))if(h.byName){
    const canRestore=['removed','sold','void'].includes(h.action)&&it.status===h.action&&it.lastAt===h.at&&atLeast('supervisor')&&!S.me.owner;
    ev.push({at:h.at,byName:h.byName,restoreId:canRestore?it.id:null,html:`${esc(ACTION[h.action]||h.action)} <b>${esc(it.product)}</b> <span class="batch">${esc(it.batch||'no batch')}</span>`});
  }
  for(const s of S.sections)for(const h of (s.history||[]))if(h.byName)ev.push({at:h.at,byName:h.byName,html:`checked <b>${esc(s.name)}</b> <span class="note">${new Date(h.at).getHours()<SPLIT_HOUR?'morning':'evening'}${h.note?`, ${esc(h.note)}`:''}</span>`});
  ev.sort((a,b)=>b.at-a.at);
  const by={};for(const e of ev){if(e.at>Date.now()-7*86400000)by[e.byName]=(by[e.byName]||0)+1}
  return `<section class="view"><h2>Activity</h2>
    ${Object.keys(by).length?`<div class="panel"><h3>Last 7 days by person</h3><div class="tablewrap"><table><tbody>${Object.entries(by).sort((a,b)=>b[1]-a[1]).map(([n,c])=>`<tr><td>${esc(n)}</td><td style="text-align:right;font-variant-numeric:tabular-nums">${c} action${c===1?'':'s'}</td></tr>`).join('')}</tbody></table></div></div>`:''}
    <div class="log">${ev.length?ev.slice(0,120).map(e=>`<div class="row"><span class="t">${fmtTime(e.at)}</span><span><b>${esc(e.byName)}</b> ${e.html}${e.restoreId?` <button class="btn small" data-restore="${e.restoreId}">Put back</button>`:''}</span></div>`).join(''):'<div class="empty">No activity yet. Every log, removal and section check shows here with who did it and when.</div>'}</div></section>`;
}
function myPinForm(){
  return `<form class="panel" id="myPinForm" autocomplete="off"><h3>Change my PIN</h3>
    <div class="grid2"><label>Current PIN<input id="mp_old" type="password" class="pin" inputmode="numeric" maxlength="6" required autocomplete="current-password"></label>
    <label>New PIN (4 to 6 digits)<input id="mp_new" type="password" class="pin" inputmode="numeric" maxlength="6" required autocomplete="new-password"></label></div>
    <div id="mpErr"></div><button class="btn">Change PIN</button></form>`;
}
function feedbackPanel(){
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
}
function staffView(){
  // Floor staff and supervisors only manage their own PIN.
  if(!isAdmin())return `<section class="view"><h2>My account</h2>
    <div class="panel" style="gap:4px"><b>${esc(S.me.name)}</b><div class="note">@${esc(S.me.username)} · ${ROLES[S.me.role]}</div></div>
    ${feedbackPanel()}
    ${myPinForm()}</section>`;
  const list=[...S.staff].sort((a,b)=>(a.active===false)-(b.active===false)||RANK[b.role||'staff']-RANK[a.role||'staff']||a.name.localeCompare(b.name));
  const card=s=>{
    const role=s.role||'staff';const open=S.editStaff===s.id;const lastMgr=role==='manager'&&s.active!==false&&activeManagers().length<=1;
    return `<div class="panel" style="padding:12px 14px;gap:10px">
    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
      <b>${esc(s.name)}</b><span class="note">@${esc(s.username)}</span>${s.id===S.me.id?' <span class="note">(you)</span>':''}
      <span class="pill ${role==='manager'?'ok':role==='supervisor'?'warn':'done'}">${ROLES[role]}</span>
      ${s.active===false?'<span class="pill crit">Inactive</span>':''}
      <button class="btn small" style="margin-left:auto" data-staff-edit="${s.id}">${open?'Close':'Manage'}</button>
    </div>
    ${open?`<div style="display:grid;gap:12px">
      <div class="grid2">
        <label>Position<select id="role_${s.id}" ${lastMgr?'disabled':''}>${Object.entries(ROLES).map(([v,l])=>`<option value="${v}" ${v===role?'selected':''}>${l}</option>`).join('')}</select></label>
        <label>New PIN (blank to keep)<input id="rpin_${s.id}" type="password" class="pin" inputmode="numeric" maxlength="6" autocomplete="new-password"></label>
      </div>
      ${lastMgr?`<div class="note">${esc(s.name)} is the only manager, so their position can't change until someone else is made manager.</div>`:''}
      <div class="actions">
        <button class="btn small primary" data-staff-save="${s.id}">Save changes</button>
        ${s.id!==S.me.id&&!lastMgr?`<button class="btn small ${s.active===false?'':'danger'}" data-staff-toggle="${s.id}">${s.active===false?'Reactivate':'Deactivate'}</button>`:''}
      </div>
      ${(s.changes||[]).length?`<div class="log">${[...s.changes].reverse().slice(0,8).map(c=>`<div class="row"><span class="t">${fmtTime(c.at)}</span><span>${esc(c.text)}${c.byName?` <span class="note">by ${esc(c.byName)}</span>`:''}</span></div>`).join('')}</div>`:''}
    </div>`:''}
  </div>`};
  const secs=activeSections();
  return `<section class="view"><h2>Staff</h2>
  <div class="panel" style="gap:6px"><h3>What each position can do</h3>
    <div class="note"><b>Floor staff:</b> do the morning and evening checks, log products, remove from shelf, mark sold through.</div>
    <div class="note"><b>Supervisor:</b> all of that, plus undo a removal or sale made by mistake.</div>
    <div class="note"><b>Manager:</b> all of that, plus this Staff page: add people, change positions, reset PINs, deactivate staff, and set up sections and check times.</div>
    <div class="note">Floor staff and supervisors only see "Change my PIN" here.</div></div>
  <div class="list">${list.map(card).join('')}</div>
  <form class="panel" id="staffForm" autocomplete="off"><h3>Add a team member</h3>
    <div class="grid2"><label>Name<input id="sf_name" required maxlength="40" placeholder="e.g. Anna K"></label>
    <label>Username<input id="sf_user" required maxlength="20" autocapitalize="none" placeholder="e.g. annak"></label>
    <label>PIN (4 to 6 digits)<input id="sf_pin" type="password" class="pin" inputmode="numeric" maxlength="6" required autocomplete="new-password"></label>
    <label>Position<select id="sf_role">${Object.entries(ROLES).reverse().map(([v,l])=>`<option value="${v}">${l}</option>`).join('')}</select></label></div>
    <div id="sfErr"></div><button class="btn primary">Add to team</button>
    <p class="note">Give them their username and PIN in person. They can sign in on any phone and change their own PIN.</p></form>

  <h2 style="margin-top:8px">Date checks</h2>
  <form class="panel" id="timesForm"><h3>Check times</h3>
    <div class="grid2"><label>Morning check due by<input id="st_morning" type="time" value="${esc(dueBy('morning'))}" required></label>
    <label>Evening check due by<input id="st_evening" type="time" value="${esc(dueBy('evening'))}" required></label></div>
    <button class="btn">Save times</button></form>
  <div class="panel"><h3>Sections</h3>
    <p class="note">Every section is ticked off in both the morning and evening check. Anyone can also add a new section while logging a product, by choosing "Other" for the section.</p>
    ${secs.length?`<div class="seclist">${secs.map(s=>`<div class="secrow"><input id="sn_${s.id}" value="${esc(s.name)}" maxlength="40" aria-label="Section name">
      <button class="btn small" data-sec-save="${s.id}">Rename</button><button class="btn small danger" data-sec-archive="${s.id}">Remove</button></div>`).join('')}</div>`:'<div class="note">No sections yet.</div>'}
    <form id="sectionForm" class="secrow"><input id="sec_name" required maxlength="40" placeholder="New section, e.g. Dairy chiller" aria-label="New section name"><button class="btn small primary">Add section</button></form>
  </div>
  ${feedbackList()}
  ${feedbackPanel()}
  ${S.me.owner?'':myPinForm()}
  </section>`;
}

/* ---------- camera scanning ---------- */
let cam=null;
async function startCamera(){
  if(!window.Html5Qrcode){flash('Camera scanner didn\'t load. Check the connection.');return}
  S.camOn=true;render();
  const F=Html5QrcodeSupportedFormats;
  cam=new Html5Qrcode('camBox',{formatsToSupport:[F.EAN_13,F.EAN_8,F.UPC_A,F.UPC_E,F.CODE_128,F.DATA_MATRIX,F.QR_CODE,F.ITF],useBarCodeDetectorIfSupported:true,verbose:false});
  try{await cam.start({facingMode:'environment'},{fps:12,qrbox:(w,h)=>({width:Math.min(300,w*0.85),height:Math.min(180,h*0.5)})},
      text=>{stopCamera();if(navigator.vibrate)navigator.vibrate(60);applyScan(text)},()=>{})}
  catch(e){S.camOn=false;cam=null;render();flash('Camera blocked. Allow camera access for this site in the browser settings.')}
}
async function stopCamera(){const c=cam;cam=null;S.camOn=false;if(c){try{await c.stop()}catch(e){}try{c.clear()}catch(e){}}render()}

/* ---------- product name lookup (Open Food Facts, free and open) ---------- */
async function offFetch(gtin){
  const c=new AbortController();const t=setTimeout(()=>c.abort(),6000);
  try{const r=await fetch(`https://world.openfoodfacts.org/api/v2/product/${encodeURIComponent(gtin)}.json?fields=product_name,brands,quantity,image_front_small_url,image_url`,{signal:c.signal,headers:{Accept:'application/json'}});
    if(!r.ok)return null;const j=await r.json();if(j.status!==1||!j.product)return null;const p=j.product;
    const brand=(p.brands||'').split(',')[0].trim();const nm=(p.product_name||'').trim();
    const name=[brand,nm,(p.quantity||'').trim()].filter(Boolean).join(' ').replace(/\s+/g,' ').slice(0,80)||null;
    const image=(p.image_front_small_url||p.image_url||'').trim()||null;
    if(!name&&!image)return null;
    return {name,image};
  }catch(e){return null}finally{clearTimeout(t)}
}
async function lookupName(gtin){
  if(window.__offStub)return window.__offStub(gtin);
  if(gtin in S.offCache)return S.offCache[gtin];
  const r=await offFetch(gtin);S.offCache[gtin]=r;return r;
}
const normName=v=>String(v||'').trim().toLowerCase();
const slug=v=>normName(v).replace(/[^a-z0-9]+/g,'-').replace(/^-+|-+$/g,'').slice(0,60)||'x';
// Search the open database by typed name, for autofill + photos.
async function offSearch(q){
  if(window.__offSearchStub)return window.__offSearchStub(q);
  const c=new AbortController();const t=setTimeout(()=>c.abort(),6000);
  try{const url=`https://world.openfoodfacts.org/cgi/search.pl?search_terms=${encodeURIComponent(q)}&search_simple=1&action=process&json=1&page_size=8&fields=product_name,brands,quantity,image_front_small_url`;
    const r=await fetch(url,{signal:c.signal,headers:{Accept:'application/json'}});
    if(!r.ok)return [];const j=await r.json();const out=[];const seen=new Set();
    for(const p of (j.products||[])){
      const brand=(p.brands||'').split(',')[0].trim();const nm=(p.product_name||'').trim();
      const name=[brand,nm,(p.quantity||'').trim()].filter(Boolean).join(' ').replace(/\s+/g,' ').slice(0,80);
      const image=(p.image_front_small_url||'').trim()||null;
      if(name&&!seen.has(normName(name))){seen.add(normName(name));out.push({name,image})}
      if(out.length>=5)break;
    }
    return out;
  }catch(e){return []}finally{clearTimeout(t)}
}
function scheduleNameSearch(q){
  clearTimeout(S.sugTimer);const v=(q||'').trim();
  if(v.length<3){const el=$('#nameSug');if(el)el.innerHTML='';return}
  S.sugTimer=setTimeout(async()=>{
    const list=await offSearch(v);
    list.forEach(x=>{if(x.image)S.nameImg[normName(x.name)]=x.image});
    const dl=$('#prodlist');if(dl){const have=new Set([...dl.options].map(o=>o.value));list.forEach(x=>{if(!have.has(x.name)){const o=document.createElement('option');o.value=x.name;dl.appendChild(o)}})}
    const el=$('#nameSug');if(!el)return;
    el.innerHTML=list.length?`<div class="note">From the product database:</div>`+list.slice(0,4).map(x=>`<button type="button" class="sug" data-usesug="${esc(x.name)}" data-img="${esc(x.image||'')}">${x.image?`<img src="${esc(x.image)}" alt="" loading="lazy">`:'<span class="noimg"></span>'}<span>${esc(x.name)}</span></button>`).join(''):'';
  },450);
}

/* ---------- scanning ---------- */
function applyScan(raw){
  if(!raw||!raw.trim()||S.me?.owner)return;
  const sc=parseScan(raw);S.scan=sc;S.tab='log';
  const known=sc.gtin&&S.products[sc.gtin];
  S.lines=[{expiry:sc.expiry||'',qty:sc.qty||''}];
  render();
  if(!sc.ok){$('#scan_in')?.focus();return}
  const set=(id,v)=>{const el=$('#'+id);if(el&&v!=null&&v!=='')el.value=v};
  set('lf_gtin',sc.gtin);set('lf_batch',sc.batch);
  if(known){set('lf_product',known.name);sc.image=known.image||null;}
  if(sc.gtin&&!known&&(window.__offStub||navigator.onLine)){
    sc.lookup='busy';render();
    lookupName(sc.gtin).then(res=>{
      const name=res&&res.name;sc.image=res&&res.image||null;
      sc.lookup=(name||sc.image)?'done':'none';
      const pe=$('#lf_product');if(name&&pe&&!pe.value)pe.value=name;
      if(S.tab==='log')render();
    });
  }
  const pe=$('#lf_product');(pe&&!pe.value?pe:document.querySelector('.dl-exp'))?.focus();
  checkDup();
}
let kb={buf:'',last:0};
document.addEventListener('keydown',e=>{
  if(!S.me)return;
  const tag=(e.target.tagName||'').toLowerCase();
  if(e.target.id==='scan_in'){if(e.key==='Enter'){e.preventDefault();const v=e.target.value;e.target.value='';applyScan(v)}return}
  if(tag==='input'||tag==='textarea'||tag==='select')return;
  const now=performance.now();if(now-kb.last>80)kb.buf='';kb.last=now;
  if(e.key==='Enter'){if(kb.buf.length>=8){e.preventDefault();applyScan(kb.buf)}kb.buf='';return}
  if(e.key.length===1)kb.buf+=e.key;
});
function checkDup(){
  const pe=$('#lf_product'),be=$('#lf_batch'),dw=$('#dupWarn');if(!pe||!be||!dw)return;
  const p=pe.value.trim().toLowerCase(),b=be.value.trim().toUpperCase();
  const dup=p&&b&&liveItems().find(i=>i.product.toLowerCase()===p&&(i.batch||'')===b);
  dw.innerHTML=dup?`<div class="warnbox">This batch is already on the list, logged by ${esc(dup.loggedByName)} on ${fmtTime(dup.loggedAt)}, use-by ${esc(dup.expiry)}. Save anyway only if it's separate stock.</div>`:'';
}

/* ---------- writes ---------- */
// Everyday writes save on the device immediately and sync later, so they never wait on the network.
function quickWrite(p,ok){if(ok)flash(navigator.onLine?ok:ok+' (will sync when back online)');p.catch(e=>flash('Not saved: '+errText(e)))}
// Admin actions are logged without a name, so nothing in the app reveals the admin login.
const by=()=>S.me.owner?{by:'admin',byName:'',at:Date.now()}:{by:S.me.id,byName:S.me.name,at:Date.now()};
const UNDOABLE=['removed','sold','void'];
function setItemStatus(id,act){
  const it=S.items.find(i=>i.id===id);if(!it||S.me.owner)return;
  if(act==='restored'&&!atLeast('supervisor')){flash('Ask a supervisor or manager to undo this');return}
  const prevStatus=it.status,prevHistory=(it.history||[]).slice();
  const status=act==='restored'?'active':act;const b=by();
  const history=[...(it.history||[]),{action:act,...b}].slice(-30);
  quickWrite(updateDoc(doc(fs,'items',id),{status,history,lastAction:act,lastBy:b.by,lastByName:b.byName,lastAt:b.at}),
    UNDOABLE.includes(act)?null:`${it.product}: ${ACTION[act]}`);
  if(UNDOABLE.includes(act))showUndo(`${it.product}: ${ACTION[act]}`,()=>revertItem(id,prevStatus,prevHistory));
}
// Put the item back exactly as it was (used by the 10-second undo).
function revertItem(id,status,history){
  const last=history.length?history[history.length-1]:{action:'logged'};const b=by();
  quickWrite(updateDoc(doc(fs,'items',id),{status,history,lastAction:last.action,lastBy:b.by,lastByName:b.byName,lastAt:b.at}),'Undone');
}
// +/- shelf count beside an item. Taps are coalesced into one write after a short pause.
const qtyTimers={},qtyPending={};
function adjustQty(id,delta){
  const it=S.items.find(i=>i.id===id);if(!it||S.me.owner)return;
  const base=qtyPending[id]!=null?qtyPending[id]:(Number(it.qty)||0);
  const next=Math.max(0,base+delta);qtyPending[id]=next;it.qty=next;
  const span=document.querySelector(`[data-qty="${id}"]`);if(span)span.textContent='× '+next;
  clearTimeout(qtyTimers[id]);
  qtyTimers[id]=setTimeout(()=>{const v=qtyPending[id];delete qtyPending[id];const b=by();
    quickWrite(updateDoc(doc(fs,'items',id),{qty:v,lastAction:'adjusted',lastBy:b.by,lastByName:b.byName,lastAt:b.at}),null);},700);
}
function checkSection(id){
  const s=S.sections.find(x=>x.id===id);if(!s||S.me.owner)return;
  const note=($('#cn_'+id)?.value||'').trim().slice(0,80);const b=by();
  const lastCheck={...b,note};
  quickWrite(updateDoc(doc(fs,'sections',id),{lastCheck,history:[...(s.history||[]),lastCheck].slice(-60)}),`${s.name} checked`);
  const r=roundState(currentRound());if(r.total&&r.done+1>=r.total&&!roundCheck(s,currentRound()))setTimeout(()=>flash(`${ROUND[currentRound()]} complete`),1200);
}
const logChange=(s,text)=>[...(s.changes||[]),{text,...by()}].slice(-20);

async function addStaff(){
  const name=$('#sf_name').value.trim(),username=$('#sf_user').value.trim().toLowerCase(),pin=$('#sf_pin').value,role=$('#sf_role').value;
  const err=m=>{$('#sfErr').innerHTML=`<div class="errbox">${m}</div>`};
  if(!USERNAME_RE.test(username))return err('Username must be 2 to 20 characters: lowercase letters, numbers, dot, dash or underscore.');
  if(!PIN_RE.test(pin))return err('PIN must be 4 to 6 digits.');
  if(!navigator.onLine)return err('Adding people needs a connection.');
  const btn=$('#staffForm button.primary');btn.disabled=true;
  try{
    const taken=await getDoc(doc(fs,'logins',username));if(taken.exists()){btn.disabled=false;return err('That username is taken. Try adding an initial or number.')}
    const uid=await createLogin(username,1,pin);
    const sref=doc(collection(fs,'staff'));const b=writeBatch(fs);
    b.set(sref,{name,username,role,active:true,authUid:uid,gen:1,createdAt:Date.now(),changes:[{text:`Added as ${ROLES[role]}`,...by()}]});
    b.set(doc(fs,'members',uid),{staffId:sref.id,role,username});
    b.set(doc(fs,'logins',username),{gen:1});
    await b.commit();flash(`${name} added. Username: ${username}`);
    ['sf_name','sf_user','sf_pin'].forEach(i=>{const el=$('#'+i);if(el)el.value=''});$('#sfErr').innerHTML='';
  }catch(e){err(e.code==='auth/email-already-in-use'?'That username is taken. Try another.':errText(e))}
  btn.disabled=false;
}
async function saveStaff(id,btn){
  if(!isAdmin())return;
  const s=S.staff.find(x=>x.id===id);if(!s)return;
  const newRole=$('#role_'+id).value,pin=$('#rpin_'+id).value.trim();const notes=[];
  const b=writeBatch(fs);const patch={};
  if(newRole!==(s.role||'staff')){
    if(s.role==='manager'&&activeManagers().length<=1){flash('Keep at least one active manager');return}
    patch.role=newRole;notes.push(`Position changed from ${ROLES[s.role||'staff']} to ${ROLES[newRole]}`);
    if(s.active!==false)b.update(doc(fs,'members',s.authUid),{role:newRole});
  }
  if(pin){
    if(!PIN_RE.test(pin)){flash('PIN must be 4 to 6 digits');return}
    if(!navigator.onLine){flash('Resetting a PIN needs a connection');return}
    btn.disabled=true;
    try{const gen=(s.gen||1)+1;const uid=await createLogin(s.username,gen,pin);
      patch.authUid=uid;patch.gen=gen;
      b.delete(doc(fs,'members',s.authUid));
      if(s.active!==false)b.set(doc(fs,'members',uid),{staffId:s.id,role:patch.role||s.role,username:s.username});
      b.set(doc(fs,'logins',s.username),{gen});notes.push('PIN reset');
    }catch(e){btn.disabled=false;flash(errText(e));return}
  }
  if(!notes.length){flash('Nothing changed');return}
  let ch=s;for(const n of notes)ch={...ch,changes:logChange(ch,n)};patch.changes=ch.changes;
  b.update(doc(fs,'staff',id),patch);
  btn.disabled=true;
  try{await b.commit();flash(`${s.name}: ${notes.join(', ').toLowerCase()}`);const pe=$('#rpin_'+id);if(pe)pe.value=''}catch(e){flash(errText(e))}
  btn.disabled=false;
}
async function toggleStaff(id){
  const s=S.staff.find(x=>x.id===id);if(!s||!isAdmin()||s.id===S.me.id)return;
  if(s.active!==false&&s.role==='manager'&&activeManagers().length<=1){flash('Keep at least one active manager');return}
  const reactivate=s.active===false;const b=writeBatch(fs);
  if(reactivate)b.set(doc(fs,'members',s.authUid),{staffId:s.id,role:s.role,username:s.username});else b.delete(doc(fs,'members',s.authUid));
  b.update(doc(fs,'staff',id),{active:reactivate,changes:logChange(s,reactivate?'Reactivated':'Deactivated')});
  try{await b.commit();flash(`${s.name} ${reactivate?'reactivated':'deactivated'}`)}catch(e){flash(errText(e))}
}
function rememberUser(u){let r=[];try{r=JSON.parse(store.get('sdc_recent')||'[]')}catch(e){}r=[u,...r.filter(x=>x!==u)].slice(0,6);store.set('sdc_recent',JSON.stringify(r))}

/* ---------- events ---------- */
document.addEventListener('click',e=>{
  // Five taps on the BB badge on the sign-in screen opens the admin sign-in.
  if(e.target.closest('[data-stamp]')&&!S.authUser){S.ownerTaps++;clearTimeout(S.tapT);S.tapT=setTimeout(()=>S.ownerTaps=0,2500);if(S.ownerTaps>=5){S.ownerTaps=0;S.showOwner=true;render()}return}
  const t=e.target.closest('button');if(!t)return;
  const d=t.dataset;
  if(d.camera){cam?stopCamera():startCamera();return}
  if(d.usesug){const pe=$('#lf_product');if(pe)pe.value=d.usesug;if(d.img)S.nameImg[normName(d.usesug)]=d.img;const el=$('#nameSug');if(el)el.innerHTML='';checkDup();pe?.focus();return}
  if(d.addphoto){if(!S.me.owner)pickPhoto(d.addphoto);return}
  if(d.signout||t.id==='signOutBtn'){if(cam)stopCamera();signOut(auth);return}
  if(t.id==='themeBtn'){cycleTheme();return}
  if(t.id==='photoBtn'){store.set('sdc_photos',photosOn()?null:'1');render();return}
  if(t.id==='fbMail'){const m=$('#fb_msg')?.value||'';if(FEEDBACK_EMAIL)location.href=`mailto:${FEEDBACK_EMAIL}?subject=${encodeURIComponent('Shelf Date Check suggestion')}&body=${encodeURIComponent(m)}`;return}
  if(d.fbdel){if(isAdmin())quickWrite(deleteDoc(doc(fs,'feedback',d.fbdel)),'Dismissed');return}
  if(d.restore){setItemStatus(d.restore,'restored');return}
  if(d.ownerClose){S.showOwner=false;render();return}
  if(d.recent){$('#li_user').value=d.recent;$('#li_pin').focus();return}
  if(d.tab&&cam)stopCamera();
  if(d.tab){S.tab=d.tab;window.scrollTo(0,0);render();if(S.tab==='log')$('#scan_in')?.focus();return}
  if(d.qtyplus){adjustQty(d.qtyplus,1);return}
  if(d.qtyminus){adjustQty(d.qtyminus,-1);return}
  if(d.act){t.disabled=true;setItemStatus(d.id,d.act);return}
  if(d.check){t.disabled=true;checkSection(d.check);return}
  if(d.addline){S.lines=readLines();S.lines.push({expiry:'',qty:''});render();return}
  if(d.delline!==undefined){S.lines=readLines();S.lines.splice(+d.delline,1);if(!S.lines.length)S.lines=[{expiry:'',qty:''}];render();return}
  if(d.secSave){const name=$('#sn_'+d.secSave).value.trim();if(name)quickWrite(updateDoc(doc(fs,'sections',d.secSave),{name}),'Section renamed');return}
  if(d.secArchive){const s=S.sections.find(x=>x.id===d.secArchive);quickWrite(updateDoc(doc(fs,'sections',d.secArchive),{archived:true}),`${s?.name||'Section'} removed`);return}
  if(d.staffEdit){S.editStaff=S.editStaff===d.staffEdit?null:d.staffEdit;render();return}
  if(d.staffSave){saveStaff(d.staffSave,t);return}
  if(d.staffToggle){toggleStaff(d.staffToggle);return}
});
document.addEventListener('input',e=>{
  if(e.target.id==='f_q'){S.filter.q=e.target.value;render()}
  if(e.target.id==='lf_product'||e.target.id==='lf_batch')checkDup();
  if(e.target.id==='lf_product')scheduleNameSearch(e.target.value);
  if(e.target.classList&&(e.target.classList.contains('dl-exp')||e.target.classList.contains('dl-qty')))S.lines=readLines();
});
document.addEventListener('change',e=>{
  if(e.target.id==='f_status'){S.filter.status=e.target.value;render()}
  if(e.target.id==='lf_loc'){const w=$('#locOtherWrap');if(w){w.hidden=e.target.value!=='__other__';if(e.target.value==='__other__')$('#lf_loc_other')?.focus()}}
});
document.addEventListener('submit',async e=>{
  e.preventDefault();const f=e.target;const btn=f.querySelector('button.primary')||f.querySelector('button');
  if(f.id==='loginForm'){
    const u=$('#li_user').value.trim().toLowerCase(),pin=$('#li_pin').value;const err=m=>{$('#loginErr').innerHTML=`<div class="errbox">${m}</div>`};
    if(!USERNAME_RE.test(u)||!PIN_RE.test(pin))return err('Check the username and PIN.');
    btn.disabled=true;
    try{const l=await getDoc(doc(fs,'logins',u));if(!l.exists()){btn.disabled=false;$('#li_pin').value='';return err('Username or PIN is wrong.')}
      await signInWithEmailAndPassword(auth,staffEmail(u,l.data().gen||1),staffPassword(u,pin));rememberUser(u);S.tab='today';
    }catch(ex){btn.disabled=false;$('#li_pin').value='';
      err(ex.code==='auth/too-many-requests'?'Too many tries. Wait a few minutes, or ask a manager to reset your PIN.':ex.code==='auth/network-request-failed'||ex.code==='unavailable'?'No connection. Connect to Wi-Fi and try again.':'Username or PIN is wrong.')}
    return;
  }
  if(f.id==='ownerForm'){
    btn.disabled=true;
    try{await signInWithEmailAndPassword(auth,$('#ow_email').value.trim(),$('#ow_pass').value);S.showOwner=false}
    catch(ex){btn.disabled=false;$('#loginErr').innerHTML=`<div class="errbox">${ex.code==='auth/network-request-failed'?'No connection.':'Email or password is wrong.'}</div>`}
    return;
  }
  if(f.id==='setupForm'){
    const store_=$('#su_store').value.trim(),name=$('#su_name').value.trim(),username=$('#su_user').value.trim().toLowerCase(),pin=$('#su_pin').value;
    const err=m=>{$('#suErr').innerHTML=`<div class="errbox">${m}</div>`};
    if(!USERNAME_RE.test(username))return err('Username must be 2 to 20 characters: lowercase letters, numbers, dot, dash or underscore.');
    if(!PIN_RE.test(pin))return err('PIN must be 4 to 6 digits.');
    btn.disabled=true;
    try{const uid=await createLogin(username,1,pin);const sref=doc(collection(fs,'staff'));const now=Date.now();const b=writeBatch(fs);
      b.set(sref,{name,username,role:'manager',active:true,authUid:uid,gen:1,createdAt:now,changes:[{text:'Added as Manager',by:'admin',byName:'',at:now}]});
      b.set(doc(fs,'members',uid),{staffId:sref.id,role:'manager',username});
      b.set(doc(fs,'logins',username),{gen:1});
      b.set(doc(fs,'config','settings'),{store:store_,morningBy:'09:00',eveningBy:'20:00',createdAt:now});
      // Starting sections for the store (every one is checked both morning and evening).
      ['Aisle 1','Fresh herbs','Pre-made sandwiches & sushi','Pizza fridge 1','Pizza fridge 2','Spider fridge','Bread']
        .forEach((secName,i)=>b.set(doc(collection(fs,'sections')),{name:secName,archived:false,order:i,createdAt:now,createdBy:name,history:[]}));
      await b.commit();rememberUser(username);
      flash(`Store set up. Now sign in as ${username}.`);await signOut(auth);
    }catch(ex){btn.disabled=false;err(ex.code==='auth/email-already-in-use'?'That username is taken.':errText(ex))}
    return;
  }
  if(f.id==='logForm'){
    const product=$('#lf_product').value.trim();
    const selv=$('#lf_loc').value;const location=(selv==='__other__'?($('#lf_loc_other')?.value||''):selv).trim();
    const batch=$('#lf_batch').value.trim().toUpperCase();const notes=$('#lf_notes').value.trim();const gtin=$('#lf_gtin').value||null;
    const lines=readLines().filter(l=>l.expiry);
    if(!product){flash('Add a product name');return}
    if(!lines.length){flash('Add at least one use-by date');return}
    btn.disabled=true;const bch=writeBatch(fs);const b=by();
    for(const l of lines){const ref=doc(collection(fs,'items'));
      bch.set(ref,{product,gtin,batch,expiry:l.expiry,qty:l.qty?Number(l.qty):null,location,notes,
        status:'active',loggedBy:b.by,loggedByName:b.byName,loggedAt:b.at,lastAction:'logged',lastBy:b.by,lastByName:b.byName,lastAt:b.at,
        history:[{action:'logged',...b}]});}
    if(gtin&&!/^2/.test(gtin)){
      const img=(S.scan&&S.scan.gtin===gtin&&S.scan.image)||S.products[gtin]?.image||null;
      if(S.products[gtin]?.name!==product||(img&&S.products[gtin]?.image!==img))
        bch.set(doc(fs,'products',gtin),{name:product,image:img,byName:b.byName,updatedAt:b.at});
    }else if(!gtin){
      const key='n_'+slug(product);const img=S.nameImg[normName(product)]||S.products[key]?.image||null;
      if(img&&S.products[key]?.image!==img)
        bch.set(doc(fs,'products',key),{name:product,image:img,byName:b.byName,updatedAt:b.at});
    }
    let newSection=false;
    if(location&&selv==='__other__'&&!activeSections().some(x=>x.name.toLowerCase()===location.toLowerCase())){
      bch.set(doc(collection(fs,'sections')),{name:location,archived:false,order:Date.now(),createdAt:b.at,createdBy:b.byName||'staff',history:[]});
      newSection=true;
    }
    quickWrite(bch.commit(),`Saved ${lines.length} ${lines.length===1?'entry':'entries'}: ${product}${newSection?` · new section "${location}" added`:''}`);
    S.scan=null;S.lines=[{expiry:'',qty:''}];const sg=$('#nameSug');if(sg)sg.innerHTML='';
    ['lf_product','lf_gtin','lf_batch','lf_notes'].forEach(id=>{const el=$('#'+id);if(el)el.value=''});
    render();$('#scan_in')?.focus();return;
  }
  if(f.id==='sectionForm'){
    const name=$('#sec_name').value.trim();if(!name)return;
    if(activeSections().some(s=>s.name.toLowerCase()===name.toLowerCase())){flash('There is already a section with that name');return}
    quickWrite(addDoc(collection(fs,'sections'),{name,archived:false,order:Date.now(),createdAt:Date.now(),history:[]}),`${name} added`);
    $('#sec_name').value='';return;
  }
  if(f.id==='timesForm'){
    const m=$('#st_morning').value,ev=$('#st_evening').value;if(!m||!ev)return;
    quickWrite(updateDoc(doc(fs,'config','settings'),{morningBy:m,eveningBy:ev}),'Check times saved');return;
  }
  if(f.id==='staffForm'){addStaff();return}
  if(f.id==='feedbackForm'){
    const msg=$('#fb_msg').value.trim();if(!msg){$('#fbErr').innerHTML='<div class="errbox">Type your idea first.</div>';return}
    const b=by();
    quickWrite(addDoc(collection(fs,'feedback'),{message:msg.slice(0,1000),byName:b.byName||'Owner',role:S.me.role,at:b.at,version:'1.3'}),'Thanks, sent to Oz7y');
    if(FEEDBACK_ENDPOINT){try{fetch(FEEDBACK_ENDPOINT,{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json'},body:JSON.stringify({message:msg,from:b.byName||'Owner',role:S.me.role})}).catch(()=>{})}catch(e){}}
    $('#fb_msg').value='';$('#fbErr').innerHTML='';render();return;
  }
  if(f.id==='myPinForm'){
    const o=$('#mp_old').value,n=$('#mp_new').value;const err=m=>{$('#mpErr').innerHTML=`<div class="errbox">${m}</div>`};
    if(!PIN_RE.test(n))return err('New PIN must be 4 to 6 digits.');
    btn.disabled=true;
    try{await reauthenticateWithCredential(auth.currentUser,EmailAuthProvider.credential(auth.currentUser.email,staffPassword(S.me.username,o)));
      await updatePassword(auth.currentUser,staffPassword(S.me.username,n));
      $('#mp_old').value='';$('#mp_new').value='';$('#mpErr').innerHTML='';flash('PIN changed');
    }catch(ex){err(ex.code==='auth/wrong-password'||ex.code==='auth/invalid-credential'?'Current PIN is wrong.':errText(ex))}
    btn.disabled=false;return;
  }
});
boot();
