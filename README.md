# API Monitor Pro

Система мониторинга и анализа SLI/SLO API-методов веб-приложений для DevOps-инженеров.

Сервис позволяет отслеживать ключевые метрики производительности API:
- **Задержка ответа** (Latency) - время ответа API-метода в миллисекундах
- **Доступность** (Availability) - процент успешных запросов
- **Частота ошибок** (Error Rate) - доля запросов с ошибками

API Monitor Pro автоматизирует мониторинг, визуализирует данные и отправляет уведомления при нарушении SLA - всё в одной системе.

## Роли пользователей

- **Зарегистрированный пользователь**: Полный доступ к своим проектам, созданию/редактированию эндпоинтов, просмотру аналитики
- **Администратор**: Управление всеми пользователями, проектами и глобальные системные отчеты

## Возможности

-  **Уведомления SLA** - Email оповещения при нарушении порогов задержки и ошибок
-  **Автоматический мониторинг** - Management command для периодической проверки API
-  **Многопользовательский режим** - Полная изоляция данных между пользователями
-  **Аналитика на Pandas** - Автоматический расчет SLI/SLO статистики

##  Модели данных

### Project
Группировка API-методов, принадлежит одному пользователю
- `name` - Название проекта
- `url` - Базовый URL API
- `owner` - Владелец
- `created_at` - Дата создания

### Endpoint
Конкретный метод API для мониторинга
- `project` - Проект, к которому относится
- `method` - HTTP метод (GET, POST, PUT, DELETE)
- `path` - Путь эндпоинта
- `sla_latency_ms` - Максимальная допустимая задержка в мс
- `sla_error_rate` - Максимальная допустимая частота ошибок

### Measurement
Результат одной проверки эндпоинта
- `endpoint` - Проверяемый эндпоинт
- `timestamp` - Время проверки
- `response_time_ms` - Время ответа
- `status_code` - HTTP статус код
- `is_error` - Была ли ошибка
- `sla_breached` - Нарушен ли SLA

## Технологии

- **Backend**: Django 4.2, Python 3.12+
- **База данных**: SQLite, PostgreSQL
- **Фронтенд**: Bootstrap 5, Plotly.js, HTML5
- **Анализ данных**: Pandas для расчета SLI/SLO метрик
- **HTTP запросы**: Requests для проверки API
- **Задачи**: Django Management Commands для автоматизации
- **Email**: SMTP

## Установка

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

## Использование

### Авторизация
- Перейдите на http://127.0.0.1:8000/
- Войдите с учетными данными суперпользователя

### Создание проекта
- Нажмите "Создать проект"
- Укажите название и базовый URL API
- Подтвердите создание

### Добавление эндпоинтов
- В проекте нажмите "Добавить эндпоинт"
- Укажите HTTP метод
- Укажите путь эндпоинта
- Установите параметры SLA
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

## Развертывание на PythonAnywhere

1. Создайте аккаунт на [pythonanywhere.com](https://www.pythonanywhere.com/)
2. Клонируйте репозиторий в `/home/username/api-monitor-pro`
3. Создайте виртуальное окружение: `mkvirtualenv --python=/usr/bin/python3.10 api-monitor-pro`
4. Установите зависимости: `pip install -r requirements.txt`
5. Создайте файл `.env` с переменными окружения
6. Выполните миграции: `python manage.py migrate`
7. Соберите статические файлы: `python manage.py collectstatic`
8. Создайте WSGI конфиг в PythonAnywhere
9. Добавьте Scheduled Task для `python manage.py check_endpoints` каждые 5 минут

## API и Интеграции

### Используемые библиотеки для анализа:
- **Pandas** - расчет SLI/SLO статистики, групповая обработка временных рядов
- **Plotly** - визуализация графиков
- **Requests** - HTTP запросы к мониторируемым API

### Интеграции:
- **SMTP Email** - отправка уведомлений при нарушении SLA
- **External APIs** - поддержка мониторинга любых HTTP API