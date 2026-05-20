import uuid
import datetime
from flask import Blueprint, request, jsonify, g
from app.database import db_context
from app.middleware.auth import require_auth, require_role
from app.services.tracker import extract_platform_and_id, mock_fetch_stats, compute_fraud_score, calculate_payout

submissions_bp = Blueprint('submissions', __name__)

def row_to_dict(row):
    return dict(row)

@submissions_bp.get('')
@require_auth
def list_submissions():
    role = g.user['role']
    user_id = g.user['id']
    task_id = request.args.get('task_id')
    status = request.args.get('status')

    query = '''SELECT s.*, u.name as author_name, t.title as task_title,
               t.cpm_rate, t.max_payout
               FROM submissions s
               JOIN users u ON s.user_id = u.id
               JOIN tasks t ON s.task_id = t.id
               WHERE 1=1'''
    params = []

    if role == 'creator':
        query += ' AND s.user_id = ?'
        params.append(user_id)
    if task_id:
        query += ' AND s.task_id = ?'
        params.append(task_id)
    if status:
        query += ' AND s.status = ?'
        params.append(status)

    query += ' ORDER BY s.created_at DESC'

    with db_context() as conn:
        rows = conn.execute(query, params).fetchall()
    return jsonify({'submissions': [row_to_dict(r) for r in rows]})

@submissions_bp.post('')
@require_auth
def create_submission():
    if g.user['role'] not in ('creator', 'admin'):
        return jsonify({'error': 'Only creators can submit videos'}), 403

    data = request.get_json() or {}
    task_id = data.get('task_id')
    video_url = (data.get('video_url') or '').strip()

    if not task_id or not video_url:
        return jsonify({'error': 'task_id and video_url are required'}), 400

    # Validate task exists and is active
    with db_context() as conn:
        task = conn.execute(
            'SELECT * FROM tasks WHERE id = ? AND status = ?', (task_id, 'active')
        ).fetchone()
    if not task:
        return jsonify({'error': 'Task not found or not active'}), 404

    # Check budget
    if task['budget_spent'] >= task['budget_pool']:
        return jsonify({'error': 'Task budget exhausted'}), 400

    # Check deadline
    if task['deadline'] < datetime.datetime.utcnow().isoformat():
        return jsonify({'error': 'Task deadline passed'}), 400

    # Extract platform info
    platform, video_id = extract_platform_and_id(video_url)
    if not platform:
        return jsonify({'error': 'Could not detect platform. Supported: YouTube, TikTok, Instagram'}), 400

    # Check allowed platforms
    allowed = task['allowed_platforms'].split(',')
    if platform not in allowed:
        return jsonify({'error': f'Platform {platform} not allowed for this task'}), 400

    # Check duplicate
    with db_context() as conn:
        dup = conn.execute(
            'SELECT id FROM submissions WHERE user_id = ? AND task_id = ?',
            (g.user['id'], task_id)
        ).fetchone()
    if dup:
        return jsonify({'error': 'You already submitted a video for this task'}), 409

    sub_id = str(uuid.uuid4())
    now = datetime.datetime.utcnow().isoformat()

    with db_context() as conn:
        conn.execute(
            '''INSERT INTO submissions (id, user_id, task_id, video_url, platform,
               platform_video_id, status, created_at)
               VALUES (?,?,?,?,?,?,?,?)''',
            (sub_id, g.user['id'], task_id, video_url, platform, video_id, 'pending', now)
        )

    with db_context() as conn:
        row = conn.execute(
            '''SELECT s.*, u.name as author_name, t.title as task_title
               FROM submissions s JOIN users u ON s.user_id=u.id JOIN tasks t ON s.task_id=t.id
               WHERE s.id = ?''', (sub_id,)
        ).fetchone()

    return jsonify({'submission': row_to_dict(row)}), 201

@submissions_bp.get('/public')
def list_public_submissions():
    """Public feed of approved submissions."""
    with db_context() as conn:
        rows = conn.execute(
            '''SELECT s.id, s.video_url, s.platform, s.views_count, s.payout_amount,
               s.created_at, u.name as author_name, t.title as task_title
               FROM submissions s
               JOIN users u ON s.user_id = u.id
               JOIN tasks t ON s.task_id = t.id
               WHERE s.status IN ('approved', 'tracking', 'completed')
               ORDER BY s.views_count DESC LIMIT 50''',
        ).fetchall()
    return jsonify({'submissions': [dict(r) for r in rows]})

@submissions_bp.post('/<sub_id>/track')
@require_role('admin', 'moderator')
def trigger_tracking(sub_id):
    """Manually trigger stats update for a submission."""
    with db_context() as conn:
        sub = conn.execute(
            'SELECT s.*, t.cpm_rate, t.max_payout, t.budget_pool, t.budget_spent FROM submissions s JOIN tasks t ON s.task_id = t.id WHERE s.id = ?',
            (sub_id,)
        ).fetchone()
    if not sub:
        return jsonify({'error': 'Submission not found'}), 404
    if sub['status'] not in ('approved', 'tracking'):
        return jsonify({'error': 'Submission must be approved for tracking'}), 400

    stats = mock_fetch_stats(sub['platform'], sub['platform_video_id'], sub['views_count'])

    # Anti-fraud check
    hours = 24.0  # Mock: assume video is 24h old
    fraud_score = compute_fraud_score(
        stats['views'], stats['likes'], stats['comments'], hours
    )

    views_credited = stats['views']
    if fraud_score > 70:
        views_credited = int(views_credited * 0.3)  # Count only 30% if suspicious

    payout = calculate_payout(views_credited, sub['cpm_rate'], sub['max_payout'])
    now = datetime.datetime.utcnow().isoformat()

    new_status = 'tracking'
    if payout >= sub['max_payout']:
        new_status = 'completed'

    with db_context() as conn:
        conn.execute(
            '''UPDATE submissions SET views_count=?, views_credited=?, payout_amount=?,
               fraud_score=?, status=?, last_tracked_at=? WHERE id=?''',
            (stats['views'], views_credited, payout, fraud_score, new_status, now, sub_id)
        )
        # Update user balance
        conn.execute(
            'UPDATE users SET balance_pending = balance_pending + ? WHERE id = ?',
            (payout, sub['user_id'])
        )
        # Update task budget
        conn.execute(
            'UPDATE tasks SET budget_spent = budget_spent + ? WHERE id = ?',
            (payout, sub['task_id'])
        )

    return jsonify({
        'views': stats['views'],
        'views_credited': views_credited,
        'payout': payout,
        'fraud_score': fraud_score,
        'status': new_status
    })
