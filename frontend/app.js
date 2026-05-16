/**
 * WAIT — app.js v4 (STREAMING AUTO-THINK)
 * Protocole backend Qt/C++ (port 1234)
 * Tout le texte vient de reponse_part, le JS segmente <think> lui-même
 */

'use strict';

// ── Éléments DOM ─────────────────────────────────────────────────────────────

const statusDot = document.getElementById('statusDot');
const statusLabel = document.getElementById('statusLabel');
const btnConnect = document.getElementById('btnConnect');
const messagesContainer = document.getElementById('messagesContainer');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const iconGrid = document.getElementById('iconGrid');
const iconCount = document.getElementById('iconCount');
const clearBtn = document.getElementById('clearBtn');

// ── État ──────────────────────────────────────────────────────────────────────

const WS_URL = 'ws://localhost:1234';

let ws = null;
let currentLLMBubble = null;
let currentThinkBlock = null;
let currentThinkContent = null;
let currentCursor = null;
let isConnected = false;
let inThinkMode = false;
let iconItems = [];
let streamAcc = ''; // buffer persistant pour le streaming

// ── WebSocket ─────────────────────────────────────────────────────────────────

function connect() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;

  setStatus('connecting');
  addSystemMsg('Connexion vers <code>' + WS_URL + '</code>…');

  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    isConnected = true;
    setStatus('connected');
    setInputEnabled(true);
    addSystemMsg('Connexion établie. Prêt.');
    btnConnect.textContent = 'DÉCONNECTER';
    btnConnect.classList.add('active');
  };

  ws.onclose = (ev) => {
    isConnected = false;
    setStatus('disconnected');
    setInputEnabled(false);
    finaliseStreamIfOpen();
    addSystemMsg('Connexion fermée. Code ' + ev.code + (ev.reason? ' — ' + ev.reason : '') + '.');
    btnConnect.textContent = 'CONNECTER';
    btnConnect.classList.remove('active');
  };

  ws.onerror = () => {
    addSystemMsg('Erreur WebSocket. Vérifiez que le serveur WAIT tourne sur le port 1234.');
  };

  ws.onmessage = (ev) => handleMessage(ev.data);
}

function disconnect() {
  if (ws) ws.close(1000, 'Fermeture manuelle');
}

// ── Réception ─────────────────────────────────────────────────────────────────

function handleMessage(raw) {
  let parsed;
  try { parsed = JSON.parse(raw); }
  catch { return; }

  const type = parsed.type?? '';
  const payload = parsed.payload?? {};

  switch (type) {

    case 'LLM/rep': {
      const chunk = payload.reponse_part?? '';
      if (chunk === '') break;
      processIncomingText(chunk);
      break;
    }

    case 'LLM/end': {
      finaliseStreamIfOpen();
      streamAcc = '';
      if (inThinkMode) closeThinkBlock();
      break;
    }

    case 'k3/icons': {
      renderIcons(payload.icons?? []);
      break;
    }

    default: {
      addSystemMsg('Paquet inconnu — type: <code>' + escapeHtml(type) + '</code>');
    }
  }
}

// ── Parser streaming robuste ──────────────────────────────────────────────────

function processIncomingText(chunk) {
  streamAcc += chunk;

  while (streamAcc.length > 0) {
    if (!inThinkMode) {
      const startIdx = streamAcc.indexOf('<think>');
      if (startIdx === -1) {
        // garde un début de balise potentiellement coupé
        const partial = streamAcc.match(/<t?h?i?n?k?$/i);
        if (partial) {
          const keep = partial[0].length;
          if (streamAcc.length > keep) {
            appendLLMChunk(streamAcc.slice(0, -keep));
          }
          streamAcc = streamAcc.slice(-keep);
        } else {
          appendLLMChunk(streamAcc);
          streamAcc = '';
        }
        break;
      }
      if (startIdx > 0) appendLLMChunk(streamAcc.slice(0, startIdx));
      streamAcc = streamAcc.slice(startIdx + 7);
      inThinkMode = true;
    } else {
      const endIdx = streamAcc.indexOf('</think>');
      if (endIdx === -1) {
        const partial = streamAcc.match(/<\/t?h?i?n?k?>?$/i);
        if (partial) {
          const keep = partial[0].length;
          if (streamAcc.length > keep) {
            appendThinkChunk(streamAcc.slice(0, -keep));
          }
          streamAcc = streamAcc.slice(-keep);
        } else {
          appendThinkChunk(streamAcc);
          streamAcc = '';
        }
        break;
      }
      if (endIdx > 0) appendThinkChunk(streamAcc.slice(0, endIdx));
      streamAcc = streamAcc.slice(endIdx + 8);
      closeThinkBlock();
    }
  }
}

