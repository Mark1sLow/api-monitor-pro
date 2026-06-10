import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('api_monitor_pro')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Расписание периодических задач
app.conf.beat_schedule = {
    'check-all-endpoints-every-5-minutes': {
        'task': 'monitor.tasks.check_all_endpoints',
        'schedule': crontab(minute='*/5'),  # Каждые 5 минут
    },
    'cleanup-old-measurements-daily': {
        'task': 'monitor.tasks.cleanup_old_measurements',
        'schedule': crontab(hour=3, minute=0),  # В 3 ночи
    },
    'send-daily-report': {
        'task': 'monitor.tasks.send_daily_report',
        'schedule': crontab(hour=9, minute=0),  # В 9 утра
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
