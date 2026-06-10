from django.contrib import admin
from .models import Project, Endpoint, Measurement, Webhook

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

@admin.register(Webhook)
class WebhookAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'trigger_type', 'is_active', 'created_at']
    list_filter = ['trigger_type', 'is_active']
    search_fields = ['name', 'project__name']
    readonly_fields = ['created_at', 'updated_at']