import uuid
import datetime
from flask import Blueprint, request, jsonify, g
from app.database import db_context
from app.middleware.auth import require_auth

creator_bp = Blueprint('creator', __name__)

@creator_bp.get('/dashboard')
@require_auth
def dashboard():
    user_id = g.user['id']
    with db_context() as conn:
        user = conn.execute(
            'SELECT id, email, name, role, status, balance_pending, balance_paid, created_at FROM users WHERE id = ?',
            (user_id,)
        ).fetchone()
        submissions = conn.execute(
            '''SELECT s.*, t.title as task_title, t.cpm_rate
               FROM submissions s JOIN tasks t ON s.task_id = t.id
               WHERE s.user_id = ? ORDER BY s.created_at DESC''',
            (user_id,)
        ).fetchall()
        payouts = conn.execute(
            'SELECT * FROM payouts WHERE user_id = ? ORDER BY created_at DESC LIMIT 10',
            (user_id,)
        ).fetchall()

        total_views = conn.execute(
            'SELECT COALESCE(SUM(views_count),0) as v FROM submissions WHERE user_id = ? AND status != ?',
            (user_id, 'rejected')
        ).fetchone()['v']

    subs = [dict(s) for s in submissions]
    stats = {
        'total_submissions': len(subs),
        'approved': sum(1 for s in subs if s['status'] in ('approved', 'tracking', 'completed')),
        'pending': sum(1 for s in subs if s['status'] == 'pending'),
        'rejected': sum(1 for s in subs if s['status'] == 'rejected'),
        'total_views': total_views,
        'balance_pending': user['balance_pending'],
        'balance_paid': user['balance_paid'],
    }

    return jsonify({
        'user': dict(user),
        'stats': stats,
        'submissions': subs[:10],
        'payouts': [dict(p) for p in payouts]
    })

@creator_bp.post('/payouts/request')
@require_auth
def request_payout():
    data = request.get_json() or {}
    amount = float(data.get('amount', 0))
    method = data.get('method', 'bank_transfer')

    if amount <= 0:
        return jsonify({'error': 'Amount must be positive'}), 400
    if amount < 10:
        return jsonify({'error': 'Minimum withdrawal is $10'}), 400

    user = g.user
    if user['balance_pending'] < amount:
        return jsonify({'error': 'Insufficient balance'}), 400

    payout_id = str(uuid.uuid4())
    now = datetime.datetime.utcnow().isoformat()

    with db_context() as conn:
        # Check no pending payout already
        existing = conn.execute(
            "SELECT id FROM payouts WHERE user_id = ? AND status = 'pending'",
            (user['id'],)
        ).fetchone()
        if existing:
            return jsonify({'error': 'You already have a pending payout request'}), 409

        conn.execute(
            'INSERT INTO payouts (id, user_id, amount, status, method, created_at, updated_at) VALUES (?,?,?,?,?,?,?)',
            (payout_id, user['id'], amount, 'pending', method, now, now)
        )

    return jsonify({'message': 'Payout requested', 'payout_id': payout_id}), 201
