// ── Mobile: fix de altura del viewport ────────────
// En móvil, el teclado virtual reduce el viewport pero 100dvh no siempre
// se actualiza a tiempo. Usamos --vh como variable CSS actualizada por JS.
function setVh() {
  const vh = (window.visualViewport?.height ?? window.innerHeight) * 0.01;
  document.documentElement.style.setProperty("--vh", `${vh}px`);
}
setVh();
if (window.visualViewport) {
  window.visualViewport.addEventListener("resize", () => {
    setVh();
    // Scroll al último mensaje cuando se abre/cierra el teclado
    setTimeout(() => messagesEl?.scrollTo({ top: messagesEl.scrollHeight, behavior: "instant" }), 50);
  });
} else {
  window.addEventListener("resize", setVh);
}

// ── Elementos ─────────────────────────────────────
const messagesEl = document.getElementById("messages");
const userInput  = document.getElementById("userInput");
const sendBtn    = document.getElementById("sendBtn");

// ── Config ─────────────────────────────────────────
const BACKEND_URL = localStorage.getItem("m2_backend_url") || "";
const HISTORY_KEY = "m2_history";
const SESSION_KEY = "m2_session_id";

// ── Sesión persistente ─────────────────────────────
let sessionId = localStorage.getItem(SESSION_KEY);
if (!sessionId) {
  sessionId = "sess-" + Math.random().toString(36).substring(2, 9);
  localStorage.setItem(SESSION_KEY, sessionId);
}

// ── Historial persistente ──────────────────────────
// Formato: [{ role: "user"|"bot", text: "...", html: "..." }]
let history = [];

function loadHistory() {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (raw) history = JSON.parse(raw);
  } catch { history = []; }
}

function saveHistory() {
  // Guardar solo los últimos 200 mensajes para no sobrepasar el límite
  const trimmed = history.slice(-200);
  try { localStorage.setItem(HISTORY_KEY, JSON.stringify(trimmed)); } catch {}
}

// ── Marked config ──────────────────────────────────
if (typeof marked !== "undefined") {
  marked.setOptions({ breaks: true, gfm: true });
}

// ── Scroll ─────────────────────────────────────────
function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

// ── Renderizar un mensaje en pantalla ──────────────
function renderMessage(role, htmlContent) {
  const isUser = role === "user";
  const div = document.createElement("div");
  div.className = `msg ${isUser ? "user" : "bot"}`;

  const avatar = document.createElement("div");
  avatar.className = "msg-avatar";
  avatar.textContent = isUser ? "Tú" : "M2";

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";
  bubble.innerHTML = htmlContent;

  div.appendChild(avatar);
  div.appendChild(bubble);
  messagesEl.appendChild(div);
  return bubble;
}

// ── Cargar historial al iniciar ────────────────────
function initHistory() {
  loadHistory();
  for (const entry of history) {
    renderMessage(entry.role, entry.html);
  }
  scrollToBottom();
}

// ── Typing indicator ───────────────────────────────
function showTyping() {
  const div = document.createElement("div");
  div.className = "msg bot";
  div.id = "typing-indicator";

  const avatar = document.createElement("div");
  avatar.className = "msg-avatar";
  avatar.textContent = "M2";

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";
  bubble.innerHTML = `<div class="typing"><span></span><span></span><span></span></div>`;

  div.appendChild(avatar);
  div.appendChild(bubble);
  messagesEl.appendChild(div);
  scrollToBottom();
  return bubble;
}

function removeTyping() {
  const el = document.getElementById("typing-indicator");
  if (el) el.remove();
}

// ── Textarea auto-resize ───────────────────────────
function autoResize() {
  userInput.style.height = "auto";
  userInput.style.height = Math.min(userInput.scrollHeight, 160) + "px";
}
userInput.addEventListener("input", autoResize);

// ── Enter envía, Shift+Enter = nueva línea ─────────
userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    handleSend();
  }
});

// ── Enviar mensaje ─────────────────────────────────
let isLoading = false;

