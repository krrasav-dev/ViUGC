import jwt
import os
from functools import wraps
from flask import request, jsonify, g
from app.database import db_context

JWT_SECRET = os.environ.get('JWT_SECRET', 'dev-secret-change-me')

def generate_token(user_id: str, role: str) -> str:
    import datetime
    payload = {
        'sub': user_id,
        'role': role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        token = auth_header[7:]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        with db_context() as conn:
            row = conn.execute(
                'SELECT id, email, name, role, status, balance_pending, balance_paid FROM users WHERE id = ?',
                (payload['sub'],)
            ).fetchone()
        if not row:
            return jsonify({'error': 'User not found'}), 401
        if row['status'] == 'banned':
            return jsonify({'error': 'Account banned'}), 403

        g.user = dict(row)
        return f(*args, **kwargs)
    return decorated

def require_role(*roles):
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated(*args, **kwargs):
            if g.user['role'] not in roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
