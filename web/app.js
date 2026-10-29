const chatContainer = document.getElementById("chatContainer");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");

// ID de sesión único por dispositivo para la memoria de conversación
let sessionId = localStorage.getItem("m2_session_id");
if (!sessionId) {
  sessionId = "sess-" + Math.random().toString(36).substring(2, 9);
  localStorage.setItem("m2_session_id", sessionId);
}

function scrollToBottom() {
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function quickAsk(text) {
  userInput.value = text;
  handleSend(new Event('submit'));
}

async function handleSend(e) {
  if (e) e.preventDefault();
  const text = userInput.value.trim();
  if (!text) return;

  // Render mensaje del usuario
  appendMessage("user", text);
  userInput.value = "";
  userInput.focus();
  sendBtn.disabled = true;

  // Render placeholder de carga
  const botMessageId = "msg-" + Date.now();
  appendMessage("assistant", `<span class="loading-dots">Consultando wiki oficial...</span>`, botMessageId);

  try {
    const response = await fetch(`/api/ask?q=${encodeURIComponent(text)}&session_id=${encodeURIComponent(sessionId)}`);
    const result = await response.json();
    
    const botMsgElement = document.getElementById(botMessageId);
    if (!result.success) {
      botMsgElement.innerHTML = `<p>${result.message || "No se encontró información."}</p>`;
    } else {
      botMsgElement.innerHTML = renderOracleResponse(result);
    }
  } catch (error) {
    const botMsgElement = document.getElementById(botMessageId);
    botMsgElement.innerHTML = `<p style="color:#ef4444;">Error al conectar con el servidor: ${error.message}</p>`;
  } finally {
    sendBtn.disabled = false;
    scrollToBottom();
  }
}

function appendMessage(sender, htmlContent, id = null) {
  const msgDiv = document.createElement("div");
  msgDiv.className = `message ${sender}`;
  if (id) msgDiv.id = id;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.innerText = sender === "user" ? "Tú" : "M2";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = htmlContent;

  msgDiv.appendChild(avatar);
  msgDiv.appendChild(bubble);

  chatContainer.appendChild(msgDiv);
  scrollToBottom();
}

function renderOracleResponse(res) {
  const ent = res.entity;
  const data = res.data;

  let html = `
    <div class="item-card">
      <div class="item-header">
        ${data.main_image ? `<img src="${data.main_image}" class="item-img" alt="${ent.title_es}">` : ''}
        <div class="item-title-group">
          <h2>${ent.title_es}</h2>
          <div class="item-subtitle">${ent.title_de} • ${ent.category_label} ${data.level ? `• Nivel ${data.level}` : ''}</div>
        </div>
      </div>
  `;

  // Renderizar tabla de mejora si es equipamiento
  if (data.upgrades && data.upgrades.length > 0) {
    html += `
      <table class="upgrade-table">
        <thead>
          <tr>
            <th>Nivel</th>
            <th>Coste</th>
            <th>Materiales</th>
            <th>Stats</th>
          </tr>
        </thead>
        <tbody>
    `;

    for (const up of data.upgrades) {
      let matsHtml = '<span style="color:#9ca3af;">Ninguno</span>';
      if (up.materials && up.materials.length > 0) {
        matsHtml = up.materials.map(m => `
          <div class="mat-item">
            ${m.icon_url ? `<img src="${m.icon_url}" alt="${m.name}">` : ''}
            <span>${m.display}</span>
          </div>
        `).join("");
      }

      html += `
        <tr>
          <td><strong>${up.from_to}</strong></td>
          <td class="yang-val">${up.yang}</td>
          <td>${matsHtml}</td>
          <td style="color:#a7f3d0; font-size:0.75rem;">${up.stats ? up.stats.join("<br>") : '-'}</td>
        </tr>
      `;
    }

    html += `</tbody></table>`;
  }

  // Renderizar misiones
  if (ent.type === "quest") {
    html += `
      <div style="font-size:0.85rem; margin-top:8px;">
        <p><strong>PNJ:</strong> ${data.quest_giver}</p>
        <p><strong>Nivel requerido:</strong> ${data.level}</p>
        ${data.items && data.items.length > 0 ? `
          <div style="margin-top:6px;"><strong>Items requeridos:</strong>
            ${data.items.map(i => `<div class="mat-item">${i.icon_url ? `<img src="${i.icon_url}">` : ''} ${i.display}</div>`).join("")}
          </div>` : ''}
        ${data.rewards_text ? `<p style="margin-top:6px;"><strong>Recompensa:</strong> ${data.rewards_text}</p>` : ''}
        ${data.solution ? `<p style="margin-top:6px; color:#cbd5e1;"><em>${data.solution}</em></p>` : ''}
      </div>
    `;
  }

  // Renderizar drops
  if (data.drops_raw) {
    html += `
      <div style="margin-top:10px; font-size:0.82rem; color:#cbd5e1;">
        <strong>Drop / Obtención:</strong> ${data.drops_raw}
      </div>
    `;
  }

  // Enlace a la fuente oficial
  html += `
      <a href="${ent.wiki_url}" target="_blank" rel="noopener noreferrer" class="wiki-link">
        🔗 Ver artículo completo en de-wiki.metin2.gameforge.com ↗
      </a>
    </div>
  `;

  return html;
}
