"""
Утилиты для расчета метрик производительности и SLA
"""
import numpy as np
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q
from .models import Endpoint, Measurement, PerformanceMetrics, SLATracking


class MetricsCalculator:
    """Класс для расчета метрик производительности"""
    
    @staticmethod
    def calculate_percentile(values, percentile):
        """Рассчитать перцентиль"""
        if not values:
            return 0
        return float(np.percentile(values, percentile))
    
    @staticmethod
    def calculate_endpoint_metrics(endpoint, period_start, period_end):
        """
        Рассчитать метрики для эндпоинта за период
        
        Args:
            endpoint: Endpoint объект
            period_start: Начало периода
            period_end: Конец периода
            
        Returns:
            PerformanceMetrics объект (не сохраненный в БД)
        """
        # Получить все измерения за период
        measurements = Measurement.objects.filter(
            endpoint=endpoint,
            timestamp__gte=period_start,
            timestamp__lt=period_end
        )
        
        if not measurements.exists():
            return None
        
        measurements_list = list(measurements.values_list(
            'response_time_ms', 'status_code', 'is_error', 'sla_breached'
        ))
        
        # Время отклика
        response_times = [m[0] for m in measurements_list]
        min_time = float(np.min(response_times))
        max_time = float(np.max(response_times))
        avg_time = float(np.mean(response_times))
        p50_time = MetricsCalculator.calculate_percentile(response_times, 50)
        p95_time = MetricsCalculator.calculate_percentile(response_times, 95)
        p99_time = MetricsCalculator.calculate_percentile(response_times, 99)
        
        # Надежность
        total_requests = measurements.count()
        failed_requests = measurements.filter(is_error=True).count()
        successful_requests = total_requests - failed_requests
        error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0
        
        # SLA
        sla_breaches = measurements.filter(sla_breached=True).count()
        sla_compliance = ((total_requests - sla_breaches) / total_requests * 100) if total_requests > 0 else 100
        
        # Статусные коды
        status_2xx = measurements.filter(status_code__gte=200, status_code__lt=300).count()
        status_3xx = measurements.filter(status_code__gte=300, status_code__lt=400).count()
        status_4xx = measurements.filter(status_code__gte=400, status_code__lt=500).count()
        status_5xx = measurements.filter(status_code__gte=500).count()
        
        # Создать объект метрик
        metrics = PerformanceMetrics(
            endpoint=endpoint,
            period_start=period_start,
            period_end=period_end,
            response_time_min=min_time,
            response_time_max=max_time,
            response_time_avg=avg_time,
            response_time_p50=p50_time,
            response_time_p95=p95_time,
            response_time_p99=p99_time,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            error_rate=error_rate,
            sla_breaches=sla_breaches,
            sla_compliance=sla_compliance,
            status_2xx=status_2xx,
            status_3xx=status_3xx,
            status_4xx=status_4xx,
            status_5xx=status_5xx,
        )
        
        return metrics
    
    @staticmethod
    def calculate_hourly_metrics(endpoint):
        """Рассчитать почасовые метрики для эндпоинта"""
        now = timezone.now()
        period_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
        period_end = period_start + timedelta(hours=1)
        
        metrics = MetricsCalculator.calculate_endpoint_metrics(endpoint, period_start, period_end)
        if metrics:
            metrics.save()
        return metrics
    
    @staticmethod
    def calculate_daily_metrics(endpoint, target_date=None):
        """Рассчитать дневные метрики для эндпоинта"""
        if target_date is None:
            target_date = timezone.now().date()
        
        period_start = timezone.make_aware(datetime.combine(target_date, datetime.min.time()))
        period_end = period_start + timedelta(days=1)
        
        metrics = MetricsCalculator.calculate_endpoint_metrics(endpoint, period_start, period_end)
        if metrics:
            metrics.save()
        return metrics
    
    @staticmethod
    def calculate_project_metrics(project, period_start, period_end):
        """
        Рассчитать агрегированные метрики для всех эндпоинтов проекта
        
        Returns:
            dict с агрегированными метриками
        """
        endpoints = project.endpoint_set.all()
        
        total_metrics = {
            'total_endpoints': endpoints.count(),
            'total_requests': 0,
            'total_sla_breaches': 0,
            'avg_response_time': 0,
            'avg_error_rate': 0,
            'avg_sla_compliance': 0,
            'endpoints_metrics': []
        }
        
        endpoint_metrics_list = []
        response_times = []
        error_rates = []
        sla_compliances = []
        
        for endpoint in endpoints:
            metrics = MetricsCalculator.calculate_endpoint_metrics(endpoint, period_start, period_end)
            if metrics:
                endpoint_metrics_list.append(metrics)
                total_metrics['total_requests'] += metrics.total_requests
                total_metrics['total_sla_breaches'] += metrics.sla_breaches
                response_times.append(metrics.response_time_avg)
                error_rates.append(metrics.error_rate)
                sla_compliances.append(metrics.sla_compliance)
        
        if endpoint_metrics_list:
            total_metrics['avg_response_time'] = float(np.mean(response_times))
            total_metrics['avg_error_rate'] = float(np.mean(error_rates))
            total_metrics['avg_sla_compliance'] = float(np.mean(sla_compliances))
            total_metrics['endpoints_metrics'] = endpoint_metrics_list
        
        return total_metrics