// ── Bloc <think> ──────────────────────────────────────────────────────────────

function appendThinkChunk(text) {
  inThinkMode = true;

  if (!currentThinkBlock) {
    const block = document.createElement('div');
    block.classList.add('think-block');

    const header = document.createElement('div');
    header.classList.add('think-header');

    const left = document.createElement('div');
    left.classList.add('think-header-left');

    const dot = document.createElement('span');
    dot.classList.add('think-dot');

    const label = document.createElement('span');
    label.classList.add('think-label');
    label.textContent = 'Raisonnement';

    left.appendChild(dot);
    left.appendChild(label);

    const toggle = document.createElement('span');
    toggle.classList.add('think-toggle');
    toggle.textContent = '▲';

    header.appendChild(left);
    header.appendChild(toggle);

    const content = document.createElement('div');
    content.classList.add('think-content', 'visible');

    header.addEventListener('click', () => {
      const isExpanded = content.classList.contains('visible');
      content.classList.toggle('visible',!isExpanded);
      header.classList.toggle('expanded',!isExpanded);
    });

    block.appendChild(header);
    block.appendChild(content);
    messagesContainer.appendChild(block);

    currentThinkBlock = block;
    currentThinkContent = content;
    scrollBottom();
  }

  currentThinkContent.appendChild(document.createTextNode(text));
  scrollBottom();
}

function closeThinkBlock() {
  if (currentThinkBlock) {
    const dot = currentThinkBlock.querySelector('.think-dot');
    if (dot) dot.classList.add('done');

    const toggle = currentThinkBlock.querySelector('.think-toggle');
    const content = currentThinkBlock.querySelector('.think-content');
    const header = currentThinkBlock.querySelector('.think-header');

    if (content && content.classList.contains('visible')) {
      content.classList.remove('visible');
      if (header) header.classList.remove('expanded');
    }
    if (toggle) toggle.textContent = '▼';
  }

  inThinkMode = false;
  currentThinkBlock = null;
  currentThinkContent = null;
}

// ── Stream LLM ────────────────────────────────────────────────────────────────

function appendLLMChunk(text) {
  if (!currentLLMBubble) {
    const msg = document.createElement('div');
    msg.classList.add('msg-llm');

    const avatar = document.createElement('div');
    avatar.classList.add('llm-avatar');
    avatar.textContent = 'W';

    const wrapper = document.createElement('div');
    wrapper.classList.add('llm-content');

    const prefix = document.createElement('div');
    prefix.classList.add('msg-prefix');

    const prefixLabel = document.createElement('span');
    prefixLabel.textContent = 'WAIT >';

    const timestamp = document.createElement('span');
    timestamp.classList.add('msg-timestamp');
    timestamp.textContent = getTime();

    prefix.appendChild(prefixLabel);
    prefix.appendChild(timestamp);

    const bubble = document.createElement('div');
    bubble.classList.add('bubble');

    currentCursor = document.createElement('span');
    currentCursor.classList.add('stream-cursor');
    bubble.appendChild(currentCursor);

    wrapper.appendChild(prefix);
    wrapper.appendChild(bubble);
    msg.appendChild(avatar);
    msg.appendChild(wrapper);
    messagesContainer.appendChild(msg);

    currentLLMBubble = bubble;
    scrollBottom();
  }

  currentLLMBubble.insertBefore(document.createTextNode(text), currentCursor);
  scrollBottom();
}

function finaliseStreamIfOpen() {
  if (currentCursor && currentCursor.parentNode) currentCursor.remove();
  currentLLMBubble = null;
  currentCursor = null;
  if (inThinkMode) closeThinkBlock();
}

// ── Icônes K3 ─────────────────────────────────────────────────────────────────

