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
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Count, Q, Avg
from django.views.decorators.http import require_http_methods
from .models import (
    Project, Endpoint, Measurement, Alert, Schedule,
    PerformanceMetrics, SLATracking, Report
)
from .forms import ProjectForm, EndpointForm, LoginForm, RegisterForm
from .utils import calculate_sli_stats
from .metrics_calculator import MetricsCalculator, SLACalculator
from .forecast import SLAForecaster
from .exporters import CSVExporter, PDFReportGenerator, HTMLReportGenerator
import plotly.graph_objs as go
from plotly.offline import plot
from datetime import datetime, timedelta
import json


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


@login_required
def alerts_list(request):
    """
    Просмотр истории оповещений.
    
    Отображает все оповещения (Alert) пользователя с фильтрацией по:
    - Типу оповещения (sla_breach, endpoint_down, error)
    - Проекту
    - Дате
    
    Доступно только для залогиненных пользователей.
    Пользователь видит только оповещения своих проектов.
    
    Args:
        request: HTTP запрос
        
    Returns:
        HttpResponse: Отображение списка оповещений
    """
    projects = Project.objects.filter(owner=request.user)
    alerts = Alert.objects.filter(project__in=projects)
    
    # Фильтрация по типу
    alert_type = request.GET.get('type')
    if alert_type:
        alerts = alerts.filter(alert_type=alert_type)
    
    # Фильтрация по проекту
    project_id = request.GET.get('project')
    if project_id:
        alerts = alerts.filter(project_id=project_id)
    
    # Фильтрация по дате
    days = request.GET.get('days', '7')
    try:
        days = int(days)
        alerts = alerts.filter(created_at__gte=datetime.now() - timedelta(days=days))
    except ValueError:
        pass
    
    # Пагинация
    page = request.GET.get('page', 1)
    from django.core.paginator import Paginator
    paginator = Paginator(alerts, 50)
    alerts = paginator.get_page(page)
    
    context = {
        'alerts': alerts,
        'projects': projects,
        'selected_type': alert_type,
        'selected_project': project_id,
        'days': days,
    }
    return render(request, 'alerts_list.html', context)


@login_required
def alert_mark_read(request, pk):
    """Отмечает оповещение как прочитанное"""
    alert = get_object_or_404(Alert, pk=pk, project__owner=request.user)
    alert.is_read = True
    alert.save()
    
    return redirect('alerts_list')


@login_required
def schedule_list(request):
    """
    Просмотр и управление расписаниями проверок.
    
    Отображает расписания всех проектов пользователя
    с возможностью включить/отключить и изменить интервал.
    
    Доступно только для залогиненных пользователей.
    
    Args:
        request: HTTP запрос
        
    Returns:
        HttpResponse: Отображение списка расписаний
    """
    projects = Project.objects.filter(owner=request.user)
    schedules = Schedule.objects.filter(project__in=projects)
    
    context = {
        'schedules': schedules,
        'projects': projects,
    }
    return render(request, 'schedule_list.html', context)


@login_required
def schedule_update(request, pk):
    """Обновление расписания проверок"""
    schedule = get_object_or_404(Schedule, pk=pk, project__owner=request.user)
    
    if request.method == 'POST':
        interval = request.POST.get('interval_minutes')
        is_active = request.POST.get('is_active') == 'on'
        
        schedule.interval_minutes = interval
        schedule.is_active = is_active
        schedule.save()
        
        # Перезагружаем расписание в scheduler
        from .scheduler import load_schedules
        load_schedules()
        
        messages.success(request, 'Расписание обновлено!')
        return redirect('schedule_list')
    
    context = {'schedule': schedule}
    return render(request, 'schedule_form.html', context)


# Расширенные метрики

