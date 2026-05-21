import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
    app.config['JSON_SORT_KEYS'] = False
    
    # CORS — разрешить все origins (или укажите конкретные домены)
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",  # Или ["https://resplendent-jelly-c82cda.netlify.app", "http://localhost:3000"]
            "methods": ["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
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
