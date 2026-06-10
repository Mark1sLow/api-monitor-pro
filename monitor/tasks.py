"""
Celery задачи для расчета метрик, прогнозирования и создания отчетов
"""
from celery import shared_task
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .models import (
    Project, Endpoint, Measurement, Alert, 
    PerformanceMetrics, SLATracking, Report
)
from .metrics_calculator import MetricsCalculator, SLACalculator
from .forecast import SLAForecaster
from .exporters import PDFReportGenerator, CSVExporter


@shared_task
def calculate_endpoint_metrics(endpoint_id):
    """Рассчитать почасовые метрики для эндпоинта"""
    try:
        endpoint = Endpoint.objects.get(id=endpoint_id)
        MetricsCalculator.calculate_hourly_metrics(endpoint)
        return f"Metrics calculated for {endpoint}"
    except Exception as e:
        return f"Error calculating metrics: {str(e)}"


@shared_task
def calculate_daily_metrics_for_all():
    """Рассчитать дневные метрики для всех эндпоинтов (запускается каждую ночь)"""
    target_date = (timezone.now() - timedelta(days=1)).date()
    
    endpoints = Endpoint.objects.all()
    count = 0
    
    for endpoint in endpoints:
        try:
            MetricsCalculator.calculate_daily_metrics(endpoint, target_date)
            count += 1
        except Exception as e:
            print(f"Error for endpoint {endpoint}: {str(e)}")
    
    return f"Calculated metrics for {count} endpoints"


@shared_task
def calculate_sla_tracking_for_all():
    """Рассчитать SLA tracking для всех эндпоинтов (запускается каждую ночь)"""
    target_date = (timezone.now() - timedelta(days=1)).date()
    
    endpoints = Endpoint.objects.all()
    count = 0
    
    for endpoint in endpoints:
        try:
            sla_tracking = SLACalculator.calculate_sla_for_endpoint(endpoint, target_date)
            
            # Проверить предсказание нарушения
            prediction = SLAForecaster.predict_breach(endpoint, forecast_days=1)
            sla_tracking.predicted_breach = prediction['predicted_breach']
            sla_tracking.breach_probability = prediction['breach_probability']
            
            sla_tracking.save()
            count += 1
            
            # Если нарушение SLA, создать алерт
            if sla_tracking.sla_breached:
                Alert.objects.get_or_create(
                    project=endpoint.project,
                    endpoint=endpoint,
                    alert_type='sla_breach',
                    created_at=timezone.now(),
                    defaults={
                        'message': f"SLA breached: {sla_tracking.actual_sla:.2f}% < {sla_tracking.target_sla:.2f}%",
                    }
                )
        except Exception as e:
            print(f"Error for endpoint {endpoint}: {str(e)}")
    
    return f"Calculated SLA tracking for {count} endpoints"


@shared_task
def forecast_sla_breaches_for_all():
    """Предсказать нарушения SLA для всех проектов (запускается каждый час)"""
    projects = Project.objects.all()
    predictions_count = 0
    at_risk_count = 0
    
    for project in projects:
        try:
            summary = SLAForecaster.get_forecast_summary(project, days_ahead=1)
            predictions_count += len(summary['predictions'])
            at_risk_count += summary['endpoints_at_risk']
        except Exception as e:
            print(f"Error forecasting for project {project}: {str(e)}")
    
    return f"Forecast completed: {predictions_count} endpoints checked, {at_risk_count} at risk"


@shared_task
def generate_daily_report(project_id):
    """Генерировать дневной отчет по проекту"""
    try:
        project = Project.objects.get(id=project_id)
        
        now = timezone.now()
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(days=1)
        
        # Генерировать PDF
        pdf_data = PDFReportGenerator.generate_report(project, period_start, period_end)
        
        # Рассчитать метрики для отчета
        metrics = MetricsCalculator.calculate_project_metrics(project, period_start, period_end)
        
        # Создать запись Report
        report = Report.objects.create(
            project=project,
            report_type='daily',
            format='pdf',
            period_start=period_start,
            period_end=period_end,
            total_endpoints=metrics['total_endpoints'],
            total_measurements=metrics['total_requests'],
            sla_breaches=metrics['total_sla_breaches'],
            average_sla=metrics['avg_sla_compliance'],
            file_size=len(pdf_data),
        )
        
        return f"Daily report generated for {project.name}"
    except Exception as e:
        return f"Error generating daily report: {str(e)}"


