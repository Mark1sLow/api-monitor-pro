from rest_framework import serializers
from .models import Project, Endpoint, Measurement, Webhook

class ProjectSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    endpoint_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = ['id', 'name', 'url', 'owner', 'owner_username', 'created_at', 'endpoint_count']
        read_only_fields = ['owner', 'created_at']
    
    def get_endpoint_count(self, obj):
        return obj.endpoint_set.count()

class WebhookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Webhook
        fields = [
            'id', 'project', 'name', 'webhook_url',
            'trigger_type', 'is_active', 'created_at', 'updated_at'
        ]

class EndpointSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    latest_measurement = serializers.SerializerMethodField()
    recent_breaches = serializers.SerializerMethodField()
    
    class Meta:
        model = Endpoint
        fields = [
            'id', 'project', 'project_name', 'method', 'path', 
            'sla_latency_ms', 'sla_error_rate', 'latest_measurement', 'recent_breaches'
        ]
    
    def get_latest_measurement(self, obj):
        try:
            latest = obj.measurement_set.latest('timestamp')
            return MeasurementSerializer(latest).data
        except Measurement.DoesNotExist:
            return None
    
    def get_recent_breaches(self, obj):
        from datetime import timedelta
        from django.utils import timezone
        
        recent = obj.measurement_set.filter(
            sla_breached=True,
            timestamp__gte=timezone.now() - timedelta(hours=24)
        ).count()
        return recent

class MeasurementSerializer(serializers.ModelSerializer):
    endpoint_method = serializers.CharField(source='endpoint.method', read_only=True)
    endpoint_path = serializers.CharField(source='endpoint.path', read_only=True)
    
    class Meta:
        model = Measurement
        fields = [
            'id', 'endpoint', 'endpoint_method', 'endpoint_path',
            'timestamp', 'response_time_ms', 'status_code', 
            'is_error', 'sla_breached'
        ]
        read_only_fields = ['timestamp']

class EndpointDetailedSerializer(serializers.ModelSerializer):
    """Детальный сериализатор эндпоинта с полной статистикой"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    measurements = serializers.SerializerMethodField()
    statistics = serializers.SerializerMethodField()
    
    class Meta:
        model = Endpoint
        fields = [
            'id', 'project', 'project_name', 'method', 'path',
            'sla_latency_ms', 'sla_error_rate', 'measurements', 'statistics'
        ]
    
    def get_measurements(self, obj):
        from datetime import timedelta
        from django.utils import timezone
        
        measurements = obj.measurement_set.filter(
            timestamp__gte=timezone.now() - timedelta(days=7)
        ).order_by('-timestamp')[:100]
        return MeasurementSerializer(measurements, many=True).data
    
    def get_statistics(self, obj):
        from datetime import timedelta
        from django.utils import timezone
        from django.db.models import Avg, Count, Q
        
        measurements = obj.measurement_set.filter(
            timestamp__gte=timezone.now() - timedelta(days=7)
        )
        
        if not measurements.exists():
            return {
                'avg_latency_ms': 0,
                'error_rate': 0,
                'availability': 0,
                'total_checks': 0,
                'breaches': 0
            }
        
        total = measurements.count()
        breaches = measurements.filter(sla_breached=True).count()
        errors = measurements.filter(is_error=True).count()
        avg_latency = measurements.aggregate(avg=Avg('response_time_ms'))['avg'] or 0
        
        return {
            'avg_latency_ms': round(avg_latency, 2),
            'error_rate': round(errors / total * 100, 2) if total > 0 else 0,
            'availability': round((total - errors) / total * 100, 2) if total > 0 else 0,
            'total_checks': total,
            'breaches': breaches
        }
