
let token = sessionStorage.getItem("token") || "";
let state;

const defaultAvatars = {
  Alex: "https://randomuser.me/api/portraits/men/32.jpg",
  Sara: "https://randomuser.me/api/portraits/women/44.jpg",
  Dev: "https://randomuser.me/api/portraits/men/75.jpg",
  Bouncer: "https://api.dicebear.com/9.x/bottts-neutral/svg?seed=Bouncer&backgroundColor=e8eaff",
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
  if (!response.ok) throw new Error(data.detail || "Something went wrong.");
  return data;
}

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[character]);
}

function fallbackAvatar(name) {
  return `https://api.dicebear.com/9.x/initials/svg?seed=${encodeURIComponent(name || "User")}`;
}

function actorDetails(actor) {
  if (actor === "bouncer") {
    return {
      name: "Bouncer",
      avatar: defaultAvatars.Bouncer,
      isBouncer: true,
    };
  }

  const member = state?.members?.find((item) => item.id === actor);

  if (member) {
    return {
      name: member.name || "Member",
      avatar: member.avatar_url || defaultAvatars[member.name] || fallbackAvatar(member.name),
      isBouncer: false,
    };
  }

  const name = actor || "Unknown";

  return {
    name,
    avatar: defaultAvatars[name] || fallbackAvatar(name),
    isBouncer: false,
  };
}

function renderPinnedContacts() {
  const container = document.getElementById("pinned-contacts");
  const members = (state?.members || []).slice(0, 3);

  if (!members.length) {
    container.innerHTML = `<div class="pinned-placeholder">No group members</div>`;
    return;
  }

  container.innerHTML = members.map((member, index) => {
    const name = member.name || "Member";
    const avatar = member.avatar_url || defaultAvatars[name] || fallbackAvatar(name);

    return `
      <div class="pinned-contact ${index === 0 ? "active" : ""}">
        <img class="pinned-avatar" src="${escapeHTML(avatar)}" alt="${escapeHTML(name)}">
        <span class="pinned-name">${escapeHTML(name)}</span>
      </div>
    `;
  }).join("");
}

function renderConversationList() {
  const container = document.getElementById("conversation-list");
  const messages = state?.conversations || [];
  const lastMessage = messages[messages.length - 1];
  const actor = lastMessage ? actorDetails(lastMessage.actor) : null;
  const preview = lastMessage?.text || "Start a conversation";
  const groupName = state?.group?.name || state?.group_name || "Montreal weekend";

  const firstMember = (state?.members || [])[0];

  const avatar = firstMember
    ? (firstMember.avatar_url || defaultAvatars[firstMember.name] || fallbackAvatar(firstMember.name))
    : fallbackAvatar(groupName);

  container.innerHTML = `
    <div class="conversation-item selected" data-search="${escapeHTML(groupName.toLowerCase())}">
      <span class="unread-dot"></span>
      <img class="conversation-avatar" src="${escapeHTML(avatar)}" alt="">
      <div class="conversation-copy">
        <div class="conversation-topline">
          <span class="conversation-name">${escapeHTML(groupName)}</span>
          <span class="conversation-time">Now</span>
        </div>
        <div class="conversation-preview">${escapeHTML(actor ? `${actor.name}: ${preview}` : preview)}</div>
      </div>
    </div>
  `;

  const search = document.getElementById("conversation-search");

  if (search) {
    const item = container.querySelector(".conversation-item");
    const query = search.value.trim().toLowerCase();

    item.style.display = item.dataset.search.includes(query) || !query ? "flex" : "none";
  }
}

function renderGroup() {
  const groupName = state?.group?.name || state?.group_name || "Montreal weekend";

  document.getElementById("chat-title").textContent = groupName;

  renderPinnedContacts();
  renderConversationList();
}

function renderMessages() {
  const log = document.getElementById("message-log");
  const messages = state?.conversations || [];

  if (!messages.length) {
    log.innerHTML = `<div class="loading-message">No messages yet. Say hello to your group.</div>`;
    return;
  }

  log.innerHTML = messages.map((message, index) => {
    const actor = actorDetails(message.actor);
    const mine = message.actor === state?.me?.id;
    const previous = messages[index - 1];
    const sameSender = previous && previous.actor === message.actor;

    const classes = [
      "message-group",
      mine ? "mine" : "",
      actor.isBouncer ? "bouncer" : "",
    ].filter(Boolean).join(" ");

    const attachment = message.image
      ? `<img class="message-attachment" src="${escapeHTML(message.image)}" alt="Message attachment">`
      : "";

    const avatar = sameSender
      ? `<span class="message-avatar-spacer"></span>`
      : `<img class="message-avatar" src="${escapeHTML(actor.avatar)}" alt="${escapeHTML(actor.name)}" onerror="this.onerror=null;this.src='${escapeHTML(fallbackAvatar(actor.name))}'">`;

    return `
      <div class="${classes}">
        ${!mine && !sameSender ? `<div class="message-sender">${escapeHTML(actor.name)}</div>` : ""}
        ${actor.isBouncer && !sameSender ? `<div class="bouncer-tag">SPLITSMART BOUNCER</div>` : ""}
        <div class="message-line">
          ${avatar}
          <div class="message-bubble">${escapeHTML(message.text)}${attachment}</div>
        </div>
      </div>
    `;
  }).join("");

  log.scrollTop = log.scrollHeight;
  renderConversationList();
}

function showNotice(message) {
  document.getElementById("notice").textContent = message || "";
}

function showAuthenticationPrompt() {
  const notice = document.getElementById("notice");
  notice.innerHTML = "";

  const prompt = document.createElement("span");
  prompt.textContent = "Enter member access token: ";

  const input = document.createElement("input");
  input.placeholder = "Access token";
  input.style.margin = "0 8px";
  input.style.padding = "5px 8px";
  input.style.borderRadius = "7px";
  input.style.border = "1px solid #666";
  input.style.background = "#303033";
  input.style.color = "#fff";

  const button = document.createElement("button");
  button.textContent = "Continue";
  button.style.padding = "5px 10px";
  button.style.border = "0";
  button.style.borderRadius = "7px";
  button.style.background = "#1685f8";
  button.style.color = "#fff";
  button.style.cursor = "pointer";

  notice.append(prompt, input, button);

  button.addEventListener("click", async () => {
    token = input.value.trim();

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

  const button = document.querySelector(".send-button");
  button.disabled = true;

  try {
    await api("chat", { text });

    input.value = "";
    input.style.height = "auto";

    document.querySelector(".composer").classList.remove("has-text");

    await loadChat();
  } catch (error) {
    showNotice(error.message);
  } finally {
    button.disabled = false;
    input.focus();
  }
}

function boot() {
  const form = document.getElementById("chat-form");
  const input = document.getElementById("message-input");
  const composer = document.querySelector(".composer");
  const search = document.getElementById("conversation-search");

  form.addEventListener("submit", sendMessage);

  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 110)}px`;

    composer.classList.toggle("has-text", Boolean(input.value.trim()));
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  search.addEventListener("input", renderConversationList);

  api("config")
    .then((config) => {
      if (config.demo && !token) {
        token = "demo-alex";
      }

      return loadChat();
    })
    .catch((error) => {
      if (!token) {
        showAuthenticationPrompt();
      } else {
        showNotice(error.message);
      }
    });
}

boot();
