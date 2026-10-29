# -*- coding: utf-8 -*-
P='public/app.js'; s=open(P,encoding='utf-8').read()
def rep(a,b,n=1):
    global s
    c=s.count(a); assert c==n, f"want {n} got {c}: {a[:90]!r}"; s=s.replace(a,b)

# Stock rows: tapping one now expands an inline editor on the scan page instead of
# jumping to All items. Admins get the full edit form (change the use-by, or add
# several more dates for this product + section), and everyone gets the quick
# shelf actions. No more "go to All items, edit, scroll up, back to Log product".
rep('''        ${onShelf.map(i=>{const n=daysLeft(i.expiry);return `<button type="button" class="stockrow" data-gotoitem="${i.id}">
          <span class="stockdate">${esc(fmtExp(i.expiry))}</span>
          <span class="pill ${band(n)}">${dueLabel(n)}</span>
          ${i.location?`<span class="stockloc">${esc(i.location)}</span>`:''}
          <span class="chev" aria-hidden="true">&rsaquo;</span>
        </button>`}).join('')}
        <div class="note">These are already on the shelf. Only add a date below for stock with a different use-by.</div>''',
'''        ${onShelf.map(i=>{const n=daysLeft(i.expiry);const open=S.editItem===i.id;return `<div class="stockitem">
          <button type="button" class="stockrow" data-edititem="${i.id}" aria-expanded="${open}">
            <span class="stockdate">${esc(fmtExp(i.expiry))}</span>
            <span class="pill ${band(n)}">${dueLabel(n)}</span>
            ${i.location?`<span class="stockloc">${esc(i.location)}</span>`:''}
            <span class="chev" aria-hidden="true">${open?'&#9662;':'&#9656;'}</span>
          </button>
          ${open?`<div class="stockedit">
            ${isAdmin()?editItemForm(i):''}
            <div class="actions">
              <button type="button" class="btn small danger" data-act="removed" data-id="${i.id}">Remove from shelf</button>
              <button type="button" class="btn small" data-act="sold" data-id="${i.id}">Sold through</button>
              <button type="button" class="btn small ghost" data-act="void" data-id="${i.id}">Delete entry</button>
              ${isAdmin()?'':'<button type="button" class="btn small ghost" data-editcancel="1">Close</button>'}
            </div>
          </div>`:''}
        </div>`}).join('')}
        <div class="note">Tap a date to edit it, add more dates for this product, or take it off the shelf.</div>''')

open(P,'w',encoding='utf-8').write(s); print("app.js v23 (inline stock edit) patched OK")
