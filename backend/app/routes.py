from flask import Blueprint, request, jsonify
from app.models import db, Group, Member, Expense, ExpenseSplit
from app.services import calculate_balances, validate_split_members, simplify_debts, compute_equal_splits

api = Blueprint('api', __name__)

# ---------- GROUPS ----------

@api.route('/groups', methods=['POST'])
def create_group():
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': 'name is required'}), 400
    group = Group(name=data['name'])
    db.session.add(group)
    db.session.commit()
    return jsonify(group.to_dict()), 201


@api.route('/groups', methods=['GET'])
def list_groups():
    groups = Group.query.all()
    return jsonify([g.to_dict() for g in groups])


@api.route('/groups/<int:group_id>', methods=['GET'])
def get_group(group_id):
    group = Group.query.get_or_404(group_id)
    result = group.to_dict()
    result['members'] = [m.to_dict() for m in group.members]
    return jsonify(result)


@api.route('/groups/<int:group_id>', methods=['DELETE'])
def delete_group(group_id):
    group = Group.query.get_or_404(group_id)
    db.session.delete(group)
    db.session.commit()
    return jsonify({'message': 'deleted'}), 200


# ---------- MEMBERS ----------

@api.route('/groups/<int:group_id>/members', methods=['POST'])
def add_member(group_id):
    Group.query.get_or_404(group_id)
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': 'name is required'}), 400
    member = Member(name=data['name'], group_id=group_id)
    db.session.add(member)
    db.session.commit()
    return jsonify(member.to_dict()), 201


@api.route('/groups/<int:group_id>/members', methods=['GET'])
def list_members(group_id):
    Group.query.get_or_404(group_id)
    members = Member.query.filter_by(group_id=group_id).all()
    return jsonify([m.to_dict() for m in members])


@api.route('/members/<int:member_id>', methods=['DELETE'])
def delete_member(member_id):
    """
    Prevents deleting a member who is involved in existing expenses,
    to avoid orphaned/broken balance calculations.
    """
    member = Member.query.get_or_404(member_id)

    has_expenses = Expense.query.filter_by(paid_by_id=member_id).first()
    has_splits = ExpenseSplit.query.filter_by(member_id=member_id).first()

    if has_expenses or has_splits:
        return jsonify({'error': 'cannot delete member with existing expenses. Delete their expenses first.'}), 400

    db.session.delete(member)
    db.session.commit()
    return jsonify({'message': 'deleted'}), 200


# ---------- EXPENSES ----------

@api.route('/groups/<int:group_id>/expenses', methods=['POST'])
def add_expense(group_id):
    """
    Expected JSON:
    {
      "description": "Dinner",
      "amount": 1200.0,
      "paid_by_id": 1,
      "split_between": [1, 2, 3]   // equal split among these member ids
    }
    """
    Group.query.get_or_404(group_id)
    data = request.get_json()

    required = ['description', 'amount', 'paid_by_id', 'split_between']
    if not data or not all(k in data for k in required):
        return jsonify({'error': f'required fields: {required}'}), 400

    if not data['split_between']:
        return jsonify({'error': 'split_between cannot be empty'}), 400

    if data['amount'] <= 0:
        return jsonify({'error': 'amount must be positive'}), 400

    # Validate payer belongs to this group
    payer = Member.query.filter_by(id=data['paid_by_id'], group_id=group_id).first()
    if not payer:
        return jsonify({'error': 'paid_by_id does not belong to this group'}), 400

    # Validate all split members belong to this group
    invalid_ids = validate_split_members(group_id, data['split_between'])
    if invalid_ids:
        return jsonify({'error': f'these member_ids do not belong to this group: {invalid_ids}'}), 400

    expense = Expense(
        description=data['description'],
        amount=data['amount'],
        paid_by_id=data['paid_by_id'],
        group_id=group_id
    )
    db.session.add(expense)
    db.session.flush()  # get expense.id before commit

    # Day 4: use remainder-safe split calculation so shares always sum
    # exactly to the original amount (avoids floating-point rounding loss)
    shares = compute_equal_splits(data['amount'], data['split_between'])
    for member_id in data['split_between']:
        db.session.add(ExpenseSplit(
            expense_id=expense.id,
            member_id=member_id,
            share_amount=shares[member_id]
        ))

    db.session.commit()
    return jsonify(expense.to_dict()), 201


