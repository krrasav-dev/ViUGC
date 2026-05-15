# One-liner — UGC Platform MVP

Платформа для UGC-креаторов: задания → загрузка видео → трекинг просмотров → выплаты.

## Быстрый старт (локально)

### Backend

```bash
cd backend
cp .env.example .env
python wsgi.py
# API запустится на http://localhost:5000
```

**Доступы для демо:**
- Admin: `admin@oneliner.io` / `admin123`
- Moderator: `mod@oneliner.io` / `mod123`
- Creator: `creator1@example.com` / `pass123`

### Frontend

Просто открой `frontend/index.html` в браузере.

> По умолчанию фронтенд обращается к `http://localhost:5000/api`.
> Для прода смени переменную `API` в `index.html` на URL своего бэкенда.

---

## Деплой на Railway

### 1. Создай аккаунт
Зайди на [railway.app](https://railway.app) → New Project.

### 2. Задеплой backend
```
New Service → Deploy from GitHub repo → выбери папку /backend
```
Или через CLI:
```bash
npm install -g @railway/cli
railway login
cd backend
railway init
railway up
```

### 3. Переменные окружения в Railway
```
SECRET_KEY=<random-string-32-chars>
JWT_SECRET=<random-string-32-chars>
FLASK_ENV=production
FRONTEND_URL=https://your-frontend-domain.com
PORT=5000
```

### 4. Frontend
Вариант A (статика через Cloudflare Pages / Vercel):
1. Загрузи `frontend/index.html`
2. В строке `const API = ...` замени на URL Railway-бэкенда

Вариант B (один сервис — Flask отдаёт фронтенд):
- Скопируй `frontend/index.html` в `backend/static/index.html`
- Добавь в `app/__init__.py`:
  ```python
  from flask import send_from_directory
  @app.get('/')
  def frontend():
      return send_from_directory('static', 'index.html')
  ```

### 5. PostgreSQL (для продакшена)
В Railway: Add Service → PostgreSQL.
Установи `DATABASE_URL` = строка подключения из Railway.

Обнови `backend/app/database.py` — замени sqlite на psycopg2:
```python
import psycopg2
conn = psycopg2.connect(os.environ['DATABASE_URL'])
```
Добавь `psycopg2-binary` в `requirements.txt`.

---

## API Endpoints

### Auth
| Method | Path | Описание |
|--------|------|----------|
| POST | /api/auth/register | Регистрация |
| POST | /api/auth/login | Вход |
| GET | /api/auth/me | Текущий пользователь |

### Tasks
| Method | Path | Доступ |
|--------|------|--------|
| GET | /api/tasks | Публичный |
| GET | /api/tasks/:id | Публичный |
| POST | /api/tasks | Admin/Mod |
| PATCH | /api/tasks/:id | Admin/Mod |

### Submissions
| Method | Path | Доступ |
|--------|------|--------|
| GET | /api/submissions/public | Публичный |
| GET | /api/submissions | Авторизованный |
| POST | /api/submissions | Creator |
| POST | /api/submissions/:id/track | Admin/Mod |

### Admin
| Method | Path | Доступ |
|--------|------|--------|
| GET | /api/admin/moderation | Admin/Mod |
| POST | /api/admin/moderation/:id | Admin/Mod |
| GET | /api/admin/users | Admin/Mod |
| POST | /api/admin/users/:id/ban | Admin/Mod |
| GET | /api/admin/payouts | Admin/Finance |
| POST | /api/admin/payouts/:id | Admin/Finance |
| GET | /api/admin/analytics | Admin |

### Creator
| Method | Path | Доступ |
|--------|------|--------|
| GET | /api/creator/dashboard | Creator |
| POST | /api/creator/payouts/request | Creator |

---

## Структура проекта

```
oneliner/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # Flask app factory
│   │   ├── database.py          # SQLite / PostgreSQL
│   │   ├── middleware/
│   │   │   └── auth.py          # JWT auth, RBAC
│   │   ├── routes/
│   │   │   ├── auth.py          # /api/auth/*
│   │   │   ├── tasks.py         # /api/tasks/*
│   │   │   ├── submissions.py   # /api/submissions/*
│   │   │   ├── admin.py         # /api/admin/*
│   │   │   └── creator.py       # /api/creator/*
│   │   └── services/
│   │       └── tracker.py       # Mock stats + anti-fraud
│   ├── wsgi.py                  # Production entry + seed
│   ├── main.py                  # Dev entry
│   ├── requirements.txt
│   ├── Procfile                 # Railway/Render
│   └── railway.toml
└── frontend/
    └── index.html               # Полный SPA (React + Recharts)
```

---

## Роли и права

| Роль | Права |
|------|-------|
| creator | Просмотр заданий, загрузка видео, кабинет, вывод средств |
| moderator | Модерация видео, просмотр авторов, баны |
| finance | Подтверждение выплат |
| admin | Полный доступ |

---

## Антифрод (MVP)

Mock-версия. Два правила:
1. **Engagement Rate** < 0.3% → +40 к скору
2. **Скорость роста** > 50K просмотров/час → +50 к скору

- Score > 70 → флаг для ручной проверки
- Score > 90 → засчитывается только 30% просмотров

В продакшене заменить `tracker.py:mock_fetch_stats()` на реальные API-вызовы.
