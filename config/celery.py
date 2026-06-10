"""
Celery конфигурация для API Monitor Pro
"""
import os
from celery import Celery
from celery.schedules import crontab

# Установить Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('api_monitor')

# Загрузить конфигурацию из Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

app.conf.beat_schedule = {
    # Расчет дневных метрик
    'calculate-daily-metrics': {
        'task': 'monitor.tasks.calculate_daily_metrics_for_all',
        'schedule': crontab(hour=1, minute=0),
    },
    # Расчет SLA tracking
    'calculate-sla-tracking': {
        'task': 'monitor.tasks.calculate_sla_tracking_for_all',
        'schedule': crontab(hour=1, minute=30),
    },
    # Прогнозирование нарушений SLA
    'forecast-sla-breaches': {
        'task': 'monitor.tasks.forecast_sla_breaches_for_all',
        'schedule': crontab(minute=0),
    },
    # Генерировать дневные отчеты
    'generate-daily-reports': {
        'task': 'monitor.tasks.generate_daily_reports_for_all',
        'schedule': crontab(hour=9, minute=0),
    },
    # Генерировать недельные отчеты
    'generate-weekly-reports': {
        'task': 'monitor.tasks.generate_weekly_reports_for_all',
        'schedule': crontab(day_of_week=0, hour=8, minute=0),
    },
    # Очистить старые метрики
    'cleanup-old-metrics': {
        'task': 'monitor.tasks.cleanup_old_metrics',
        'schedule': crontab(hour=3, minute=0),
    },
    # Очистить старые SLA tracking
    'cleanup-old-sla-tracking': {
        'task': 'monitor.tasks.cleanup_old_sla_tracking',
        'schedule': crontab(hour=3, minute=30),
    },
}

app.conf.timezone = 'UTC'
app.conf.task_serializer = 'json'
app.conf.accept_content = ['json']
app.conf.result_serializer = 'json'

@app.task(bind=True)
def debug_task(self):
    """Тестовая задача для отладки"""
    print(f'Request: {self.request!r}')
