import os
from flask import Flask, jsonify
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
    app.config['JSON_SORT_KEYS'] = False

    # CORS — allow frontend
    @app.after_request
    def add_cors(response):
        origin = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PATCH, DELETE, OPTIONS'
        return response

    @app.before_request
    def handle_options():
        from flask import request
        if request.method == 'OPTIONS':
            return jsonify({}), 200

    # Init DB
    from app.database import init_db
    with app.app_context():
        init_db()

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.tasks import tasks_bp
    from app.routes.submissions import submissions_bp
    from app.routes.admin import admin_bp
    from app.routes.creator import creator_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(tasks_bp, url_prefix='/api/tasks')
    app.register_blueprint(submissions_bp, url_prefix='/api/submissions')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(creator_bp, url_prefix='/api/creator')

    @app.get('/api/health')
    def health():
        return jsonify({'status': 'ok', 'version': '1.0.0'})

    return app
