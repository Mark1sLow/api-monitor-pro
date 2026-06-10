from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import models
from datetime import timedelta
from .models import Project, Endpoint, Measurement, Webhook
from .serializers import ProjectSerializer, EndpointSerializer, MeasurementSerializer, EndpointDetailedSerializer, WebhookSerializer
from .tasks import check_endpoint

class ProjectViewSet(viewsets.ModelViewSet):
    """
    API для управления проектами
    
    list: Получить все проекты текущего пользователя
    create: Создать новый проект
    retrieve: Получить детали проекта
    update: Обновить проект
    destroy: Удалить проект
    """
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'url']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Получить статистику проекта"""
        project = self.get_object()
        endpoints = project.endpoint_set.all()
        
        measurements = Measurement.objects.filter(
            endpoint__in=endpoints,
            timestamp__gte=timezone.now() - timedelta(days=7)
        )
        
        total_checks = measurements.count()
        breaches = measurements.filter(sla_breached=True).count()
        errors = measurements.filter(is_error=True).count()
        
        return Response({
            'project_id': project.id,
            'endpoints_count': endpoints.count(),
            'total_checks_7d': total_checks,
            'breaches_7d': breaches,
            'error_rate_7d': round(errors / total_checks * 100, 2) if total_checks > 0 else 0,
        })

class EndpointViewSet(viewsets.ModelViewSet):
    """
    API для управления эндпоинтами
    
    list: Получить все эндпоинты (с фильтром по проекту)
    create: Создать новый эндпоинт
    retrieve: Получить детали эндпоинта
    update: Обновить эндпоинт
    destroy: Удалить эндпоинт
    """
    serializer_class = EndpointSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['path', 'method']
    ordering_fields = ['path', 'sla_latency_ms']
    ordering = ['path']
    
    def get_queryset(self):
        user = self.request.user
        return Endpoint.objects.filter(project__owner=user)
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EndpointDetailedSerializer
        return EndpointSerializer
    
    @action(detail=True, methods=['post'])
    def check_now(self, request, pk=None):
        """Немедленно проверить эндпоинт"""
        endpoint = self.get_object()
        check_endpoint.delay(endpoint.id)
        return Response({
            'status': 'queued',
            'message': f'Endpoint {endpoint.method} {endpoint.path} queued for checking'
        })
    
    @action(detail=True, methods=['get'])
    def recent_measurements(self, request, pk=None):
        """Получить последние измерения"""
        endpoint = self.get_object()
        hours = int(request.query_params.get('hours', 24))
        
        measurements = endpoint.measurement_set.filter(
            timestamp__gte=timezone.now() - timedelta(hours=hours)
        ).order_by('-timestamp')[:100]
        
        return Response({
            'endpoint_id': endpoint.id,
            'hours': hours,
            'measurements': MeasurementSerializer(measurements, many=True).data
        })
    
    @action(detail=True, methods=['get'])
    def sla_summary(self, request, pk=None):
        """Получить SLA сводку"""
        endpoint = self.get_object()
        days = int(request.query_params.get('days', 7))
        
        measurements = endpoint.measurement_set.filter(
            timestamp__gte=timezone.now() - timedelta(days=days)
        )
        
        total = measurements.count()
        if total == 0:
            return Response({
                'endpoint_id': endpoint.id,
                'days': days,
                'message': 'No measurements found'
            })
        
        breaches = measurements.filter(sla_breached=True).count()
        errors = measurements.filter(is_error=True).count()
        avg_latency = measurements.aggregate(avg=models.Avg('response_time_ms'))['avg'] or 0
        min_latency = measurements.aggregate(min=models.Min('response_time_ms'))['min'] or 0
        max_latency = measurements.aggregate(max=models.Max('response_time_ms'))['max'] or 0
        
        return Response({
            'endpoint_id': endpoint.id,
            'days': days,
            'total_checks': total,
            'sla_breaches': breaches,
            'breach_percentage': round(breaches / total * 100, 2),
            'error_rate': round(errors / total * 100, 2),
            'availability': round((total - errors) / total * 100, 2),
            'avg_latency_ms': round(avg_latency, 2),
            'min_latency_ms': round(min_latency, 2),
            'max_latency_ms': round(max_latency, 2),
            'sla_limit_ms': endpoint.sla_latency_ms,
        })

class MeasurementViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API для просмотра измерений (только чтение)
    """
    serializer_class = MeasurementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['timestamp', 'response_time_ms']
    ordering = ['-timestamp']
    
    def get_queryset(self):
        user = self.request.user
        return Measurement.objects.filter(endpoint__project__owner=user)

class WebhookViewSet(viewsets.ModelViewSet):
    """
    API для управления вебхуками для уведомлений
    
    list: Получить все вебхуки проекта
    create: Создать новый вебхук
    retrieve: Получить детали вебхука
    update: Обновить вебхук
    destroy: Удалить вебхук
    test: Тест отправки уведомления
    """
    serializer_class = WebhookSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        return Webhook.objects.filter(project__owner=user)
    
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Тест отправки тестового уведомления"""
        webhook = self.get_object()
        from .webhooks import send_webhook_notification
        from .models import Endpoint, Measurement
        from django.utils import timezone
        
        try:
            endpoint = webhook.project.endpoint_set.first()
            
            if not endpoint:
                return Response(
                    {'error': 'No endpoints in this project'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            test_measurement = Measurement(
                endpoint=endpoint,
                timestamp=timezone.now(),
                response_time_ms=1500,
                status_code=200,
                is_error=False,
                sla_breached=True
            )
            
            success = send_webhook_notification(webhook.webhook_url, endpoint, test_measurement)
            
            return Response({
                'success': success,
                'message': 'Test notification sent' if success else 'Failed to send notification'
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
