
let token = sessionStorage.getItem("token") || "";
let state;

const avatars = {
  Alex: "https://randomuser.me/api/portraits/men/32.jpg",
  Sara: "https://randomuser.me/api/portraits/women/44.jpg",
  Dev: "https://randomuser.me/api/portraits/men/75.jpg",
  Bouncer:
    "https://api.dicebear.com/9.x/bottts-neutral/svg?seed=Bouncer&backgroundColor=e8eaff",
};

async function api(path, body) {
  const response = await fetch(`/api/${path}`, {
    method: body ? "POST" : "GET",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Something went wrong.");
  }

  return data;
}

function actorDetails(actor) {
  if (actor === "bouncer") {
    return {
      name: "Bouncer",
      avatar: avatars.Bouncer,
      isBouncer: true,
    };
  }

  const member = state?.members?.find((item) => item.id === actor);

  if (member) {
    return {
      name: member.name,
      avatar: member.avatar_url || avatars[member.name] || fallbackAvatar(member.name),
      isBouncer: false,
    };
  }

  const name = actor || "Unknown";

  return {
    name,
    avatar: avatars[name] || fallbackAvatar(name),
    isBouncer: false,
  };
}

function fallbackAvatar(name) {
  return `https://api.dicebear.com/9.x/initials/svg?seed=${encodeURIComponent(name || "User")}`;
}

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => {
    const entities = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };

    return entities[character];
  });
}

function renderMessages() {
  const log = document.getElementById("message-log");

  const messages = state?.conversations || [];

  if (!messages.length) {
    log.innerHTML = `
      <div class="loading-message">
        Start the conversation with your group.
      </div>
    `;
    return;
  }

  log.innerHTML = messages
    .map((message) => {
      const actor = actorDetails(message.actor);
      const mine = message.actor === state?.me?.id;

      const classes = [
        "message-row",
        mine ? "mine" : "",
        actor.isBouncer ? "bouncer" : "",
      ]
        .filter(Boolean)
        .join(" ");

      const attachment = message.image
        ? `<img class="message-attachment" src="${escapeHTML(message.image)}" alt="Message attachment">`
        : "";

      return `
        <div class="${classes}">
          <img
            class="message-avatar"
            src="${escapeHTML(actor.avatar)}"
            alt="${escapeHTML(actor.name)}"
            onerror="this.src='${escapeHTML(fallbackAvatar(actor.name))}'"
          >

          <div class="message-content">
            ${
              !mine
                ? `<span class="message-sender">${escapeHTML(actor.name)}</span>`
                : ""
            }

            ${
              actor.isBouncer
                ? `<span class="bouncer-label">SPLITSMART BOUNCER</span>`
                : ""
            }

            <div class="message-bubble">
              ${escapeHTML(message.text)}
              ${attachment}
            </div>
          </div>
        </div>
      `;
    })
    .join("");

  log.scrollTop = log.scrollHeight;
}

function renderGroup() {
  const members = state?.members || [];

  const participantNames = members.map((member) => member.name);

  const participants = document.getElementById("participants");

  if (participants) {
    participants.textContent = participantNames.join(", ") || "Group conversation";
  }
}

function showNotice(message) {
  const notice = document.getElementById("notice");

  notice.textContent = message || "";
}

function showAuthenticationPrompt() {
  const message = "Enter your member access token to continue.";

  showNotice(message);

  const tokenInput = document.createElement("input");
  tokenInput.placeholder = "Access token";
  tokenInput.style.margin = "8px";
  tokenInput.style.padding = "8px";
  tokenInput.style.borderRadius = "8px";
  tokenInput.style.border = "1px solid #ccc";

  const button = document.createElement("button");
  button.textContent = "Continue";
  button.style.padding = "8px 14px";
  button.style.borderRadius = "8px";
  button.style.border = "none";
  button.style.background = "#007aff";
  button.style.color = "white";
  button.style.cursor = "pointer";

  const notice = document.getElementById("notice");

  notice.innerHTML = "";
  notice.append(tokenInput, button);

  button.addEventListener("click", async () => {
    token = tokenInput.value.trim();

    if (!token) return;

    sessionStorage.setItem("token", token);

    try {
      await loadChat();
    } catch (error) {
      showNotice(error.message);
    }
  });
}

async function loadChat() {
  state = await api("state");

  renderGroup();
  renderMessages();
  showNotice("");
}

async function sendMessage(event) {
  event.preventDefault();

  const input = document.getElementById("message-input");
  const text = input.value.trim();

  if (!text) return;

  const sendButton = document.querySelector(".send-button");

  sendButton.disabled = true;

  try {
    await api("chat", { text });

    input.value = "";
    input.style.height = "auto";

    await loadChat();
  } catch (error) {
    showNotice(error.message);
  } finally {
    sendButton.disabled = false;
    input.focus();
  }
}

async function boot() {
  const form = document.getElementById("chat-form");
  const input = document.getElementById("message-input");

  form.addEventListener("submit", sendMessage);

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = `${input.scrollHeight}px`;
  });

  try {
    const config = await api("config");

    if (config.demo && !token) {
      token = "demo-alex";
    }

    await loadChat();
  } catch (error) {
    if (!token) {
      showAuthenticationPrompt();
    } else {
      showNotice(error.message);
    }
  }
}

boot();
