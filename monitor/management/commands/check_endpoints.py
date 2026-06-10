from django.core.management.base import BaseCommand
from django.utils import timezone
from monitor.models import Endpoint, Measurement, Alert
from monitor.utils import send_sla_breach_notification
import requests
from datetime import datetime

class Command(BaseCommand):
    help = 'Проверяет все эндпоинты и сохраняет результаты'

    def add_arguments(self, parser):
        parser.add_argument('--project', type=int, help='Check specific project ID')
        parser.add_argument('--endpoint', type=int, help='Check specific endpoint ID')

    def handle(self, *args, **options):
        project_id = options.get('project')
        endpoint_id = options.get('endpoint')
        
        if endpoint_id:
            endpoints = Endpoint.objects.filter(id=endpoint_id)
        elif project_id:
            endpoints = Endpoint.objects.filter(project_id=project_id)
        else:
            endpoints = Endpoint.objects.all()
        
        checked = 0
        errors = 0
        alerts = 0
        
        for endpoint in endpoints:
            try:
                url = endpoint.project.url.rstrip('/') + endpoint.path
                
                start = timezone.now()
                try:
                    resp = requests.get(url, timeout=10)
                    elapsed = (timezone.now() - start).total_seconds() * 1000  # ms
                    is_error = resp.status_code >= 400
                except requests.Timeout:
                    elapsed = 10000
                    is_error = True
                    resp = None
                except Exception as e:
                    elapsed = 0
                    is_error = True
                    resp = None
                
                sla_breached = (
                    elapsed > endpoint.sla_latency_ms or
                    (is_error and endpoint.sla_error_rate < 1)
                )
                
                status_code = resp.status_code if resp else 0
                
                measurement = Measurement.objects.create(
                    endpoint=endpoint,
                    timestamp=timezone.now(),
                    response_time_ms=elapsed,
                    status_code=status_code,
                    is_error=is_error,
                    sla_breached=sla_breached
                )
                
                # Логирование в Alert
                if sla_breached:
                    alert_type = 'endpoint_down' if is_error else 'sla_breach'
                    message = f"{endpoint.method} {endpoint.path}: "
                    
                    if is_error:
                        message += f"Status {status_code}"
                    else:
                        message += f"Response time {elapsed}ms (limit: {endpoint.sla_latency_ms}ms)"
                    
                    Alert.objects.create(
                        project=endpoint.project,
                        endpoint=endpoint,
                        alert_type=alert_type,
                        measurement=measurement,
                        message=message
                    )
                    
                    send_sla_breach_notification(endpoint, measurement)
                    alerts += 1
                
                checked += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ {endpoint.method} {endpoint.path}')
                )
            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f'✗ {endpoint.method} {endpoint.path}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nПроверка завершена: {checked} успешно, {errors} ошибок, {alerts} оповещений')
        )