async function handleSend() {
  const text = userInput.value.trim();
  if (!text || isLoading) return;

  isLoading = true;
  sendBtn.disabled = true;

  // Mostrar mensaje del usuario
  const userHtml = escapeHtml(text).replace(/\n/g, "<br>");
  renderMessage("user", userHtml);
  history.push({ role: "user", html: userHtml });
  saveHistory();

  userInput.value = "";
  autoResize();

  // Typing
  const botBubble = showTyping();

  try {
    const url = `${BACKEND_URL}/api/ask?q=${encodeURIComponent(text)}&session_id=${encodeURIComponent(sessionId)}`;
    const res  = await fetch(url);
    const data = await res.json();

    removeTyping();

    let botHtml;

    if (!data.success) {
      // Error amigable con markdown
      botHtml = typeof marked !== "undefined"
        ? marked.parse(data.message || "No se encontró información.")
        : `<p>${data.message}</p>`;
    } else if (data.type === "conversational") {
      // Respuesta conversacional — markdown
      botHtml = typeof marked !== "undefined"
        ? marked.parse(data.message)
        : `<p>${data.message}</p>`;
    } else if (data.type === "wiki_card_with_ai") {
      // Explicación inteligente con IA + ficha oficial de la wiki
      const aiText = data.message ? (typeof marked !== "undefined" ? marked.parse(data.message) : `<p>${data.message}</p>`) : "";
      const cardHtml = buildWikiCard(data);
      botHtml = `<div class="ai-comment">${aiText}</div>` + cardHtml;
    } else {
      // Respuesta wiki directa
      botHtml = buildWikiCard(data);
    }

    const bubble = renderMessage("bot", botHtml);
    bubble.style.opacity = "0";
    requestAnimationFrame(() => {
      bubble.style.transition = "opacity 0.25s";
      bubble.style.opacity = "1";
    });

    history.push({ role: "bot", html: botHtml });
    saveHistory();
    scrollToBottom();

  } catch (err) {
    removeTyping();
    const errHtml = `<p style="color:#ef4444;">Error de conexión: ${err.message}</p>`;
    renderMessage("bot", errHtml);
    history.push({ role: "bot", html: errHtml });
    saveHistory();
    scrollToBottom();
  } finally {
    isLoading = false;
    sendBtn.disabled = false;
    userInput.focus();
  }
}

sendBtn.addEventListener("click", handleSend);

// ── Escape HTML ────────────────────────────────────
function escapeHtml(t) {
  return t.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

// ── Construir card de wiki ─────────────────────────
function buildWikiCard(res) {
  const ent  = res.entity;
  const data = res.data;

  let h = `<div class="item-card">`;

  // Header
  h += `<div class="item-header">`;
  if (data.main_image) h += `<img src="${data.main_image}" class="item-img" alt="${ent.title_es}" loading="lazy">`;
  h += `<div class="item-title">
    <h2>${ent.title_es}</h2>
    <div class="item-subtitle">${ent.category_label}${data.level ? ` · Nivel ${data.level}` : ""}</div>
  </div></div>`;

  // Tabla mejoras
  if (data.upgrades && data.upgrades.length > 0) {
    h += `<div class="table-scroll"><table class="upgrade-table">
      <thead><tr><th>Nivel</th><th>Coste</th><th>Materiales</th><th>Atributos</th></tr></thead>
      <tbody>`;
    for (const up of data.upgrades) {
      let mats = `<span style="color:#555">—</span>`;
      if (up.materials?.length) {
        mats = up.materials.map(m => `
          <div class="mat-item">
            ${m.icon_url ? `<img src="${m.icon_url}" loading="lazy">` : ""}
            ${m.display || m.name_es}
          </div>`).join("");
      }
      h += `<tr>
        <td><strong>${up.from_to}</strong></td>
        <td class="yang-val">${up.yang}</td>
        <td>${mats}</td>
        <td style="color:#a7f3d0;font-size:0.75rem;">${up.stats?.join("<br>") ?? "—"}</td>
      </tr>`;
    }
    h += `</tbody></table></div>`;
  }

  // Misiones
  if (ent.type === "quest") {
    h += `<div style="font-size:0.85rem;line-height:1.7;margin-top:8px;">`;
    if (data.quest_giver) h += `<p><strong>Personaje (PNJ):</strong> ${data.quest_giver}</p>`;
    if (data.level)       h += `<p><strong>Nivel requerido:</strong> ${data.level}</p>`;
    if (data.items?.length) {
      h += `<div style="margin-top:6px;"><strong>Objetos requeridos:</strong><div style="margin-top:4px;">`;
      h += data.items.map(i => `<div class="mat-item">${i.icon_url?`<img src="${i.icon_url}" loading="lazy">`:""}${i.display || i.name_es}</div>`).join("");
      h += `</div></div>`;
    }
    if (data.rewards_text) h += `<p style="margin-top:6px;"><strong>Recompensa:</strong> ${data.rewards_text}</p>`;
    if (data.solution)     h += `<p style="margin-top:6px;color:#8e8ea0;"><strong>Cómo completarla:</strong> ${data.solution}</p>`;
    h += `</div>`;
  }

  // Drops
  if (data.drops_raw) {
    h += `<div class="drop-box"><strong>Dónde se consigue (Drops): </strong>${data.drops_raw}</div>`;
  }

  // Wiki link
  h += `<a href="${ent.wiki_url}" target="_blank" rel="noopener noreferrer" class="wiki-link">
    🔗 Ver artículo oficial en Metin2 Wiki ↗
  </a></div>`;

  return h;
}

// ── Init ───────────────────────────────────────────
initHistory();
userInput.focus();