function renderIcons(icons) {
  iconItems = Array.isArray(icons)? icons : [];
  iconGrid.innerHTML = '';

  if (iconItems.length === 0) {
    iconGrid.innerHTML = `
      <div class="icon-placeholder">
        <span class="placeholder-dash">— — —</span>
        <span class="placeholder-label">en attente</span>
      </div>`;
    iconCount.textContent = '0';
    iconCount.classList.remove('has-items');
    return;
  }

  iconCount.textContent = iconItems.length;
  iconCount.classList.add('has-items');

  iconItems.forEach(item => {
    const card = document.createElement('div');
    card.classList.add('icon-card');

    const emojiSpan = document.createElement('span');
    emojiSpan.classList.add('icon-emoji');

    const labelSpan = document.createElement('span');
    labelSpan.classList.add('icon-label');

    if (typeof item === 'string') {
      emojiSpan.textContent = item;
    } else {
      emojiSpan.textContent = item.emoji?? '?';
      labelSpan.textContent = item.label?? '';
    }

    card.appendChild(emojiSpan);
    card.appendChild(labelSpan);
    iconGrid.appendChild(card);
  });
}

// ── Envoi ─────────────────────────────────────────────────────────────────────

function sendRequest() {
  const text = userInput.value.trim();
  if (!text ||!isConnected) return;

  finaliseStreamIfOpen();
  addUserMessage(text);

  ws.send(JSON.stringify({ type: 'user/ask', payload: { request: text } }));

  userInput.value = '';
  autoResize(userInput);
}

// ── Messages UI ───────────────────────────────────────────────────────────────

function addUserMessage(text) {
  const msg = document.createElement('div');
  msg.classList.add('msg-user');

  const inner = document.createElement('div');
  inner.classList.add('msg-user-inner');

  const prefix = document.createElement('div');
  prefix.classList.add('msg-prefix');

  const label = document.createElement('span');
  label.textContent = 'VOUS >';

  const timestamp = document.createElement('span');
  timestamp.classList.add('msg-timestamp');
  timestamp.textContent = getTime();

  prefix.appendChild(label);
  prefix.appendChild(timestamp);

  const bubble = document.createElement('div');
  bubble.classList.add('bubble');
  bubble.textContent = text;

  inner.appendChild(prefix);
  inner.appendChild(bubble);
  msg.appendChild(inner);
  messagesContainer.appendChild(msg);
  scrollBottom();
}

function addSystemMsg(html) {
  const msg = document.createElement('div');
  msg.classList.add('system-msg');
  msg.innerHTML = '<span class="sys-prefix">SYS &gt;</span> ' + html;
  messagesContainer.appendChild(msg);
  scrollBottom();
}

// ── Status ────────────────────────────────────────────────────────────────────

function setStatus(state) {
  statusDot.className = 'status-dot';
  document.body.className = '';

  const labels = {
    connected: 'CONNECTÉ',
    disconnected: 'DÉCONNECTÉ',
    connecting: 'CONNEXION…',
  };

  if (state!== 'disconnected') {
    statusDot.classList.add(state);
    document.body.classList.add(state);
  }

  statusLabel.textContent = labels[state]?? state.toUpperCase();
}

function setInputEnabled(enabled) {
  userInput.disabled =!enabled;
  sendBtn.disabled =!enabled;
  if (enabled) userInput.focus();
}

// ── Utilitaires ───────────────────────────────────────────────────────────────

function scrollBottom() {
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function escapeHtml(str) {
  return String(str)
   .replace(/&/g, '&amp;')
   .replace(/</g, '&lt;')
   .replace(/>/g, '&gt;')
   .replace(/"/g, '&quot;');
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 140) + 'px';
}

function getTime() {
  return new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

// ── Écouteurs ─────────────────────────────────────────────────────────────────

btnConnect.addEventListener('click', () => {
  if (isConnected) disconnect(); else connect();
});

sendBtn.addEventListener('click', sendRequest);

userInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' &&!e.shiftKey) {
    e.preventDefault();
    sendRequest();
  }
});

userInput.addEventListener('input', () => autoResize(userInput));

clearBtn.addEventListener('click', () => {
  finaliseStreamIfOpen();
  messagesContainer.innerHTML = '';
  addSystemMsg('Conversation effacée.');
});