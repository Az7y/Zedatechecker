# -*- coding: utf-8 -*-
P='public/app.js'; s=open(P,encoding='utf-8').read()
def rep(a,b,n=1):
    global s
    c=s.count(a); assert c==n, f"want {n} got {c}: {a[:80]!r}"; s=s.replace(a,b)

# 1. EGGS: swap xyzzy for Harry Potter 'alohomora', add 'quidditch' (the game)
rep("const EGGS={oz7y:'Who is Oz7y',xyzzy:'The magic word',logo:'Logo tickler',sameer:'The idea guy'};",
    "const EGGS={oz7y:'Who is Oz7y',alohomora:'The unlocking charm',logo:'Logo tickler',sameer:'The idea guy',quidditch:'Seeker'};")

# 2. Secrets board: add a Play button once the game is unlocked
rep(
"""  eggModal(`<h3>Secrets</h3><div class="egg-list">${rows}</div><div class="egg-count">${found.length} of ${total} found</div>
    ${found.length<total?'<p class="note">Keep poking around…</p>':''}`);""",
"""  eggModal(`<h3>Secrets</h3><div class="egg-list">${rows}</div><div class="egg-count">${found.length} of ${total} found</div>
    ${found.includes('quidditch')?'<button type="button" class="btn primary" data-playgame="1">Play Date Dash ▶</button>':''}
    ${found.length<total?'<p class="note">Keep poking around…</p>':''}`);""")

# 3. SECRET words (HP spells) + the hidden game + streak helpers
rep(
"""const SECRET={
  'xyzzy':()=>foundEgg('xyzzy','Nothing happens.','…or does it? Any old-school adventurer would smile. You found a secret. 🕸️')
};""",
"""const SECRET={
  'alohomora':()=>foundEgg('alohomora','Alohomora!','The unlocking charm — a hidden secret clicks open. 🗝️'),
  'lumos':()=>{store.set('sdc_theme','light');applyTheme();updateThemeBtn();flash('Lumos! 💡');},
  'nox':()=>{store.set('sdc_theme','dark');applyTheme();updateThemeBtn();flash('Nox. 🌙');},
  'quidditch':()=>{const f=eggsFound();if(!f.includes('quidditch')){f.push('quidditch');try{localStorage.setItem('sdc_eggs',JSON.stringify(f))}catch(e){}}flash('🧹 Secret found: Seeker');openGame();}
};

/* ---------- hidden mini-game: Date Dash (tap the out-of-date items) ---------- */
let game=null;
const GAME_FOODS=['🥛','🍞','🧀','🍕','🥐','🍓','🥪','🍎'];
function stopGame(){if(game){clearInterval(game.spawn);clearInterval(game.tick);clearTimeout(game.hide);game.active=false;}}
function openGame(){
  let m=document.getElementById('gameModal');if(m)m.remove();stopGame();
  const best=+(store.get('sdc_game_best')||0);
  m=document.createElement('div');m.id='gameModal';m.className='egg-modal';
  m.innerHTML=`<div class="egg-card game-card">
    <h3>Date Dash</h3>
    <p class="note">Tap the out-of-date items before they vanish. 30 seconds.</p>
    <div class="game-hud"><span>Score <b id="g_score">0</b></span><span>Best <b id="g_best">${best}</b></span><span>Time <b id="g_time">30</b></span></div>
    <div class="game-grid" id="g_grid">${Array.from({length:9}).map((_,i)=>`<button type="button" class="g-cell" data-cell="${i}"></button>`).join('')}</div>
    <div class="actions" style="justify-content:center"><button type="button" class="btn primary" data-gamestart="1">Start</button><button type="button" class="btn" data-eggclose="1">Close</button></div>
  </div>`;
  document.body.appendChild(m);
}
function startGame(){
  const grid=document.getElementById('g_grid');if(!grid)return;stopGame();
  const cells=[...grid.querySelectorAll('.g-cell')];cells.forEach(c=>{c.textContent='';c.classList.remove('up')});
  const sEl=document.getElementById('g_score'),tEl=document.getElementById('g_time');
  const st={score:0,time:30,active:true,cur:-1};game=st;
  const clearCur=()=>{if(st.cur>=0&&cells[st.cur]){cells[st.cur].textContent='';cells[st.cur].classList.remove('up')}st.cur=-1;};
  const spawn=()=>{clearCur();const i=Math.floor(Math.random()*9);st.cur=i;cells[i].textContent=GAME_FOODS[Math.floor(Math.random()*GAME_FOODS.length)];cells[i].classList.add('up');
    const life=Math.max(450,900-(30-st.time)*16);clearTimeout(st.hide);st.hide=setTimeout(clearCur,life);};
  st.tap=(i)=>{if(st.active&&i===st.cur){st.score++;sEl.textContent=st.score;clearTimeout(st.hide);spawn();}};
  spawn();st.spawn=setInterval(spawn,700);
  st.tick=setInterval(()=>{st.time--;if(tEl)tEl.textContent=st.time;if(st.time<=0)endGame();},1000);
}
function endGame(){
  if(!game)return;const st=game;st.active=false;clearInterval(st.spawn);clearInterval(st.tick);clearTimeout(st.hide);
  const best=+(store.get('sdc_game_best')||0);const nb=Math.max(best,st.score);store.set('sdc_game_best',String(nb));
  const bEl=document.getElementById('g_best');if(bEl)bEl.textContent=nb;
  const grid=document.getElementById('g_grid');if(grid)grid.querySelectorAll('.g-cell').forEach(c=>{c.textContent='';c.classList.remove('up')});
  flash(st.score>best?`🏆 New best: ${st.score}!`:`Time! You cleared ${st.score}.`);
}

/* ---------- personal streak: consecutive days this person logged or checked ---------- */
function myStreak(){
  if(!S.me||S.me.owner)return 0;const id=S.me.id;const set=new Set();
  const k=ms=>{const d=new Date(ms);return d.getFullYear()+'-'+d.getMonth()+'-'+d.getDate();};
  for(const it of S.items)for(const h of (it.history||[]))if(h.by===id)set.add(k(h.at));
  for(const sec of S.sections)for(const h of (sec.history||[]))if(h.by===id)set.add(k(h.at));
  if(!set.size)return 0;
  const key=d=>d.getFullYear()+'-'+d.getMonth()+'-'+d.getDate();
  let n=0;const d=new Date();if(!set.has(key(d)))d.setDate(d.getDate()-1);
  while(set.has(key(d))){n++;d.setDate(d.getDate()-1);}
  return n;
}""")

