# API Monitor Pro

**Платформа мониторинга и аналитики SLI/SLO для современных DevOps-команд.**

API Monitor Pro — это комплексное решение для реального мониторинга производительности ваших сервисов.

**Рабочий проект:** [https://api-monitor.pythonanywhere.com](https://api-monitor.pythonanywhere.com)

---

## Возможности

- **Расширенная аналитика** - Отслеживание задержек, доступности, ошибок
- **Прогнозирование** - Предсказание нарушений SLA за 24 часа вперед
- **Гибкое расписание** - Проверка API каждую минуту до 1 раза в день
- **Профессиональные отчеты** - Экспорт в PDF, CSV, HTML с графиками и таблицами
- **Автоматизация** - Django Management Command для периодических проверок через Cron/APScheduler
- **История** - Полная история SLA, анализ трендов, обнаружение аномалий

## Роли пользователей

- **Зарегистрированный пользователь**: Создание/управление проектами, эндпоинтами, просмотр аналитики, генерация отчетов, экспорт данных

## Архитектура системы

### Основные модели данных

**Project** - Группировка API-методов 
**Endpoint** - Конкретный метод API 
**Measurement** - Результат одной проверки 
**PerformanceMetrics** - Агрегированная статистика 
**SLATracking** - Ежедневное отслеживание SLA 
**Alert** - История уведомлений 
**Schedule** - Расписание проверок 
**Report** - Сохраненные отчеты 

---

## Стек

### Backend
- **Python 3.12+**
- **Django 4.2**
- **Django REST Framework 3.14**
- **APScheduler 3.10**

### Data Science & Analytics
- **Pandas 2.2**
- **NumPy 1.26**
- **scikit-learn 1.4**
- **ReportLab 4.0**

### Frontend
- **Bootstrap 5**
- **Plotly.js 5.20**
- **HTML5 / CSS3**

### Database & Caching
- **SQLite**
- **PostgreSQL**
- **Django ORM**

---

## Быстрый старт

### Требования
- Python 3.10+
- pip
- Git

### 1. Клонирование репозитория
```bash
git clone https://github.com/Mark1sLow/api-monitor-pro.git
cd api-monitor-pro
```

### 2. Создание и активация виртуального окружения
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 4. Настройка переменных окружения
Создайте файл `.env` в корне проекта с необходимыми параметрами:
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Email-уведомления
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587

# Database
# DATABASE_URL=postgresql://user:password@localhost:5432/api_monitor
```

### 5. Запуск локального сервера
```bash
python manage.py runserver
```

Приложение будет доступно по адресу: **http://127.0.0.1:8000/**

---

## Использование

### Вход в систему
1. Перейдите на http://127.0.0.1:8000/
2. Нажмите "Login" или "Регистрация"
3. Введите учетные данные

### Создание проекта
1. На главной странице нажмите "Создать проект"
2. Укажите:
   - **Название** - название вашего сервиса
   - **Base URL** - базовый URL вашего API
3. Подтвердите создание

### Добавление эндпоинтов для мониторинга
1. Откройте только что созданный проект
2. Нажмите "Добавить эндпоинт"
3. Заполните форму:
   - **Method** - HTTP метод
   - **Path** - путь эндпоинта
   - **SLA Latency** - максимально допустимое время ответа
   - **SLA Error Rate** - максимально допустимый процент ошибок
4. Подтвердите добавление

### Запуск проверки API вручную
```bash
python manage.py check_endpoints
```

### Автоматизация проверок через Cron (Linux/macOS)
```bash
# Отредактируйте crontab
crontab -e

# Добавьте строку для проверки каждые 5 минут
*/5 * * * * cd /path/to/api-monitor-pro && python manage.py check_endpoints
```

### Просмотр аналитики
- **Dashboard** - общая статистика по всем проектам
- **Endpoint Metrics** - подробная аналитика эндпоинта
- **SLA Dashboard** - панель управления SLA со всеми проектами
- **SLA Forecast** - прогноз нарушений на 1 день вперед
- **SLA History** - история SLA с трендами и аномалиями
- **Reports** - генерация и загрузка отчетов


---

## Развертывание на PythonAnywhere

API Monitor Pro полностью поддерживает развертывание на [PythonAnywhere](https://www.pythonanywhere.com/).

### Пошаговое развертывание

1. **Создание аккаунта**
   - Зарегистрируйтесь на pythonanywhere.com
   - Выберите бесплатный или платный план

2. **Клонирование репозитория**
   ```bash
   git clone https://github.com/Mark1sLow/api-monitor-pro.git
   cd api-monitor-pro
   ```

3. **Создание виртуального окружения**
   ```bash
   mkvirtualenv --python=/usr/bin/python3.10 api-monitor-pro
   pip install -r requirements.txt
   ```

4. **Настройка переменных окружения**
   - Создайте файл `.env` с конфигурацией
   - Убедитесь, что DEBUG=False для продакшена

5. **Выполнение миграций**
   ```bash
   python manage.py migrate
   python manage.py collectstatic
   ```

6. **Создание WSGI конфига**
   - Используйте встроенный WSGI конфигуратор PythonAnywhere
   - Укажите путь к wsgi.py файлу

### Ссылка на сервис
**Рабочий проект:** [https://markis.pythonanywhere.com]

---

## Структура проекта

```
api-monitor-pro/
├── config/                   # Конфигурация Django
│   ├── settings.py           # Основные настройки
│   ├── urls.py               # URL маршруты
│   ├── wsgi.py               # WSGI конфигурация
│   └── celery.py             # Celery конфигурация
├── monitor/                  # Основное приложение
│   ├── models.py             # 8 моделей БД
│   ├── views.py              # 20+ представлений
│   ├── urls.py               # URL маршруты
│   ├── forms.py              # Django формы
│   ├── admin.py              # Admin интерфейс
│   ├── metrics_calculator.py # Расчет метрик (P50, P95, P99)
│   ├── forecast.py           # ML-прогноз нарушений SLA
│   ├── exporters.py          # Экспорт в PDF, CSV, HTML
│   ├── tasks.py              # Celery задачи
│   ├── signals.py            # Django signals
│   ├── scheduler.py          # APScheduler
│   ├── management/
│   │   └── commands/
│   │       └── check_endpoints.py  # Management command для проверки API
│   ├── migrations/           # Миграции БД
│   └── templates/            # HTML шаблоны
├── static/                   # Статические файлы (CSS, JS)
├── requirements.txt          # Зависимости Python
├── manage.py                 # Django управление
├── README.md                 # Этот файл
├── TZ.md                     # Техническое задание
└── db.sqlite3                # SQLite база данных
```

---

## API Endpoints

### Аутентификация
- `POST /api/token/` - Получить токен
- `POST /api/token/refresh/` - Обновить токен

### Метрики
- `GET /api/endpoint/<id>/metrics/` - JSON метрики эндпоинта
- `GET /api/endpoint/<id>/sla-forecast/` - JSON прогноз нарушений

### Экспорт
- `GET /endpoint/<id>/export/measurements/` - CSV измерений
- `GET /project/<id>/export/metrics/` - CSV метрик
- `GET /endpoint/<id>/export/sla/` - CSV SLA

### Web Views (HTML)
- `GET /` - Главная страница (редирект на dashboard)
- `GET /dashboard/` - Dashboard
- `GET /project/<id>/` - Страница проекта
- `GET /endpoint/<id>/` - Аналитика эндпоинта
- `GET /sla/dashboard/` - SLA Dashboard
- `GET /endpoint/<id>/sla-forecast/` - SLA Forecast
- `GET /endpoint/<id>/sla-history/` - SLA History
- `GET /reports/` - Список отчетов
- `GET /project/<id>/generate-report/` - Генератор отчетов

---

## Ключевые метрики и расчеты

### Performance Metrics
- **Response Time**: Min, Max, Avg, P50, P95, P99
- **Error Rate**: Процент ошибок
- **Availability**: Процент успешных запросов
- **Status Code Distribution**: Распределение 2xx, 3xx, 4xx, 5xx
- **SLA Compliance**: Процент соблюдения SLA за период

### SLA Tracking
- **Target SLA**: Целевой процент SLA
- **Actual SLA**: Фактический процент SLA за день
- **Breach Probability**: ML-прогноз вероятности нарушения
- **Trend Analysis**: Анализ тренда

---