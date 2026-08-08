const API_BASE = 'http://127.0.0.1:5000/api';

let currentGroupId = null;

// ---------- DOM references ----------
const groupsView = document.getElementById('groups-view');
const groupDetailView = document.getElementById('group-detail-view');
const groupsList = document.getElementById('groups-list');
const groupDetailTitle = document.getElementById('group-detail-title');
const membersList = document.getElementById('members-list');
const toast = document.getElementById('toast');

// ---------- Utility ----------

function showToast(message, isError = false) {
  toast.textContent = message;
  toast.classList.remove('hidden');
  toast.classList.toggle('error', isError);
  setTimeout(() => toast.classList.add('hidden'), 3000);
}

async function apiCall(endpoint, method = 'GET', body = null) {
  try {
    const options = {
      method,
      headers: { 'Content-Type': 'application/json' }
    };
    if (body) options.body = JSON.stringify(body);

    const response = await fetch(`${API_BASE}${endpoint}`, options);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Something went wrong');
    }
    return data;
  } catch (err) {
    showToast(err.message, true);
    throw err;
  }
}

function initials(name) {
  return name.trim().charAt(0).toUpperCase();
}

// ---------- View switching ----------

function showGroupsView() {
  groupDetailView.classList.add('hidden');
  groupsView.classList.remove('hidden');
  currentGroupId = null;
  loadGroups();
}

function showGroupDetailView(groupId) {
  currentGroupId = groupId;
  groupsView.classList.add('hidden');
  groupDetailView.classList.remove('hidden');
  loadGroupDetail(groupId);
}

// ---------- Groups ----------

async function loadGroups() {
  groupsList.innerHTML = '<p class="muted-text">Loading...</p>';
  try {
    const groups = await apiCall('/groups');

    if (groups.length === 0) {
      groupsList.innerHTML = '<p class="empty-state">No groups yet. Create one to get started.</p>';
      return;
    }

    groupsList.innerHTML = '';
    groups.forEach(group => {
      const card = document.createElement('div');
      card.className = 'group-card';
      card.innerHTML = `
        <h4>${escapeHtml(group.name)}</h4>
        <p class="member-count">${group.member_count} member${group.member_count !== 1 ? 's' : ''}</p>
      `;
      card.addEventListener('click', () => showGroupDetailView(group.id));
      groupsList.appendChild(card);
    });
  } catch (err) {
    groupsList.innerHTML = '<p class="empty-state">Failed to load groups.</p>';
  }
}

document.getElementById('show-create-group-btn').addEventListener('click', () => {
  document.getElementById('create-group-form').classList.remove('hidden');
});

document.getElementById('cancel-create-group-btn').addEventListener('click', () => {
  document.getElementById('create-group-form').classList.add('hidden');
  document.getElementById('group-name-input').value = '';
});

document.getElementById('create-group-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const nameInput = document.getElementById('group-name-input');
  const name = nameInput.value.trim();
  if (!name) return;

  try {
    await apiCall('/groups', 'POST', { name });
    nameInput.value = '';
    document.getElementById('create-group-form').classList.add('hidden');
    showToast('Group created');
    loadGroups();
  } catch (err) {
    // error already shown via toast in apiCall
  }
});

document.getElementById('back-to-groups-btn').addEventListener('click', showGroupsView);

// ---------- Group Detail ----------

async function loadGroupDetail(groupId) {
  try {
    const group = await apiCall(`/groups/${groupId}`);
    groupDetailTitle.textContent = group.name;
    renderMembers(group.members);
  } catch (err) {
    showGroupsView();
  }
}

function renderMembers(members) {
  if (members.length === 0) {
    membersList.innerHTML = '<li class="muted-text">No members yet. Add someone to get started.</li>';
    return;
  }

  membersList.innerHTML = '';
  members.forEach(member => {
    const li = document.createElement('li');
    li.innerHTML = `
      <span class="member-avatar">
        <span class="avatar-circle">${initials(member.name)}</span>
        ${escapeHtml(member.name)}
      </span>
    `;
    membersList.appendChild(li);
  });
}

document.getElementById('show-add-member-btn').addEventListener('click', () => {
  document.getElementById('add-member-form').classList.remove('hidden');
  document.getElementById('member-name-input').focus();
});

document.getElementById('add-member-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const nameInput = document.getElementById('member-name-input');
  const name = nameInput.value.trim();
  if (!name || !currentGroupId) return;

  try {
    await apiCall(`/groups/${currentGroupId}/members`, 'POST', { name });
    nameInput.value = '';
    showToast('Member added');
    loadGroupDetail(currentGroupId);
  } catch (err) {
    // error already shown via toast
  }
});

// ---------- Helper: prevent XSS from user-entered names ----------

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// ---------- Init ----------

loadGroups();