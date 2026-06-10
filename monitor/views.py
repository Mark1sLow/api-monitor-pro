"""
Представления (Views) приложения API Monitor Pro

Этот модуль содержит все view функции для обработки:
- Аутентификации пользователей (регистрация, вход, выход)
- Управления проектами (создание, просмотр, редактирование)
- Управления эндпоинтами (создание, просмотр, удаление)
- Отображения данных мониторинга и статистики

Все view функции используют:
- Django шаблоны для отрендеринга HTML
- Bootstrap 5 для стилизации
- Plotly для интерактивных графиков
- Celery для асинхронных задач мониторинга

Автор: API Monitor Pro Team
Версия: 1.0
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q
from .models import Project, Endpoint, Measurement
from .forms import ProjectForm, EndpointForm, LoginForm, RegisterForm
from .utils import calculate_sli_stats, send_sla_breach_notification
import plotly.graph_objs as go
from plotly.offline import plot
from datetime import datetime, timedelta


def home(request):
    """
    Главная страница приложения.
    
    Логика:
    - Если пользователь залогинен → редирект на dashboard
    - Если пользователь не залогинен → редирект на страницу входа
    
    Args:
        request: HTTP запрос
        
    Returns:
        HttpResponseRedirect: Редирект на dashboard или login
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


def register(request):
    """
    Регистрация нового пользователя.
    
    GET: Отображает форму регистрации
    POST: Обрабатывает отправку формы, создаёт нового пользователя
    
    Процесс:
    1. Если пользователь уже залогинен → редирект на dashboard
    2. Получить данные из RegisterForm
    3. Проверить валидацию (уникальность username/email, надёжность пароля)
    4. Создать пользователя с хешированным паролем
    5. Показать сообщение об успехе и редирект на login
    
    Args:
        request: HTTP запрос
        
    Returns:
        HttpResponse: Отображение шаблона регистрации
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, 'Аккаунт создан! Пожалуйста, войдите.')
            return redirect('login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    if isinstance(error, list):
                        for e in error:
                            messages.error(request, str(e))
                    else:
                        messages.error(request, str(error))
    else:
        form = RegisterForm()
    
    return render(request, 'registration/register.html', {'form': form})


def login_view(request):
    """
    Вход пользователя в систему.
    
    GET: Отображает форму входа
    POST: Обрабатывает отправку формы, проверяет учётные данные
    
    Процесс:
    1. Если пользователь уже залогинен → редирект на dashboard
    2. Получить данные (username и password) из LoginForm
    3. Проверить учётные данные используя authenticate()
    4. Если учётные данные верны → создать сессию и редирект на dashboard
    5. Если ошибка → показать сообщение об ошибке
    
    Args:
        request: HTTP запрос
        
    Returns:
        HttpResponse: Отображение шаблона входа или редирект на dashboard
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Добро пожаловать, {user.username}!')
                return redirect('dashboard')
            else:
                messages.error(request, 'Неверный логин или пароль')
    else:
        form = LoginForm()
    
    return render(request, 'registration/login.html', {'form': form})


def logout_view(request):
    """
    Выход пользователя из системы.
    
    Процесс:
    1. Удалить сессию пользователя используя logout()
    2. Показать сообщение об успешном выходе
    3. Редирект на страницу входа
    
    Args:
        request: HTTP запрос
        
    Returns:
        HttpResponseRedirect: Редирект на страницу входа
    """
    logout(request)
    messages.success(request, 'Вы успешно вышли из системы')
    return redirect('login')

