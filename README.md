# 💸 Expense Splitter — with Debt Simplification

A full-stack expense-splitting app (like Splitwise) that goes beyond basic CRUD by implementing an actual **debt-simplification algorithm** — reducing a tangle of who-owes-whom into the minimum number of settlement transactions.

**🔗 Live App:** https://khindimegha-hub.github.io/expense-splitter/frontend/index.html
**🔗 Live API:** https://expense-splitter-api-sr80.onrender.com
**📦 Repo:** https://github.com/khindimegha-hub/expense-splitter

> ⚠️ **Note:** The live backend runs on Render's free tier, which spins down after 15 minutes of inactivity. The first request after idle time may take 30–60 seconds to respond — this is expected, not a bug.

---

## Screenshots

![Group detail view showing expenses, balances, and simplified settlements](screenshots/group-detail.png)

## Why this project

Most expense-splitter tutorials stop at basic CRUD: add an expense, split it evenly, done. The interesting part — turning a group's tangled web of debts into the *minimum* number of payments needed to settle everyone up — is a genuine graph/greedy optimization problem, and most tutorial projects skip it entirely.

This project implements that algorithm from scratch, tests it against edge cases, and exposes it through a working full-stack app.

---

## Features

- **Groups & members** — create groups, add/remove members
- **Expense tracking** — add expenses with custom payer and split-between selection
- **Balance calculation** — real-time net balance per member (who's owed, who owes)
- **Debt simplification** — greedy max-heap algorithm collapses N-way debts into the minimum settlement transactions
- **Rounding-safe splits** — custom paise-based split calculation guarantees shares always sum exactly to the original amount (fixes a real floating-point bug most tutorials never catch)
- **Full CRUD** — edit/delete expenses, remove members (with safeguards against deleting members tied to existing expenses)
- **Cross-group validation** — prevents a member from one group being added to another group's expense split

---

## Tech Stack

**Backend:** Python, Flask, SQLAlchemy, SQLite, pytest
**Frontend:** Vanilla HTML/CSS/JavaScript (no framework — deliberately kept simple)
**Infra:** Docker, Docker Compose, gunicorn (production WSGI server)
**Deployment:** Render (backend), GitHub Pages (frontend)
**Testing:** 16 automated tests — unit tests for the core algorithm + integration tests exercising the full HTTP API

---

## The Debt Simplification Algorithm

Given each member's net balance (`total paid − total owed`), the app computes the minimum-ish set of transactions to settle everyone up.

**Approach:** Greedy max-heap matching.
1. Split members into creditors (owed money) and debtors (owe money)
2. Repeatedly match the person owed the most with the person who owes the most
3. Settle the smaller of the two amounts; push any remainder back onto the heap
4. Repeat until everyone is settled

```python
# Simplified core logic (see backend/app/services.py for full implementation)
while creditors and debtors:
    creditor = pop_largest(creditors)
    debtor = pop_largest(debtors)
    settle_amount = min(creditor.balance, debtor.balance)
    record_transaction(debtor, creditor, settle_amount)
    push_back_remainder(creditor, debtor, settle_amount)
```

**Honest limitation:** this greedy approach does *not* guarantee the mathematically optimal minimum number of transactions in every case — finding the true minimum is NP-hard in general (it's related to a set-partition problem). Greedy performs close to optimal in practice and runs in O(n log n), which is the right tradeoff for a real app. I chose to be upfront about this rather than overclaim optimality.

**Example:** 4-person group with expenses of ₹800, ₹400, and ₹1200 paid by different people. Naive settling could require up to 6 pairwise transactions (n(n−1)/2). The algorithm collapses this down to 2 transactions.

---

## Architecture
expense-splitter/
├── backend/
│ ├── app/
│ │ ├── models.py # SQLAlchemy models: Group, Member, Expense, ExpenseSplit
│ │ ├── routes.py # Flask REST API endpoints
│ │ ├── services.py # Business logic: balance calc, debt simplification, split rounding
│ │ └── config.py
│ ├── tests/
│ │ ├── test_services.py # 10 unit tests — algorithm correctness, edge cases
│ │ └── test_api.py # 6 integration tests — full HTTP request/response flow
│ ├── Dockerfile
│ ├── requirements.txt
│ └── run.py
├── frontend/
│ ├── index.html
│ ├── css/style.css
│ └── js/app.js
└── docker-compose.yml


**Design choice — separated business logic from routes:** `services.py` contains no Flask-specific code, making the core algorithms independently testable and reusable (e.g., could plug into a CLI tool or a different API framework without rewriting the logic).

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/groups` | Create a group |
| GET | `/api/groups` | List all groups |
| GET | `/api/groups/<id>` | Get group details + members |
| DELETE | `/api/groups/<id>` | Delete a group |
| POST | `/api/groups/<id>/members` | Add a member |
| DELETE | `/api/members/<id>` | Remove a member (blocked if tied to expenses) |
| POST | `/api/groups/<id>/expenses` | Add an expense |
| GET | `/api/groups/<id>/expenses` | List expenses |
| PUT | `/api/expenses/<id>` | Edit an expense |
| DELETE | `/api/expenses/<id>` | Delete an expense |
| GET | `/api/groups/<id>/balances` | Get net balance per member |
| GET | `/api/groups/<id>/settlements` | Get simplified settlement transactions |

---

## Running Locally

### Option A: Docker (recommended — one command)

```bash
git clone https://github.com/khindimegha-hub/expense-splitter.git
cd expense-splitter
docker-compose up --build
```

Backend runs at `http://127.0.0.1:5000`. Open `frontend/index.html` in your browser (or serve it with VS Code's Live Server extension), and update `frontend/js/app.js`'s `API_BASE` to `http://127.0.0.1:5000/api` if testing locally.

### Option B: Manual setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
python run.py
```

Then open `frontend/index.html` via Live Server or any static file server.

---

## Running Tests

```bash
cd backend
pytest tests/ -v
```

16 tests covering:
- Split calculation correctness (including the floating-point rounding fix)
- Debt simplification algorithm correctness across multiple scenarios (simple case, already-settled, near-zero balances, single-debtor-multiple-creditors)
- Full API integration (create group → add members → add expense → verify balances → verify settlements)
- Data integrity guards (cross-group validation, member deletion safeguards)

---

## Known Limitations

- **SQLite on Render's free tier is ephemeral** — data resets on redeploy/restart. A production deployment would use persistent PostgreSQL.
- **Greedy algorithm is not provably optimal** in all cases (see algorithm section above) — a known, deliberate tradeoff for speed and simplicity over guaranteed minimality.
- **No authentication** — this is a portfolio demo; a real deployment would need user accounts and access control per group.
- **Free-tier cold starts** — first request after backend inactivity can take up to a minute.

---

## What I'd Improve With More Time

- PostgreSQL + persistent storage
- User authentication and per-user group access
- Unequal/percentage-based expense splits (currently equal-split only)
- An exact (non-greedy) settlement algorithm as an optional mode, to compare against the heuristic
- Real-time updates via WebSockets if multiple users are editing the same group

---

## Author

Megha Khindi — [LinkedIn](https://linkedin.com/in/megha-khindi) · [GitHub](https://github.com/khindimegha-hub)