@shared_task
def generate_weekly_report(project_id):
    """Генерировать недельный отчет по проекту"""
    try:
        project = Project.objects.get(id=project_id)
        
        now = timezone.now()
        period_end = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_start = period_end - timedelta(days=7)
        
        # Генерировать PDF
        pdf_data = PDFReportGenerator.generate_report(project, period_start, period_end)
        
        # Рассчитать метрики для отчета
        metrics = MetricsCalculator.calculate_project_metrics(project, period_start, period_end)
        
        # Создать запись Report
        report = Report.objects.create(
            project=project,
            report_type='weekly',
            format='pdf',
            period_start=period_start,
            period_end=period_end,
            total_endpoints=metrics['total_endpoints'],
            total_measurements=metrics['total_requests'],
            sla_breaches=metrics['total_sla_breaches'],
            average_sla=metrics['avg_sla_compliance'],
            file_size=len(pdf_data),
        )
        
        return f"Weekly report generated for {project.name}"
    except Exception as e:
        return f"Error generating weekly report: {str(e)}"


@shared_task
def generate_monthly_report(project_id):
    """Генерировать месячный отчет по проекту"""
    try:
        project = Project.objects.get(id=project_id)
        
        now = timezone.now()
        period_end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_start = period_end - timedelta(days=30)
        
        # Генерировать PDF
        pdf_data = PDFReportGenerator.generate_report(project, period_start, period_end)
        
        # Рассчитать метрики для отчета
        metrics = MetricsCalculator.calculate_project_metrics(project, period_start, period_end)
        
        # Создать запись Report
        report = Report.objects.create(
            project=project,
            report_type='monthly',
            format='pdf',
            period_start=period_start,
            period_end=period_end,
            total_endpoints=metrics['total_endpoints'],
            total_measurements=metrics['total_requests'],
            sla_breaches=metrics['total_sla_breaches'],
            average_sla=metrics['avg_sla_compliance'],
            file_size=len(pdf_data),
        )
        
        return f"Monthly report generated for {project.name}"
    except Exception as e:
        return f"Error generating monthly report: {str(e)}"


@shared_task
def export_measurements_to_csv(endpoint_id, days=7):
    """Экспортировать измерения в CSV"""
    try:
        endpoint = Endpoint.objects.get(id=endpoint_id)
        
        now = timezone.now()
        period_start = now - timedelta(days=days)
        period_end = now
        
        csv_data = CSVExporter.export_measurements(endpoint, period_start, period_end)
        
        return f"CSV export completed for {endpoint} ({len(csv_data)} bytes)"
    except Exception as e:
        return f"Error exporting CSV: {str(e)}"


@shared_task
def send_sla_breach_notification(endpoint_id, breach_message):
    """Отправить уведомление о нарушении SLA (email)"""
    try:
        endpoint = Endpoint.objects.get(id=endpoint_id)
        project = endpoint.project
        
        # Получить email владельца проекта
        owner_email = project.owner.email
        
        if owner_email:
            subject = f"SLA Breach Alert - {endpoint.method} {endpoint.path}"
            
            message = f"""
            SLA Breach Detected!
            
            Endpoint: {endpoint.method} {endpoint.path}
            Project: {project.name}
            
            Message: {breach_message}
            
            Target SLA: {(1 - endpoint.sla_error_rate) * 100:.2f}%
            Max Latency: {endpoint.sla_latency_ms}ms
            
            Please investigate immediately.
            """
            
            send_mail(subject, message, 'noreply@apimonitor.local', [owner_email])
        
        return f"Notification sent for {endpoint}"
    except Exception as e:
        return f"Error sending notification: {str(e)}"


@shared_task
def cleanup_old_metrics():
    """Очистить старые метрики (старше 90 дней)"""
    cutoff_date = timezone.now() - timedelta(days=90)
    
    deleted_count, _ = PerformanceMetrics.objects.filter(
        created_at__lt=cutoff_date
    ).delete()
    
    return f"Deleted {deleted_count} old metrics"


@shared_task
def cleanup_old_sla_tracking():
    """Очистить старые записи SLA tracking (старше 1 года)"""
    cutoff_date = (timezone.now() - timedelta(days=365)).date()
    
    deleted_count, _ = SLATracking.objects.filter(
        date__lt=cutoff_date
    ).delete()
    
    return f"Deleted {deleted_count} old SLA tracking records"


@shared_task
def generate_daily_reports_for_all():
    """Генерировать дневные отчеты для всех проектов"""
    projects = Project.objects.all()
    count = 0
    
    for project in projects:
        try:
            generate_daily_report.apply_async(args=[project.id])
            count += 1
        except Exception as e:
            print(f"Error generating report for {project}: {str(e)}")
    
    return f"Daily reports queued for {count} projects"


@shared_task
def generate_weekly_reports_for_all():
    """Генерировать недельные отчеты для всех проектов"""
    projects = Project.objects.all()
    count = 0
    
    for project in projects:
        try:
            generate_weekly_report.apply_async(args=[project.id])
            count += 1
        except Exception as e:
            print(f"Error generating report for {project}: {str(e)}")
    
    return f"Weekly reports queued for {count} projects"
