import requests
from datetime import datetime, timedelta
# from django_q.models import Schedule
# from django_q.tasks import async_task
from .models import Endpoint, Measurement

def check_endpoint(endpoint_id):
    try:
        ep = Endpoint.objects.get(id=endpoint_id)
        url = ep.project.url.rstrip('/') + ep.path
        start = datetime.now()
        resp = requests.get(url, timeout=10)
        elapsed = (datetime.now() - start).total_seconds() * 1000  # ms
        is_error = resp.status_code >= 400
        sla_breached = (
            elapsed > ep.sla_latency_ms or
            is_error and (ep.sla_error_rate < 1)  # если SLA Error Rate < 100%
        )

        Measurement.objects.create(
            endpoint=ep,
            timestamp=datetime.now(),
            response_time_ms=elapsed,
            status_code=resp.status_code,
            is_error=is_error,
            sla_breached=sla_breached
        )
    except Exception as e:
        # Логируем ошибку (в продакшене — в логи)
        pass

# def schedule_all_endpoints():
#     for ep in Endpoint.objects.all():
#         Schedule.objects.get_or_create(
#             func='monitor.tasks.check_endpoint',
#             args=ep.id,
#             repeats=-1,
#             minutes=5,  # каждые 5 минут
#             hook='monitor.tasks.handle_schedule_result'
#         )