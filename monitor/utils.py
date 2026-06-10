import pandas as pd
from .models import Measurement
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, timedelta

def calculate_sli_stats(endpoint_id, days=7):
    """Возвращает DataFrame с SLI за последние N дней"""
    qs = Measurement.objects.filter(
        endpoint_id=endpoint_id,
        timestamp__gte=datetime.now() - timedelta(days=days)
    ).values('timestamp', 'response_time_ms', 'is_error')
    
    if not qs:
        return pd.DataFrame(columns=['timestamp', 'latency_mean', 'error_rate', 'availability'])

    df = pd.DataFrame(qs)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp').sort_index()
    df.rename(columns={'response_time_ms': 'latency', 'is_error': 'error'}, inplace=True)
    
    # Группировка по дням
    daily = df.resample('D').agg({
        'latency': ['mean', 'count'],
        'error': ['sum', 'count']
    })
    daily.columns = ['latency_mean', 'latency_count', 'error_sum', 'error_count']
    daily['error_rate'] = daily['error_sum'] / daily['error_count']
    daily['availability'] = 1 - daily['error_rate']
    
    return daily.reset_index()

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