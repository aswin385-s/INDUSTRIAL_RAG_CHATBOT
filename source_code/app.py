import base64

import streamlit as st
import streamlit.components.v1 as components

from rag import IndustrialChatbot

st.set_page_config(page_title="Industrial Chatbot", page_icon="✨")

ICON_SVG = """
<svg width="64" height="64" viewBox="0 0 110 110" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="dg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#3fd9b4"/>
      <stop offset="0.45" stop-color="#2f8ff0"/>
      <stop offset="1" stop-color="#1b3fd8"/>
    </linearGradient>
    <radialGradient id="hl" cx="0.35" cy="0.3" r="0.6">
      <stop offset="0" stop-color="#fff" stop-opacity="0.55"/>
      <stop offset="1" stop-color="#fff" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <path d="M46 4 C50 34 60 46 90 50 C60 54 50 66 46 96 C42 66 32 54 2 50 C32 46 42 34 46 4 Z"
        fill="url(#dg)"/>
  <path d="M46 4 C50 34 60 46 90 50 C60 54 50 66 46 96 C42 66 32 54 2 50 C32 46 42 34 46 4 Z"
        fill="url(#hl)"/>
  <path d="M94 66 C95.5 77 99 81 108 83 C99 85 95.5 89 94 100 C92.5 89 89 85 80 83 C89 81 92.5 77 94 66 Z"
        fill="url(#dg)"/>
  <g transform="translate(46 51)">
    <line x1="0" y1="-14" x2="0" y2="-9" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
    <circle cx="0" cy="-16" r="2.6" fill="#fff"/>
    <rect x="-14" y="-9" width="28" height="22" rx="8" fill="#fff"/>
    <rect x="-17" y="-1" width="3" height="7" rx="1.5" fill="#fff"/>
    <rect x="14" y="-1" width="3" height="7" rx="1.5" fill="#fff"/>
    <circle cx="-5.5" cy="1.5" r="2.8" fill="#1b3fd8"/>
    <circle cx="5.5" cy="1.5" r="2.8" fill="#1b3fd8"/>
    <rect x="-4" y="7" width="8" height="2" rx="1" fill="#1b3fd8"/>
  </g>
</svg>
"""

FACTORY_GLASS_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800">
  <defs>
    <linearGradient id="disc" x1="0.15" y1="0" x2="0.85" y2="1">
      <stop offset="0" stop-color="#8fd2ff" stop-opacity="0.75"/>
      <stop offset="0.55" stop-color="#4a9cf0" stop-opacity="0.55"/>
      <stop offset="1" stop-color="#2d6fd6" stop-opacity="0.6"/>
    </linearGradient>
    <radialGradient id="shine" cx="0.3" cy="0.18" r="0.55">
      <stop offset="0" stop-color="#fff" stop-opacity="0.65"/>
      <stop offset="1" stop-color="#fff" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="bld" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#fff" stop-opacity="0.85"/>
      <stop offset="1" stop-color="#e3f2ff" stop-opacity="0.6"/>
    </linearGradient>
    <filter id="glass" x="-5%" y="-5%" width="110%" height="110%">
      <feGaussianBlur in="SourceAlpha" stdDeviation="7" result="blur"/>
      <feSpecularLighting in="blur" surfaceScale="7" specularConstant="1" specularExponent="28"
                          lighting-color="#ffffff" result="spec">
        <fePointLight x="170" y="90" z="280"/>
      </feSpecularLighting>
      <feComposite in="spec" in2="SourceAlpha" operator="in" result="specIn"/>
      <feComposite in="SourceGraphic" in2="specIn" operator="arithmetic" k1="0" k2="1" k3="1" k4="0"/>
    </filter>
  </defs>

  <g filter="url(#glass)">
    <circle cx="400" cy="400" r="332" fill="url(#disc)"/>
  </g>
  <circle cx="400" cy="400" r="330" fill="none" stroke="#fff" stroke-opacity="0.7" stroke-width="4"/>
  <ellipse cx="330" cy="190" rx="210" ry="110" fill="url(#shine)"/>

  <g filter="url(#glass)">
    <g fill="url(#bld)">
      <rect x="198" y="370" width="404" height="204"/>
      <polygon points="242,306 280,326 280,370 242,370"/>
      <polygon points="334,306 374,326 374,370 334,370"/>
      <polygon points="427,306 466,326 466,370 427,370"/>
      <polygon points="518,258 558,258 558,270 554,270 558,370 518,370 522,270 518,270"/>
    </g>
    <path d="M412 192 C398 202 404 226 430 231 C446 246 482 249 502 241 C523 246 541 230 531 214
             C536 198 510 184 490 195 C470 175 430 176 412 192 Z"
          fill="none" stroke="#fff" stroke-opacity="0.85" stroke-width="10" stroke-linejoin="round"/>
  </g>

  <g fill="#bfe3ff" fill-opacity="0.35" stroke="#2f6fd0" stroke-opacity="0.6" stroke-width="5">
    <rect x="225" y="403" width="72" height="32"/>
    <rect x="318" y="403" width="72" height="32"/>
    <rect x="411" y="403" width="72" height="32"/>
    <rect x="504" y="403" width="72" height="32"/>
    <rect x="225" y="463" width="43" height="70"/>
    <rect x="531" y="463" width="44" height="70"/>
    <rect x="346" y="477" width="109" height="97"/>
  </g>