class SLACalculator:
    """Класс для расчета SLA и отслеживания нарушений"""
    
    @staticmethod
    def calculate_sla_for_endpoint(endpoint, target_date=None):
        """
        Рассчитать SLA для эндпоинта за день
        
        Args:
            endpoint: Endpoint объект
            target_date: целевая дата (если None, используется текущая)
            
        Returns:
            SLATracking объект
        """
        if target_date is None:
            target_date = timezone.now().date()
        
        period_start = timezone.make_aware(datetime.combine(target_date, datetime.min.time()))
        period_end = period_start + timedelta(days=1)
        
        measurements = Measurement.objects.filter(
            endpoint=endpoint,
            timestamp__gte=period_start,
            timestamp__lt=period_end
        )
        
        total_requests = measurements.count()
        breached_requests = measurements.filter(sla_breached=True).count()
        
        if total_requests == 0:
            actual_sla = 100.0
        else:
            actual_sla = ((total_requests - breached_requests) / total_requests) * 100
        
        avg_response_time = measurements.aggregate(
            avg=__import__('django.db.models', fromlist=['Avg']).Avg('response_time_ms')
        )['avg'] or 0
        
        target_sla = (1 - endpoint.sla_error_rate) * 100
        sla_breached = actual_sla < target_sla
        
        sla_tracking = SLATracking(
            endpoint=endpoint,
            date=target_date,
            target_sla=target_sla,
            actual_sla=actual_sla,
            sla_breached=sla_breached,
            total_requests=total_requests,
            breached_requests=breached_requests,
            average_response_time=avg_response_time,
        )
        
        return sla_tracking
    
    @staticmethod
    def get_sla_trend(endpoint, days=7):
        """
        Получить тренд SLA за последние N дней
        
        Returns:
            list из (date, sla_percent, breached) кортежей
        """
        today = timezone.now().date()
        start_date = today - timedelta(days=days)
        
        sla_records = SLATracking.objects.filter(
            endpoint=endpoint,
            date__gte=start_date,
            date__lte=today
        ).order_by('date')
        
        trend = [
            (record.date, record.actual_sla, record.sla_breached)
            for record in sla_records
        ]
        
        return trend
    
    @staticmethod
    def get_sla_statistics(endpoint, days=30):
        """
        Получить SLA статистику за период
        
        Returns:
            dict со статистикой
        """
        today = timezone.now().date()
        start_date = today - timedelta(days=days)
        
        sla_records = SLATracking.objects.filter(
            endpoint=endpoint,
            date__gte=start_date,
            date__lte=today
        )
        
        if not sla_records.exists():
            return {
                'days_total': 0,
                'days_compliant': 0,
                'days_breached': 0,
                'avg_sla': 0,
                'min_sla': 0,
                'max_sla': 0,
            }
        
        sla_values = list(sla_records.values_list('actual_sla', flat=True))
        breached_count = sla_records.filter(sla_breached=True).count()
        
        return {
            'days_total': sla_records.count(),
            'days_compliant': sla_records.count() - breached_count,
            'days_breached': breached_count,
            'avg_sla': float(np.mean(sla_values)),
            'min_sla': float(np.min(sla_values)),
            'max_sla': float(np.max(sla_values)),
            'compliance_rate': ((sla_records.count() - breached_count) / sla_records.count() * 100),
        }
