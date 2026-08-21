const API_BASE = 'https://expense-splitter-api-sr80.onrender.com/api';

let currentGroupId = null;

// ---------- DOM references ----------
const groupsView = document.getElementById('groups-view');
const groupDetailView = document.getElementById('group-detail-view');
const groupsList = document.getElementById('groups-list');
const groupDetailTitle = document.getElementById('group-detail-title');
const membersList = document.getElementById('members-list');
const expensesList = document.getElementById('expenses-list');
const balancesList = document.getElementById('balances-list');
const settlementsList = document.getElementById('settlements-list');
const settlementsSubtitle = document.getElementById('settlements-subtitle');
const paidBySelect = document.getElementById('expense-paid-by-select');
const splitCheckboxes = document.getElementById('expense-split-checkboxes');
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

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
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
    populateExpenseFormOptions(group.members);

    await Promise.all([
      loadExpenses(groupId),
      loadBalancesAndSettlements(groupId)
    ]);
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

// ---------- Expenses ----------

function populateExpenseFormOptions(members) {
  // Payer dropdown
  paidBySelect.innerHTML = '';
  members.forEach(member => {
    const option = document.createElement('option');
    option.value = member.id;
    option.textContent = member.name;
    paidBySelect.appendChild(option);
  });

  // Split checkboxes — all checked by default (equal split among everyone)
  splitCheckboxes.innerHTML = '';
  members.forEach(member => {
    const label = document.createElement('label');
    label.className = 'checkbox-item';
    label.innerHTML = `
      <input type="checkbox" value="${member.id}" checked>
      ${escapeHtml(member.name)}
    `;
    splitCheckboxes.appendChild(label);
  });
}

async function loadExpenses(groupId) {
  try {
    const expenses = await apiCall(`/groups/${groupId}/expenses`);
    renderExpenses(expenses);
  } catch (err) {
    expensesList.innerHTML = '<li class="muted-text">Failed to load expenses.</li>';
  }
}

function renderExpenses(expenses) {
  if (expenses.length === 0) {
    expensesList.innerHTML = '<li class="muted-text">No expenses yet.</li>';
    return;
  }

  expensesList.innerHTML = '';
  expenses.forEach(expense => {
    const li = document.createElement('li');
    const splitNames = expense.splits.map(s => s.member_name).join(', ');
    li.innerHTML = `
      <div class="expense-item-row">
        <div class="expense-item">
          <div class="expense-item-top">
            <span>${escapeHtml(expense.description)}</span>
            <span class="expense-amount">₹${expense.amount.toFixed(2)}</span>
          </div>
          <span class="expense-item-meta">Paid by ${escapeHtml(expense.paid_by)} · split between ${escapeHtml(splitNames)}</span>
        </div>
        <button class="expense-delete-btn" data-expense-id="${expense.id}" title="Delete expense">✕</button>
      </div>
    `;
    expensesList.appendChild(li);
  });

  // Attach delete handlers
  document.querySelectorAll('.expense-delete-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const expenseId = btn.getAttribute('data-expense-id');
      if (!confirm('Delete this expense?')) return;

      try {
        await apiCall(`/expenses/${expenseId}`, 'DELETE');
        showToast('Expense deleted');
        await Promise.all([
          loadExpenses(currentGroupId),
          loadBalancesAndSettlements(currentGroupId)
        ]);
      } catch (err) {
        // error shown via toast
      }
    });
  });
}

document.getElementById('show-add-expense-btn').addEventListener('click', () => {
  document.getElementById('add-expense-form').classList.remove('hidden');
});

document.getElementById('cancel-add-expense-btn').addEventListener('click', () => {
  document.getElementById('add-expense-form').classList.add('hidden');
  resetExpenseForm();
});

function resetExpenseForm() {
  document.getElementById('expense-desc-input').value = '';
  document.getElementById('expense-amount-input').value = '';
}

document.getElementById('add-expense-form').addEventListener('submit', async (e) => {
  e.preventDefault();

  const description = document.getElementById('expense-desc-input').value.trim();
  const amount = parseFloat(document.getElementById('expense-amount-input').value);
  const paidById = parseInt(paidBySelect.value);

  const checkedBoxes = splitCheckboxes.querySelectorAll('input[type="checkbox"]:checked');
  const splitBetween = Array.from(checkedBoxes).map(cb => parseInt(cb.value));

  if (!description || !amount || amount <= 0) {
    showToast('Please enter a description and valid amount', true);
    return;
  }

  if (splitBetween.length === 0) {
    showToast('Select at least one person to split with', true);
    return;
  }

  try {
    await apiCall(`/groups/${currentGroupId}/expenses`, 'POST', {
      description,
      amount,
      paid_by_id: paidById,
      split_between: splitBetween
    });

    resetExpenseForm();
    document.getElementById('add-expense-form').classList.add('hidden');
    showToast('Expense added');

    await Promise.all([
      loadExpenses(currentGroupId),
      loadBalancesAndSettlements(currentGroupId)
    ]);
  } catch (err) {
    // error already shown via toast
  }
});

// ---------- Balances + Settlements ----------

async function loadBalancesAndSettlements(groupId) {
  try {
    const data = await apiCall(`/groups/${groupId}/settlements`);
    renderBalances(data.balances);
    renderSettlements(data.settlements);
  } catch (err) {
    balancesList.innerHTML = '<li class="muted-text">Failed to load balances.</li>';
    settlementsList.innerHTML = '<li class="muted-text">Failed to load settlements.</li>';
  }
}

function renderBalances(balances) {
  if (balances.length === 0) {
    balancesList.innerHTML = '<li class="muted-text">No members yet.</li>';
    return;
  }

  balancesList.innerHTML = '';
  balances.forEach(entry => {
    const li = document.createElement('li');
    let statusClass = 'balance-zero';
    let statusText = 'settled up';

    if (entry.balance > 0.01) {
      statusClass = 'balance-positive';
      statusText = `is owed ₹${entry.balance.toFixed(2)}`;
    } else if (entry.balance < -0.01) {
      statusClass = 'balance-negative';
      statusText = `owes ₹${Math.abs(entry.balance).toFixed(2)}`;
    }

    li.innerHTML = `
      <span>${escapeHtml(entry.member_name)}</span>
      <span class="${statusClass}">${statusText}</span>
    `;
    balancesList.appendChild(li);
  });
}

function renderSettlements(settlements) {
  if (settlements.length === 0) {
    settlementsSubtitle.textContent = 'Everyone is settled up! 🎉';
    settlementsList.innerHTML = '';
    return;
  }

  settlementsSubtitle.textContent = `${settlements.length} transaction${settlements.length !== 1 ? 's' : ''} to settle everyone up:`;
  settlementsList.innerHTML = '';
  settlements.forEach(txn => {
    const li = document.createElement('li');
    li.innerHTML = `
      <span class="settlement-item">
        <strong>${escapeHtml(txn.from)}</strong>
        <span class="settlement-arrow">→</span>
        <strong>${escapeHtml(txn.to)}</strong>
      </span>
      <span class="settlement-amount">₹${txn.amount.toFixed(2)}</span>
    `;
    settlementsList.appendChild(li);
  });
}

// ---------- Init ----------

loadGroups();