@login_required
def dashboard(request):
    """
    Главная панель управления (Dashboard).
    
    Отображает:
    - Список проектов пользователя
    - Список эндпоинтов по проектам
    - Статистика по нарушениям SLA за последние 24 часа
    - Статистика по количеству проверок за последние 7 дней
    
    Доступно только для залогиненных пользователей (@login_required).
    Пользователь видит только свои проекты и эндпоинты.
    
    Args:
        request: HTTP запрос
        
    Returns:
        HttpResponse: Отображение dashboard шаблона с контекстом
    """
    projects = Project.objects.filter(owner=request.user)
    endpoints = Endpoint.objects.filter(project__in=projects)
    
    # Статистика по нарушениям SLA
    sla_breaches = Measurement.objects.filter(
        endpoint__project__in=projects,
        sla_breached=True,
        timestamp__gte=datetime.now() - timedelta(days=1)
    ).count()
    
    total_measurements = Measurement.objects.filter(
        endpoint__project__in=projects,
        timestamp__gte=datetime.now() - timedelta(days=7)
    ).count()
    
    context = {
        'projects': projects,
        'endpoints': endpoints,
        'sla_breaches': sla_breaches,
        'total_measurements': total_measurements,
        'project_count': projects.count(),
        'endpoint_count': endpoints.count(),
    }
    return render(request, 'dashboard.html', context)

@login_required
def endpoint_detail(request, pk):
    """
    Детальный просмотр эндпоинта с графиками и статистикой.
    
    Отображает:
    - Информация об эндпоинте
    - Последние 10 измерений
    - Количество нарушений SLA за 24 часа
    - Интерактивные графики (время отклика, статус коды и т.д.)
    - Статистика по SLI (Service Level Indicator)
    
    Доступно только для залогиненных пользователей.
    Пользователь может просмотреть только эндпоинты из своих проектов.
    
    Args:
        request: HTTP запрос
        pk: ID эндпоинта
        
    Returns:
        HttpResponse: Отображение шаблона с деталями эндпоинта
    """
    ep = get_object_or_404(Endpoint, pk=pk, project__owner=request.user)
    stats_df = calculate_sli_stats(ep.id)
    
    # Последние 10 измерений
    recent_measurements = Measurement.objects.filter(endpoint=ep).order_by('-timestamp')[:10]
    
    # Проверка нарушений за последние 24 часа
    recent_breaches = Measurement.objects.filter(
        endpoint=ep,
        sla_breached=True,
        timestamp__gte=datetime.now() - timedelta(hours=24)
    ).count()
    
    plots = {}
    
    if not stats_df.empty:
        # График задержки
        latency_plot = go.Figure()
        latency_plot.add_trace(go.Scatter(
            x=stats_df['timestamp'],
            y=stats_df['latency_mean'],
            mode='lines+markers',
            name='Средняя задержка (мс)',
            line=dict(color='blue'),
            fill='tozeroy'
        ))
        latency_plot.add_hline(
            y=ep.sla_latency_ms,
            line_dash="dash",
            line_color="red",
            annotation_text=f"SLA: {ep.sla_latency_ms}ms"
        )
        latency_plot.update_layout(
            title="Задержка API за 7 дней",
            xaxis_title="Дата",
            yaxis_title="мс",
            template="plotly_white",
            height=400
        )
        plots['latency'] = plot(latency_plot, output_type='div', include_plotlyjs=False)

        # График доступности
        avail_plot = go.Figure()
        avail_plot.add_trace(go.Scatter(
            x=stats_df['timestamp'],
            y=stats_df['availability'] * 100,
            mode='lines+markers',
            name='Доступность (%)',
            line=dict(color='green'),
            fill='tozeroy'
        ))
        avail_plot.update_layout(
            title="Доступность API за 7 дней",
            xaxis_title="Дата",
            yaxis_title="%",
            template="plotly_white",
            height=400
        )
        plots['availability'] = plot(avail_plot, output_type='div', include_plotlyjs=False)

        # График ошибок
        error_plot = go.Figure()
        error_plot.add_trace(go.Bar(
            x=stats_df['timestamp'],
            y=stats_df['error_rate'] * 100,
            name='Частота ошибок (%)',
            marker=dict(color='orange')
        ))
        error_plot.update_layout(
            title="Частота ошибок за 7 дней",
            xaxis_title="Дата",
            yaxis_title="%",
            template="plotly_white",
            height=400
        )
        plots['errors'] = plot(error_plot, output_type='div', include_plotlyjs=False)

    context = {
        'endpoint': ep,
        'recent_measurements': recent_measurements,
        'recent_breaches': recent_breaches,
        'plots': plots,
        'stats': stats_df.tail(7).to_dict('records') if not stats_df.empty else []
    }
    return render(request, 'endpoint_detail.html', context)

