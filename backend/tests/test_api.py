import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import create_app
from app.models import db


@pytest.fixture
def client():
    """
    Creates a fresh Flask app with an in-memory SQLite database for each test.
    In-memory means it's wiped clean automatically after each test — no
    leftover data between tests, and no risk of touching your real dev database.
    """
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True

    with app.app_context():
        db.create_all()
        with app.test_client() as client:
            yield client
        db.drop_all()


def test_create_group(client):
    response = client.post('/api/groups', json={'name': 'Trip to Manali'})
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == 'Trip to Manali'
    assert 'id' in data


def test_create_group_without_name_fails(client):
    response = client.post('/api/groups', json={})
    assert response.status_code == 400


def test_full_expense_flow(client):
    """
    Integration test: create a group, add members, add an expense,
    then verify balances and settlements are computed correctly —
    exercising the full request/response cycle through real HTTP calls.
    """
    group_res = client.post('/api/groups', json={'name': 'Flat 4B'})
    group_id = group_res.get_json()['id']

    member_ids = []
    for name in ['Meera', 'Sam', 'Ken']:
        res = client.post(f'/api/groups/{group_id}/members', json={'name': name})
        member_ids.append(res.get_json()['id'])

    expense_res = client.post(f'/api/groups/{group_id}/expenses', json={
        'description': 'Groceries',
        'amount': 900,
        'paid_by_id': member_ids[0],
        'split_between': member_ids
    })
    assert expense_res.status_code == 201
    splits = expense_res.get_json()['splits']
    assert len(splits) == 3
    assert sum(s['share_amount'] for s in splits) == 900.0

    balances_res = client.get(f'/api/groups/{group_id}/balances')
    balances = balances_res.get_json()
    meera_balance = next(b for b in balances if b['member_name'] == 'Meera')
    assert meera_balance['balance'] == 600.0

    settlements_res = client.get(f'/api/groups/{group_id}/settlements')
    settlements_data = settlements_res.get_json()
    assert settlements_data['transaction_count'] == 2


def test_expense_with_invalid_member_fails(client):
    """A member from a different group should never be allowed into a split."""
    group1_res = client.post('/api/groups', json={'name': 'Group 1'})
    group1_id = group1_res.get_json()['id']

    group2_res = client.post('/api/groups', json={'name': 'Group 2'})
    group2_id = group2_res.get_json()['id']

    member1_res = client.post(f'/api/groups/{group1_id}/members', json={'name': 'Alice'})
    member1_id = member1_res.get_json()['id']

    member2_res = client.post(f'/api/groups/{group2_id}/members', json={'name': 'Bob'})
    member2_id = member2_res.get_json()['id']

    response = client.post(f'/api/groups/{group1_id}/expenses', json={
        'description': 'Cross-group leak attempt',
        'amount': 100,
        'paid_by_id': member1_id,
        'split_between': [member1_id, member2_id]
    })
    assert response.status_code == 400


def test_delete_expense_updates_balances(client):
    group_res = client.post('/api/groups', json={'name': 'Test Group'})
    group_id = group_res.get_json()['id']

    m1 = client.post(f'/api/groups/{group_id}/members', json={'name': 'X'}).get_json()['id']
    m2 = client.post(f'/api/groups/{group_id}/members', json={'name': 'Y'}).get_json()['id']

    expense_res = client.post(f'/api/groups/{group_id}/expenses', json={
        'description': 'Test expense',
        'amount': 200,
        'paid_by_id': m1,
        'split_between': [m1, m2]
    })
    expense_id = expense_res.get_json()['id']

    balances_before = client.get(f'/api/groups/{group_id}/balances').get_json()
    x_balance = next(b for b in balances_before if b['member_name'] == 'X')
    assert x_balance['balance'] == 100.0

    delete_res = client.delete(f'/api/expenses/{expense_id}')
    assert delete_res.status_code == 200

    balances_after = client.get(f'/api/groups/{group_id}/balances').get_json()
    x_balance_after = next(b for b in balances_after if b['member_name'] == 'X')
    assert x_balance_after['balance'] == 0.0


def test_member_cannot_be_deleted_if_has_expenses(client):
    group_res = client.post('/api/groups', json={'name': 'Test Group'})
    group_id = group_res.get_json()['id']

    m1 = client.post(f'/api/groups/{group_id}/members', json={'name': 'P'}).get_json()['id']
    m2 = client.post(f'/api/groups/{group_id}/members', json={'name': 'Q'}).get_json()['id']

    client.post(f'/api/groups/{group_id}/expenses', json={
        'description': 'Lunch',
        'amount': 100,
        'paid_by_id': m1,
        'split_between': [m1, m2]
    })

    response = client.delete(f'/api/members/{m1}')
    assert response.status_code == 400