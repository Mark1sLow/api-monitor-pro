# API Monitor Pro

Система мониторинга и анализа SLI/SLO API-методов веб-приложений для DevOps-инженеров.

Сервис позволяет отслеживать ключевые метрики производительности API:
- **Задержка ответа** (Latency)
- **Доступность** (Availability)
- **Частота ошибок** (Error Rate)

## 🚀 Возможности

- 📊 **Визуализация метрик** - Графики на Plotly для анализа трендов
- ⚠️ **Уведомления SLA** - Email оповещения при нарушении порогов
- 🔄 **Автоматический мониторинг** - Периодическая проверка API
- 👥 **Многопользовательский режим** - Изоляция проектов между пользователями
- 📱 **Адаптивный интерфейс** - Bootstrap 5 дизайн

## 🛠 Технологии

- **Backend**: Django 4.2, Python 3.12+
- **База данных**: SQLite (для разработки), PostgreSQL (для продакшена)
- **Фронтенд**: Bootstrap 5, Plotly.js
- **Задачи**: Django Management Commands
- **Email**: SMTP (Gmail, etc.)

## 📦 Установка

### 1. Клонирование репозитория
```bash
git clone https://github.com/Mark1sLow/api-monitor-pro.git
cd api-monitor-pro
```

### 2. Создание виртуального окружения
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

### 3. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 4. Настройка переменных окружения
Создайте файл `.env` в корне проекта:
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
```

### 5. Миграции базы данных
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Создание суперпользователя
```bash
python manage.py createsuperuser
# Или используйте скрипт:
python create_admin.py
```

## 🚀 Запуск

### Режим разработки
```bash
python manage.py runserver
```
Приложение будет доступно по адресу: http://127.0.0.1:8000/

### Проверка API (ручной запуск)
```bash
python manage.py check_endpoints
```

## 📊 Использование

### 1. Авторизация
- Перейдите на http://127.0.0.1:8000/
- Войдите с учетными данными суперпользователя

### 2. Создание проекта
- Нажмите "Создать проект"
- Укажите название и базовый URL API

### 3. Добавление эндпоинтов
- В проекте нажмите "Добавить эндпоинт"
- Укажите метод (GET/POST/PUT/DELETE), путь и параметры SLA

### 4. Мониторинг
- Просматривайте графики и статистику на странице эндпоинта
- Получайте уведомления при нарушении SLA

## 📁 Структура проекта

```
api-monitor-pro/
├── config/                 # Настройки Django
├── monitor/                # Основное приложение
│   ├── management/commands/  # Management команды
│   ├── migrations/          # Миграции БД
│   ├── templates/           # HTML шаблоны
│   └── ...
├── static/                 # Статические файлы
├── .env                    # Переменные окружения
├── requirements.txt        # Зависимости Python
└── README.md              # Документация
```

## 🔧 Настройка для продакшена

### Переменные окружения
```env
DEBUG=False
ALLOWED_HOSTS=your-domain.com
SECRET_KEY=generate-strong-secret-key
```

### База данных
Рекомендуется использовать PostgreSQL:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'api_monitor',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Cron для автоматической проверки
```bash
# Каждый 5 минут
*/5 * * * * /path/to/venv/bin/python /path/to/project/manage.py check_endpoints
```

## 🤝 Вклад в проект

1. Fork репозиторий
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Создайте Pull Request

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. См. файл `LICENSE` для подробностей.

## 📞 Контакты

- **Автор**: Mark1sLow
- **Email**: voronovmd8@gmail.com
- **GitHub**: https://github.com/Mark1sLow

---

⭐ Если проект оказался полезным, поставьте звезду на GitHub!

