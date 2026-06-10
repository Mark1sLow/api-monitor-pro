from django.contrib import admin
from .models import (
    Project, Endpoint, Measurement, Alert, Schedule,
    PerformanceMetrics, SLATracking, Report, Webhook
)

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'created_at']
    search_fields = ['name', 'owner__username']

@admin.register(Endpoint)
class EndpointAdmin(admin.ModelAdmin):
    list_display = ['project', 'method', 'path', 'sla_latency_ms', 'sla_error_rate']
    list_filter = ['project', 'method']
    search_fields = ['path']

@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = ['endpoint', 'timestamp', 'response_time_ms', 'status_code', 'is_error', 'sla_breached']
    list_filter = ['endpoint', 'timestamp', 'is_error']
    date_hierarchy = 'timestamp'
    readonly_fields = ['timestamp', 'response_time_ms', 'status_code', 'is_error', 'sla_breached']

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['endpoint', 'alert_type', 'created_at', 'is_read']
    list_filter = ['alert_type', 'created_at', 'is_read', 'project']
    search_fields = ['endpoint__path', 'project__name']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ['project', 'interval_minutes', 'is_active', 'last_run', 'next_run']
    list_filter = ['is_active']
    readonly_fields = ['last_run', 'next_run', 'created_at', 'updated_at']


@admin.register(PerformanceMetrics)
class PerformanceMetricsAdmin(admin.ModelAdmin):
    list_display = ['endpoint', 'period_start', 'period_end', 'response_time_avg', 'sla_compliance']
    list_filter = ['endpoint', 'period_start']
    date_hierarchy = 'period_start'
    readonly_fields = ['created_at', 'updated_at']
    search_fields = ['endpoint__path']


@admin.register(SLATracking)
class SLATrackingAdmin(admin.ModelAdmin):
    list_display = ['endpoint', 'date', 'actual_sla', 'target_sla', 'sla_breached', 'predicted_breach']
    list_filter = ['date', 'sla_breached', 'predicted_breach', 'endpoint']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at']
    search_fields = ['endpoint__path']


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['project', 'report_type', 'format', 'period_start', 'created_at', 'created_by']
    list_filter = ['report_type', 'format', 'created_at', 'project']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
    search_fields = ['project__name']


@admin.register(Webhook)
class WebhookAdmin(admin.ModelAdmin):
    list_display = ['project', 'name', 'webhook_type', 'trigger_type', 'is_active']
    list_filter = ['webhook_type', 'trigger_type', 'is_active', 'project']
    search_fields = ['name', 'project__name']