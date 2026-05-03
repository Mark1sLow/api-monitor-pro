from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('project/new/', views.create_project, name='create_project'),
    path('project/<int:pk>/', views.project_detail, name='project_detail'),
    path('endpoint/<int:pk>/', views.endpoint_detail, name='endpoint_detail'),
    path('project/<int:project_pk>/endpoint/new/', views.create_endpoint, name='create_endpoint'),
    path('endpoint/<int:pk>/delete/', views.endpoint_delete, name='endpoint_delete'),
]