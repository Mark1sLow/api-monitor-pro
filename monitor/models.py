from django.db import models
from django.contrib.auth.models import User

class Project(models.Model):
    name = models.CharField(max_length=100)
    url = models.URLField(help_text="Base URL, e.g. https://api.example.com")
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Endpoint(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    method = models.CharField(max_length=10, choices=[
        ('GET', 'GET'), ('POST', 'POST'), ('PUT', 'PUT'), ('DELETE', 'DELETE')
    ])
    path = models.CharField(max_length=255, help_text="/users, /health")
    sla_latency_ms = models.PositiveIntegerField(default=500, help_text="Max acceptable latency (ms)")
    sla_error_rate = models.FloatField(default=0.05, help_text="Max error rate (e.g. 0.05 = 5%)")

    class Meta:
        unique_together = ('project', 'method', 'path')

    def __str__(self):
        return f"{self.method} {self.path} @ {self.project}"

class Measurement(models.Model):
    endpoint = models.ForeignKey(Endpoint, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    response_time_ms = models.FloatField()
    status_code = models.IntegerField()
    is_error = models.BooleanField()
    sla_breached = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.endpoint} | {self.response_time_ms}ms | {self.status_code}"


class Alert(models.Model):
    """История всех уведомлений об оповещениях"""
    ALERT_TYPES = [
        ('sla_breach', 'SLA Breach'),
        ('endpoint_down', 'Endpoint Down'),
        ('error', 'Error'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    endpoint = models.ForeignKey(Endpoint, on_delete=models.CASCADE)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    measurement = models.ForeignKey(Measurement, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'created_at']),
            models.Index(fields=['alert_type', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.alert_type} - {self.endpoint} ({self.created_at})"


class Schedule(models.Model):
    """Расписание проверки эндпоинтов"""
    INTERVAL_CHOICES = [
        ('1', 'Each minute'),
        ('5', 'Every 5 minutes'),
        ('10', 'Every 10 minutes'),
        ('15', 'Every 15 minutes'),
        ('30', 'Every 30 minutes'),
        ('60', 'Every hour'),
        ('360', 'Every 6 hours'),
        ('1440', 'Every day'),
    ]
    
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='schedule')
    interval_minutes = models.CharField(max_length=10, choices=INTERVAL_CHOICES, default='5')
    is_active = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.project.name} - Every {self.interval_minutes} min"


class PerformanceMetrics(models.Model):
    """Кэшированные метрики производительности эндпоинта за период"""
    endpoint = models.ForeignKey(Endpoint, on_delete=models.CASCADE, related_name='performance_metrics')
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    # Метрики времени отклика
    response_time_min = models.FloatField()
    response_time_max = models.FloatField()
    response_time_avg = models.FloatField()
    response_time_p50 = models.FloatField()
    response_time_p95 = models.FloatField()
    response_time_p99 = models.FloatField()
    
    # Метрики надежности
    total_requests = models.IntegerField()
    successful_requests = models.IntegerField()
    failed_requests = models.IntegerField()
    error_rate = models.FloatField(default=0.0)
    sla_breaches = models.IntegerField(default=0)
    sla_compliance = models.FloatField(default=100.0)
    
    # Статусные коды
    status_2xx = models.IntegerField(default=0)
    status_3xx = models.IntegerField(default=0)
    status_4xx = models.IntegerField(default=0)
    status_5xx = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('endpoint', 'period_start', 'period_end')
        ordering = ['-period_start']
        indexes = [
            models.Index(fields=['endpoint', 'period_start']),
            models.Index(fields=['endpoint', 'period_end']),
        ]
    
    def __str__(self):
        return f"{self.endpoint} - {self.period_start} to {self.period_end}"


class SLATracking(models.Model):
    """Отслеживание SLA и истории нарушений"""
    endpoint = models.ForeignKey(Endpoint, on_delete=models.CASCADE, related_name='sla_tracking')
    date = models.DateField()  # День отслеживания
    
    # SLA метрики за день
    target_sla = models.FloatField(help_text="Target SLA %")
    actual_sla = models.FloatField(help_text="Actual SLA %") 
    sla_breached = models.BooleanField(default=False)
    
    # Подробности
    total_requests = models.IntegerField()
    breached_requests = models.IntegerField()
    average_response_time = models.FloatField()
    
    # Предсказание
    predicted_breach = models.BooleanField(default=False)
    breach_probability = models.FloatField(default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('endpoint', 'date')
        ordering = ['-date']
        indexes = [
            models.Index(fields=['endpoint', 'date']),
            models.Index(fields=['sla_breached', 'date']),
        ]
    
    def __str__(self):
        status = "✓" if self.actual_sla >= self.target_sla else "✗"
        return f"{status} {self.endpoint} - {self.date} ({self.actual_sla:.2f}%)"


class Report(models.Model):
    """Сохраненные отчеты в различных форматах"""
    REPORT_TYPES = [
        ('daily', 'Daily Report'),
        ('weekly', 'Weekly Report'),
        ('monthly', 'Monthly Report'),
        ('custom', 'Custom Report'),
    ]
    
    FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('csv', 'CSV'),
        ('html', 'HTML'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='reports')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES)
    
    # Период отчета
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    # Файл отчета
    file_path = models.FileField(upload_to='reports/', null=True, blank=True)
    file_size = models.IntegerField(default=0, help_text="File size in bytes")
    
    # Статистика
    total_endpoints = models.IntegerField()
    total_measurements = models.IntegerField()
    sla_breaches = models.IntegerField()
    average_sla = models.FloatField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'report_type', 'created_at']),
            models.Index(fields=['format', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.report_type.upper()} - {self.project.name} ({self.period_start.date()})"


class Webhook(models.Model):
    """Вебхуки для уведомлений"""
    WEBHOOK_TYPES = [
        ('discord', 'Discord'),
        ('telegram', 'Telegram'),
        ('generic', 'Generic'),
    ]
    
    TRIGGER_TYPES = [
        ('sla_breach', 'SLA Breach'),
        ('endpoint_down', 'Endpoint Down'),
        ('error', 'Any Error'),
        ('all', 'All Events'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='webhooks')
    name = models.CharField(max_length=100)
    webhook_type = models.CharField(max_length=20, choices=WEBHOOK_TYPES)
    url = models.URLField()
    trigger_type = models.CharField(max_length=20, choices=TRIGGER_TYPES, default='all')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['project', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.webhook_type})"