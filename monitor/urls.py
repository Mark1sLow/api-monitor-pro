"""
URL маршруты для веб-интерфейса приложения API Monitor Pro

Маршруты:
- /register/           → регистрация новых пользователей
- /login/              → вход в систему
- /logout/             → выход из системы
- /dashboard/          → главная панель управления
- /project/new/        → создание нового проекта
- /project/<id>/       → просмотр деталей проекта
- /endpoint/<id>/      → просмотр деталей эндпоинта
- /endpoint/<id>/delete/ → удаление эндпоинта
- /alerts/             → просмотр истории оповещений
- /alerts/<id>/read/   → отметить оповещение как прочитанное
- /schedule/           → просмотр и управление расписаниями
- /schedule/<id>/      → редактирование расписания

Все операции защищены @login_required и проверяют права доступа пользователя.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Аутентификация
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Главные страницы
    path('dashboard/', views.dashboard, name='dashboard'),
    path('', views.home, name='home'),
    
    # Управление проектами
    path('project/new/', views.create_project, name='create_project'),
    path('project/<int:pk>/', views.project_detail, name='project_detail'),
    
    # Управление эндпоинтами
    path('project/<int:project_pk>/endpoint/new/', views.create_endpoint, name='create_endpoint'),
    path('endpoint/<int:pk>/', views.endpoint_detail, name='endpoint_detail'),
    path('endpoint/<int:pk>/delete/', views.endpoint_delete, name='endpoint_delete'),
    
    # История оповещений
    path('alerts/', views.alerts_list, name='alerts_list'),
    path('alerts/<int:pk>/read/', views.alert_mark_read, name='alert_mark_read'),
    
    # Управление расписаниями
    path('schedule/', views.schedule_list, name='schedule_list'),
    path('schedule/<int:pk>/', views.schedule_update, name='schedule_update'),
    
    # Расширенные метрики
    path('endpoint/<int:pk>/metrics/', views.endpoint_metrics, name='endpoint_metrics'),
    path('project/<int:pk>/metrics/', views.project_metrics, name='project_metrics'),
    
    # SLA Трекинг
    path('sla/dashboard/', views.sla_dashboard, name='sla_dashboard'),
    path('endpoint/<int:pk>/sla-history/', views.endpoint_sla_history, name='endpoint_sla_history'),
    path('endpoint/<int:pk>/sla-forecast/', views.predict_sla_breach, name='sla_forecast'),
    
    # Отчеты
    path('reports/', views.reports_list, name='reports_list'),
    path('project/<int:project_id>/generate-report/', views.generate_report, name='generate_report'),
    
    # CSV Экспорт
    path('endpoint/<int:pk>/export/measurements/', views.export_measurements_csv, name='export_measurements_csv'),
    path('project/<int:project_id>/export/metrics/', views.export_metrics_csv, name='export_metrics_csv'),
    path('endpoint/<int:pk>/export/sla/', views.export_sla_csv, name='export_sla_csv'),
    
    # API для графиков
    path('api/endpoint/<int:pk>/metrics/', views.api_endpoint_metrics, name='api_endpoint_metrics'),
    path('api/endpoint/<int:pk>/sla-forecast/', views.api_sla_forecast, name='api_sla_forecast'),
]