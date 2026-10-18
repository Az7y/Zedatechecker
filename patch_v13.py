# -*- coding: utf-8 -*-
P='public/app.js'; s=open(P,encoding='utf-8').read()
def rep(a,b,n=1):
    global s
    c=s.count(a); assert c==n, f"want {n} got {c}: {a[:80]!r}"; s=s.replace(a,b)

# 1. state: shared scores
rep("offCache:{}, feedback:[], nameImg:{}",
    "offCache:{}, feedback:[], scores:[], nameImg:{}")

# 2. listen to the shared scores collection
rep("  listen(collection(fs,'feedback'),'feedback',s=>{S.feedback=s.docs.map(d=>({id:d.id,...d.data()})).sort((a,b)=>(b.at||0)-(a.at||0))});",
    "  listen(collection(fs,'feedback'),'feedback',s=>{S.feedback=s.docs.map(d=>({id:d.id,...d.data()})).sort((a,b)=>(b.at||0)-(a.at||0))});\n"
    "  listen(collection(fs,'scores'),'scores',s=>{S.scores=s.docs.map(d=>({id:d.id,...d.data()})).sort((a,b)=>(b.score||0)-(a.score||0));if(document.getElementById('gameModal'))refreshBoard();});")

# 3. endGame: submit your best to the shared board, then refresh it
rep("  flash(st.score>best?`🏆 New best: ${st.score}!`:`Time! You cleared ${st.score}.`);",
    "  if(!S.me.owner&&st.score>0){const mine=(S.scores||[]).find(x=>x.id===S.me.id);\n"
    "    if(!mine||st.score>(mine.score||0))quickWrite(setDoc(doc(fs,'scores',S.me.id),{name:S.me.name,score:st.score,at:Date.now()}),null);}\n"
    "  refreshBoard();\n"
    "  flash(st.score>best?`🏆 New best: ${st.score}!`:`Time! You cleared ${st.score}.`);")

# 4. game modal: add a leaderboard container + render it on open
rep('    <div class="game-grid" id="g_grid">${Array.from({length:9}).map((_,i)=>`<button type="button" class="g-cell" data-cell="${i}"></button>`).join(\'\')}</div>',
    '    <div class="game-grid" id="g_grid">${Array.from({length:9}).map((_,i)=>`<button type="button" class="g-cell" data-cell="${i}"></button>`).join(\'\')}</div>\n    <div class="game-board" id="g_board"></div>')
rep("  document.body.appendChild(m);\n}\nfunction startGame(){",
    "  document.body.appendChild(m);refreshBoard();\n}\nfunction refreshBoard(){\n"
    "  const el=document.getElementById('g_board');if(!el)return;\n"
    "  const top=(S.scores||[]).slice(0,8);\n"
    "  el.innerHTML='<div class=\"board-h\">Store leaderboard</div>'+(top.length?top.map((r,i)=>`<div class=\"board-row${r.id===S.me?.id?' me':''}\"><span>${i+1}. ${esc(r.name||'\\u2014')}</span><b>${esc(r.score)}</b></div>`).join(''):'<div class=\"note\">No scores yet. Be the first!</div>');\n"
    "}\nfunction startGame(){")

# 5. seasonal skins + a once-a-day greeting
rep("  if(parts.length)flash(parts.join(', '));",
    "  const _se=seasonal();if(_se&&_se.hello){const today=new Date().toDateString();if(store.get('sdc_season_hi')!==today){store.set('sdc_season_hi',today);parts.unshift(_se.hello);}}\n"
    "  if(parts.length)flash(parts.join(' \u00b7 '));")
rep("  $('#storeName').textContent=S.settings.store||'';",
    "  $('#storeName').textContent=S.settings.store||'';\n  {const _se=seasonal();const _b=document.getElementById('brandSeason');if(_b)_b.textContent=_se?' '+_se.emoji:'';}")
# define seasonal() next to briefing's brand helper
rep("const brand=()=>`<div class=\"brand\"><span class=\"mark-wrap\" data-stamp=\"1\">${LOGO}</span> Zedatechecker</div>`;",
    "const brand=()=>`<div class=\"brand\"><span class=\"mark-wrap\" data-stamp=\"1\">${LOGO}</span> Zedatechecker</div>`;\n"
    "// Seasonal skin: a small emoji by the name on certain days, with a once-a-day hello.\n"
    "function seasonal(){const d=new Date(),m=d.getMonth()+1,day=d.getDate();\n"
    "  if(m===1&&day===1)return{emoji:'\\ud83c\\udf86',hello:'Happy New Year! \\ud83c\\udf86'};\n"
    "  if(m===2&&day===14)return{emoji:'\\ud83d\\udc9d',hello:null};\n"
    "  if(m===3&&day===17)return{emoji:'\\u2618\\ufe0f',hello:'Happy St Patrick\\u2019s Day \\u2618\\ufe0f'};\n"
    "  if(m===10&&day>=24)return{emoji:'\\ud83c\\udf83',hello:'Spooky season \\ud83c\\udf83'};\n"
    "  if(m===12&&day<=26)return{emoji:'\\ud83c\\udf84',hello:'Happy Christmas! \\ud83c\\udf84'};\n"
    "  if(m===12)return{emoji:'\\u2744\\ufe0f',hello:null};\n"
    "  return null;}")

open(P,'w',encoding='utf-8').write(s); print("app.js v13 (shared leaderboard + seasonal) patched OK")
