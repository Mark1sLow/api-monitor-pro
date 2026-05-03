from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q
from .models import Project, Endpoint, Measurement
from .forms import ProjectForm, EndpointForm
from .utils import calculate_sli_stats, send_sla_breach_notification
import plotly.graph_objs as go
from plotly.offline import plot
from datetime import datetime, timedelta

@login_required
def dashboard(request):
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
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    endpoints = project.endpoint_set.all()
    
    context = {
        'project': project,
        'endpoints': endpoints,
    }
    return render(request, 'project_detail.html', context)

@login_required
def create_endpoint(request, project_pk):
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
    endpoint = get_object_or_404(Endpoint, pk=pk, project__owner=request.user)
    project = endpoint.project
    
    if request.method == 'POST':
        endpoint.delete()
        messages.success(request, 'Эндпоинт удалён!')
        return redirect('project_detail', pk=project.pk)
    
    return render(request, 'endpoint_confirm_delete.html', {'endpoint': endpoint})