# 4. header: show a streak flame next to the name
rep("  $('#whoName').textContent=S.me.owner?'Boss':S.me.name+' · '+ROLES[myRole()];updateThemeBtn();updatePhotoBtn();",
    "  {const _st=myStreak();$('#whoName').innerHTML=(S.me.owner?'Boss':esc(S.me.name)+' · '+ROLES[myRole()])+(_st>=2?` <span class=\"streak\" title=\"${_st}-day streak\">🔥 ${_st}</span>`:'');}updateThemeBtn();updatePhotoBtn();")

# 5. briefing: mention the streak when it's going
rep("  const parts=[];if(r.total-r.done)push=0;",  # dummy anchor that will fail if present
    "  const parts=[];",0)  # no-op guard (count 0)
rep("  const parts=[];if(r.total-r.done)push",
    "  const parts=[];if(r.total-r.done)push",0)  # no-op guard
rep("  const parts=[];if(r.total-r.done)",
    "  const parts=[];const _st=myStreak();if(_st>=3)parts.push(`🔥 ${_st}-day streak`);if(r.total-r.done)")

# 6. click handler: game + modal controls
rep(
"""  if(e.target.id==='eggModal'){e.target.remove();return}
  if(e.target.closest('[data-eggclose]')){document.getElementById('eggModal')?.remove();return}
  const _eg=e.target.closest('[data-egg]');if(_eg){tapEgg(_eg.dataset.egg);return}""",
"""  if(e.target.id==='eggModal'||e.target.id==='gameModal'){stopGame();e.target.remove();return}
  if(e.target.closest('[data-eggclose]')){stopGame();document.getElementById('eggModal')?.remove();document.getElementById('gameModal')?.remove();return}
  if(e.target.closest('[data-gamestart]')){startGame();return}
  if(e.target.closest('[data-playgame]')){document.getElementById('eggModal')?.remove();openGame();return}
  {const _gc=e.target.closest('[data-cell]');if(_gc){if(game)game.tap(+_gc.dataset.cell);return}}
  const _eg=e.target.closest('[data-egg]');if(_eg){tapEgg(_eg.dataset.egg);return}""")

open(P,'w',encoding='utf-8').write(s); print("app.js v12 (HP spells, streak, mini-game) patched OK")
