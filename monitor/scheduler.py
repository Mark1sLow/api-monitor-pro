"""
APScheduler integration для периодической проверки эндпоинтов

Этот модуль управляет расписанием проверок эндпоинтов через APScheduler.
Задачи сохраняются в базу данных и могут быть изменены через веб-интерфейс.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from django.core.management import call_command
from django.utils import timezone
from .models import Schedule
import logging

logger = logging.getLogger(__name__)
scheduler = None


def start_scheduler():
    """Запускает APScheduler"""
    global scheduler
    
    if scheduler and scheduler.running:
        logger.warning('Scheduler already running')
        return
    
    scheduler = BackgroundScheduler(
        jobstores={'default': MemoryJobStore()},
        job_defaults={'coalesce': True, 'max_instances': 1}
    )
    
    # Загружаем расписания из базы
    load_schedules()
    
    scheduler.start()
    logger.info('Scheduler started')


def stop_scheduler():
    """Останавливает APScheduler"""
    global scheduler
    
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        scheduler = None
        logger.info('Scheduler stopped')


def load_schedules():
    """Загружает все активные расписания из базы в scheduler"""
    global scheduler
    
    if not scheduler:
        return
    
    # Удаляем все старые задачи
    scheduler.remove_all_jobs()
    
    # Загружаем активные расписания
    schedules = Schedule.objects.filter(is_active=True)
    
    for schedule in schedules:
        add_schedule(schedule)
    
    logger.info(f'Loaded {schedules.count()} schedules')


def add_schedule(schedule):
    """Добавляет расписание в scheduler"""
    global scheduler
    
    if not scheduler:
        return False
    
    try:
        job_id = f'check_project_{schedule.project.id}'
        
        # Удаляем старую задачу если существует
        try:
            scheduler.remove_job(job_id)
        except:
            pass
        
        # Добавляем новую задачу
        scheduler.add_job(
            check_project_endpoints,
            trigger=IntervalTrigger(minutes=int(schedule.interval_minutes)),
            args=[schedule.project.id],
            id=job_id,
            name=f"Check {schedule.project.name}",
            replace_existing=True
        )
        
        logger.info(f'Added schedule for project {schedule.project.id}')
        return True
    except Exception as e:
        logger.error(f'Failed to add schedule: {str(e)}')
        return False


def remove_schedule(schedule):
    """Удаляет расписание из scheduler"""
    global scheduler
    
    if not scheduler:
        return False
    
    try:
        job_id = f'check_project_{schedule.project.id}'
        scheduler.remove_job(job_id)
        logger.info(f'Removed schedule for project {schedule.project.id}')
        return True
    except Exception as e:
        logger.error(f'Failed to remove schedule: {str(e)}')
        return False


def check_project_endpoints(project_id):
    """
    Проверяет все эндпоинты проекта
    
    Args:
        project_id: ID проекта
    """
    try:
        # Обновляем last_run в Schedule
        schedule = Schedule.objects.get(project_id=project_id)
        schedule.last_run = timezone.now()
        schedule.save()
        
        # Вызываем management command
        call_command('check_endpoints', '--project', str(project_id))
        
        logger.info(f'Successfully checked endpoints for project {project_id}')
    except Exception as e:
        logger.error(f'Error checking endpoints for project {project_id}: {str(e)}')


def get_scheduler():
    """Возвращает текущий scheduler"""
    global scheduler
    return scheduler


def is_scheduler_running():
    """Проверяет, запущен ли scheduler"""
    global scheduler
    return scheduler is not None and scheduler.running
