from flask import Blueprint, request, jsonify
from app.models import db, Group, Member, Expense, ExpenseSplit

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

    expense = Expense(
        description=data['description'],
        amount=data['amount'],
        paid_by_id=data['paid_by_id'],
        group_id=group_id
    )
    db.session.add(expense)
    db.session.flush()  # get expense.id before commit

    share = round(data['amount'] / len(data['split_between']), 2)
    for member_id in data['split_between']:
        db.session.add(ExpenseSplit(
            expense_id=expense.id,
            member_id=member_id,
            share_amount=share
        ))

    db.session.commit()
    return jsonify(expense.to_dict()), 201

@api.route('/groups/<int:group_id>/expenses', methods=['GET'])
def list_expenses(group_id):
    Group.query.get_or_404(group_id)
    expenses = Expense.query.filter_by(group_id=group_id).order_by(Expense.created_at.desc()).all()
    return jsonify([e.to_dict() for e in expenses])

@api.route('/expenses/<int:expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    return jsonify({'message': 'deleted'}), 200