@login_required
def create_project(request):
    """
    Создание нового проекта.
    
    GET: Отображает форму создания проекта
    POST: Обрабатывает отправку формы, создаёт новый проект
    
    Процесс:
    1. Получить данные (name и url) из ProjectForm
    2. Создать проект с owner=текущий пользователь
    3. Редирект на страницу проекта
    
    Доступно только для залогиненных пользователей.
    
    Args:
        request: HTTP запрос
        
    Returns:
        HttpResponse: Отображение формы или редирект на проект
    """
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.owner = request.user
            project.save()
            messages.success(request, f'Проект "{project.name}" создан!')
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm()
    return render(request, 'project_form.html', {'form': form})

@login_required
def project_detail(request, pk):
    """
    Детальный просмотр проекта.
    
    Отображает:
    - Информация о проекте (название, URL)
    - Список эндпоинтов в проекте
    - Кнопки для добавления/удаления эндпоинтов
    
    Доступно только для залогиненных пользователей.
    Пользователь может просмотреть только свои проекты.
    
    Args:
        request: HTTP запрос
        pk: ID проекта
        
    Returns:
        HttpResponse: Отображение шаблона с деталями проекта
    """
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    endpoints = project.endpoint_set.all()
    
    context = {
        'project': project,
        'endpoints': endpoints,
    }
    return render(request, 'project_detail.html', context)

@login_required
def create_endpoint(request, project_pk):
    """
    Создание нового эндпоинта в проекте.
    
    GET: Отображает форму создания эндпоинта
    POST: Обрабатывает отправку формы, создаёт новый эндпоинт
    
    Процесс:
    1. Получить проект по ID (проверить что он принадлежит пользователю)
    2. Получить данные из EndpointForm
    3. Создать эндпоинт и связать с проектом
    4. Редирект на страницу проекта
    
    Доступно только для залогиненных пользователей.
    Пользователь может создать эндпоинт только в своём проекте.
    
    Args:
        request: HTTP запрос
        project_pk: ID проекта
        
    Returns:
        HttpResponse: Отображение формы или редирект на проект
    """
    project = get_object_or_404(Project, pk=project_pk, owner=request.user)
    
    if request.method == 'POST':
        form = EndpointForm(request.POST)
        if form.is_valid():
            endpoint = form.save(commit=False)
            endpoint.project = project
            try:
                endpoint.save()
                messages.success(request, f'Эндпоинт {endpoint.method} {endpoint.path} создан!')
                return redirect('project_detail', pk=project.pk)
            except Exception as e:
                messages.error(request, f'Ошибка: {str(e)}')
    else:
        form = EndpointForm()
    
    context = {
        'form': form,
        'project': project,
    }
    return render(request, 'endpoint_form.html', context)

@login_required
def endpoint_delete(request, pk):
    """
    Удаление эндпоинта.
    
    GET: Отображает страницу подтверждения удаления
    POST: Выполняет удаление эндпоинта и всех связанных данных
    
    Процесс:
    1. Получить эндпоинт по ID (проверить что он принадлежит пользователю)
    2. Если POST → удалить эндпоинт из БД
    3. Редирект на страницу проекта
    
    Доступно только для залогиненных пользователей.
    Пользователь может удалить только свой эндпоинт.
    
    Args:
        request: HTTP запрос
        pk: ID эндпоинта
        
    Returns:
        HttpResponse: Отображение подтверждения или редирект на проект
    """
    endpoint = get_object_or_404(Endpoint, pk=pk, project__owner=request.user)
    project = endpoint.project
    
    if request.method == 'POST':
        endpoint.delete()
        messages.success(request, 'Эндпоинт удалён!')
        return redirect('project_detail', pk=project.pk)
    
    return render(request, 'endpoint_confirm_delete.html', {'endpoint': endpoint})