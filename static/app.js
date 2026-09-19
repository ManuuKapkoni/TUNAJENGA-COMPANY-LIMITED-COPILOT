const THREAD_KEY = 'tunajenga_thread_id';

function newThreadId(){
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return 'project-' + crypto.randomUUID();
  }
  const rand = () => Math.random().toString(36).slice(2, 10);
  return 'project-' + Date.now().toString(36) + '-' + rand() + rand();
}

let threadId = localStorage.getItem(THREAD_KEY) || newThreadId();
localStorage.setItem(THREAD_KEY, threadId);

const q = document.getElementById('question');
const send = document.getElementById('sendBtn');
const messages = document.getElementById('messages');
const upload = document.getElementById('uploadBtn');
const fileInput = document.getElementById('fileInput');
const uploadStatus = document.getElementById('uploadStatus');
const fileLabel = document.getElementById('fileLabel');
const starters = document.getElementById('starterPrompts');
const sessionId = document.getElementById('sessionId');
const newSessionBtn = document.getElementById('newSessionBtn');

function renderSession(){
  if(sessionId) sessionId.textContent = 'MEMORY / ' + threadId.slice(-8).toUpperCase();
}
renderSession();

function esc(s=''){
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'
  }[c]));
}

function addMessage(role, html, meta=''){
  const el = document.createElement('div');
  el.className = `message ${role}`;
  const avatar = role === 'assistant' ? '<div class="avatar">T</div>' : '';
  const label = role === 'assistant' ? 'TUNAJENGA COPILOT' : 'PROJECT ENGINEER';
  el.innerHTML = `${avatar}<div class="message-body"><div class="message-label">${label}</div><div class="bubble">${html}</div>${meta}</div>`;
  messages.appendChild(el);
  messages.scrollTop = messages.scrollHeight;
  return el;
}

function loadingMarkup(){
  return '<span class="thinking">Searching project documents <i></i><i></i><i></i></span>';
}

function pretty(v=''){
  return String(v).replaceAll('_',' ').replace(/\b\w/g, m => m.toUpperCase());
}

async function ask(){
  const question = q.value.trim();
  if(!question) return;

  starters.style.display = 'none';
  addMessage('user', esc(question));
  q.value = '';
  send.disabled = true;

  const loading = addMessage('assistant', loadingMarkup());

  try{
    const r = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({question, thread_id: threadId})
    });
    const data = await r.json();
    if(!r.ok) throw new Error(data.detail || 'Request failed');

    loading.remove();

    let meta = `<div class="meta-card"><div class="verification">`;

    if(data.need_retrieval !== undefined){
      meta += `<span class="tag">ROUTE · ${data.need_retrieval ? 'RETRIEVE' : 'DIRECT'}</span>`;
    }
    if(data.issup){
      meta += `<span class="tag ok">IsSUP · ${esc(pretty(data.issup))}</span>`;
    }
    if(data.isuse){
      meta += `<span class="tag ok">IsUSE · ${esc(pretty(data.isuse))}</span>`;
    }
    if(data.rewrite_tries){
      meta += `<span class="tag">REWRITES · ${data.rewrite_tries}</span>`;
    }
    if(data.retries){
      meta += `<span class="tag">REVISIONS · ${data.retries}</span>`;
    }
    meta += `</div>`;

    if(data.sources && data.sources.length){
      meta += '<div class="sources">' + data.sources.map(s => `
        <div class="source">
          <span class="source-icon">▱</span>
          <span>${esc(s.title || s.source || 'Project document')}${s.page ? ' · p.' + s.page : ''}</span>
        </div>`).join('') + '</div>';
    }

    if(data.evidence && data.evidence.length){
      meta += `<div class="trace"><details><summary>Supporting evidence from documents</summary><ol>${
        data.evidence.map(e => `<li>${esc(e)}</li>`).join('')
      }</ol></details></div>`;
    }

    meta += '</div>';

    addMessage('assistant', esc(data.answer), meta);
  }
  catch(e){
    loading.remove();
    addMessage('assistant', 'Request failed: ' + esc(e.message));
  }
  finally{
    send.disabled = false;
    q.focus();
  }
}

send.addEventListener('click', ask);
q.addEventListener('keydown', e => {
  if(e.key === 'Enter' && !e.shiftKey){ e.preventDefault(); ask(); }
});
starters.addEventListener('click', e => {
  const b = e.target.closest('button[data-q]');
  if(!b) return;
  q.value = b.dataset.q;
  q.focus();
});

fileInput.addEventListener('change', () => {
  fileLabel.textContent = fileInput.files[0]?.name || 'Choose document';
  uploadStatus.textContent = '';
});

upload.addEventListener('click', async () => {
  const file = fileInput.files[0];
  if(!file){ uploadStatus.textContent = 'Choose a document first.'; return; }
  upload.disabled = true;
  uploadStatus.textContent = 'Indexing project document…';
  try{
    const fd = new FormData();
    fd.append('file', file);
    const r = await fetch('/api/upload', {method:'POST', body: fd});
    const d = await r.json();
    if(!r.ok) throw new Error(d.detail || 'Upload failed');
    uploadStatus.textContent = `✓ ${d.chunks_indexed} chunks indexed in ${d.namespace}`;
  }
  catch(e){
    uploadStatus.textContent = 'Error: ' + e.message;
  }
  finally{
    upload.disabled = false;
  }
});

newSessionBtn?.addEventListener('click', () => {
  threadId = newThreadId();
  localStorage.setItem(THREAD_KEY, threadId);
  renderSession();
  messages.innerHTML = `
    <div class="message assistant">
      <div class="avatar">T</div>
      <div class="message-body">
        <div class="message-label">TUNAJENGA COPILOT</div>
        <div class="bubble intro">New project session started. Ask about specs, drawings, BoQs, contracts, or site procedures — I'll build context across your follow-up questions.</div>
      </div>
    </div>`;
  starters.style.display = 'flex';
  q.value = '';
  q.focus();
});