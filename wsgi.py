import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Set production defaults
os.environ.setdefault('FLASK_ENV', 'production')

sys.path.insert(0, os.path.dirname(__file__))
from app import create_app

app = create_app()

def seed_demo_data():
    """Seed demo data on first run."""
    import uuid
    import hashlib
    import datetime
    from app.database import db_context

    now = datetime.datetime.utcnow().isoformat()
    def h(p): return hashlib.sha256(p.encode()).hexdigest()

    with db_context() as conn:
        existing = conn.execute('SELECT COUNT(*) as c FROM users').fetchone()['c']
        if existing > 0:
            return

        admin_id = str(uuid.uuid4())
        conn.execute(
            'INSERT INTO users (id, email, password_hash, name, role, status, balance_pending, balance_paid, created_at) VALUES (?,?,?,?,?,?,?,?,?)',
            (admin_id, 'admin@oneliner.io', h('admin123'), 'Admin User', 'admin', 'active', 0, 0, now)
        )
        conn.execute(
            'INSERT INTO users (id, email, password_hash, name, role, status, balance_pending, balance_paid, created_at) VALUES (?,?,?,?,?,?,?,?,?)',
            (str(uuid.uuid4()), 'mod@oneliner.io', h('mod123'), 'Moderator', 'moderator', 'active', 0, 0, now)
        )
        demo_creator = str(uuid.uuid4())
        conn.execute(
            'INSERT INTO users (id, email, password_hash, name, role, status, balance_pending, balance_paid, created_at) VALUES (?,?,?,?,?,?,?,?,?)',
            (demo_creator, 'creator1@example.com', h('pass123'), 'Alex Ivanov', 'creator', 'active', 247.5, 120.0, now)
        )

        # Demo tasks
        for title, desc, budget, cpm, maxp in [
            ('Обзор iPhone 16', 'Честный обзор iPhone 16 до 60 секунд. Камера, производительность, сравнение.', 5000, 5.0, 500),
            ('Топ-5 лайфхаков для путешествий', 'Покажите 5 реальных лайфхаков для путешественников.', 3000, 3.0, 300),
            ('Рецепт за 5 минут', 'Быстрый и вкусный рецепт. Вертикальное видео до 45 секунд.', 2000, 2.5, 250),
        ]:
            conn.execute(
                '''INSERT INTO tasks (id, title, description, budget_pool, budget_spent, cpm_rate, max_payout,
                   deadline, status, allowed_platforms, created_by, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                (str(uuid.uuid4()), title, desc, budget, 0, cpm, maxp,
                 '2026-12-31T23:59:59', 'active', 'youtube,tiktok,instagram', admin_id, now)
            )

with app.app_context():
    seed_demo_data()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'production') == 'development'
    print(f"✓ Starting One-liner API on port {port}")
    print("  Admin: admin@oneliner.io / admin123")
    print("  Creator: creator1@example.com / pass123")
    app.run(host='0.0.0.0', port=port, debug=debug)
