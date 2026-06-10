from django.apps import AppConfig


class MonitorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitor'
    
    def ready(self):
        """Инициализация при загрузке приложения"""
        import os
        
        # Подключаем signals
        import monitor.signals
        
        # Не запускаем scheduler для manage.py команд
        if os.environ.get('RUN_MAIN') != 'true':
            return
        
        try:
            from .scheduler import start_scheduler
            start_scheduler()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Failed to start scheduler: {str(e)}')
