import requests
from datetime import datetime, timedelta
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db import models
from .models import Endpoint, Measurement, Project
from .utils import send_sla_breach_notification, calculate_sli_stats
from .webhooks import send_webhook_notification

@shared_task
def check_endpoint(endpoint_id):
    """Проверяет один эндпоинт и сохраняет результат"""
    try:
        ep = Endpoint.objects.get(id=endpoint_id)
        url = ep.project.url.rstrip('/') + ep.path
        
        start = timezone.now()
        try:
            resp = requests.get(url, timeout=10)
            elapsed = (timezone.now() - start).total_seconds() * 1000  # ms
            is_error = resp.status_code >= 400
            status_code = resp.status_code
        except requests.Timeout:
            elapsed = 10000  # timeout
            is_error = True
            status_code = 0
        except Exception as e:
            elapsed = 0
            is_error = True
            status_code = 0
        
        sla_breached = (
            elapsed > ep.sla_latency_ms or
            (is_error and ep.sla_error_rate < 1)
        )
        
        measurement = Measurement.objects.create(
            endpoint=ep,
            timestamp=timezone.now(),
            response_time_ms=elapsed,
            status_code=status_code,
            is_error=is_error,
            sla_breached=sla_breached
        )
        
        if sla_breached:
            send_sla_breach_notification.delay(ep.id, measurement.id)
            send_webhook_notification_task.delay(ep.id, measurement.id)
        
        return {
            'endpoint_id': endpoint_id,
            'status': 'success',
            'response_time': elapsed,
            'sla_breached': sla_breached
        }
    except Exception as e:
        return {
            'endpoint_id': endpoint_id,
            'status': 'error',
            'error': str(e)
        }

@shared_task
def check_all_endpoints():
    """Проверяет все активные эндпоинты"""
    endpoints = Endpoint.objects.all()
    for ep in endpoints:
        check_endpoint.delay(ep.id)
    return f"Queued {endpoints.count()} endpoints for checking"

@shared_task
def send_sla_breach_notification(endpoint_id, measurement_id):
    """Отправляет Email уведомление о нарушении SLA"""
    try:
        ep = Endpoint.objects.get(id=endpoint_id)
        measurement = Measurement.objects.get(id=measurement_id)
        project = ep.project
        owner = project.owner
        
        subject = f"⚠️ SLA нарушено: {ep.method} {ep.path}"
        
        message = f"""
Нарушение SLA для эндпоинта: {ep.method} {ep.path}

Проект: {project.name}
URL проекта: {project.url}

Метрики:
- Время ответа: {measurement.response_time_ms}ms (лимит: {ep.sla_latency_ms}ms)
- Статус код: {measurement.status_code}
- Ошибка: {'Да' if measurement.is_error else 'Нет'}
- Время: {measurement.timestamp}

Перейдите в систему мониторинга для просмотра деталей:
http://localhost:8000/monitor/endpoints/{ep.id}/
"""
        
        if owner.email:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [owner.email],
                fail_silently=True,
            )
            return f"Notification sent to {owner.email}"
    except Exception as e:
        return f"Error sending notification: {str(e)}"

@shared_task
def send_webhook_notification_task(endpoint_id, measurement_id):
    """Отправляет webhook уведомления"""
    try:
        ep = Endpoint.objects.get(id=endpoint_id)
        measurement = Measurement.objects.get(id=measurement_id)
        results = send_webhook_notification(ep, measurement, breach_type='sla_breach')
        return {
            'status': 'success',
            'results': results
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

@shared_task
def cleanup_old_measurements(days=30):
    """Удаляет измерения старше N дней"""
    cutoff_date = timezone.now() - timedelta(days=days)
    deleted_count, _ = Measurement.objects.filter(
        timestamp__lt=cutoff_date
    ).delete()
    return f"Deleted {deleted_count} old measurements"

@shared_task
def send_daily_report():
    """Отправляет дневной отчет владельцам проектов"""
    projects = Project.objects.all()
    
    for project in projects:
        owner = project.owner
        if not owner.email:
            continue
        
        endpoints = project.endpoint_set.all()
        
        measurements = Measurement.objects.filter(
            endpoint__in=endpoints,
            timestamp__gte=timezone.now() - timedelta(hours=24)
        )
        
        breaches_count = measurements.filter(sla_breached=True).count()
        total_count = measurements.count()
        error_rate = (measurements.filter(is_error=True).count() / total_count * 100) if total_count > 0 else 0
        avg_latency = measurements.aggregate(avg=models.Avg('response_time_ms'))['avg'] or 0
        
        subject = f"📊 Дневной отчет: {project.name}"
        message = f"""
Дневной отчет мониторинга для проекта: {project.name}

Статистика за последние 24 часа:
- Всего проверок: {total_count}
- Нарушений SLA: {breaches_count}
- Частота ошибок: {error_rate:.2f}%
- Средняя задержка: {avg_latency:.0f}ms
- Активных эндпоинтов: {endpoints.count()}

Детали доступны в личном кабинете:
http://localhost:8000/monitor/dashboard/
"""
        
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [owner.email],
            fail_silently=True,
        )
    
    return f"Daily reports sent to {projects.count()} projects"