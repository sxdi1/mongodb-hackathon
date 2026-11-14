const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[char]));

let token = sessionStorage.getItem('token') || '';
let state;
const EMPTY_CHAT_MARKER = '__empty__';

async function api(path, body) {
  const response = await fetch(`/api/${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  const contentType = response.headers.get('content-type') || '';
  const data = contentType.includes('application/json')
    ? await response.json()
    : { detail: (await response.text()).slice(0, 500) || `Request failed with HTTP ${response.status}` };
  if (!response.ok) {
    throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
  }
  return data;
}

function initials(name) {
  return String(name || '?').trim().split(/\s+/).slice(0, 2).map(part => part[0] || '').join('').toUpperCase();
}

function timeLabel(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? ''
    : new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(date);
}

function dateLabel(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Today';
  const today = new Date();
  if (date.toDateString() === today.toDateString()) return 'Today';
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  if (date.toDateString() === yesterday.toDateString()) return 'Yesterday';
  return new Intl.DateTimeFormat(undefined, { month: 'long', day: 'numeric', year: 'numeric' }).format(date);
}

function actorDetails(actor) {
  if (actor === 'bouncer') return { name: 'Bouncer', avatar: 'B', className: 'avatar-agent', role: 'Planning assistant' };
  const member = state.members.find(person => person.id === actor);
  const name = member?.name || actor;
  const className = actor === 'sara' ? 'avatar-sara' : actor === 'dev' ? 'avatar-dev' : '';
  return {
    name,
    avatar: initials(name),
    className,
    role: ''
  };
}

function visibleMessages() {
  const key = `splitsmart-chat-cleared:${state.me.id}`;
  const marker = localStorage.getItem(key);
  if (!marker) return { messages:state.conversations, cleared:false };
  if (marker === EMPTY_CHAT_MARKER) return { messages:state.conversations, cleared:true };
  const markerIndex = state.conversations.findIndex(message => message.id === marker);
  if (markerIndex < 0) {
    localStorage.removeItem(key);
    return { messages:state.conversations, cleared:false };
  }
  return { messages:state.conversations.slice(markerIndex + 1), cleared:true };
}

function renderMessages() {
  const view = visibleMessages();
  const messages = view.messages.length
    ? view.messages
    : view.cleared
      ? []
      : [{ actor: 'bouncer', text: 'Hey, everyone! I’m Bouncer, your planning buddy. What sounds fun for the weekend?', time: new Date().toISOString() }];
  if (!messages.length) {
    $('#messages').innerHTML = '<p class="empty-chat">Chat cleared from this browser. New messages will appear here.</p>';
    return;
  }
  let previousDate = '';
  const html = messages.map(message => {
    const day = dateLabel(message.time);
    const divider = day !== previousDate ? `<div class="date-divider">${esc(day)}</div>` : '';
    previousDate = day;
    const sender = actorDetails(message.actor);
    return `${divider}
      <article class="message">
        <div class="message-avatar ${sender.className}" aria-hidden="true">${esc(sender.avatar)}</div>
        <div class="message-content">
          <div class="message-meta">
            <span class="message-name">${esc(sender.name)}</span>
            ${sender.role ? `<span class="message-role">${esc(sender.role)}</span>` : ''}
            <time class="message-time">${esc(timeLabel(message.time))}</time>
          </div>
          <p class="message-text">${esc(message.text)}</p>
          ${message.has_image ? '<p class="message-attachment">Screenshot attached · unverified</p>' : ''}
        </div>
      </article>`;
  }).join('');
  $('#messages').innerHTML = html;
  $('#messages').scrollTop = $('#messages').scrollHeight;
}

function renderGroup() {
  $('#participants').textContent = `${state.members.length} people · ${state.members.map(member => member.name).join(', ')}`;
  $('#headerMembers').innerHTML = state.members.map(member =>
    `<span class="member-avatar" title="${esc(member.name)}" aria-label="${esc(member.name)}">${esc(initials(member.name))}</span>`
  ).join('');
  $('#accountAvatar').textContent = initials(state.me.name);
  $('#accountAvatar').setAttribute('aria-label', `Signed in as ${state.me.name}`);
}

function showNotice(message) {
  const notice = $('#notice');
  notice.textContent = message;
}

function showAuthenticationPrompt() {
  const notice = $('#notice');
  notice.innerHTML = `
    <span>Enter your member access token to join this chat.</span>
    <form class="connect-form">
      <label class="sr-only" for="accessToken">Member access token</label>
      <input id="accessToken" type="password" autocomplete="current-password" placeholder="Member access token" required>
      <button type="submit">Join chat</button>
    </form>`;
  notice.setAttribute('role', 'status');
  notice.querySelector('.connect-form').addEventListener('submit', async event => {
    event.preventDefault();
    token = $('#accessToken').value;
    sessionStorage.setItem('token', token);
    await loadChat();
  });
}

async function loadChat() {
  try {
    state = await api('state');
    renderGroup();
    renderMessages();
    showNotice('');
  } catch (error) {
    if (error.message.includes('token')) {
      showAuthenticationPrompt();
    } else {
      showNotice(error.message);
    }
  }
}

$('#chatForm').addEventListener('submit', async event => {
  event.preventDefault();
  const input = $('#message');
  const text = input.value.trim();
  if (!text) return;

  const button = $('#sendButton');
  button.disabled = true;
  showNotice('');
  try {
    await api('chat', { text });
    input.value = '';
    input.style.height = 'auto';
    await loadChat();
    input.focus();
  } catch (error) {
    showNotice(error.message);
  } finally {
    button.disabled = false;
  }
});

$('#message').addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    $('#chatForm').requestSubmit();
  }
});

$('#message').addEventListener('input', event => {
  event.target.style.height = 'auto';
  event.target.style.height = `${Math.min(event.target.scrollHeight, 140)}px`;
});

$('#clearChatButton').addEventListener('click', () => {
  if (!state) return;
  const confirmed = window.confirm(
    'Clear the conversation from this browser? This does not delete messages for other group members.'
  );
  if (!confirmed) return;
  const marker = state.conversations.at(-1)?.id || EMPTY_CHAT_MARKER;
  try {
    localStorage.setItem(`splitsmart-chat-cleared:${state.me.id}`, marker);
  } catch (error) {
    showNotice(`Could not clear this browser's chat view: ${error.message}`);
    return;
  }
  renderMessages();
  showNotice('Chat cleared from this browser. Other members can still see the conversation.');
});

(async () => {
  try {
    const config = await api('config');
    if (config.demo && !token) {
      token = 'demo-alex';
      sessionStorage.setItem('token', token);
    }
    await loadChat();
  } catch (error) {
    showNotice(error.message);
  }
})();