@login_required
def endpoint_metrics(request, pk):
    """
    Детальный просмотр метрик эндпоинта с расширённой аналитикой.
    
    Отображает:
    - Процентили (P50, P95, P99)
    - Минимальное/максимальное время отклика
    - Распределение статус-кодов
    - Тренд SLA за последние 30 дней
    - График распределения времени ответа
    """
    endpoint = get_object_or_404(Endpoint, pk=pk, project__owner=request.user)
    
    # Период по умолчанию 
    days = int(request.GET.get('days', 7))
    period_end = timezone.now()
    period_start = period_end - timedelta(days=days)
    
    # Рассчитать метрики
    metrics = MetricsCalculator.calculate_endpoint_metrics(endpoint, period_start, period_end)
    
    if not metrics:
        messages.warning(request, 'Недостаточно данных для расчета метрик')
        return redirect('endpoint_detail', pk=pk)
    
    # Получить SLA тренд
    sla_trend = SLACalculator.get_sla_trend(endpoint, days=30)
    sla_stats = SLACalculator.get_sla_statistics(endpoint, days=30)
    
    # Получить распределение времени ответа
    measurements = Measurement.objects.filter(
        endpoint=endpoint,
        timestamp__gte=period_start,
        timestamp__lt=period_end
    ).order_by('-response_time_ms')
    
    response_times = list(measurements.values_list('response_time_ms', flat=True))
    
    # График распределения времени ответа
    if response_times:
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=response_times,
            nbinsx=50,
            name='Response Time Distribution',
            marker_color='#1f77b4'
        ))
        fig.update_layout(
            title='Distribution of Response Times',
            xaxis_title='Response Time (ms)',
            yaxis_title='Frequency',
            height=400,
            template='plotly_white'
        )
        distribution_plot = plot(fig, output_type='div', include_plotlyjs=False)
    else:
        distribution_plot = None
    
    # График SLA тренда
    if sla_trend:
        dates = [item[0] for item in sla_trend]
        slas = [item[1] for item in sla_trend]
        breached = [item[2] for item in sla_trend]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates,
            y=slas,
            mode='lines+markers',
            name='SLA %',
            line=dict(color='#1f77b4'),
            fill='tozeroy'
        ))
        
        target_sla = (1 - endpoint.sla_error_rate) * 100
        fig.add_hline(y=target_sla, line_dash="dash", line_color="red", 
                     annotation_text=f"Target: {target_sla:.1f}%")
        
        fig.update_layout(
            title='SLA Trend (30 days)',
            xaxis_title='Date',
            yaxis_title='SLA %',
            height=400,
            template='plotly_white'
        )
        sla_trend_plot = plot(fig, output_type='div', include_plotlyjs=False)
    else:
        sla_trend_plot = None
    
    context = {
        'endpoint': endpoint,
        'metrics': metrics,
        'sla_stats': sla_stats,
        'sla_trend_plot': sla_trend_plot,
        'distribution_plot': distribution_plot,
        'days': days,
    }
    return render(request, 'endpoint_metrics.html', context)


@login_required
def project_metrics(request, pk):
    """
    Просмотр агрегированных метрик по проекту.
    
    Отображает:
    - Метрики по всем эндпоинтам
    - Средние показатели (время ответа, ошибки, SLA)
    - Сравнение эндпоинтов
    - Графики трендов
    """
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    
    # Период по умолчанию
    days = int(request.GET.get('days', 7))
    period_end = timezone.now()
    period_start = period_end - timedelta(days=days)
    
    # Рассчитать метрики по проекту
    metrics = MetricsCalculator.calculate_project_metrics(project, period_start, period_end)
    
    # График сравнения эндпоинтов по времени ответа
    endpoints_data = []
    response_times = []
    endpoint_names = []
    
    for endpoint_metrics in metrics.get('endpoints_metrics', []):
        endpoints_data.append({
            'endpoint': endpoint_metrics.endpoint,
            'metrics': endpoint_metrics,
        })
        response_times.append(endpoint_metrics.response_time_avg)
        endpoint_names.append(f"{endpoint_metrics.endpoint.method} {endpoint_metrics.endpoint.path}")
    
    if endpoints_data:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=endpoint_names,
            y=response_times,
            marker_color='#1f77b4'
        ))
        fig.update_layout(
            title='Average Response Time by Endpoint',
            xaxis_title='Endpoint',
            yaxis_title='Response Time (ms)',
            height=400,
            template='plotly_white'
        )
        comparison_plot = plot(fig, output_type='div', include_plotlyjs=False)
    else:
        comparison_plot = None
    
    context = {
        'project': project,
        'metrics': metrics,
        'endpoints_data': endpoints_data,
        'comparison_plot': comparison_plot,
        'days': days,
    }
    return render(request, 'project_metrics.html', context)


# SLA Трекинг 

@login_required
def sla_dashboard(request):
    """
    Главная панель управления SLA.
    
    Отображает:
    - Статус SLA для всех эндпоинтов
    - Прогноз нарушений на ближайшие дни
    - Статистика по дням с нарушениями
    - Аномалии в SLA
    """
    projects = Project.objects.filter(owner=request.user)
    
    # Получить прогнозы по всем проектам
    forecast_data = {}
    all_at_risk = []
    
    for project in projects:
        summary = SLAForecaster.get_forecast_summary(project, days_ahead=1)
        forecast_data[project.id] = summary
        all_at_risk.extend([p['endpoint'] for p in summary['high_risk_endpoints']])
    
    context = {
        'projects': projects,
        'forecast_data': forecast_data,
        'at_risk_count': len(all_at_risk),
        'at_risk_endpoints': all_at_risk[:10],  # Top 10
    }
    return render(request, 'sla_dashboard.html', context)