</svg>
"""
FACTORY_URI = "data:image/svg+xml;base64," + base64.b64encode(FACTORY_GLASS_SVG.encode()).decode()
LOGO_URI = "data:image/svg+xml;base64," + base64.b64encode(ICON_SVG.encode()).decode()

CSS = """
<style>
:root {
  --glass-bg: linear-gradient(135deg, rgba(255,255,255,0.55), rgba(255,255,255,0.18));
  --glass-border: rgba(255,255,255,0.65);
  --glass-shadow:
      0 8px 32px rgba(40, 110, 190, 0.18),
      inset 0 1px 1px rgba(255,255,255,0.9),
      inset 0 -1px 2px rgba(120,180,255,0.25);
  --ink: #10294d;
}

html, body {
  background:
    radial-gradient(900px 600px at 10% 10%, #d9f0ff 0%, transparent 60%),
    radial-gradient(800px 600px at 90% 20%, #bfe3ff 0%, transparent 55%),
    radial-gradient(900px 700px at 50% 100%, #cfeeff 0%, transparent 60%),
    linear-gradient(160deg, #e6f5ff, #bfe0fb) !important;
  background-attachment: fixed !important;
}

body::before {
  content: "";
  position: fixed;
  top: 50%;
  left: calc(50% + 10.5rem);
  width: min(80vh, 62vw);
  height: min(80vh, 62vw);
  transform: translate(-50%, -50%);
  background: url("__FACTORY__") center / contain no-repeat;
  filter: drop-shadow(0 30px 60px rgba(40,110,200,0.35));
  opacity: 0.9;
  pointer-events: none;
  z-index: 0;
}
@media (max-width: 900px) { body::before { left: 50%; } }

.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"],
[data-testid="stBottom"], [data-testid="stBottom"] > div {
  background: transparent !important;
}
[data-testid="stAppViewContainer"], [data-testid="stSidebar"], [data-testid="stHeader"] {
  position: relative; z-index: 1;
}
html, body, .stApp, p, span, label, li, h1, h2, h3, div { color: var(--ink); }

[data-testid="stSidebar"] {
  background: var(--glass-bg) !important;
  backdrop-filter: blur(28px) saturate(180%);
  -webkit-backdrop-filter: blur(28px) saturate(180%);
  border-right: 1px solid var(--glass-border);
  box-shadow: var(--glass-shadow);
}

.hero { display: flex; align-items: center; gap: 14px; margin-bottom: 2px; }
.hero h1 { margin: 0; padding: 0; font-size: 2.1rem; font-weight: 700; }
.hero-sub {
  margin: 0 0 18px 0 !important;
  padding-left: 78px !important;
  opacity: 0.7;
  font-size: 0.95rem;
}

.glass-box {
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  border-radius: 18px;
  padding: 12px 16px;
  margin: 10px 0;
  backdrop-filter: blur(18px) saturate(170%);
  -webkit-backdrop-filter: blur(18px) saturate(170%);
  box-shadow: var(--glass-shadow);
  transition: transform .25s ease, box-shadow .25s ease;
}
.glass-box:hover { transform: translateY(-2px) scale(1.01); }
.glass-box .k { font-size: 0.75rem; font-weight: 600; opacity: 0.6; }
.glass-box .v { font-size: 0.95rem; font-weight: 600; }

.stButton > button {
  background: var(--glass-bg) !important;
  color: var(--ink) !important;
  border: 1px solid var(--glass-border) !important;
  border-radius: 999px !important;
  padding: 0.45rem 1.4rem !important;
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  box-shadow: var(--glass-shadow) !important;
  transition: transform .2s ease, box-shadow .2s ease, background .2s ease;
}
.stButton > button:hover {
  transform: translateY(-2px) scale(1.03);
  background: linear-gradient(135deg, rgba(255,255,255,0.8), rgba(190,225,255,0.45)) !important;
  box-shadow: 0 12px 36px rgba(40,110,190,0.28), inset 0 1px 2px #fff !important;
}
.stButton > button:active { transform: scale(0.97); }

[data-testid="stChatMessage"] {
  background: var(--glass-bg) !important;
  border: 1px solid var(--glass-border);
  border-radius: 22px;
  padding: 14px 18px;
  backdrop-filter: blur(20px) saturate(170%);
  -webkit-backdrop-filter: blur(20px) saturate(170%);
  box-shadow: var(--glass-shadow);
}

[data-testid="stChatMessageAvatarUser"],
[data-testid="chatAvatarIcon-user"] {
  background: #ffffff !important;
  color: var(--ink) !important;
  border: 1px solid var(--glass-border);
  box-shadow: 0 4px 12px rgba(40,110,190,0.2), inset 0 1px 2px #fff;
}
[data-testid="stChatMessageAvatarAssistant"],
[data-testid="chatAvatarIcon-assistant"] {
  background: rgba(255,255,255,0.75) url("__LOGO__") center / 82% no-repeat !important;
  border: 1px solid var(--glass-border);
  box-shadow: 0 4px 12px rgba(40,110,190,0.2), inset 0 1px 2px #fff;
}
[data-testid="stChatMessageAvatarAssistant"] > *,
[data-testid="chatAvatarIcon-assistant"] > * { opacity: 0 !important; }

[data-testid="stBottom"] > div { padding-bottom: 3.2rem !important; }
[data-testid="stMainBlockContainer"], .block-container { padding-bottom: 9rem !important; }

[data-testid="stChatInput"] { background: transparent !important; }
[data-testid="stChatInput"] > div {
  background: var(--glass-bg) !important;
  border: 1px solid var(--glass-border) !important;
  border-radius: 20px !important;
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  box-shadow: var(--glass-shadow);
}
[data-testid="stChatInput"] textarea { color: #000 !important; }
[data-testid="stChatInput"] textarea::placeholder,
[data-testid="stChatInputTextArea"]::placeholder {
  color: #000 !important;
  opacity: 0.8 !important;
  -webkit-text-fill-color: #000 !important;
}
[data-testid="stChatInput"] button {
  background: linear-gradient(135deg, #5fd8ff, #2f7cf0) !important;
  border-radius: 50% !important;
  box-shadow: 0 4px 14px rgba(47,124,240,0.45), inset 0 1px 2px rgba(255,255,255,0.8);
}
[data-testid="stChatInput"] button svg { fill: #fff !important; color: #fff !important; }

[data-testid="stExpander"] {
  background: var(--glass-bg);
  border: 1px solid var(--glass-border) !important;
  border-radius: 18px;
  backdrop-filter: blur(16px) saturate(170%);
  -webkit-backdrop-filter: blur(16px) saturate(170%);
  box-shadow: var(--glass-shadow);
}
[data-testid="stExpander"] { overflow: hidden; }
[data-testid="stExpander"] details,
[data-testid="stExpander"] details[open],
[data-testid="stExpanderDetails"] {
  background: transparent !important;
  border: none !important;
  border-radius: 18px;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary:hover,
[data-testid="stExpander"] summary:focus,
[data-testid="stExpander"] summary:active,
[data-testid="stExpander"] details[open] > summary,
[data-testid="stExpander"] details[open] > summary:hover {
  background: transparent !important;
  color: var(--ink) !important;
  border-radius: 18px;
}
[data-testid="stExpander"] summary *,
[data-testid="stExpander"] summary svg {
  color: var(--ink) !important;
  fill: var(--ink);
}

[data-testid="stSlider"] [role="slider"] {
  background: linear-gradient(135deg, #fff, #bfe3ff) !important;
  border: 1px solid #fff;
  box-shadow: 0 3px 10px rgba(40,110,190,0.4), inset 0 1px 2px #fff;
}

[data-testid="stSpinner"] { color: var(--ink); }

#liquid-canvas {
  position: fixed; inset: 0; width: 100vw; height: 100vh;
  pointer-events: none; z-index: 0;
}
@media (prefers-reduced-motion: reduce) { #liquid-canvas { display: none; } }
</style>
""".replace("__FACTORY__", FACTORY_URI).replace("__LOGO__", LOGO_URI)

st.markdown(CSS, unsafe_allow_html=True)

components.html(
    """
<script>
(function () {
  const P = window.parent, D = P.document;
  if (D.getElementById('liquid-script')) return;
  const old = D.getElementById('liquid-canvas'); if (old) old.remove();

  function liquid() {
    const canvas = document.createElement('canvas');
    canvas.id = 'liquid-canvas';
    document.body.appendChild(canvas);
    const ctx = canvas.getContext('2d');

    function resize() {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = window.innerWidth * dpr;
      canvas.height = window.innerHeight * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();
    window.addEventListener('resize', resize);

    const mouse = { x: window.innerWidth / 2, y: window.innerHeight / 2, lx: 0, ly: 0 };
    const blob = { x: mouse.x, y: mouse.y };
    const ripples = [], drops = [];
    let travelled = 0;

    window.addEventListener('mousemove', (e) => {
      mouse.x = e.clientX; mouse.y = e.clientY;
      travelled += Math.hypot(e.clientX - mouse.lx, e.clientY - mouse.ly);
      if (travelled > 38) {
        travelled = 0;
        ripples.push({ x: e.clientX, y: e.clientY, r: 4, a: 0.55 });
        if (Math.random() < 0.5) {
          drops.push({
            x: e.clientX + (Math.random() - 0.5) * 26,
            y: e.clientY + (Math.random() - 0.5) * 26,
            r: 3 + Math.random() * 6, a: 0.5,
            vx: (Math.random() - 0.5) * 0.6, vy: 0.3 + Math.random() * 0.8
          });
        }
      }
      mouse.lx = e.clientX; mouse.ly = e.clientY;
    });
    window.addEventListener('mousedown', (e) => {
      for (let i = 0; i < 3; i++)
        ripples.push({ x: e.clientX, y: e.clientY, r: 4 - i * 6, a: 0.7 - i * 0.15 });
    });

    function frame() {
      ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);

      blob.x += (mouse.x - blob.x) * 0.12;
      blob.y += (mouse.y - blob.y) * 0.12;
      const g = ctx.createRadialGradient(blob.x, blob.y, 0, blob.x, blob.y, 150);
      g.addColorStop(0, 'rgba(120,200,255,0.45)');
      g.addColorStop(0.5, 'rgba(90,170,255,0.18)');
      g.addColorStop(1, 'rgba(90,170,255,0)');
      ctx.fillStyle = g;
      ctx.beginPath(); ctx.arc(blob.x, blob.y, 150, 0, Math.PI * 2); ctx.fill();

      for (let i = ripples.length - 1; i >= 0; i--) {
        const p = ripples[i];
        p.r += 2.2; p.a *= 0.95;
        if (p.a < 0.01) { ripples.splice(i, 1); continue; }
        if (p.r < 0) continue;
        ctx.lineWidth = 2;
        ctx.strokeStyle = 'rgba(255,255,255,' + p.a + ')';
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.stroke();
        ctx.lineWidth = 1;
        ctx.strokeStyle = 'rgba(70,150,235,' + (p.a * 0.6) + ')';
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r + 3, 0, Math.PI * 2); ctx.stroke();
      }

      for (let i = drops.length - 1; i >= 0; i--) {
        const d = drops[i];
        d.x += d.vx; d.y += d.vy; d.a *= 0.965;
        if (d.a < 0.02) { drops.splice(i, 1); continue; }
        const dg = ctx.createRadialGradient(d.x - d.r * 0.3, d.y - d.r * 0.3, 0, d.x, d.y, d.r);
        dg.addColorStop(0, 'rgba(255,255,255,' + d.a + ')');
        dg.addColorStop(1, 'rgba(90,170,255,' + d.a * 0.5 + ')');
        ctx.fillStyle = dg;
        ctx.beginPath(); ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2); ctx.fill();
      }
      window.requestAnimationFrame(frame);
    }
    frame();
  }

  const s = D.createElement('script');
  s.id = 'liquid-script';
  s.textContent = '(' + liquid.toString() + ')();';
  D.head.appendChild(s);
})();
</script>
""",
    height=0,
)

components.html(
    """
<script>
(function () {
  const P = window.parent;
  const D = P.document;
  if (D.getElementById('chat-selection-autoscroll-script')) return;

  let rafId = null;
  let pointerY = null;
  let pointerX = null;
  let selecting = false;

  function getScrollables() {
    const selection = D.getSelection();
    const anchor = selection && selection.anchorNode;
    let el = anchor ? (anchor.nodeType === 1 ? anchor : anchor.parentElement) : null;
    const list = [];
    const seen = new Set();

    while (el && el !== D.body && el !== D.documentElement) {
      const css = P.getComputedStyle(el);
      if (/(auto|scroll|overlay)/.test(css.overflowY) && el.scrollHeight > el.clientHeight + 2) {
        list.push(el);
        seen.add(el);
      }
      el = el.parentElement;
    }

    const selectors = [
      '[data-testid="stMain"]',
      '[data-testid="stAppViewContainer"]',
      '[data-testid="stMainBlockContainer"]',
      '.main',
      '.block-container',
      'section[data-testid="stSidebar"]'
    ];
    for (const selector of selectors) {
      for (const node of D.querySelectorAll(selector)) {
        const css = P.getComputedStyle(node);
        if (/(auto|scroll|overlay)/.test(css.overflowY) &&
            node.scrollHeight > node.clientHeight + 2 && !seen.has(node)) {
          list.push(node);
          seen.add(node);
        }
      }
    }

    const docScroller = D.scrollingElement || D.documentElement;
    if (docScroller && !seen.has(docScroller)) list.push(docScroller);
    return list;
  }

  function scrollOne(delta) {
    if (!delta) return;
    const candidates = getScrollables();
    for (const el of candidates) {
      const before = el.scrollTop;
      const maxTop = Math.max(0, el.scrollHeight - el.clientHeight);
      const next = Math.max(0, Math.min(maxTop, before + delta));
      if (next !== before) {
        el.scrollTop = next;
        if (el.scrollTop !== before) return;
      }
    }
    P.scrollBy(0, delta);
  }

  function tick() {
    rafId = null;
    if (!selecting || pointerY === null) return;

    const edge = 85;
    const distanceFromEdge = pointerY > P.innerHeight - edge
      ? pointerY - (P.innerHeight - edge)
      : pointerY < edge ? edge - pointerY : 0;

    if (distanceFromEdge > 0) {
      const direction = pointerY > P.innerHeight - edge ? 1 : -1;
      const speed = Math.min(22, 3 + distanceFromEdge * 0.45);
      scrollOne(direction * speed);
    }

    rafId = P.requestAnimationFrame(tick);
  }

  function startLoop() {
    if (rafId === null && selecting) rafId = P.requestAnimationFrame(tick);
  }

  function onDown(e) {
    selecting = true;
    pointerX = e.clientX;
    pointerY = e.clientY;
    startLoop();
  }

  function onMove(e) {
    if (!selecting || (typeof e.buttons === 'number' && e.buttons === 0)) return;
    pointerX = e.clientX;
    pointerY = e.clientY;
    startLoop();
  }

  function stop() {
    selecting = false;
    pointerY = null;
    if (rafId !== null) P.cancelAnimationFrame(rafId);
    rafId = null;
  }

  D.addEventListener('mousedown', onDown, true);
  D.addEventListener('mousemove', onMove, true);
  D.addEventListener('mouseup', stop, true);
  D.addEventListener('pointerdown', onDown, true);
  D.addEventListener('pointermove', onMove, true);
  D.addEventListener('pointerup', stop, true);
  P.addEventListener('blur', stop);

  const marker = D.createElement('script');
  marker.id = 'chat-selection-autoscroll-script';
  D.head.appendChild(marker);
})();
</script>
""",
    height=0,
)


@st.cache_resource(show_spinner="Loading models...")
def load_bot():
    return IndustrialChatbot()


bot = load_bot()

if "messages" not in st.session_state:
    st.session_state.messages = []

st.markdown(
    f"""
<div class="hero">{ICON_SVG}<h1>AI-Powered Industrial Chatbot</h1></div>
<div class="hero-sub">Ask any questions about industrial maintenance</div>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Settings")
    top_k = st.slider("Chunks retrieved (top-k)", 1, 6, 3)
    st.markdown(
        """
<div class="glass-box"><div class="k">LLM</div><div class="v">Qwen2.5-0.5B-Instruct</div></div>
<div class="glass-box"><div class="k">Embeddings</div><div class="v">all-MiniLM-L6-v2</div></div>
<div class="glass-box"><div class="k">Vector DB</div><div class="v">FAISS</div></div>
""",
        unsafe_allow_html=True,
    )
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if question := st.chat_input("e.g. How often should the mechanical seal be replaced?"):
    previous_question = next(
      (
          message["content"]
          for message in reversed(st.session_state.messages)
          if message["role"] == "user"
      ),
      None,
    )
    previous_answer = next(
      (
          message["content"]
          for message in reversed(st.session_state.messages)
          if message["role"] == "assistant"
      ),
      None,
    )
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching documents and generating answer..."):
            answer, hits = bot.answer(
                question,
                k=top_k,
                previous_question=previous_question,
                previous_answer=previous_answer,
            )
        st.markdown(answer)
        with st.expander("Retrieved sources"):
            for h in hits:
                st.markdown(f"**{h['source']}** (chunk {h['chunk_id']}, similarity {h['score']:.2f})")
                st.caption(h["text"])
    st.session_state.messages.append({"role": "assistant", "content": answer})