import uuid
import datetime
from flask import Blueprint, request, jsonify, g
from app.database import db_context
from app.middleware.auth import require_role

admin_bp = Blueprint('admin', __name__)

# ── Moderation queue ──────────────────────────────────────────────

@admin_bp.get('/moderation')
@require_role('admin', 'moderator')
def moderation_queue():
    status = request.args.get('status', 'pending')
    with db_context() as conn:
        rows = conn.execute(
            '''SELECT s.*, u.name as author_name, u.email as author_email,
               t.title as task_title, t.cpm_rate, t.max_payout
               FROM submissions s
               JOIN users u ON s.user_id = u.id
               JOIN tasks t ON s.task_id = t.id
               WHERE s.status = ?
               ORDER BY s.created_at ASC''',
            (status,)
        ).fetchall()
    return jsonify({'submissions': [dict(r) for r in rows]})

@admin_bp.post('/moderation/<sub_id>')
@require_role('admin', 'moderator')
def moderate_submission(sub_id):
    data = request.get_json() or {}
    action = data.get('action')  # 'approve' | 'reject'
    note = data.get('note', '')

    if action not in ('approve', 'reject'):
        return jsonify({'error': 'action must be approve or reject'}), 400

    new_status = 'approved' if action == 'approve' else 'rejected'

    with db_context() as conn:
        sub = conn.execute('SELECT * FROM submissions WHERE id = ?', (sub_id,)).fetchone()
        if not sub:
            return jsonify({'error': 'Submission not found'}), 404

        conn.execute(
            'UPDATE submissions SET status = ?, moderation_note = ? WHERE id = ?',
            (new_status, note, sub_id)
        )
        # Log action
        conn.execute(
            'INSERT INTO audit_log (id, admin_id, action, target_id, details, created_at) VALUES (?,?,?,?,?,?)',
            (str(uuid.uuid4()), g.user['id'], f'submission_{action}', sub_id, note,
             datetime.datetime.utcnow().isoformat())
        )

    return jsonify({'message': f'Submission {action}d', 'status': new_status})

# ── Users management ─────────────────────────────────────────────

@admin_bp.get('/users')
@require_role('admin', 'moderator')
def list_users():
    role = request.args.get('role')
    status = request.args.get('status')
    search = request.args.get('search', '')

    query = 'SELECT id, email, name, role, status, balance_pending, balance_paid, created_at FROM users WHERE 1=1'
    params = []
    if role:
        query += ' AND role = ?'; params.append(role)
    if status:
        query += ' AND status = ?'; params.append(status)
    if search:
        query += ' AND (email LIKE ? OR name LIKE ?)'; params += [f'%{search}%', f'%{search}%']
    query += ' ORDER BY created_at DESC'

    with db_context() as conn:
        rows = conn.execute(query, params).fetchall()
    return jsonify({'users': [dict(r) for r in rows]})

@admin_bp.get('/users/<user_id>')
@require_role('admin', 'moderator')
def get_user(user_id):
    with db_context() as conn:
        user = conn.execute(
            'SELECT id, email, name, role, status, balance_pending, balance_paid, created_at FROM users WHERE id = ?',
            (user_id,)
        ).fetchone()
        submissions = conn.execute(
            '''SELECT s.*, t.title as task_title FROM submissions s
               JOIN tasks t ON s.task_id = t.id
               WHERE s.user_id = ? ORDER BY s.created_at DESC''',
            (user_id,)
        ).fetchall()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({
        'user': dict(user),
        'submissions': [dict(s) for s in submissions]
    })

@admin_bp.post('/users/<user_id>/ban')
@require_role('admin', 'moderator')
def ban_user(user_id):
    data = request.get_json() or {}
    reason = data.get('reason', '')
    with db_context() as conn:
        conn.execute('UPDATE users SET status = ? WHERE id = ?', ('banned', user_id))
        conn.execute(
            'INSERT INTO audit_log (id, admin_id, action, target_id, details, created_at) VALUES (?,?,?,?,?,?)',
            (str(uuid.uuid4()), g.user['id'], 'user_ban', user_id, reason,
             datetime.datetime.utcnow().isoformat())
        )
    return jsonify({'message': 'User banned'})

@admin_bp.post('/users/<user_id>/unban')
@require_role('admin')
def unban_user(user_id):
    with db_context() as conn:
        conn.execute('UPDATE users SET status = ? WHERE id = ?', ('active', user_id))
    return jsonify({'message': 'User unbanned'})

