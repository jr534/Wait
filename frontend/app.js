const socketUrl = "ws://localhost:8765";

const statusEl = document.querySelector("#status");
const formEl = document.querySelector("#askForm");
const inputEl = document.querySelector("#requestInput");
const messagesEl = document.querySelector("#messages");
const waitRailEl = document.querySelector("#waitRail");

let socket;
let waitTimers = [];
let currentAssistantMessage = null;

function setStatus(label, live = false) {
  statusEl.textContent = label;
  statusEl.classList.toggle("is-live", live);
}

function addMessage(role, text) {
  const message = document.createElement("div");
  message.className = `message ${role}`;
  message.textContent = text;
  messagesEl.appendChild(message);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return message;
}

function clearWaitState() {
  waitTimers.forEach((timerId) => window.clearTimeout(timerId));
  waitTimers = [];
  waitRailEl.innerHTML = "";
}

function showWaitIcons(payload) {
  clearWaitState();

  [1, 2, 3].forEach((index) => {
    const delay = Number(payload[`t_icon${index}`] || 0) * 1000;
    const name = payload[`name_icon${index}`] || `icon ${index}`;
    const icon = payload[`icon${index}`];

    const item = document.createElement("div");
    item.className = "wait-icon";
    item.title = name;

    if (icon) {
      const image = document.createElement("img");
      image.alt = name;
      image.src = `data:image/svg+xml;base64,${icon}`;
      item.appendChild(image);
    } else {
      item.textContent = name;
    }

    waitRailEl.appendChild(item);

    const timerId = window.setTimeout(() => {
      item.classList.add("is-visible");
    }, delay);

    waitTimers.push(timerId);
  });
}

function connect() {
  socket = new WebSocket(socketUrl);
  setStatus("Connexion...");

  socket.addEventListener("open", () => setStatus("Connecte", true));
  socket.addEventListener("close", () => {
    setStatus("Deconnecte");
    window.setTimeout(connect, 1500);
  });
  socket.addEventListener("error", () => setStatus("Erreur"));

  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);

    if (message.type === "user/ask/ack") {
      setStatus("Demande recue", true);
    }

    if (message.type === "wait") {
      showWaitIcons(message.payload || {});
    }

    if (message.type === "LLM/rep") {
      clearWaitState();
      const part = message.payload?.reponse_part || "";
      if (!currentAssistantMessage) {
        currentAssistantMessage = addMessage("assistant", "");
      }
      currentAssistantMessage.textContent += part;
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }
  });
}

formEl.addEventListener("submit", (event) => {
  event.preventDefault();

  const request = inputEl.value.trim();
  if (!request || socket?.readyState !== WebSocket.OPEN) {
    return;
  }

  currentAssistantMessage = null;
  clearWaitState();
  addMessage("user", request);
  socket.send(JSON.stringify({ type: "user/ask", payload: { request } }));
  inputEl.value = "";
});

connect();
