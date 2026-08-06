from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Group(db.Model):
    __tablename__ = 'groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    members = db.relationship('Member', backref='group', cascade='all, delete-orphan')
    expenses = db.relationship('Expense', backref='group', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat(),
            'member_count': len(self.members)
        }


class Member(db.Model):
    __tablename__ = 'members'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'group_id': self.group_id}


class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    paid_by_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    paid_by = db.relationship('Member', foreign_keys=[paid_by_id])
    splits = db.relationship('ExpenseSplit', backref='expense', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'description': self.description,
            'amount': self.amount,
            'paid_by': self.paid_by.name,
            'paid_by_id': self.paid_by_id,
            'group_id': self.group_id,
            'created_at': self.created_at.isoformat(),
            'splits': [s.to_dict() for s in self.splits]
        }


class ExpenseSplit(db.Model):
    """Who owes what share of a given expense."""
    __tablename__ = 'expense_splits'
    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey('expenses.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    share_amount = db.Column(db.Float, nullable=False)

    member = db.relationship('Member', foreign_keys=[member_id])

    def to_dict(self):
        return {
            'member_id': self.member_id,
            'member_name': self.member.name,
            'share_amount': self.share_amount
        }