@login_required
def endpoint_sla_history(request, pk):
    """
    История SLA эндпоинта за период.
    
    Отображает:
    - Таблицу с дневным SLA
    - График тренда SLA
    - Статистику по соответствию SLA
    """
    endpoint = get_object_or_404(Endpoint, pk=pk, project__owner=request.user)
    
    # Получить SLA историю
    days = int(request.GET.get('days', 30))
    today = timezone.now().date()
    start_date = today - timedelta(days=days)
    
    sla_records = SLATracking.objects.filter(
        endpoint=endpoint,
        date__gte=start_date,
        date__lte=today
    ).order_by('-date')
    
    # Статистика
    stats = SLACalculator.get_sla_statistics(endpoint, days=days)
    
    # График
    if sla_records.exists():
        dates = [r.date for r in reversed(list(sla_records))]
        sla_values = [r.actual_sla for r in reversed(list(sla_records))]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates,
            y=sla_values,
            mode='lines+markers',
            name='SLA %',
            line=dict(color='#1f77b4'),
            fill='tozeroy'
        ))
        
        target_sla = (1 - endpoint.sla_error_rate) * 100
        fig.add_hline(y=target_sla, line_dash="dash", line_color="red",
                     annotation_text=f"Target: {target_sla:.1f}%")
        
        fig.update_layout(
            title=f'SLA History - {endpoint.method} {endpoint.path}',
            xaxis_title='Date',
            yaxis_title='SLA %',
            height=400,
            template='plotly_white'
        )
        sla_plot = plot(fig, output_type='div', include_plotlyjs=False)
    else:
        sla_plot = None
    
    context = {
        'endpoint': endpoint,
        'sla_records': sla_records,
        'stats': stats,
        'sla_plot': sla_plot,
        'days': days,
    }
    return render(request, 'sla_history.html', context)


@login_required
def predict_sla_breach(request, pk):
    """
    Просмотр прогноза нарушения SLA для эндпоинта.
    
    Отображает:
    - Вероятность нарушения
    - Тренд (улучшается/ухудшается/стабильно)
    - Рекомендации
    """
    endpoint = get_object_or_404(Endpoint, pk=pk, project__owner=request.user)
    
    # Получить прогноз
    prediction = SLAForecaster.predict_breach(endpoint, forecast_days=1)
    
    # Получить аномалии
    anomalies = SLAForecaster.get_anomalies(endpoint, window_size=7)
    
    context = {
        'endpoint': endpoint,
        'prediction': prediction,
        'anomalies': anomalies,
    }
    return render(request, 'sla_forecast.html', context)


# Отчеты

@login_required
def reports_list(request):
    """Список всех сгенерированных отчетов"""
    projects = Project.objects.filter(owner=request.user)
    reports = Report.objects.filter(project__in=projects).order_by('-created_at')
    
    # Фильтрация по типу
    report_type = request.GET.get('type')
    if report_type:
        reports = reports.filter(report_type=report_type)
    
    # Фильтрация по проекту
    project_id = request.GET.get('project')
    if project_id:
        reports = reports.filter(project_id=project_id)
    
    # Пагинация
    from django.core.paginator import Paginator
    page = request.GET.get('page', 1)
    paginator = Paginator(reports, 20)
    reports = paginator.get_page(page)
    
    context = {
        'reports': reports,
        'projects': projects,
        'selected_type': report_type,
        'selected_project': project_id,
    }
    return render(request, 'reports_list.html', context)


