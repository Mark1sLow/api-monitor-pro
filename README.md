# API Monitor Pro

Система мониторинга и анализа SLI/SLO API-методов веб-приложений для DevOps-инженеров.

Сервис позволяет отслеживать ключевые метрики производительности API:
- **Задержка ответа** (Latency) - время ответа API-метода в миллисекундах
- **Доступность** (Availability) - процент успешных запросов
- **Частота ошибок** (Error Rate) - доля запросов с ошибками

**Ссылка на рабочий проект:** [https://voron.pythonanywhere.com/](https://voron.pythonanywhere.com/)

## 🎯 Проблема, которую решает сервис

DevOps-инженеры теряют значительное время на анализ логов и метрик API. API Monitor Pro автоматизирует мониторинг, визуализирует данные и отправляет уведомления при нарушении SLA - всё в одной системе.

## 👥 Роли пользователей

- **Гость**: Просмотр общедоступных метрик и статус-страницы
- **Зарегистрированный пользователь**: Полный доступ к своим проектам, созданию/редактированию эндпоинтов, просмотру аналитики
- **Администратор**: Управление всеми пользователями, проектами и глобальные системные отчеты

## 🚀 Возможности

- 📊 **Визуализация метрик** - Графики на Plotly для анализа трендов за последние 7 дней
- ⚠️ **Уведомления SLA** - Email оповещения при нарушении порогов задержки и ошибок
- 🔄 **Автоматический мониторинг** - Management command для периодической проверки API
- 👥 **Многопользовательский режим** - Полная изоляция данных между пользователями
- 📱 **Адаптивный интерфейс** - Bootstrap 5, работает на мобильных устройствах
- 📈 **Аналитика на Pandas** - Автоматический расчет SLI/SLO статистики

## 📊 Модели данных

### Project (Проект)
Группировка API-методов, принадлежит одному пользователю
- `name` - Название проекта
- `url` - Базовый URL API
- `owner` - Владелец (ForeignKey на User)
- `created_at` - Дата создания

### Endpoint (Эндпоинт)
Конкретный метод API для мониторинга
- `project` - Проект, к которому относится (ForeignKey)
- `method` - HTTP метод (GET, POST, PUT, DELETE)
- `path` - Путь эндпоинта (например, `/users`)
- `sla_latency_ms` - Максимальная допустимая задержка в мс
- `sla_error_rate` - Максимальная допустимая частота ошибок (0.05 = 5%)

### Measurement (Измерение)
Результат одной проверки эндпоинта
- `endpoint` - Проверяемый эндпоинт (ForeignKey)
- `timestamp` - Время проверки
- `response_time_ms` - Время ответа
- `status_code` - HTTP статус код
- `is_error` - Была ли ошибка
- `sla_breached` - Нарушен ли SLA

## 🛠 Технологии

- **Backend**: Django 4.2, Python 3.12+
- **База данных**: SQLite (разработка), PostgreSQL (продакшен)
- **Фронтенд**: Bootstrap 5, Plotly.js, HTML5
- **Анализ данных**: Pandas для расчета SLI/SLO метрик
- **HTTP запросы**: Requests для проверки API
- **Задачи**: Django Management Commands для автоматизации
- **Email**: SMTP (поддержка Gmail и других SMTP провайдеров)

## 📸 Скриншоты

### Панель управления (Dashboard)
![Dashboard](/screenshots/dashboard.png)
*Главная страница с статистикой проектов, эндпоинтов и нарушений SLA за 24 часа*

### Детали эндпоинта с графиками
![Endpoint Details](/screenshots/endpoint_detail.png)
*Страница эндпоинта с графиками задержки, доступности и частоты ошибок за 7 дней*

### Управление проектом
![Project Management](/screenshots/project_detail.png)
*Страница проекта со списком эндпоинтов и возможностью их управления*

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

### 7. Запуск сервера
```bash
python manage.py runserver
```
Приложение будет доступно по адресу: http://127.0.0.1:8000/

## 🚀 Использование

### Авторизация
- Перейдите на http://127.0.0.1:8000/
- Войдите с учетными данными суперпользователя

### Создание проекта
- Нажмите "Создать проект"
- Укажите название и базовый URL API
- Подтвердите создание

### Добавление эндпоинтов
- В проекте нажмите "Добавить эндпоинт"
- Укажите HTTP метод (GET/POST/PUT/DELETE)
- Укажите путь эндпоинта (например, `/posts/1`)
- Установите параметры SLA (макс. задержка в мс, макс. ошибок в %)
- Подтвердите

### Проверка и Мониторинг
```bash
# Ручная проверка API
python manage.py check_endpoints

# Для автоматизации добавьте в cron (каждые 5 минут):
*/5 * * * * cd /path/to/project && python manage.py check_endpoints
```

### Просмотр аналитики
- На странице эндпоинта вы увидите:
  - Графики задержки, доступности и ошибок за 7 дней
  - Таблицу последних измерений
  - Счетчик нарушений SLA за 24 часа

## 📁 Структура проекта

```
api-monitor-pro/
├── config/                      # Конфигурация Django
│   ├── settings.py              # Основные настройки
│   ├── urls.py                  # URL маршруты
│   ├── wsgi.py                  # WSGI приложение
│   └── asgi.py                  # ASGI приложение
│
├── monitor/                     # Основное приложение
│   ├── models.py                # Models: Project, Endpoint, Measurement
│   ├── views.py                 # Views: 8+ функций для работы с данными
│   ├── forms.py                 # Forms: ProjectForm, EndpointForm
│   ├── urls.py                  # URL маршруты приложения
│   ├── utils.py                 # Утилиты: расчет статистики, отправка email
│   ├── admin.py                 # Администраторский интерфейс
│   │
│   ├── management/
│   │   └── commands/
│   │       └── check_endpoints.py   # Command для проверки API
│   │
│   ├── migrations/              # Миграции БД
│   │
│   └── templates/               # HTML шаблоны
│       ├── base.html            # Базовый шаблон
│       ├── dashboard.html       # Панель управления
│       ├── project_detail.html  # Детали проекта
│       ├── endpoint_detail.html # Детали эндпоинта с графиками
│       └── ...
│
├── static/                      # Статические файлы (CSS, JS, images)
├── .env                         # Переменные окружения (не коммитится)
├── .gitignore                   # Файлы для игнорирования
├── requirements.txt             # Зависимости Python
├── manage.py                    # Django CLI
├── README.md                    # Этот файл
└── TZ.md                        # Техническое задание
```

## 🔧 Развертывание на PythonAnywhere

1. Создайте аккаунт на [pythonanywhere.com](https://www.pythonanywhere.com/)
2. Клонируйте репозиторий в `/home/username/api-monitor-pro`
3. Создайте виртуальное окружение: `mkvirtualenv --python=/usr/bin/python3.10 api-monitor-pro`
4. Установите зависимости: `pip install -r requirements.txt`
5. Создайте файл `.env` с переменными окружения
6. Выполните миграции: `python manage.py migrate`
7. Соберите статические файлы: `python manage.py collectstatic`
8. Создайте WSGI конфиг в PythonAnywhere
9. Добавьте Scheduled Task для `python manage.py check_endpoints` каждые 5 минут

## 📊 API и Интеграции

### Используемые библиотеки для анализа:
- **Pandas** - расчет SLI/SLO статистики, групповая обработка временных рядов
- **Plotly** - визуализация графиков (задержка, доступность, ошибки)
- **Requests** - HTTP запросы к мониторируемым API

### Интеграции:
- **SMTP Email** - отправка уведомлений при нарушении SLA
- **External APIs** - поддержка мониторинга любых HTTP API (REST, JSON)

## 🏆 Ключевые особенности реализации

✅ **Многопользовательская система** - Каждый пользователь видит только свои проекты
✅ **Автоматическая аналитика** - Расчет SLI/SLO метрик с помощью Pandas
✅ **Визуализация данных** - Интерактивные графики на Plotly
✅ **Email уведомления** - Автоматические письма при нарушении SLA
✅ **Django Admin** - Полноценный административный интерфейс с фильтрами и поиском
✅ **Чистая архитектура** - Разделение на Models, Views, Utils, Templates
✅ **PEP8** - Соблюдение стандартов Python

## 🐛 Решение проблем

### ModuleNotFoundError при запуске
```bash
# Убедитесь что виртуальное окружение активировано
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Переустановите зависимости
pip install -r requirements.txt
```

### Ошибка при отправке email
```python
# Проверьте .env переменные:
# - EMAIL_HOST_USER должен быть вашим email
# - EMAIL_HOST_PASSWORD должен быть app-password (для Gmail)
# Для Gmail используйте двухфакторную аутентификацию и сгенерируйте app password
```

### БД не обновляется
```bash
# Выполните миграции
python manage.py migrate

# Пересоздайте БД если нужно
python manage.py flush
python manage.py migrate
```

## 📞 Поддержка

- **Email**: voronovmd8@gmail.com
- **GitHub Issues**: [https://github.com/Mark1sLow/api-monitor-pro/issues](https://github.com/Mark1sLow/api-monitor-pro/issues)

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. См. файл `LICENSE` для подробностей.

---

⭐ Если проект оказался полезным, поставьте звезду на GitHub!

