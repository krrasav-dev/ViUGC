import os
import uuid
import hashlib
import datetime
from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.database import db_context

def seed_demo_data():
    """Seed demo users, tasks, and submissions for development."""
    now = datetime.datetime.utcnow().isoformat()

    def h(p): return hashlib.sha256(p.encode()).hexdigest()

    users = [
        (str(uuid.uuid4()), 'admin@oneliner.io', h('admin123'), 'Admin User', 'admin', 'active', 0, 0, now),
        (str(uuid.uuid4()), 'mod@oneliner.io', h('mod123'), 'Moderator', 'moderator', 'active', 0, 0, now),
        (str(uuid.uuid4()), 'creator1@example.com', h('pass123'), 'Alex Ivanov', 'creator', 'active', 247.5, 120.0, now),
        (str(uuid.uuid4()), 'creator2@example.com', h('pass123'), 'Maria Smirnova', 'creator', 'active', 89.0, 450.0, now),
        (str(uuid.uuid4()), 'creator3@example.com', h('pass123'), 'Denis Petrov', 'creator', 'active', 12.5, 0, now),
    ]

    tasks = [
        (str(uuid.uuid4()), 'Обзор нового iPhone 16', 'Сделайте честный обзор iPhone 16 в формате до 60 секунд. Покажите камеру, производительность, сравните с предыдущей моделью.', 5000.0, 1247.5, 5.0, 500.0, '2026-12-31T23:59:59', 'active', 'youtube,tiktok,instagram', users[0][0], now),
        (str(uuid.uuid4()), 'Топ-5 лайфхаков для путешествий', 'Покажите 5 реальных лайфхаков для путешественников. Видео должно быть практичным и полезным.', 3000.0, 567.0, 3.0, 300.0, '2026-11-30T23:59:59', 'active', 'tiktok,instagram', users[0][0], now),
        (str(uuid.uuid4()), 'Рецепт за 5 минут', 'Быстрый и вкусный рецепт который можно приготовить за 5 минут. Формат — вертикальное видео до 45 секунд.', 2000.0, 234.0, 2.5, 250.0, '2026-10-31T23:59:59', 'active', 'tiktok,instagram,youtube', users[0][0], now),
        (str(uuid.uuid4()), 'День из жизни разработчика', 'Снимите день из своей жизни как разработчика. Покажите рабочий процесс, инструменты, ритуалы.', 8000.0, 0, 8.0, 800.0, '2026-12-15T23:59:59', 'active', 'youtube', users[0][0], now),
    ]

    with db_context() as conn:
        # Only seed if empty
        existing = conn.execute('SELECT COUNT(*) as c FROM users').fetchone()['c']
        if existing > 0:
            return False

        for u in users:
            conn.execute(
                'INSERT INTO users (id, email, password_hash, name, role, status, balance_pending, balance_paid, created_at) VALUES (?,?,?,?,?,?,?,?,?)', u
            )
        for t in tasks:
            conn.execute(
                'INSERT INTO tasks (id, title, description, budget_pool, budget_spent, cpm_rate, max_payout, deadline, status, allowed_platforms, created_by, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', t
            )

        # Add some submissions
        sub_data = [
            (str(uuid.uuid4()), users[2][0], tasks[0][0], 'https://youtube.com/watch?v=dQw4w9WgXcQ', 'youtube', 'dQw4w9WgXcQ', 'tracking', 12, 249500, 245000, 247.5, None, now, now),
            (str(uuid.uuid4()), users[3][0], tasks[0][0], 'https://tiktok.com/@mariasm/video/7234567890123456789', 'tiktok', '7234567890123456789', 'approved', 5, 89000, 87000, 89.0, None, now, now),
            (str(uuid.uuid4()), users[4][0], tasks[1][0], 'https://youtube.com/watch?v=abc123def45', 'youtube', 'abc123def45', 'pending', 0, 0, 0, 0, None, None, now),
            (str(uuid.uuid4()), users[2][0], tasks[2][0], 'https://instagram.com/reel/CxYzAbCdEfG', 'instagram', 'CxYzAbCdEfG', 'rejected', 0, 15000, 0, 0, 'Видео не соответствует требованиям задания', now, now),
        ]
        for s in sub_data:
            conn.execute(
                '''INSERT INTO submissions (id, user_id, task_id, video_url, platform, platform_video_id,
                   status, fraud_score, views_count, views_credited, payout_amount, moderation_note,
                   last_tracked_at, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', s
            )

        # Add a payout request
        conn.execute(
            'INSERT INTO payouts (id, user_id, amount, status, method, created_at, updated_at) VALUES (?,?,?,?,?,?,?)',
            (str(uuid.uuid4()), users[2][0], 100.0, 'pending', 'bank_transfer', now, now)
        )

    return True

app = create_app()

if __name__ == '__main__':
    seeded = seed_demo_data()
    if seeded:
        print("✓ Demo data seeded")
        print("  Admin:   admin@oneliner.io / admin123")
        print("  Mod:     mod@oneliner.io   / mod123")
        print("  Creator: creator1@example.com / pass123")
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    print(f"✓ Starting One-liner API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
