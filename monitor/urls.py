"""
URL маршруты для приложения API Monitor Pro

Этот модуль определяет все маршруты для:
1. REST API (для программного доступа через JSON)
   - /api/projects/       → ProjectViewSet (CRUD операции)
   - /api/endpoints/      → EndpointViewSet (CRUD операции)
   - /api/measurements/   → MeasurementViewSet (только чтение)
   - /api/webhooks/       → WebhookViewSet (CRUD операции)

2. Веб-интерфейса (для браузера)
   - /register/           → регистрация новых пользователей
   - /login/              → вход в систему
   - /logout/             → выход из системы
   - /dashboard/          → главная панель управления
   - /project/new/        → создание нового проекта
   - /project/<id>/       → просмотр деталей проекта
   - /endpoint/<id>/      → просмотр деталей эндпоинта
   - /endpoint/<id>/delete/ → удаление эндпоинта

API запросы требуют JWT токены, веб-интерфейс использует сессии.
Все операции проверяют права доступа пользователя.

Автор: API Monitor Pro Team
Версия: 1.0
"""

from django.urls import path, include
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter
from . import views
from .api import ProjectViewSet, EndpointViewSet, MeasurementViewSet, WebhookViewSet

# ============ REST API Router ============
# Автоматически создаёт маршруты для CRUD операций
router = DefaultRouter()
router.register(r'api/projects', ProjectViewSet, basename='project')
router.register(r'api/endpoints', EndpointViewSet, basename='endpoint')
router.register(r'api/measurements', MeasurementViewSet, basename='measurement')
router.register(r'api/webhooks', WebhookViewSet, basename='webhook')

urlpatterns = [
    # ============ API маршруты ============
    # Все API маршруты из router
    path('', include(router.urls)),
    
    # ============ Аутентификация ============
    # Регистрация новых пользователей
    path('register/', views.register, name='register'),
    # Вход в систему
    path('login/', views.login_view, name='login'),
    # Выход из системы
    path('logout/', views.logout_view, name='logout'),
    
    # ============ Веб-интерфейс ============
    # Главная панель управления (защищена @login_required)
    path('dashboard/', views.dashboard, name='dashboard'),
    # Главная страница (редирект для авторизованных пользователей)
    path('', views.home, name='home'),
    # Создание нового проекта (защищено @login_required)
    path('project/new/', views.create_project, name='create_project'),
    # Просмотр проекта (защищено @login_required)
    path('project/<int:pk>/', views.project_detail, name='project_detail'),
    # Просмотр эндпоинта с графиками (защищено @login_required)
    path('endpoint/<int:pk>/', views.endpoint_detail, name='endpoint_detail'),
    # Создание нового эндпоинта в проекте (защищено @login_required)
    path('project/<int:project_pk>/endpoint/new/', views.create_endpoint, name='create_endpoint'),
    # Удаление эндпоинта (защищено @login_required)
    path('endpoint/<int:pk>/delete/', views.endpoint_delete, name='endpoint_delete'),
]