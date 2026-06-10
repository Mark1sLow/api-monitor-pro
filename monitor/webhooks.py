import requests
import json
from .models import Webhook

def send_webhook_notification(webhook_url, endpoint, measurement, breach_type='sla'):
    """Отправить уведомление через webhook"""
    try:
        payload = {
            "event": "sla_breach" if breach_type == 'sla_breach' else "error",
            "project": endpoint.project.name,
            "endpoint": {
                "method": endpoint.method,
                "path": endpoint.path,
                "sla_latency_ms": endpoint.sla_latency_ms,
                "sla_error_rate": endpoint.sla_error_rate,
            },
            "measurement": {
                "timestamp": measurement.timestamp.isoformat(),
                "response_time_ms": measurement.response_time_ms,
                "status_code": measurement.status_code,
                "is_error": measurement.is_error,
                "sla_breached": measurement.sla_breached,
            }
        }
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        return response.status_code in [200, 201, 202, 204]
    except Exception as e:
        print(f"Error sending webhook: {str(e)}")
        return False

def send_all_webhook_notifications(endpoint, measurement, breach_type='sla'):
    """Отправить уведомления через все настроенные вебхуки проекта"""
    webhooks = Webhook.objects.filter(
        project=endpoint.project,
        is_active=True,
        trigger_type=breach_type if breach_type in ['sla_breach', 'endpoint_down', 'all_errors'] else 'sla_breach'
    )
    
    results = []
    for webhook in webhooks:
        try:
            success = send_webhook_notification(webhook.webhook_url, endpoint, measurement, breach_type)
            results.append({
                'webhook_id': webhook.id,
                'name': webhook.name,
                'success': success
            })
        except Exception as e:
            results.append({
                'webhook_id': webhook.id,
                'name': webhook.name,
                'success': False,
                'error': str(e)
            })
    
    return results