# ── Payouts ──────────────────────────────────────────────────────

@admin_bp.get('/payouts')
@require_role('admin', 'finance')
def list_payouts():
    status = request.args.get('status', 'pending')
    with db_context() as conn:
        rows = conn.execute(
            '''SELECT p.*, u.name as user_name, u.email as user_email
               FROM payouts p JOIN users u ON p.user_id = u.id
               WHERE p.status = ? ORDER BY p.created_at DESC''',
            (status,)
        ).fetchall()
    return jsonify({'payouts': [dict(r) for r in rows]})

@admin_bp.post('/payouts/<payout_id>')
@require_role('admin', 'finance')
def process_payout(payout_id):
    data = request.get_json() or {}
    action = data.get('action')  # 'approve' | 'reject'
    note = data.get('note', '')

    if action not in ('approve', 'reject'):
        return jsonify({'error': 'action must be approve or reject'}), 400

    now = datetime.datetime.utcnow().isoformat()
    new_status = 'approved' if action == 'approve' else 'rejected'

    with db_context() as conn:
        payout = conn.execute('SELECT * FROM payouts WHERE id = ?', (payout_id,)).fetchone()
        if not payout:
            return jsonify({'error': 'Payout not found'}), 404

        conn.execute(
            'UPDATE payouts SET status = ?, note = ?, updated_at = ? WHERE id = ?',
            (new_status, note, now, payout_id)
        )
        if action == 'approve':
            conn.execute(
                '''UPDATE users SET
                   balance_pending = balance_pending - ?,
                   balance_paid = balance_paid + ?
                   WHERE id = ?''',
                (payout['amount'], payout['amount'], payout['user_id'])
            )
        conn.execute(
            'INSERT INTO audit_log (id, admin_id, action, target_id, details, created_at) VALUES (?,?,?,?,?,?)',
            (str(uuid.uuid4()), g.user['id'], f'payout_{action}', payout_id, note, now)
        )

    return jsonify({'message': f'Payout {action}d'})

# ── Analytics ────────────────────────────────────────────────────

@admin_bp.get('/analytics')
@require_role('admin')
def analytics():
    with db_context() as conn:
        stats = conn.execute('''
            SELECT
              (SELECT COUNT(*) FROM users WHERE role = 'creator') as total_creators,
              (SELECT COUNT(*) FROM users WHERE role = 'creator' AND created_at >= date('now', '-30 days')) as new_creators_30d,
              (SELECT COUNT(*) FROM submissions) as total_submissions,
              (SELECT COUNT(*) FROM submissions WHERE status = 'pending') as pending_moderation,
              (SELECT COUNT(*) FROM submissions WHERE status IN ('approved','tracking','completed')) as approved_submissions,
              (SELECT COALESCE(SUM(views_count),0) FROM submissions WHERE status != 'rejected') as total_views,
              (SELECT COALESCE(SUM(payout_amount),0) FROM submissions) as total_payouts_accrued,
              (SELECT COALESCE(SUM(balance_paid),0) FROM users) as total_paid_out,
              (SELECT COUNT(*) FROM tasks WHERE status = 'active') as active_tasks
        ''').fetchone()

        # Top videos
        top_videos = conn.execute(
            '''SELECT s.id, s.video_url, s.platform, s.views_count, s.payout_amount,
               u.name as author_name, t.title as task_title
               FROM submissions s JOIN users u ON s.user_id=u.id JOIN tasks t ON s.task_id=t.id
               WHERE s.status != 'rejected'
               ORDER BY s.views_count DESC LIMIT 10'''
        ).fetchall()

        # Platform breakdown
        platforms = conn.execute(
            '''SELECT platform, COUNT(*) as count, SUM(views_count) as total_views
               FROM submissions WHERE status != 'rejected'
               GROUP BY platform'''
        ).fetchall()

    return jsonify({
        'stats': dict(stats),
        'top_videos': [dict(v) for v in top_videos],
        'platforms': [dict(p) for p in platforms]
    })

@admin_bp.get('/audit-log')
@require_role('admin')
def audit_log():
    with db_context() as conn:
        rows = conn.execute(
            '''SELECT a.*, u.name as admin_name FROM audit_log a
               JOIN users u ON a.admin_id = u.id
               ORDER BY a.created_at DESC LIMIT 100'''
        ).fetchall()
    return jsonify({'log': [dict(r) for r in rows]})
