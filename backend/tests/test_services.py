import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services import calculate_balances, simplify_debts, compute_equal_splits


# ---------- compute_equal_splits ----------

def test_equal_split_divides_evenly():
    shares = compute_equal_splits(300, [1, 2, 3])
    assert shares == {1: 100.0, 2: 100.0, 3: 100.0}
    assert sum(shares.values()) == 300


def test_equal_split_with_remainder():
    """100 / 3 doesn't divide evenly — shares must still sum exactly to 100."""
    shares = compute_equal_splits(100, [1, 2, 3])
    assert round(sum(shares.values()), 2) == 100.0
    # first member(s) absorb the extra paise
    assert shares[1] >= shares[3]


def test_equal_split_single_member():
    shares = compute_equal_splits(500, [1])
    assert shares == {1: 500.0}


def test_equal_split_large_group_no_drift():
    """Regression test for floating point drift across many members."""
    member_ids = list(range(1, 8))  # 7 members
    shares = compute_equal_splits(1000, member_ids)
    assert round(sum(shares.values()), 2) == 1000.0


# ---------- simplify_debts ----------

def test_simplify_debts_simple_case():
    balances = [
        {'member_id': 1, 'member_name': 'A', 'balance': 900.0},
        {'member_id': 2, 'member_name': 'B', 'balance': -300.0},
        {'member_id': 3, 'member_name': 'C', 'balance': -600.0},
    ]
    settlements = simplify_debts(balances)
    assert len(settlements) == 2
    total_settled = sum(s['amount'] for s in settlements)
    assert total_settled == 900.0


def test_simplify_debts_already_settled():
    balances = [
        {'member_id': 1, 'member_name': 'A', 'balance': 0.0},
        {'member_id': 2, 'member_name': 'B', 'balance': 0.0},
    ]
    settlements = simplify_debts(balances)
    assert settlements == []


def test_simplify_debts_near_zero_treated_as_settled():
    """Tiny floating point residue (e.g. 0.005) should not create a phantom transaction."""
    balances = [
        {'member_id': 1, 'member_name': 'A', 'balance': 0.005},
        {'member_id': 2, 'member_name': 'B', 'balance': -0.005},
    ]
    settlements = simplify_debts(balances)
    assert settlements == []


def test_simplify_debts_balances_conserved():
    """No matter the input, total credited must equal total debited across all transactions."""
    balances = [
        {'member_id': 1, 'member_name': 'A', 'balance': 200.0},
        {'member_id': 2, 'member_name': 'B', 'balance': -200.0},
        {'member_id': 3, 'member_name': 'C', 'balance': 600.0},
        {'member_id': 4, 'member_name': 'D', 'balance': -600.0},
    ]
    settlements = simplify_debts(balances)
    total = sum(s['amount'] for s in settlements)
    assert total == 800.0


def test_simplify_debts_single_debtor_multiple_creditors():
    balances = [
        {'member_id': 1, 'member_name': 'A', 'balance': 100.0},
        {'member_id': 2, 'member_name': 'B', 'balance': 200.0},
        {'member_id': 3, 'member_name': 'C', 'balance': -300.0},
    ]
    settlements = simplify_debts(balances)
    # C should pay both A and B
    payers = {s['from'] for s in settlements}
    assert payers == {'C'}
    assert sum(s['amount'] for s in settlements) == 300.0


def test_simplify_debts_never_exceeds_n_minus_1_transactions():
    """
    Known property of this greedy approach: transaction count should never
    exceed (number of people involved - 1), which is the theoretical ceiling
    for settling any set of balances that sum to zero.
    """
    balances = [
        {'member_id': 1, 'member_name': 'A', 'balance': 150.0},
        {'member_id': 2, 'member_name': 'B', 'balance': -50.0},
        {'member_id': 3, 'member_name': 'C', 'balance': -100.0},
    ]
    settlements = simplify_debts(balances)
    assert len(settlements) <= len(balances) - 1