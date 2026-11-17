let token = sessionStorage.getItem("token") || "";
let state;
let demoMode = false;
let chatBusy = false;

const defaultAvatars = {
  Alex: "https://randomuser.me/api/portraits/men/32.jpg",
  Sara: "https://randomuser.me/api/portraits/women/44.jpg",
  Dev: "https://randomuser.me/api/portraits/men/75.jpg",
  Bouncer: "https://api.dicebear.com/9.x/bottts-neutral/svg?seed=Bouncer&backgroundColor=e8eaff",
};

async function api(path, body) {
  const response = await fetch(`/api/${path}`, {
    cache: "no-store",
    method: body ? "POST" : "GET",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });

  const raw = await response.text();
  let data;
  try { data = JSON.parse(raw); }
  catch { throw new Error(`Server error (${response.status}). Please retry or check the server terminal.`); }
  if (!response.ok) throw new Error(response.status === 405 && path === "chat/clear"
    ? "This server has not loaded Clear messages yet. Restart Start-Demo.ps1, open port 8010, then press Ctrl+F5."
    : data.detail || "Something went wrong.");
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

function avatarFor(name, customAvatar) {
  return customAvatar || defaultAvatars[name] || fallbackAvatar(name);
}

function avatarMarkup(name, avatar, className) {
  const fallback = fallbackAvatar(name);
  return `<img class="${className}" src="${escapeHTML(avatar)}" alt="${escapeHTML(name)}" onerror="this.onerror=null;this.src='${escapeHTML(fallback)}'">`;
}

function actorDetails(actor) {
  if (actor === "bouncer") {
    return {
      name: "SplitSmart Bouncer",
      avatar: defaultAvatars.Bouncer,
      isBouncer: true,
    };
  }

  const member = state?.members?.find((item) => item.id === actor);
  if (member) {
    return {
      name: member.name || "Member",
      avatar: avatarFor(member.name, member.avatar_url),
      isBouncer: false,
    };
  }

  const name = actor || "Unknown";
  return {
    name,
    avatar: avatarFor(name),
    isBouncer: false,
  };
}

function renderGroupHeader() {
  const members = state?.members || [];
  const groupName = state?.group?.name || state?.group_name || "Montreal weekend";

  document.getElementById("chat-title").textContent = groupName;
  document.getElementById("group-participants").innerHTML = members.map((member) => {
    const name = member.name || "Member";
    return `
      <div class="group-participant">
        ${avatarMarkup(name, avatarFor(name, member.avatar_url), "participant-avatar")}
        <span>${escapeHTML(name)}</span>
      </div>
    `;
  }).join("");

  document.getElementById("group-info-members").innerHTML = members.map((member) => {
    const name = member.name || "Member";
    return `
      <div class="group-info-member">
        ${avatarMarkup(name, avatarFor(name, member.avatar_url), "group-info-avatar")}
        <span>${escapeHTML(name)}</span>
      </div>
    `;
  }).join("");

  const memberSwitch = document.getElementById("demo-member-switch");
  const memberSelect = document.getElementById("demo-member-select");
  memberSwitch.hidden = !demoMode;
  if (demoMode) {
    memberSelect.innerHTML = members.map((member) =>
      `<option value="${escapeHTML(member.id)}">${escapeHTML(member.name)}</option>`
    ).join("");
    memberSelect.value = state?.me?.id || "";
  }
}

function formatMessageTime(value) {
  const date = new Date(value);
  if (!value || Number.isNaN(date.getTime())) return "";

  const day = date.toDateString() === new Date().toDateString()
    ? "Today"
    : new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(date);
  const time = new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(date);
  return `${day} ${time}`;
}

function shouldShowTimestamp(messages, index) {
  if (index === 0) return true;
  const current = new Date(messages[index].time);
  const previous = new Date(messages[index - 1].time);
  return !Number.isNaN(current.getTime())
    && !Number.isNaN(previous.getTime())
    && (current.toDateString() !== previous.toDateString() || current - previous > 4 * 60 * 60 * 1000);
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

    const timestamp = shouldShowTimestamp(messages, index)
      ? `<div class="message-date">${escapeHTML(formatMessageTime(message.time))}</div>`
      : "";
    const attachment = message.image
      ? `<img class="message-attachment" src="${escapeHTML(message.image)}" alt="Message attachment">`
      : "";
    const avatar = mine
      ? ""
      : sameSender
        ? `<span class="message-avatar-spacer" aria-hidden="true"></span>`
        : avatarMarkup(actor.name, actor.avatar, "message-avatar");

    return `
      ${timestamp}
      <article class="${classes}">
        ${!mine && !sameSender ? `<div class="message-sender">${escapeHTML(actor.name)}</div>` : ""}
        <div class="message-line">
          ${avatar}
          <div class="message-bubble">${escapeHTML(message.text)}${attachment}</div>
        </div>
      </article>
    `;
  }).join("");

  log.scrollTop = log.scrollHeight;
}

