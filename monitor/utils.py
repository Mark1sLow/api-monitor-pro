import numpy as np
from .models import Measurement
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, timedelta, date
from collections import defaultdict

def calculate_sli_stats(endpoint_id, days=7):
    """Возвращает список дней с SLI метриками за последние N дней"""
    qs = Measurement.objects.filter(
        endpoint_id=endpoint_id,
        timestamp__gte=datetime.now() - timedelta(days=days)
    ).values('timestamp', 'response_time_ms', 'is_error')
    
    if not qs:
        return []

    # Группировка по дням
    daily_data = defaultdict(lambda: {'latencies': [], 'errors': []})
    
    for measurement in qs:
        day = measurement['timestamp'].date()
        daily_data[day]['latencies'].append(measurement['response_time_ms'])
        daily_data[day]['errors'].append(1 if measurement['is_error'] else 0)
    
    # Формирование результата
    result = []
    for day in sorted(daily_data.keys()):
        data = daily_data[day]
        latencies = data['latencies']
        errors = data['errors']
        
        latency_mean = float(np.mean(latencies)) if latencies else 0
        error_count = sum(errors)
        total_count = len(errors)
        error_rate = float(error_count / total_count) if total_count > 0 else 0
        availability = 1 - error_rate
        
        result.append({
            'timestamp': datetime.combine(day, datetime.min.time()),
            'latency_mean': latency_mean,
            'latency_count': len(latencies),
            'error_sum': error_count,
            'error_count': total_count,
            'error_rate': error_rate,
            'availability': availability,
        })
    
    return result

def send_sla_breach_notification(endpoint, measurement):
    """Отправляет уведомление о нарушении SLA на email"""
    try:
        project = endpoint.project
        owner = project.owner
        
        subject = f"⚠️ SLA нарушено: {endpoint.method} {endpoint.path}"
        
        message = f"""
        Нарушение SLA для эндпоинта: {endpoint.method} {endpoint.path}
        
        Проект: {project.name}
        URL проекта: {project.url}
        
        Метрики:
        - Время ответа: {measurement.response_time_ms}ms (лимит: {endpoint.sla_latency_ms}ms)
        - Статус код: {measurement.status_code}
        - Ошибка: {'Да' if measurement.is_error else 'Нет'}
        - Время: {measurement.timestamp}
        
        Перейдите в систему мониторинга для просмотра деталей.
        """
        
        if owner.email:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [owner.email],
                fail_silently=True,
            )
    except Exception as e:
        print(f"Error sending SLA breach notification: {str(e)}")

def get_sla_statistics(endpoint):
    """Возвращает статистику SLA за последние 7 дней"""
    stats = calculate_sli_stats(endpoint.id, days=7)
    
    if stats.empty:
        return {
            'avg_latency': 0,
            'error_rate': 0,
            'availability': 0,
            'total_checks': 0,
            'breaches': 0,
        }
    
    total_measurements = Measurement.objects.filter(
        endpoint=endpoint,
        timestamp__gte=datetime.now() - timedelta(days=7)
    ).count()
    
    breaches = Measurement.objects.filter(
        endpoint=endpoint,
        sla_breached=True,
        timestamp__gte=datetime.now() - timedelta(days=7)
    ).count()
    
    return {
        'avg_latency': stats['latency_mean'].mean(),
        'error_rate': stats['error_rate'].mean() * 100,
        'availability': stats['availability'].mean() * 100,
        'total_checks': total_measurements,
        'breaches': breaches,
    }