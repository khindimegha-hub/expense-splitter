import heapq
from app.models import Member, Expense


def compute_equal_splits(amount, member_ids):
    """
    Splits `amount` equally among `member_ids`, guaranteeing the shares
    sum EXACTLY back to `amount` — even when division doesn't come out even.

    Naive approach (round(amount/n, 2) for each person) can lose or gain
    paise due to floating-point rounding (e.g. 100 / 3 = 33.33 each,
    which sums to 99.99, not 100.00). This function distributes the
    leftover paise to the first few members so the total always matches.

    Returns a dict: {member_id: share_amount}
    """
    n = len(member_ids)
    total_paise = int(round(amount * 100))  # work in integer paise to avoid float drift
    base_share = total_paise // n
    remainder = total_paise - (base_share * n)

    shares = {}
    for i, member_id in enumerate(member_ids):
        share_paise = base_share + (1 if i < remainder else 0)
        shares[member_id] = round(share_paise / 100, 2)

    return shares


def calculate_balances(group_id):
    """
    Computes each member's net balance in a group.

    Positive balance = this member is owed money (they paid more than their share)
    Negative balance = this member owes money (they paid less than their share)

    Logic:
      - When a member pays for an expense, credit them the full amount
      - When a member is included in a split, debit them their share
      - Net balance = total paid - total owed
    """
    members = Member.query.filter_by(group_id=group_id).all()
    balances = {member.id: 0.0 for member in members}

    expenses = Expense.query.filter_by(group_id=group_id).all()

    for expense in expenses:
        # Credit the payer
        balances[expense.paid_by_id] += expense.amount

        # Debit everyone included in the split
        for split in expense.splits:
            balances[split.member_id] -= split.share_amount

    result = []
    for member in members:
        result.append({
            'member_id': member.id,
            'member_name': member.name,
            'balance': round(balances[member.id], 2)
        })

    return result


def validate_split_members(group_id, member_ids):
    """
    Ensures every member_id in a split actually belongs to this group.
    Prevents a bug where someone from another group gets added to a split.
    """
    valid_ids = {m.id for m in Member.query.filter_by(group_id=group_id).all()}
    invalid = [mid for mid in member_ids if mid not in valid_ids]
    return invalid  # empty list means all valid


def simplify_debts(balances):
    """
    Given a list of {member_id, member_name, balance} dicts,
    computes the minimum-ish set of transactions to settle all debts.

    Algorithm: Greedy max-heap matching.
      - Creditors (positive balance) go into a max-heap (people owed money)
      - Debtors (negative balance) go into a max-heap (people who owe money)
      - Repeatedly match the biggest creditor with the biggest debtor,
        settle the smaller of the two amounts, and push back any remainder.

    This is a well-known greedy heuristic for the "minimum cash flow" problem.
    NOTE: This does not guarantee the mathematically optimal minimum number
    of transactions in all cases (that problem is NP-hard in general), but
    it performs close to optimal and runs in O(n log n).

    Returns a list of settlement transactions:
      [{"from": "Arjun", "to": "Megha", "amount": 600.0}, ...]
    """
    # Python's heapq is a min-heap, so negate values to simulate a max-heap
    creditors = []  # (-balance, member_name) — people who are owed money
    debtors = []    # (balance, member_name) — people who owe money (stored negative)

    for entry in balances:
        bal = round(entry['balance'], 2)
        if bal > 0.01:
            heapq.heappush(creditors, (-bal, entry['member_name']))
        elif bal < -0.01:
            heapq.heappush(debtors, (bal, entry['member_name']))
        # balances within 0.01 of zero are treated as already settled

    transactions = []

    while creditors and debtors:
        credit_amt, creditor_name = heapq.heappop(creditors)
        debit_amt, debtor_name = heapq.heappop(debtors)

        credit_amt = -credit_amt   # back to positive
        debit_amt = -debit_amt     # back to positive (was stored negative)

        settle_amount = round(min(credit_amt, debit_amt), 2)

        transactions.append({
            'from': debtor_name,
            'to': creditor_name,
            'amount': settle_amount
        })

        remaining_credit = round(credit_amt - settle_amount, 2)
        remaining_debit = round(debit_amt - settle_amount, 2)

        # Push back whichever side still has a balance left
        if remaining_credit > 0.01:
            heapq.heappush(creditors, (-remaining_credit, creditor_name))
        if remaining_debit > 0.01:
            heapq.heappush(debtors, (-remaining_debit, debtor_name))

    return transactions