@api.route('/groups/<int:group_id>/expenses', methods=['GET'])
def list_expenses(group_id):
    Group.query.get_or_404(group_id)
    expenses = Expense.query.filter_by(group_id=group_id).order_by(Expense.created_at.desc()).all()
    return jsonify([e.to_dict() for e in expenses])


@api.route('/groups/<int:group_id>/expenses/by-member/<int:member_id>', methods=['GET'])
def expenses_by_member(group_id, member_id):
    """Returns all expenses in a group that a specific member paid for or was part of."""
    Group.query.get_or_404(group_id)
    expenses = Expense.query.filter_by(group_id=group_id).all()
    filtered = [
        e.to_dict() for e in expenses
        if e.paid_by_id == member_id or any(s.member_id == member_id for s in e.splits)
    ]
    return jsonify(filtered)


@api.route('/expenses/<int:expense_id>', methods=['PUT'])
def update_expense(expense_id):
    """
    Allows editing description, amount, paid_by_id, or split_between.
    Re-calculates splits from scratch if amount or split_between changes.

    Expected JSON (all fields optional, include only what you want to change):
    {
      "description": "Updated name",
      "amount": 1500.0,
      "paid_by_id": 2,
      "split_between": [1, 2, 3]
    }
    """
    expense = Expense.query.get_or_404(expense_id)
    data = request.get_json()

    if not data:
        return jsonify({'error': 'no data provided'}), 400

    if 'description' in data:
        expense.description = data['description']

    if 'paid_by_id' in data:
        payer = Member.query.filter_by(id=data['paid_by_id'], group_id=expense.group_id).first()
        if not payer:
            return jsonify({'error': 'paid_by_id does not belong to this group'}), 400
        expense.paid_by_id = data['paid_by_id']

    # If amount or split_between changes, recompute splits entirely
    if 'amount' in data or 'split_between' in data:
        new_amount = data.get('amount', expense.amount)
        new_split = data.get('split_between', [s.member_id for s in expense.splits])

        if new_amount <= 0:
            return jsonify({'error': 'amount must be positive'}), 400

        if not new_split:
            return jsonify({'error': 'split_between cannot be empty'}), 400

        invalid_ids = validate_split_members(expense.group_id, new_split)
        if invalid_ids:
            return jsonify({'error': f'these member_ids do not belong to this group: {invalid_ids}'}), 400

        # Delete old splits, create new ones
        for split in list(expense.splits):
            db.session.delete(split)

        expense.amount = new_amount

        # Day 4: remainder-safe split calculation
        shares = compute_equal_splits(new_amount, new_split)
        for member_id in new_split:
            db.session.add(ExpenseSplit(
                expense_id=expense.id,
                member_id=member_id,
                share_amount=shares[member_id]
            ))

    db.session.commit()
    return jsonify(expense.to_dict()), 200


@api.route('/expenses/<int:expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    return jsonify({'message': 'deleted'}), 200


# ---------- BALANCES ----------

@api.route('/groups/<int:group_id>/balances', methods=['GET'])
def get_balances(group_id):
    """
    Returns each member's net balance in the group.
    Positive = they are owed money. Negative = they owe money.
    This is the direct input to the debt-simplification algorithm.
    """
    Group.query.get_or_404(group_id)
    balances = calculate_balances(group_id)
    return jsonify(balances)


# ---------- SETTLEMENTS (debt simplification) ----------

@api.route('/groups/<int:group_id>/settlements', methods=['GET'])
def get_settlements(group_id):
    """
    Returns the minimum-ish set of transactions to settle all debts in the group.
    This is the core differentiator of the project — debt simplification via
    a greedy max-heap matching algorithm (see services.simplify_debts).
    """
    Group.query.get_or_404(group_id)
    balances = calculate_balances(group_id)
    settlements = simplify_debts(balances)

    return jsonify({
        'balances': balances,
        'settlements': settlements,
        'transaction_count': len(settlements)
    })