"""
Экспортеры данных в различные форматы (CSV, PDF, HTML)
"""
import csv
import io
from datetime import datetime, timedelta
from django.utils import timezone
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image as RLImage
from reportlab.lib import colors
from reportlab.pdfgen import canvas
import plotly.graph_objects as go
import plotly.io as pio
from .models import Measurement, PerformanceMetrics, SLATracking
from .metrics_calculator import MetricsCalculator, SLACalculator


class CSVExporter:
    """Экспортер измерений в CSV"""
    
    @staticmethod
    def export_measurements(endpoint, period_start, period_end, response=None):
        """
        Экспортировать измерения эндпоинта в CSV
        
        Args:
            endpoint: Endpoint объект
            period_start: Начало периода
            period_end: Конец периода
            response: HttpResponse объект (если None, возвращает строку)
        
        Returns:
            HttpResponse или str с CSV данными
        """
        measurements = Measurement.objects.filter(
            endpoint=endpoint,
            timestamp__gte=period_start,
            timestamp__lt=period_end
        ).order_by('timestamp')
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Заголовок
        writer.writerow([
            'Timestamp', 'Response Time (ms)', 'Status Code',
            'Is Error', 'SLA Breached'
        ])
        
        # Данные
        for m in measurements:
            writer.writerow([
                m.timestamp.isoformat(),
                m.response_time_ms,
                m.status_code,
                'Yes' if m.is_error else 'No',
                'Yes' if m.sla_breached else 'No',
            ])
        
        csv_data = output.getvalue()
        
        if response is None:
            return csv_data
        
        response['Content-Type'] = 'text/csv'
        response['Content-Disposition'] = f'attachment; filename="measurements_{endpoint.path.replace("/", "_")}_{period_start.date()}.csv"'
        response.write(csv_data)
        return response
    
    @staticmethod
    def export_metrics(project, period_start, period_end):
        """
        Экспортировать метрики проекта в CSV
        
        Returns:
            str с CSV данными
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Заголовок
        writer.writerow([
            'Endpoint', 'Method', 'Path',
            'Total Requests', 'Successful', 'Failed',
            'Error Rate (%)', 'Avg Response (ms)', 'P95 Response (ms)',
            'P99 Response (ms)', 'SLA Compliance (%)', 'SLA Breaches'
        ])
        
        # Метрики для каждого эндпоинта
        for endpoint in project.endpoint_set.all():
            metrics = MetricsCalculator.calculate_endpoint_metrics(endpoint, period_start, period_end)
            if metrics:
                writer.writerow([
                    str(endpoint),
                    endpoint.method,
                    endpoint.path,
                    metrics.total_requests,
                    metrics.successful_requests,
                    metrics.failed_requests,
                    f"{metrics.error_rate:.2f}",
                    f"{metrics.response_time_avg:.2f}",
                    f"{metrics.response_time_p95:.2f}",
                    f"{metrics.response_time_p99:.2f}",
                    f"{metrics.sla_compliance:.2f}",
                    metrics.sla_breaches,
                ])
        
        return output.getvalue()
    
    @staticmethod
    def export_sla_tracking(endpoint, start_date, end_date):
        """
        Экспортировать SLA tracking в CSV
        
        Returns:
            str с CSV данными
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Заголовок
        writer.writerow([
            'Date', 'Target SLA (%)', 'Actual SLA (%)',
            'Compliant', 'Total Requests', 'Breached Requests',
            'Average Response Time (ms)'
        ])
        
        # Данные
        sla_records = SLATracking.objects.filter(
            endpoint=endpoint,
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')
        
        for record in sla_records:
            writer.writerow([
                record.date.isoformat(),
                f"{record.target_sla:.2f}",
                f"{record.actual_sla:.2f}",
                'Yes' if not record.sla_breached else 'No',
                record.total_requests,
                record.breached_requests,
                f"{record.average_response_time:.2f}",
            ])
        
        return output.getvalue()


class PDFReportGenerator:
    """Генератор PDF отчетов"""
    
    @staticmethod
    def generate_report(project, period_start, period_end, response=None):
        """
        Генерировать комплексный PDF отчет по проекту
        
        Args:
            project: Project объект
            period_start: Начало периода
            period_end: Конец периода
            response: HttpResponse объект (если None, возвращает bytes)
        
        Returns:
            HttpResponse или bytes с PDF данными
        """
        # Создать PDF документ
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        
        # Стили
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=30,
            alignment=1,
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=12,
            spaceBefore=12,
        )
        
        # Подготовить содержимое
        content = []
        
        # Заголовок
        title = f"API Monitor Report - {project.name}"
        content.append(Paragraph(title, title_style))
        content.append(Spacer(1, 0.3 * inch))
        
        # Метаинформация
        meta_data = [
            ['Project:', project.name],
            ['Report Period:', f"{period_start.date()} to {period_end.date()}"],
            ['Generated:', timezone.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['Endpoints:', str(project.endpoint_set.count())],
        ]
        
        meta_table = Table(meta_data, colWidths=[2*inch, 4*inch])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        
        content.append(meta_table)
        content.append(Spacer(1, 0.3 * inch))
        
        # Сводка по проекту
        content.append(Paragraph("Project Summary", heading_style))
        
        metrics = MetricsCalculator.calculate_project_metrics(project, period_start, period_end)
        
        summary_data = [
            ['Metric', 'Value'],
            ['Total Requests', str(metrics['total_requests'])],
            ['Total SLA Breaches', str(metrics['total_sla_breaches'])],
            ['Average Response Time', f"{metrics['avg_response_time']:.2f} ms"],
            ['Average Error Rate', f"{metrics['avg_error_rate']:.2f}%"],
            ['Average SLA Compliance', f"{metrics['avg_sla_compliance']:.2f}%"],
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ]))
        
        content.append(summary_table)
        content.append(Spacer(1, 0.3 * inch))
        
        # Детали по эндпоинтам
        content.append(Paragraph("Endpoints Details", heading_style))
        
        endpoints_data = [
            ['Endpoint', 'Requests', 'Errors', 'Error %', 'Avg Time (ms)', 'SLA Compliance'],
        ]
        
        for endpoint in project.endpoint_set.all()[:10]: 
            endpoint_metrics = MetricsCalculator.calculate_endpoint_metrics(endpoint, period_start, period_end)
            if endpoint_metrics:
                endpoints_data.append([
                    f"{endpoint.method} {endpoint.path}",
                    str(endpoint_metrics.total_requests),
                    str(endpoint_metrics.failed_requests),
                    f"{endpoint_metrics.error_rate:.2f}%",
                    f"{endpoint_metrics.response_time_avg:.2f}",
                    f"{endpoint_metrics.sla_compliance:.2f}%",
                ])
        
        endpoints_table = Table(endpoints_data, colWidths=[2*inch, 1*inch, 0.8*inch, 0.8*inch, 1*inch, 1.2*inch])
        endpoints_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ]))
        
        content.append(endpoints_table)
        
        # Сборка PDF
        doc.build(content)
        
        pdf_data = buffer.getvalue()
        buffer.close()
        
        if response is None:
            return pdf_data
        
        response['Content-Type'] = 'application/pdf'
        response['Content-Disposition'] = f'attachment; filename="report_{project.name.replace(" ", "_")}_{period_start.date()}.pdf"'
        response.write(pdf_data)
        return response
    
    @staticmethod
    def generate_endpoint_report(endpoint, period_start, period_end):
        """
        Генерировать детальный PDF отчет по эндпоинту
        
        Returns:
            bytes с PDF данными
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=20,
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=10,
        )
        
        content = []
        
        # Заголовок
        title = f"Endpoint Report - {endpoint.method} {endpoint.path}"
        content.append(Paragraph(title, title_style))
        content.append(Spacer(1, 0.2 * inch))
        
        # Метрики
        metrics = MetricsCalculator.calculate_endpoint_metrics(endpoint, period_start, period_end)
        if metrics:
            content.append(Paragraph("Performance Metrics", heading_style))
            
            metrics_data = [
                ['Response Time', f"{metrics.response_time_avg:.2f} ms (avg)"],
                ['P95', f"{metrics.response_time_p95:.2f} ms"],
                ['P99', f"{metrics.response_time_p99:.2f} ms"],
                ['Min/Max', f"{metrics.response_time_min:.2f} / {metrics.response_time_max:.2f} ms"],
                ['Total Requests', str(metrics.total_requests)],
                ['Failed Requests', f"{metrics.failed_requests} ({metrics.error_rate:.2f}%)"],
                ['SLA Compliance', f"{metrics.sla_compliance:.2f}%"],
                ['SLA Breaches', str(metrics.sla_breaches)],
            ]
            
            metrics_table = Table(metrics_data, colWidths=[3*inch, 2*inch])
            metrics_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ]))
            
            content.append(metrics_table)
            content.append(Spacer(1, 0.2 * inch))
            
            content.append(Paragraph("Status Code Distribution", heading_style))
            
            status_data = [
                ['Status Code', 'Count'],
                ['2xx', str(metrics.status_2xx)],
                ['3xx', str(metrics.status_3xx)],
                ['4xx', str(metrics.status_4xx)],
                ['5xx', str(metrics.status_5xx)],
            ]
            
            status_table = Table(status_data, colWidths=[2*inch, 1*inch])
            status_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            
            content.append(status_table)
        
        doc.build(content)
        
        pdf_data = buffer.getvalue()
        buffer.close()
        
        return pdf_data


class HTMLReportGenerator:
    """Генератор HTML отчетов"""
    
    @staticmethod
    def generate_report(project, period_start, period_end):
        """
        Генерировать HTML отчет
        
        Returns:
            str с HTML
        """
        metrics = MetricsCalculator.calculate_project_metrics(project, period_start, period_end)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>API Monitor Report - {project.name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #1f77b4; }}
                h2 {{ color: #1f77b4; border-bottom: 2px solid #1f77b4; padding-bottom: 10px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th {{ background-color: #1f77b4; color: white; padding: 10px; text-align: left; }}
                td {{ border: 1px solid #ddd; padding: 10px; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .metric-card {{ background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                .warning {{ color: #ff6b6b; font-weight: bold; }}
                .success {{ color: #51cf66; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>API Monitor Report - {project.name}</h1>
            
            <div class="metric-card">
                <h3>Report Period</h3>
                <p>{period_start.date()} to {period_end.date()}</p>
                <p>Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <h2>Project Summary</h2>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                </tr>
                <tr>
                    <td>Total Requests</td>
                    <td>{metrics['total_requests']}</td>
                </tr>
                <tr>
                    <td>Total SLA Breaches</td>
                    <td class="warning">{metrics['total_sla_breaches']}</td>
                </tr>
                <tr>
                    <td>Average Response Time</td>
                    <td>{metrics['avg_response_time']:.2f} ms</td>
                </tr>
                <tr>
                    <td>Average Error Rate</td>
                    <td>{metrics['avg_error_rate']:.2f}%</td>
                </tr>
                <tr>
                    <td>Average SLA Compliance</td>
                    <td class="success">{metrics['avg_sla_compliance']:.2f}%</td>
                </tr>
            </table>
            
            <h2>Endpoints</h2>
            <table>
                <tr>
                    <th>Endpoint</th>
                    <th>Requests</th>
                    <th>Errors</th>
                    <th>Error Rate</th>
                    <th>Avg Time (ms)</th>
                    <th>SLA Compliance</th>
                </tr>
        """
        
        for endpoint in project.endpoint_set.all():
            endpoint_metrics = MetricsCalculator.calculate_endpoint_metrics(endpoint, period_start, period_end)
            if endpoint_metrics:
                html += f"""
                <tr>
                    <td>{endpoint.method} {endpoint.path}</td>
                    <td>{endpoint_metrics.total_requests}</td>
                    <td>{endpoint_metrics.failed_requests}</td>
                    <td>{endpoint_metrics.error_rate:.2f}%</td>
                    <td>{endpoint_metrics.response_time_avg:.2f}</td>
                    <td class="{'warning' if endpoint_metrics.sla_compliance < 100 else 'success'}">{endpoint_metrics.sla_compliance:.2f}%</td>
                </tr>
                """
        
        html += """
            </table>
        </body>
        </html>
        """
        
        return html
