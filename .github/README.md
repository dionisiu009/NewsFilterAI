# 🔍 NewsFilter AI

<div align="center">

![NewsFilter AI](https://img.shields.io/badge/NewsFilter-AI-00d4ff?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxMDAgMTAwIj48dGV4dCB5PSIuOWVtIiBmb250LXNpemU9IjkwIj7wn5SNPC90ZXh0Pjwvc3ZnPg==)
![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.0-092E20?style=for-the-badge&logo=django&logoColor=white)
![React](https://img.shields.io/badge/React-18-61dafb?style=for-the-badge&logo=react&logoColor=black)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)

**Інтелектуальна система перевірки новин на достовірність з використанням штучного інтелекту**

[🚀 Швидкий старт](#-швидкий-старт) • [📖 Документація](#-архітектура-системи) • [🤖 API](#-api-endpoints) • [📱 Telegram Bot](#-telegram-bot)

</div>

---

## 📋 Зміст

- [Про проєкт](#-про-проєкт)
- [Технологічний стек](#-технологічний-стек)
- [Архітектура системи](#-архітектура-системи)
- [Швидкий старт](#-швидкий-старт)
- [Структура проєкту](#-структура-проєкту)
- [Сервіси Docker](#-сервіси-docker)
- [API Endpoints](#-api-endpoints)
- [Frontend (React)](#-frontend-react)
- [Telegram Bot](#-telegram-bot)
- [Celery Tasks](#-celery-tasks)
- [Redis Cache & Списки доменів](#-redis-cache--списки-доменів)
- [Google Gemini AI](#-google-gemini-ai)
- [Змінні середовища](#-змінні-середовища)
- [Розробка](#-розробка)

---

## 🎯 Про проєкт

**NewsFilter AI** — це комплексна система для автоматичної перевірки новин на достовірність. Система використовує штучний інтелект (Google Gemini) для аналізу тексту новин та визначення рівня їх достовірності.

### ✨ Основні можливості

| Функція | Опис |
|---------|------|
| 🔍 **Перевірка URL** | Вставте посилання на новину — система автоматично розпарсить та проаналізує її |
| 🤖 **AI-аналіз** | Google Gemini AI перевіряє факти, джерело та ознаки маніпуляції |
| ⚡ **Кешування** | Результати зберігаються в Redis (TTL 6 годин) для миттєвих відповідей |
| 📊 **Історія** | Всі перевірки зберігаються в PostgreSQL |
| 🌐 **Web-інтерфейс** | Сучасний React SPA з адаптивним дизайном |
| 📱 **Telegram Bot** | Повноцінний бот для перевірки новин в месенджері |
| ⚫⚪ **Списки доменів** | Білий/чорний списки для відомих джерел |

### 🏷️ Типи вердиктів

| Вердикт | Emoji | Опис |
|---------|-------|------|
| **Достовірна** | ✅ | Інформація підтверджена, факти перевірені |
| **Фейк** | 🔴 | Виявлено недостовірну інформацію |
| **Частково правда** | 🟡 | Містить як правдиву, так і сумнівну інформацію |
| **Неможливо перевірити** | ❓ | Недостатньо даних для однозначного висновку |
| **Помилка** | ⚠️ | Виникла технічна помилка при перевірці |

---

## 🛠 Технологічний стек

### Backend
| Технологія | Версія | Призначення |
|------------|--------|-------------|
| Python | 3.11+ | Основна мова |
| Django | 5.0 | Web-фреймворк |
| Django REST Framework | 3.14 | REST API |
| Celery | 5.3 | Асинхронні задачі |
| Redis | 7.0 | Кеш + Message Broker |
| PostgreSQL | 15 | Основна БД |
| Gunicorn | 21.0 | WSGI сервер |

### AI & Parsing
| Технологія | Призначення |
|------------|-------------|
| Google Gemini AI | Аналіз тексту на достовірність |
| newspaper3k | Парсинг новинних статей |

### Frontend
| Технологія | Версія | Призначення |
|------------|--------|-------------|
| React | 18.2 | UI бібліотека |
| Vite | 5.0 | Збірник |
| Axios | 1.6 | HTTP клієнт |

### Telegram Bot
| Технологія | Версія | Призначення |
|------------|--------|-------------|
| Aiogram | 3.2 | Telegram Bot Framework |
| aiohttp | 3.9 | Асинхронний HTTP |

### Infrastructure
| Технологія | Призначення |
|------------|-------------|
| Docker & Docker Compose | Контейнеризація |
| Traefik | Reverse Proxy |
| Ngrok | Tunnel для Webhook |

---

## 🏗 Архітектура системи

```
                                    ┌─────────────────┐
                                    │   Користувач    │
                                    └────────┬────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
                    ▼                        ▼                        ▼
            ┌───────────────┐      ┌─────────────────┐      ┌─────────────────┐
            │  Web Browser  │      │  Telegram App   │      │   Admin Panel   │
            └───────┬───────┘      └────────┬────────┘      └────────┬────────┘
                    │                       │                        │
                    │                       │                        │
                    ▼                       ▼                        ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                              TRAEFIK (Reverse Proxy)                          │
│                                    Port 80                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────────┐ │
│  │ /  → Frontend    │  │ /api → Backend   │  │ /admin → Django Admin        │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────┘
                    │                       │
                    ▼                       ▼
        ┌───────────────────┐     ┌───────────────────┐
        │     FRONTEND      │     │      BACKEND      │
        │   React + Vite    │     │  Django + DRF     │
        │    Port 5173      │     │    Port 8000      │
        └───────────────────┘     └─────────┬─────────┘
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    │                       │                       │
                    ▼                       ▼                       ▼
        ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
        │    POSTGRESQL     │   │       REDIS       │   │   CELERY WORKER   │
        │    Port 5432      │   │    Port 6379      │   │                   │
        │  ┌─────────────┐  │   │  ┌─────────────┐  │   │  ┌─────────────┐  │
        │  │ NewsCheck   │  │   │  │ Cache       │  │   │  │ check_news  │  │
        │  │ Domain      │  │   │  │ Whitelist   │  │   │  │ _task()     │  │
        │  │ Reputation  │  │   │  │ Blacklist   │  │   │  └──────┬──────┘  │
        │  └─────────────┘  │   │  └─────────────┘  │   │         │         │
        └───────────────────┘   └───────────────────┘   └─────────┼─────────┘
                                                                  │
                                                                  ▼
                                                      ┌───────────────────┐
                                                      │   GOOGLE GEMINI   │
                                                      │        AI         │
                                                      │  (External API)   │
                                                      └───────────────────┘

        ┌───────────────────┐     ┌───────────────────┐
        │   TELEGRAM BOT    │     │       NGROK       │
        │     Aiogram       │◄────│   Tunnel:4040     │
        │   (Polling/Hook)  │     │                   │
        └───────────────────┘     └───────────────────┘
```

### 📊 Data Flow (Перевірка новини)

```
1. Користувач надсилає URL (Web/Telegram)
                    │
                    ▼
2. POST /api/check/ {"url": "https://..."}
                    │
                    ▼
3. ┌─────────────────────────────────────┐
   │         Перевірка Redis Cache       │
   │         (news:check:<url_hash>)     │
   └───────────────┬─────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
   Cache HIT             Cache MISS
        │                     │
        ▼                     ▼
   Миттєва            4. Створення запису
   відповідь             NewsCheck (DB)
   (200 OK)                   │
                              ▼
                    5. Celery Task
                       check_news_task.delay()
                              │
                              ▼
                    6. ┌─────────────────┐
                       │ Перевірка домену│
                       │ Whitelist/Black │
                       └────────┬────────┘
                                │
                       ┌────────┴────────┐
                       │                 │
                  Blacklist          Normal
                       │                 │
                       ▼                 ▼
                   Verdict:         7. Парсинг
                   "false"             (newspaper3k)
                   (90%)                  │
                                          ▼
                                 8. Google Gemini AI
                                    Аналіз тексту
                                          │
                                          ▼
                                 9. Збереження результату
                                    PostgreSQL + Redis
                                          │
                                          ▼
                                 10. Відповідь клієнту
                                     (polling task-status)
```

---

## 🚀 Швидкий старт

### Передумови

- [Docker](https://docs.docker.com/get-docker/) (20.10+)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2.0+)
- [Git](https://git-scm.com/)

### 1️⃣ Клонування репозиторію

```bash
git clone https://github.com/your-username/NewsFilterAI.git
cd NewsFilterAI
```

### 2️⃣ Налаштування змінних середовища

```bash
# Копіюємо шаблон
cp .env.example .env

# Редагуємо .env файл
nano .env  # або code .env
```

**Обов'язкові змінні:**
```env
# Генеруємо секретний ключ
DJANGO_SECRET_KEY=your-secret-key-here

# Пароль PostgreSQL
POSTGRES_PASSWORD=your-strong-password

# Google Gemini API Key (https://aistudio.google.com/app/apikey)
GEMINI_API_KEY=your-gemini-api-key

# Telegram Bot Token (від @BotFather)
TELEGRAM_BOT_TOKEN=your-bot-token
```

### 3️⃣ Запуск системи

```bash
# Збираємо та запускаємо всі сервіси
docker-compose up --build -d

# Перевіряємо статус
docker-compose ps
```

### 4️⃣ Ініціалізація Django

```bash
# Застосовуємо міграції
docker-compose exec backend python manage.py migrate

# Створюємо суперкористувача
docker-compose exec backend python manage.py createsuperuser

# Збираємо статичні файли
docker-compose exec backend python manage.py collectstatic --noinput

# Заповнюємо білий/чорний списки доменів
docker-compose exec backend python manage.py seed_domain_lists
```

### 5️⃣ Перевірка

| Сервіс | URL | Опис |
|--------|-----|------|
| 🌐 Frontend | http://localhost | Web-інтерфейс |
| 🔧 API Health | http://localhost/api/health/ | Статус API |
| 👤 Admin Panel | http://localhost/admin/ | Адмін-панель Django |
| 📊 Traefik | http://localhost:8080 | Dashboard Traefik |
| 🚇 Ngrok | http://localhost:4040 | Dashboard Ngrok |

---

## 📁 Структура проєкту

```
NewsFilterAI/
│
├── 📄 docker-compose.yml       # Конфігурація 8 сервісів
├── 📄 .env.example             # Шаблон змінних середовища
├── 📄 .env                     # Змінні середовища (не в git!)
├── 📄 .gitignore
├── 📄 README.md                # Ця документація
├── 📄 технічне_завадання.md    # ТЗ проєкту
│
├── 📁 backend/                 # Django Backend
│   ├── 📄 Dockerfile
│   ├── 📄 requirements.txt     # Python залежності
│   ├── 📄 manage.py
│   │
│   ├── 📁 config/              # Django конфігурація
│   │   ├── 📄 __init__.py
│   │   ├── 📄 settings.py      # Налаштування Django
│   │   ├── 📄 urls.py          # Головні URL routes
│   │   ├── 📄 wsgi.py          # WSGI application
│   │   └── 📄 celery.py        # Конфігурація Celery
│   │
│   ├── 📁 news/                # Основний Django App
│   │   ├── 📄 __init__.py
│   │   ├── 📄 models.py        # NewsCheck, DomainReputation
│   │   ├── 📄 serializers.py   # DRF серіалізатори
│   │   ├── 📄 views.py         # API views
│   │   ├── 📄 urls.py          # API routes
│   │   ├── 📄 tasks.py         # Celery tasks
│   │   ├── 📄 services.py      # Redis сервіси
│   │   ├── 📄 ai_service.py    # Google Gemini інтеграція
│   │   ├── 📄 parser_service.py # Парсинг статей
│   │   ├── 📄 admin.py         # Django Admin
│   │   └── 📁 management/
│   │       └── 📁 commands/
│   │           └── 📄 seed_domain_lists.py
│   │
│   ├── 📁 telegram_bot/        # Telegram Bot
│   │   ├── 📄 __init__.py
│   │   └── 📄 main.py          # Aiogram bot
│   │
│   └── 📁 staticfiles/         # Статичні файли Django
│
└── 📁 frontend/                # React Frontend
    ├── 📄 Dockerfile
    ├── 📄 package.json
    ├── 📄 vite.config.js
    ├── 📄 index.html
    │
    └── 📁 src/
        ├── 📄 main.jsx         # Entry point
        ├── 📄 App.jsx          # Головний компонент
        ├── 📄 App.css
        ├── 📄 index.css        # Глобальні стилі
        │
        ├── 📁 components/      # React компоненти
        │   ├── 📄 index.js
        │   ├── 📄 Header.jsx
        │   ├── 📄 UrlInputForm.jsx
        │   ├── 📄 LoadingIndicator.jsx
        │   ├── 📄 ResultCard.jsx
        │   └── 📄 ErrorMessage.jsx
        │
        ├── 📁 hooks/           # Custom hooks
        │   └── 📄 useNewsCheck.js
        │
        └── 📁 services/        # API сервіси
            └── 📄 api.js
```

---

## 🐳 Сервіси Docker

### Огляд сервісів

```yaml
services:
  ├── dockerproxy    # Docker Socket Proxy (безпека)
  ├── traefik        # Reverse Proxy
  ├── frontend       # React SPA
  ├── backend        # Django API
  ├── celery_worker  # Celery Worker
  ├── telegram_bot   # Aiogram Bot
  ├── ngrok          # Webhook Tunnel
  ├── redis          # Cache + Broker
  └── postgres       # Database
```

### Детальний опис

| Сервіс | Image/Build | Порти | Опис |
|--------|-------------|-------|------|
| **dockerproxy** | `tecnativa/docker-socket-proxy` | - | Безпечний доступ до Docker socket для Traefik |
| **traefik** | `traefik:latest` | 80, 8080 | Reverse proxy, маршрутизація запитів |
| **frontend** | `./frontend` | 5173 (internal) | React SPA з Vite |
| **backend** | `./backend` | 8000 (internal) | Django + Gunicorn |
| **celery_worker** | `./backend` | - | Celery worker для фонових задач |
| **telegram_bot** | `./backend` | - | Telegram bot (polling/webhook) |
| **ngrok** | `ngrok/ngrok:latest` | 4040 | Tunnel для Telegram webhook |
| **redis** | `redis:7-alpine` | 6379 | Кеш + Message broker |
| **postgres** | `postgres:15-alpine` | 5432 | PostgreSQL база даних |

### Маршрутизація Traefik

| Path | Сервіс | Priority |
|------|--------|----------|
| `/api/*` | backend | 10 |
| `/admin/*` | backend | 10 |
| `/static/*` | backend | 10 |
| `/*` (all other) | frontend | 1 |

---

## 🔌 API Endpoints

### Base URL
```
http://localhost/api/
```

### Endpoints

#### 🔍 Перевірка новини

```http
POST /api/check/
Content-Type: application/json

{
  "url": "https://example.com/news/article"
}
```

**Response (Cache HIT):**
```json
{
  "cached": true,
  "result": {
    "id": 1,
    "url": "https://example.com/news/article",
    "title": "Заголовок статті",
    "source_domain": "example.com",
    "verdict": "true",
    "verdict_display": "Достовірна",
    "is_fake": false,
    "confidence_score": 85.0,
    "summary": "Аналіз AI...",
    "recommendation": "Рекомендація..."
  }
}
```

**Response (Cache MISS):**
```json
{
  "cached": false,
  "status": "processing",
  "task_id": "abc123-def456-...",
  "check_id": 1,
  "message": "Новина відправлена на перевірку..."
}
```

#### 📊 Статус задачі

```http
GET /api/task-status/{task_id}/
```

**Response:**
```json
{
  "task_id": "abc123-def456-...",
  "status": "success",
  "result": { ... },
  "message": "Перевірка завершена"
}
```

#### 📝 Деталі перевірки

```http
GET /api/check/{check_id}/
```

#### 📜 Історія перевірок

```http
GET /api/history/?limit=20&offset=0&domain=bbc.com&verdict=true
```

**Response:**
```json
{
  "total": 100,
  "limit": 20,
  "offset": 0,
  "results": [...]
}
```

#### 🌐 Перевірка домену

```http
GET /api/domain-check/?domain=bbc.com
```

```http
POST /api/domain-check/
{"url": "https://bbc.com/news/article"}
```

**Response:**
```json
{
  "domain": "bbc.com",
  "in_whitelist": true,
  "in_blacklist": false,
  "reputation": "trusted"
}
```

#### 📋 Списки доменів

```http
GET /api/domains/?type=all
```

**Response:**
```json
{
  "stats": {
    "whitelist_count": 25,
    "blacklist_count": 5
  },
  "whitelist": ["bbc.com", "pravda.com.ua", ...],
  "blacklist": ["fake-news.com", ...]
}
```

#### ❤️ Health Check

```http
GET /api/health/
```

**Response:**
```json
{
  "status": "healthy",
  "service": "NewsFilter API",
  "version": "1.0.0"
}
```

---

## 💻 Frontend (React)

### Компоненти

| Компонент | Опис |
|-----------|------|
| `App.jsx` | Головний компонент, state management |
| `Header.jsx` | Шапка з логотипом |
| `UrlInputForm.jsx` | Форма введення URL з валідацією |
| `LoadingIndicator.jsx` | Анімація завантаження з етапами |
| `ResultCard.jsx` | Картка результату з вердиктом |
| `ErrorMessage.jsx` | Відображення помилок |

### Custom Hooks

| Hook | Опис |
|------|------|
| `useNewsCheck` | Управління станом перевірки (loading, result, error) |

### API Service

```javascript
// services/api.js
checkNews(url)        // POST /api/check/
getTaskStatus(taskId) // GET /api/task-status/{id}/
waitForResult(taskId) // Polling з інтервалом 2 сек
checkDomain(domain)   // GET /api/domain-check/
getHistory(params)    // GET /api/history/
```

### Стилі

- 🎨 Темна тема з градієнтами
- 📱 Responsive design (mobile-first)
- ✨ CSS анімації
- 🌈 Кольорове кодування вердиктів

---

## 📱 Telegram Bot

### Команди

| Команда | Опис |
|---------|------|
| `/start` | Привітання та інструкція |
| `/help` | Список команд та пояснення вердиктів |
| `/check <url>` | Перевірити новину за URL |
| `/ngrok` | Показати публічний URL тунелю |

### Використання

Просто надішліть посилання на новину — бот автоматично його розпізнає та перевірить.

### Режими роботи

| Режим | Змінна | Опис |
|-------|--------|------|
| **Polling** | `USE_WEBHOOK=false` | Бот опитує Telegram API (для розробки) |
| **Webhook** | `USE_WEBHOOK=true` | Telegram надсилає оновлення через ngrok |

### Приклад відповіді

```
✅ РЕЗУЛЬТАТ: ДОСТОВІРНА

📰 Заголовок: Breaking News Article...
🌐 Джерело: bbc.com
📊 Впевненість: 85%

📝 Аналіз:
Новина містить перевірені факти...

💡 Рекомендація:
Інформацію можна довіряти...

📦 (результат з кешу)
```

---

## ⚙️ Celery Tasks

### Основна задача

```python
# news/tasks.py

@shared_task(bind=True, max_retries=3)
def check_news_task(self, url: str, news_check_id: int) -> dict:
    """
    1. Перевіряє домен у білому/чорному списку
    2. Парсить статтю (newspaper3k)
    3. Відправляє в Google Gemini AI
    4. Зберігає результат в PostgreSQL
    5. Кешує в Redis
    """
```

### Налаштування

```python
# config/settings.py

CELERY_BROKER_URL = 'redis://redis:6379/0'
CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300  # 5 хвилин
```

### Моніторинг

```bash
# Логи Celery worker
docker-compose logs -f celery_worker

# Статус задачі
curl http://localhost/api/task-status/{task_id}/
```

---

## 🗄 Redis Cache & Списки доменів

### Структура ключів

| Ключ | Тип | Опис |
|------|-----|------|
| `news:check:<url_hash>` | String (JSON) | Кешований результат перевірки |
| `domains:whitelist` | Set | Білий список доменів |
| `domains:blacklist` | Set | Чорний список доменів |

### TTL

- Результати перевірки: **6 годин** (налаштовується через `NEWS_CACHE_TTL`)

### Білий список (приклади)

```
bbc.com, reuters.com, apnews.com, theguardian.com,
pravda.com.ua, ukrinform.ua, unian.ua, liga.net,
suspilne.media, radiosvoboda.org, president.gov.ua
```

### Команди управління

```bash
# Заповнити списки початковими даними
docker-compose exec backend python manage.py seed_domain_lists

# Очистити та перезаповнити
docker-compose exec backend python manage.py seed_domain_lists --clear
```

---

## 🤖 Google Gemini AI

### Налаштування

```env
GEMINI_API_KEY=your-api-key
GEMINI_MODEL_NAME=gemini-1.5-flash  # або gemini-1.5-pro
```

### Отримання API Key

1. Перейдіть на [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Створіть новий API key
3. Додайте його в `.env` файл

### Промпт для аналізу

Система використовує детальний промпт, який аналізує:
- ✅ Точність фактів
- 🌐 Достовірність джерела
- ⚠️ Ознаки маніпуляції
- 📋 Перевірені факти
- ❓ Неперевірені твердження

### Формат відповіді AI

```json
{
  "verdict": "true|false|partial|unverifiable",
  "confidence_score": 0-100,
  "is_fake": true|false,
  "summary": "Короткий висновок",
  "analysis": {
    "factual_accuracy": "...",
    "source_credibility": "...",
    "manipulation_signs": [...],
    "verified_facts": [...],
    "unverified_claims": [...]
  },
  "recommendation": "..."
}
```

---

## 🔐 Змінні середовища

### Повний список

| Змінна | Обов'язкова | За замовчуванням | Опис |
|--------|-------------|------------------|------|
| `DJANGO_SECRET_KEY` | ✅ | - | Секретний ключ Django |
| `DJANGO_DEBUG` | ❌ | `False` | Режим відладки |
| `DJANGO_ALLOWED_HOSTS` | ❌ | `localhost,127.0.0.1,backend` | Дозволені хости |
| `POSTGRES_DB` | ❌ | `newsfilter_db` | Назва БД |
| `POSTGRES_USER` | ❌ | `newsfilter_user` | Користувач БД |
| `POSTGRES_PASSWORD` | ✅ | - | Пароль БД |
| `POSTGRES_HOST` | ❌ | `postgres` | Хост БД |
| `POSTGRES_PORT` | ❌ | `5432` | Порт БД |
| `REDIS_URL` | ❌ | `redis://redis:6379/0` | URL Redis |
| `CELERY_BROKER_URL` | ❌ | `redis://redis:6379/0` | Broker URL |
| `GEMINI_API_KEY` | ✅ | - | API ключ Gemini |
| `GEMINI_MODEL_NAME` | ❌ | `gemini-1.5-flash` | Модель Gemini |
| `TELEGRAM_BOT_TOKEN` | ✅ | - | Токен Telegram бота |
| `BACKEND_API_URL` | ❌ | `http://backend:8000/api` | URL API для бота |
| `USE_WEBHOOK` | ❌ | `false` | Режим webhook |
| `NGROK_AUTHTOKEN` | ❌ | - | Токен ngrok |
| `NEWS_CACHE_TTL` | ❌ | `21600` | TTL кешу (сек) |
| `CORS_ALLOWED_ORIGINS` | ❌ | `http://localhost:5173,...` | CORS origins |

---

## 🔧 Розробка

### Корисні команди

```bash
# Перезапуск окремого сервісу
docker-compose restart backend

# Логи сервісу
docker-compose logs -f backend

# Доступ до контейнера
docker-compose exec backend bash

# Django shell
docker-compose exec backend python manage.py shell

# Створення міграцій
docker-compose exec backend python manage.py makemigrations

# Redis CLI
docker-compose exec redis redis-cli

# PostgreSQL
docker-compose exec postgres psql -U newsfilter_user -d newsfilter_db
```

### Тестування API

```bash
# Health check
curl http://localhost/api/health/

# Перевірка новини
curl -X POST http://localhost/api/check/ \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.bbc.com/news/example"}'

# Статус задачі
curl http://localhost/api/task-status/{task_id}/
```

### Очищення

```bash
# Зупинити всі сервіси
docker-compose down

# Зупинити та видалити volumes
docker-compose down -v

# Повне очищення (включаючи images)
docker-compose down -v --rmi all
```

---

## 📋 Етапи розробки

- [x] **Етап 1:** Інфраструктура (Docker Compose, структура проєкту)
- [x] **Етап 2:** Backend (моделі, серіалізатори, Redis сервіси)
- [x] **Етап 3:** AI інтеграція (Gemini API, Celery tasks, Views)
- [x] **Етап 4:** Telegram Bot (Aiogram, команди, API клієнт)
- [x] **Етап 5:** Frontend (React компоненти, hooks, стилі)
- [x] **Етап 6:** Документація (README.md)
- [ ] **Етап 7:** Тестування та деплой

---

## 🐛 Troubleshooting

### Помилка підключення до Redis

```bash
# Перевірте чи Redis запущений
docker-compose ps redis

# Перезапустіть Redis
docker-compose restart redis
```

### Celery задачі не виконуються

```bash
# Перевірте логи worker'а
docker-compose logs -f celery_worker

# Перезапустіть worker
docker-compose restart celery_worker
```

### Telegram bot не відповідає

```bash
# Перевірте токен
docker-compose logs telegram_bot

# Перевірте режим (polling vs webhook)
# USE_WEBHOOK=false для локальної розробки
```

### Frontend не завантажується

```bash
# Перевірте логи Traefik
docker-compose logs traefik

# Перевірте frontend
docker-compose logs frontend
```

---

## 📄 Ліцензія

MIT License © 2024

---

<div align="center">

**Розроблено з ❤️ та 🤖 AI**

[⬆ Повернутися на початок](#-newsfilter-ai)

</div>

