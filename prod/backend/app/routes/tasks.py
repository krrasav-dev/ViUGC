import uuid
import datetime
from flask import Blueprint, request, jsonify, g
from app.database import db_context
from app.middleware.auth import require_auth, require_role

tasks_bp = Blueprint('tasks', __name__)

def task_row_to_dict(row):
    d = dict(row)
    d['allowed_platforms'] = d['allowed_platforms'].split(',') if d['allowed_platforms'] else []
    return d

@tasks_bp.get('')
def list_tasks():
    status = request.args.get('status', 'active')
    with db_context() as conn:
        rows = conn.execute(
            '''SELECT t.*, u.name as creator_name,
               (SELECT COUNT(*) FROM submissions s WHERE s.task_id = t.id) as submission_count
               FROM tasks t JOIN users u ON t.created_by = u.id
               WHERE t.status = ? ORDER BY t.created_at DESC''',
            (status,)
        ).fetchall()
    return jsonify({'tasks': [task_row_to_dict(r) for r in rows]})

@tasks_bp.get('/<task_id>')
def get_task(task_id):
    with db_context() as conn:
        row = conn.execute(
            '''SELECT t.*, u.name as creator_name,
               (SELECT COUNT(*) FROM submissions s WHERE s.task_id = t.id) as submission_count,
               (SELECT COUNT(*) FROM submissions s WHERE s.task_id = t.id AND s.status = 'approved') as approved_count
               FROM tasks t JOIN users u ON t.created_by = u.id WHERE t.id = ?''',
            (task_id,)
        ).fetchone()
    if not row:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify({'task': task_row_to_dict(row)})

@tasks_bp.post('')
@require_role('admin', 'moderator')
def create_task():
    data = request.get_json() or {}
    required = ['title', 'description', 'budget_pool', 'cpm_rate', 'max_payout', 'deadline']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    task_id = str(uuid.uuid4())
    now = datetime.datetime.utcnow().isoformat()
    platforms = ','.join(data.get('allowed_platforms', ['youtube', 'tiktok', 'instagram']))

    with db_context() as conn:
        conn.execute(
            '''INSERT INTO tasks (id, title, description, budget_pool, cpm_rate, max_payout,
               deadline, status, allowed_platforms, created_by, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
            (task_id, data['title'], data['description'], float(data['budget_pool']),
             float(data['cpm_rate']), float(data['max_payout']),
             data['deadline'], data.get('status', 'active'), platforms, g.user['id'], now)
        )

    with db_context() as conn:
        row = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
    return jsonify({'task': task_row_to_dict(row)}), 201

@tasks_bp.patch('/<task_id>')
@require_role('admin', 'moderator')
def update_task(task_id):
    data = request.get_json() or {}
    allowed = ['title', 'description', 'budget_pool', 'cpm_rate', 'max_payout', 'deadline', 'status']
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({'error': 'No valid fields to update'}), 400

    set_clause = ', '.join(f'{k} = ?' for k in updates)
    values = list(updates.values()) + [task_id]

    with db_context() as conn:
        conn.execute(f'UPDATE tasks SET {set_clause} WHERE id = ?', values)
        row = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify({'task': task_row_to_dict(row)})

@tasks_bp.delete('/<task_id>')
@require_role('admin')
def delete_task(task_id):
    with db_context() as conn:
        conn.execute('UPDATE tasks SET status = ? WHERE id = ?', ('closed', task_id))
    return jsonify({'message': 'Task closed'})
