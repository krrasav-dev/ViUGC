import uuid
import hashlib
import datetime
from flask import Blueprint, request, jsonify, g
from app.database import db_context
from app.middleware.auth import generate_token, require_auth

auth_bp = Blueprint('auth', __name__)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

@auth_bp.post('/register')
def register():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    name = (data.get('name') or '').strip()

    if not email or not password or not name:
        return jsonify({'error': 'Email, password and name are required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    if '@' not in email:
        return jsonify({'error': 'Invalid email'}), 400

    user_id = str(uuid.uuid4())
    now = datetime.datetime.utcnow().isoformat()

    try:
        with db_context() as conn:
            conn.execute(
                'INSERT INTO users (id, email, password_hash, name, role, status, created_at) VALUES (?,?,?,?,?,?,?)',
                (user_id, email, hash_password(password), name, 'creator', 'active', now)
            )
    except Exception:
        return jsonify({'error': 'Email already registered'}), 409

    token = generate_token(user_id, 'creator')
    return jsonify({
        'token': token,
        'user': {'id': user_id, 'email': email, 'name': name, 'role': 'creator'}
    }), 201

@auth_bp.post('/login')
def login():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    with db_context() as conn:
        user = conn.execute(
            'SELECT * FROM users WHERE email = ?', (email,)
        ).fetchone()

    if not user or not verify_password(password, user['password_hash']):
        return jsonify({'error': 'Invalid credentials'}), 401
    if user['status'] == 'banned':
        return jsonify({'error': 'Account banned'}), 403

    token = generate_token(user['id'], user['role'])
    return jsonify({
        'token': token,
        'user': {
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'role': user['role'],
            'balance_pending': user['balance_pending'],
            'balance_paid': user['balance_paid'],
        }
    })

@auth_bp.get('/me')
@require_auth
def me():
    return jsonify({'user': g.user})