@login_required
def generate_report(request, project_id):
    """Генерировать отчет"""
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    
    if request.method == 'POST':
        report_type = request.POST.get('report_type', 'daily')
        format_type = request.POST.get('format', 'pdf')
        
        # Определить период
        if report_type == 'daily':
            period_end = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            period_start = period_end - timedelta(days=1)
        elif report_type == 'weekly':
            period_end = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            period_start = period_end - timedelta(days=7)
        else:
            period_end = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            period_start = period_end - timedelta(days=30)
        
        try:
            if format_type == 'pdf':
                pdf_data = PDFReportGenerator.generate_report(project, period_start, period_end)
                
                response = HttpResponse(pdf_data, content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="report_{project.name.replace(" ", "_")}_{timezone.now().date()}.pdf"'
                
                # Сохранить отчет в БД
                metrics = MetricsCalculator.calculate_project_metrics(project, period_start, period_end)
                Report.objects.create(
                    project=project,
                    report_type=report_type,
                    format='pdf',
                    period_start=period_start,
                    period_end=period_end,
                    total_endpoints=metrics['total_endpoints'],
                    total_measurements=metrics['total_requests'],
                    sla_breaches=metrics['total_sla_breaches'],
                    average_sla=metrics['avg_sla_compliance'],
                    file_size=len(pdf_data),
                    created_by=request.user,
                )
                
                return response
            
            elif format_type == 'html':
                html_data = HTMLReportGenerator.generate_report(project, period_start, period_end)
                return HttpResponse(html_data, content_type='text/html')
        
        except Exception as e:
            messages.error(request, f'Error generating report: {str(e)}')
    
    context = {
        'project': project,
    }
    return render(request, 'generate_report.html', context)


# CSV Экспорт

@login_required
@require_http_methods(["GET"])
def export_measurements_csv(request, pk):
    """Экспортировать измерения эндпоинта в CSV"""
    endpoint = get_object_or_404(Endpoint, pk=pk, project__owner=request.user)
    
    days = int(request.GET.get('days', 7))
    period_end = timezone.now()
    period_start = period_end - timedelta(days=days)
    
    csv_data = CSVExporter.export_measurements(endpoint, period_start, period_end)
    
    response = HttpResponse(csv_data, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="measurements_{endpoint.path.replace("/", "_")}_{timezone.now().date()}.csv"'
    
    return response


@login_required
@require_http_methods(["GET"])
def export_metrics_csv(request, project_id):
    """Экспортировать метрики проекта в CSV"""
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    
    days = int(request.GET.get('days', 7))
    period_end = timezone.now()
    period_start = period_end - timedelta(days=days)
    
    csv_data = CSVExporter.export_metrics(project, period_start, period_end)
    
    response = HttpResponse(csv_data, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="metrics_{project.name.replace(" ", "_")}_{timezone.now().date()}.csv"'
    
    return response


@login_required
@require_http_methods(["GET"])
def export_sla_csv(request, pk):
    """Экспортировать SLA tracking в CSV"""
    endpoint = get_object_or_404(Endpoint, pk=pk, project__owner=request.user)
    
    days = int(request.GET.get('days', 30))
    today = timezone.now().date()
    start_date = today - timedelta(days=days)
    
    csv_data = CSVExporter.export_sla_tracking(endpoint, start_date, today)
    
    response = HttpResponse(csv_data, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="sla_{endpoint.path.replace("/", "_")}_{today}.csv"'
    
    return response


# API для графиков

@login_required
@require_http_methods(["GET"])
def api_endpoint_metrics(request, pk):
    """API endpoint для получения метрик эндпоинта в JSON"""
    endpoint = get_object_or_404(Endpoint, pk=pk, project__owner=request.user)
    
    days = int(request.GET.get('days', 7))
    period_end = timezone.now()
    period_start = period_end - timedelta(days=days)
    
    metrics = MetricsCalculator.calculate_endpoint_metrics(endpoint, period_start, period_end)
    
    if not metrics:
        return JsonResponse({'error': 'No data'}, status=404)
    
    return JsonResponse({
        'endpoint': str(endpoint),
        'response_time_min': metrics.response_time_min,
        'response_time_max': metrics.response_time_max,
        'response_time_avg': metrics.response_time_avg,
        'response_time_p50': metrics.response_time_p50,
        'response_time_p95': metrics.response_time_p95,
        'response_time_p99': metrics.response_time_p99,
        'total_requests': metrics.total_requests,
        'failed_requests': metrics.failed_requests,
        'error_rate': metrics.error_rate,
        'sla_compliance': metrics.sla_compliance,
        'sla_breaches': metrics.sla_breaches,
    })


@login_required
@require_http_methods(["GET"])
def api_sla_forecast(request, pk):
    """API endpoint для получения прогноза SLA в JSON"""
    endpoint = get_object_or_404(Endpoint, pk=pk, project__owner=request.user)
    
    days = int(request.GET.get('days', 1))
    prediction = SLAForecaster.predict_breach(endpoint, forecast_days=days)
    
    return JsonResponse({
        'endpoint': str(endpoint),
        'predicted_breach': prediction['predicted_breach'],
        'breach_probability': prediction['breach_probability'],
        'predicted_sla': prediction.get('predicted_sla'),
        'target_sla': prediction.get('target_sla'),
        'trend': prediction.get('trend'),
        'confidence': prediction['confidence'],
    })