function showNotice(message) {
  document.getElementById("notice").textContent = message || "";
}

function showAuthenticationPrompt() {
  const notice = document.getElementById("notice");
  notice.innerHTML = "";

  const prompt = document.createElement("span");
  prompt.textContent = "Enter member access token:";

  const input = document.createElement("input");
  input.className = "auth-input";
  input.placeholder = "Access token";
  input.setAttribute("aria-label", "Access token");

  const button = document.createElement("button");
  button.className = "auth-button";
  button.textContent = "Continue";

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
  renderGroupHeader();
  renderMessages();
  showNotice("");
}

async function sendMessage(event) {
  event.preventDefault();
  if (chatBusy || document.querySelector('.send-button').disabled) return;

  const input = document.getElementById("message-input");
  const text = input.value.trim();
  if (!text) return;

  const button = document.querySelector(".send-button");
  chatBusy = true;
  document.getElementById("clear-messages").disabled = true;
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
    chatBusy = false;
    document.getElementById("clear-messages").disabled = false;
    button.disabled = !input.value.trim();
    input.focus();
  }
}

function boot() {
  const form = document.getElementById("chat-form");
  const input = document.getElementById("message-input");
  const composer = document.querySelector(".composer");
  const infoButton = document.getElementById("group-info-button");
  const infoPanel = document.getElementById("group-info");
  const memberSelect = document.getElementById("demo-member-select");
  const clearButton = document.getElementById("clear-messages");
  clearButton.addEventListener("click", async () => {
    if (chatBusy || !confirm("Permanently clear all saved messages and their expense mentions for everyone in this demo? Policies and ledger records will be kept.")) return;
    chatBusy = true;
    clearButton.disabled = true;
    try {
      await api("chat/clear", {});
      input.value = "";
      input.dispatchEvent(new Event("input"));
      await loadChat();
      if (state.conversations.length) throw new Error("Messages are still present. Another chat request may have arrived; try clearing again.");
      showNotice("Messages cleared. Ready for a new demo.");
    } catch (error) {
      showNotice(error.message);
    } finally {
      chatBusy = false;
      clearButton.disabled = false;
      input.focus();
    }
  });

  form.addEventListener("submit", sendMessage);
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 110)}px`;
    const hasText = Boolean(input.value.trim());
    composer.classList.toggle("has-text", hasText);
    document.querySelector(".send-button").disabled = !hasText;
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  infoButton.addEventListener("click", () => {
    const expanded = infoButton.getAttribute("aria-expanded") === "true";
    infoButton.setAttribute("aria-expanded", String(!expanded));
    infoPanel.hidden = expanded;
  });

  memberSelect.addEventListener("change", async () => {
    if (!demoMode) return;
    token = `demo-${memberSelect.value}`;
    sessionStorage.setItem("token", token);
    try {
      await loadChat();
    } catch (error) {
      showNotice(error.message);
    }
  });

  api("config")
    .then((config) => {
      demoMode = Boolean(config.demo);
      clearButton.hidden = !demoMode;
      if (config.agent === 'scripted') {
        const guide = document.createElement('div');
        guide.style.cssText = 'padding:10px;display:flex;gap:8px;flex-wrap:wrap;align-items:center';
        const label = document.createElement('span');
        label.textContent = 'Scripted demo';
        guide.append(label);
        for (const text of ['Hey Bouncer!', 'I want tacos in Montreal', 'Our budget is $30 per person', 'We need halal and nut-free options', 'We paid $90 for dinner', 'Split it equally', 'Recap']) {
          const button = document.createElement('button');
          button.type = 'button';
          button.textContent = text;
          button.style.cssText = 'border:1px solid #ccc;border-radius:16px;padding:6px 10px;background:white;color:#222;cursor:pointer';
          button.addEventListener('click', () => {
            input.value = text;
            input.dispatchEvent(new Event('input'));
            input.focus();
          });
          guide.append(button);
        }
        form.before(guide);
      }
      if (demoMode && !token) {
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
