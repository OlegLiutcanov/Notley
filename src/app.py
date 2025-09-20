# src/app.py
from __future__ import annotations
from typing import Optional, Iterable, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from src.db import init_db
from src.services import (
    list_notes,
    create_note,
    get_note,
    edit_note,
    delete_note,
    pin_note,
    archive_note,
    restore_note,
    purge_note,
    backlinks_for,
)

# --- bootstrap DB ---
init_db()

app = FastAPI(title="Notely API")

# ---------- Schemas ----------
class NoteCreate(BaseModel):
    title: str
    content: str = ""
    tags: list[str] = Field(default_factory=list)

class NoteEdit(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[list[str]] = None
    pinned: Optional[bool] = None
    archived: Optional[bool] = None

class NoteOut(BaseModel):
    id: int
    title: str
    content: str
    tags: list[str]
    pinned: bool
    archived: bool
    created_at: datetime
    updated_at: datetime

def _to_out(n) -> NoteOut:
    # n.tags is provided by your model helper
    return NoteOut(
        id=n.id, title=n.title, content=n.content,
        tags=list(n.tags), pinned=n.pinned, archived=n.archived,
        created_at=n.created_at, updated_at=n.updated_at
    )

# ---------- API ----------
@app.get("/api/notes", response_model=list[NoteOut])
def api_list_notes(
    tag: Optional[str] = None,
    search: Optional[str] = None,
    include_archived: bool = Query(False, alias="archived"),
    sort: str = Query("updated", pattern="^(updated|created|title)$"),
):
    notes = list_notes(tag=tag, search=search, include_archived=include_archived, sort=sort)
    return [_to_out(n) for n in notes]

@app.post("/api/notes", response_model=NoteOut, status_code=201)
def api_create_note(payload: NoteCreate):
    try:
        n = create_note(payload.title, payload.content, payload.tags)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_out(n)

@app.get("/api/notes/{identifier}", response_model=NoteOut)
def api_get_note(identifier: str):
    n = get_note(identifier)
    if not n:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_out(n)

@app.patch("/api/notes/{identifier}", response_model=NoteOut)
def api_edit_note(identifier: str, payload: NoteEdit):
    n = edit_note(
        identifier,
        title=payload.title,
        content=payload.content,
        tags=payload.tags,
        pinned=payload.pinned,
        archived=payload.archived,
    )
    return _to_out(n)

@app.delete("/api/notes/{identifier}")
def api_delete_note(identifier: str, hard: bool = False):
    delete_note(identifier, hard=hard)
    return {"ok": True}

@app.post("/api/notes/{identifier}/pin", response_model=NoteOut)
def api_pin(identifier: str, value: bool = True):
    n = pin_note(identifier, value)
    return _to_out(n)

@app.post("/api/notes/{identifier}/archive", response_model=NoteOut)
def api_archive(identifier: str, value: bool = True):
    n = archive_note(identifier, value)
    return _to_out(n)

@app.post("/api/notes/{identifier}/restore", response_model=NoteOut)
def api_restore(identifier: str):
    n = restore_note(identifier)
    return _to_out(n)

@app.post("/api/notes/{identifier}/purge")
def api_purge(identifier: str):
    purge_note(identifier)
    return {"ok": True}

@app.get("/api/notes/{identifier}/backlinks", response_model=list[NoteOut])
def api_backlinks(identifier: str, archived: bool = False):
    notes = backlinks_for(identifier, include_archived=archived)
    return [_to_out(n) for n in notes]

# ---------- Tiny UI (single file, no build) ----------
_INDEX = """
<!doctype html>
<html lang="en" class="h-full">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Notely</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    // Tailwind config for dark mode class
    tailwind.config = { darkMode: 'class' };
  </script>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/dompurify@3.1.6/dist/purify.min.js"></script>
<style>
  .scroll-smooth { scroll-behavior: smooth; }

  /* ---------- Buttons & Pills (no @apply) ---------- */
  .pill { padding: 2px 8px; border-radius: 999px; font-size: 12px; border: 1px solid #cbd5e1; }
  .btn { display: inline-flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 12px;
         border: 1px solid #cbd5e1; background: #fff; transition: transform .1s ease; }
  .btn:hover { transform: translateY(-2px); }
  .btn-primary { background: #0b5cff; color: #fff; border-color: #0b5cff; }
  .btn-ghost { background: #fff; }
  .btn-warn { background: #ffe3e3; color: #111827; border-color: #fecaca; }

  /* ---------- Dark mode readability ---------- */
  .dark body { color: #f8fafc; } /* near-white */
  .dark .btn, .dark .btn * { color: #fff !important; } /* force white text on buttons */
  .dark .btn-ghost { background-color: #0b1220; border-color: #334155; } /* slate-950 / slate-700 */
  .dark .btn-primary { background-color: #2563eb; border-color: #2563eb; } /* blue-600 */
  .dark .btn-warn { background-color: #e11d48; border-color: #e11d48; } /* rose-600 */

  .dark input, .dark textarea, .dark select {
    color: #fff; background-color: #0b1220; border-color: #334155;
  }
  .dark input::placeholder, .dark textarea::placeholder { color: #94a3b8; } /* slate-400 */
  .dark .pill { border-color: #334155; color: #e2e8f0; }

  /* ---------- Markdown preview fallback (no typography plugin needed) ---------- */
  .markdown { line-height: 1.6; }
  .markdown h1 { font-size: 1.5rem; margin: 1rem 0 .5rem; }
  .markdown h2 { font-size: 1.25rem; margin: .9rem 0 .5rem; }
  .markdown h3 { font-size: 1.1rem; margin: .8rem 0 .4rem; }
  .markdown p { margin: .5rem 0; }
  .markdown ul, .markdown ol { margin: .5rem 0 .5rem 1.25rem; }
  .markdown code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
                   background: rgba(148,163,184,.2); padding: 0 .25rem; border-radius: .25rem; }
  .markdown pre { padding: .75rem; border-radius: .5rem; overflow: auto; background: #0f172a; color: #e2e8f0; }
  .dark .markdown pre { background: #0b1220; }
  .markdown blockquote { border-left: 3px solid #94a3b8; padding-left: .75rem; color: #64748b; }
  a { color: #2563eb; text-decoration: none; }
  a:hover { text-decoration: underline; }
</style>

</head>
<body class="h-full bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
  <div id="toast" class="fixed top-4 right-4 space-y-2 z-50"></div>

  <header class="sticky top-0 z-40 border-b border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-950/70 backdrop-blur">
    <div class="max-w-7xl mx-auto px-4 py-3 flex items-center gap-3">
      <h1 class="text-xl font-semibold tracking-tight">🗒️ Notely</h1>
      <span class="text-slate-500 text-sm hidden md:inline">local notes • tags • backlinks</span>
      <div class="flex-1"></div>

      <div class="relative">
        <input id="q" class="w-64 md:w-80 rounded-lg border px-3 py-2 bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
               placeholder="Search (press /)" />
        <kbd class="absolute right-2 top-2 text-xs text-slate-400 border px-1 rounded">/</kbd>
      </div>

      <button id="newBtn" class="btn btn-primary" title="New (N)">New</button>

      <button id="themeBtn" class="btn btn-ghost" title="Toggle theme">
        <span id="sun">🌞</span><span id="moon" class="hidden">🌙</span>
      </button>
    </div>
  </header>

  <main class="max-w-7xl mx-auto px-4 py-4 grid grid-cols-1 md:grid-cols-[240px_1fr_1.25fr] gap-4">
    <!-- Sidebar -->
    <aside class="space-y-4">
      <section class="rounded-xl border border-slate-200 dark:border-slate-800 p-3">
        <h3 class="text-sm font-semibold mb-2">Filters</h3>
        <label class="flex items-center gap-2 text-sm mb-1">
          <input type="checkbox" id="showArchived" class="h-4 w-4"> Show archived
        </label>
        <label class="flex items-center gap-2 text-sm">
          <input type="checkbox" id="onlyPinned" class="h-4 w-4"> Only pinned
        </label>
      </section>

      <section class="rounded-xl border border-slate-200 dark:border-slate-800 p-3">
        <div class="flex items-center justify-between mb-2">
          <h3 class="text-sm font-semibold">Tags</h3>
          <button id="clearTag" class="text-xs text-blue-600 hover:underline hidden">clear</button>
        </div>
        <div id="tags" class="flex flex-wrap gap-2"></div>
      </section>
    </aside>

    <!-- List -->
    <section class="space-y-2">
      <div class="flex items-center justify-between">
        <h2 class="font-semibold">Notes</h2>
        <select id="sort" class="rounded-lg border px-2 py-1 bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700">
          <option value="updated">Sort by updated</option>
          <option value="created">Sort by created</option>
          <option value="title">Sort by title</option>
        </select>
      </div>
      <div id="list" class="grid gap-2 max-h-[70vh] overflow-auto pr-1"></div>
    </section>

    <!-- Detail -->
    <section id="detail" class="space-y-3"></section>
  </main>

  <!-- New/Edit Modal -->
  <dialog id="modal" class="rounded-xl border border-slate-200 dark:border-slate-800 p-0 w-[min(90vw,720px)]">
    <form method="dialog" class="bg-white dark:bg-slate-950 rounded-xl overflow-hidden">
      <div class="px-4 py-3 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
        <h3 id="modalTitle" class="font-semibold">New note</h3>
        <button id="modalClose" class="btn btn-ghost" value="close">✖</button>
      </div>
      <div class="p-4 space-y-3">
        <input id="mtitle" class="w-full rounded-lg border px-3 py-2 bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700" placeholder="Title" />
        <input id="mtags" class="w-full rounded-lg border px-3 py-2 bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700" placeholder="tags (comma, separated)" />
        <div class="flex items-center gap-3 text-sm">
          <button type="button" id="tabEdit" class="btn btn-ghost">Edit</button>
          <button type="button" id="tabPreview" class="btn btn-ghost">Preview</button>
        </div>
        <textarea id="mcontent" class="w-full h-52 rounded-lg border px-3 py-2 bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700" placeholder="Write markdown…"></textarea>
        <div id="mpreview" class="prose prose-slate dark:prose-invert max-w-none hidden"></div>
      </div>
      <div class="px-4 py-3 border-t border-slate-200 dark:border-slate-800 flex items-center justify-end gap-2">
        <button id="saveBtn" class="btn btn-primary">Save</button>
      </div>
    </form>
  </dialog>

  <script>
    // ---------- tiny utils ----------
    const $ = (sel, root=document) => root.querySelector(sel);
    const $$ = (sel, root=document) => Array.from(root.querySelectorAll(sel));
    const sleep = (ms) => new Promise(r=>setTimeout(r, ms));
    const store = {
      get k(){ return 'notely-ui'; },
      get(){ try{return JSON.parse(localStorage.getItem(this.k)||'{}')}catch{return{}} },
      set(v){ localStorage.setItem(this.k, JSON.stringify(v)) }
    };
    function toast(msg, kind='ok'){
      const el = document.createElement('div');
      el.className = 'px-3 py-2 rounded-lg shadow bg-white dark:bg-slate-900 border ' +
                     (kind==='err'?'border-rose-400 text-rose-700 dark:text-rose-300':'border-slate-200 dark:border-slate-700');
      el.textContent = msg;
      $('#toast').appendChild(el);
      setTimeout(()=>{ el.classList.add('opacity-0','translate-y-1'); }, 2500);
      setTimeout(()=> el.remove(), 3000);
    }
    async function j(url, opts={}){
      const res = await fetch(url, {headers:{'content-type':'application/json'}, ...opts});
      if(!res.ok){
        let text = await res.text().catch(()=>res.statusText);
        try{ const d=JSON.parse(text); text=d.detail||text }catch{}
        throw new Error(text || res.statusText);
      }
      if(res.status===204) return null;
      return res.json();
    }
    function debounce(fn, ms=250){
      let t; return (...args)=>{ clearTimeout(t); t = setTimeout(()=>fn(...args), ms); }
    }

    // ---------- theme ----------
    function applyTheme(){
      const st = store.get();
      const dark = st.theme==='dark' || (!('theme' in st) && window.matchMedia('(prefers-color-scheme: dark)').matches);
      document.documentElement.classList.toggle('dark', dark);
      $('#sun').classList.toggle('hidden', dark);
      $('#moon').classList.toggle('hidden', !dark);
    }
    applyTheme();
    $('#themeBtn').addEventListener('click', ()=>{
      const st = store.get(); st.theme = (document.documentElement.classList.contains('dark') ? 'light' : 'dark'); store.set(st); applyTheme();
    });

    // ---------- app state ----------
    let notes = [];
    let current = null;
    let selectedTag = null;

    const qInput = $('#q');
    const sortSel = $('#sort');
    const chkArchived = $('#showArchived');
    const chkPinned = $('#onlyPinned');

    // ---------- fetch & render ----------
    async function load(){
      const params = new URLSearchParams();
      params.set('sort', sortSel.value);
      if(qInput.value.trim()) params.set('search', qInput.value.trim());
      if(selectedTag) params.set('tag', selectedTag);
      if(chkArchived.checked) params.set('archived','true');
      const data = await j('/api/notes?'+params.toString());
      notes = data;
      renderTags();
      renderList();
      if(current){
        const refreshed = notes.find(n => n.id===current.id);
        if(refreshed) current = refreshed;
        renderDetail();
      } else if(notes[0]) { select(notes[0].id); }
    }

    function renderTags(){
      const set = new Set();
      notes.forEach(n => (n.tags||[]).forEach(t => set.add(t)));
      const tags = Array.from(set).sort((a,b)=>a.localeCompare(b));
      const box = $('#tags');
      box.innerHTML = tags.map(t => `
        <button data-tag="${t}" class="pill border-slate-300 dark:border-slate-700 ${selectedTag===t?'bg-blue-600 text-white border-blue-600':''}">
          #${t}
        </button>`).join('') || '<div class="text-sm text-slate-500">no tags</div>';
      $$('#tags [data-tag]').forEach(btn => btn.addEventListener('click', ()=>{
        selectedTag = (selectedTag===btn.dataset.tag) ? null : btn.dataset.tag;
        $('#clearTag').classList.toggle('hidden', !selectedTag);
        load();
      }));
      $('#clearTag').classList.toggle('hidden', !selectedTag);
      $('#clearTag').onclick = ()=>{ selectedTag=null; load(); };
    }

    function renderList(){
      const list = $('#list');
      const filt = notes.filter(n => chkPinned.checked ? n.pinned : true);
      list.innerHTML = filt.map(n => `
        <button class="text-left rounded-xl border border-slate-200 dark:border-slate-800 p-3 hover:bg-slate-100 dark:hover:bg-slate-900 transition ${current && current.id===n.id ? 'ring-2 ring-blue-500' : ''}"
                onclick="select(${n.id})">
          <div class="flex items-center gap-2">
            <div class="font-semibold truncate">#${n.id} ${n.title}</div>
            ${n.pinned ? '<span class="pill border-yellow-400 text-yellow-700 dark:text-yellow-300">pinned</span>' : ''}
            ${n.archived ? '<span class="pill border-slate-400 text-slate-500">archived</span>' : ''}
          </div>
          <div class="mt-1 text-sm text-slate-500">
            ${(n.tags||[]).map(t=>`<span class="pill border-slate-300 dark:border-slate-700">#${t}</span>`).join(' ')}
          </div>
          <div class="mt-1 text-xs text-slate-400">updated ${new Date(n.updated_at).toLocaleString()}</div>
        </button>
      `).join('') || '<div class="text-sm text-slate-500">no notes</div>';
    }

    function renderDetail(){
      const d = $('#detail'); if(!current){ d.innerHTML=''; return; }
      d.innerHTML = `
        <div class="rounded-xl border border-slate-200 dark:border-slate-800">
          <div class="p-3 border-b border-slate-200 dark:border-slate-800 flex items-center gap-2">
            <input id="title" class="flex-1 bg-transparent outline-none font-semibold" value="${escapeHtml(current.title)}" />
            <button class="btn btn-ghost" onclick="togglePin()">${current.pinned?'Unpin':'Pin'}</button>
            <button class="btn btn-ghost" onclick="toggleArchive()">${current.archived?'Unarchive':'Archive'}</button>
            <button class="btn btn-warn" onclick="delNote()">Delete</button>
          </div>
          <div class="p-3">
            <div class="flex items-center gap-3 text-sm mb-2">
              <button id="dTabEdit" class="btn btn-ghost">Edit</button>
              <button id="dTabPreview" class="btn btn-ghost">Preview</button>
            </div>
            <textarea id="content" class="w-full h-64 rounded-lg border px-3 py-2 bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700">${escapeHtml(current.content||"")}</textarea>
            <div id="preview" class="prose prose-slate dark:prose-invert max-w-none hidden"></div>
            <div class="mt-2 text-sm text-slate-500">
              ${(current.tags||[]).map(t=>`<span class="pill border-slate-300 dark:border-slate-700">#${t}</span>`).join(' ')}
            </div>
            <div class="mt-3">
              <strong>Backlinks</strong>
              <div id="backlinks" class="mt-1 text-sm"></div>
            </div>
          </div>
        </div>
      `;
      $('#dTabEdit').onclick = ()=>{ $('#content').classList.remove('hidden'); $('#preview').classList.add('hidden'); };
      $('#dTabPreview').onclick = ()=>{ renderPreview('#content','#preview'); };
      loadBacklinks();
      $('#title').addEventListener('change', saveTitle);
      $('#content').addEventListener('change', saveContent);
    }

    function renderPreview(srcSel, destSel){
      const md = $(srcSel).value;
      const html = DOMPurify.sanitize(marked.parse(md||""));
      $(destSel).innerHTML = html;
      $(srcSel).classList.add('hidden');
      $(destSel).classList.remove('hidden');
    }

    async function loadBacklinks(){
      const bl = await j(`/api/notes/${current.id}/backlinks`);
      $('#backlinks').innerHTML = bl.length
        ? bl.map(b=>`<a class="text-blue-600 hover:underline" href="javascript:select(${b.id})">#${b.id} ${escapeHtml(b.title)}</a>`).join('<br/>')
        : '<span class="text-slate-500">none</span>';
    }

    // ---------- actions ----------
    async function select(id){
      current = await j(`/api/notes/${id}`);
      renderList(); renderDetail();
      // Keep scroll in view for current item
      await sleep(50);
      const btn = $(`#list button[onclick="select(${id})"]`); if(btn) btn.scrollIntoView({block:'nearest'});
    }
    async function saveTitle(){
      const title = $('#title').value.trim();
      if(!title){ toast('Title required','err'); return; }
      current = await j(`/api/notes/${current.id}`, {method:'PATCH', body: JSON.stringify({title})});
      toast('Saved title'); load();
    }
    async function saveContent(){
      const content = $('#content').value;
      current = await j(`/api/notes/${current.id}`, {method:'PATCH', body: JSON.stringify({content})});
      toast('Saved content'); load();
    }
    async function togglePin(){
      current = await j(`/api/notes/${current.id}/pin?value=${!current.pinned}`, {method:'POST'});
      toast(current.pinned?'Pinned':'Unpinned'); load();
    }
    async function toggleArchive(){
      current = await j(`/api/notes/${current.id}/archive?value=${!current.archived}`, {method:'POST'});
      toast(current.archived?'Archived':'Unarchived'); load();
    }
    async function delNote(){
      if(!confirm('Delete this note?')) return;
      await j(`/api/notes/${current.id}`, {method:'DELETE'});
      current = null; toast('Deleted'); load();
    }

    // ---------- modal new note ----------
    const modal = $('#modal'); const newBtn = $('#newBtn'); const mtitle=$('#mtitle'); const mcontent=$('#mcontent'); const mtags=$('#mtags');
    const tabEdit=$('#tabEdit'); const tabPrev=$('#tabPreview'); const mprev=$('#mpreview'); const saveBtn=$('#saveBtn');
    newBtn.addEventListener('click', ()=>{ $('#modalTitle').textContent='New note'; mtitle.value=''; mcontent.value=''; mtags.value=''; mprev.classList.add('hidden'); $('#mcontent').classList.remove('hidden'); modal.showModal(); mtitle.focus(); });
    $('#modalClose').addEventListener('click', ()=> modal.close());
    tabEdit.onclick = ()=>{ mprev.classList.add('hidden'); mcontent.classList.remove('hidden'); };
    tabPrev.onclick = ()=>{ mprev.innerHTML = DOMPurify.sanitize(marked.parse(mcontent.value||"")); mcontent.classList.add('hidden'); mprev.classList.remove('hidden'); };
    saveBtn.addEventListener('click', async (e)=>{ e.preventDefault();
      const title = mtitle.value.trim(); if(!title){ toast('Title required','err'); return; }
      const tags = mtags.value.split(',').map(s=>s.trim()).filter(Boolean);
      await j('/api/notes', {method:'POST', body:JSON.stringify({title, content:mcontent.value, tags})});
      toast('Created'); modal.close(); load();
    });

    // ---------- events & shortcuts ----------
    qInput.addEventListener('input', debounce(load, 250));
    sortSel.addEventListener('change', load);
    chkArchived.addEventListener('change', load);
    chkPinned.addEventListener('change', load);

    document.addEventListener('keydown', (e)=>{
        const tag = e.target.tagName;
        const isTyping = tag === 'INPUT' || tag === 'TEXTAREA' || e.target.isContentEditable;
        const k = e.key;

        // Focus search with "/"
        if (k === '/' && !isTyping) {
        e.preventDefault();
        qInput.focus();
        return;
        }

        // Save with Ctrl/Cmd+S (allowed while typing)
        if ((k === 's' || k === 'S') && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        if (current) { saveContent(); }
        return;
        }

        // Ignore the rest while typing (so letters like 'n','p','a' don't trigger)
        if (isTyping) return;

        // New / Pin / Archive
        if (k === 'n' || k === 'N') { e.preventDefault(); $('#newBtn').click(); return; }
        if (k === 'p' || k === 'P') { if (current) { e.preventDefault(); togglePin(); } return; }
        if (k === 'a' || k === 'A') { if (current) { e.preventDefault(); toggleArchive(); } return; }
    });

    function escapeHtml(s){ return (s||'').replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

    // initial load
    load();
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(content=_INDEX)
