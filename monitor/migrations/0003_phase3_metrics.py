"""
Миграция для добавления моделей Phase 3:
- PerformanceMetrics
- SLATracking
- Report
- Webhook
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0002_schedule_alert'),
    ]

    operations = [
        migrations.CreateModel(
            name='PerformanceMetrics',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('period_start', models.DateTimeField()),
                ('period_end', models.DateTimeField()),
                ('response_time_min', models.FloatField()),
                ('response_time_max', models.FloatField()),
                ('response_time_avg', models.FloatField()),
                ('response_time_p50', models.FloatField()),
                ('response_time_p95', models.FloatField()),
                ('response_time_p99', models.FloatField()),
                ('total_requests', models.IntegerField()),
                ('successful_requests', models.IntegerField()),
                ('failed_requests', models.IntegerField()),
                ('error_rate', models.FloatField(default=0.0)),
                ('sla_breaches', models.IntegerField(default=0)),
                ('sla_compliance', models.FloatField(default=100.0)),
                ('status_2xx', models.IntegerField(default=0)),
                ('status_3xx', models.IntegerField(default=0)),
                ('status_4xx', models.IntegerField(default=0)),
                ('status_5xx', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('endpoint', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='performance_metrics', to='monitor.endpoint')),
            ],
            options={
                'ordering': ['-period_start'],
            },
        ),
        migrations.CreateModel(
            name='SLATracking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('target_sla', models.FloatField(help_text='Target SLA %')),
                ('actual_sla', models.FloatField(help_text='Actual SLA %')),
                ('sla_breached', models.BooleanField(default=False)),
                ('total_requests', models.IntegerField()),
                ('breached_requests', models.IntegerField()),
                ('average_response_time', models.FloatField()),
                ('predicted_breach', models.BooleanField(default=False)),
                ('breach_probability', models.FloatField(default=0.0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('endpoint', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sla_tracking', to='monitor.endpoint')),
            ],
            options={
                'ordering': ['-date'],
            },
        ),
        migrations.CreateModel(
            name='Report',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('report_type', models.CharField(choices=[('daily', 'Daily Report'), ('weekly', 'Weekly Report'), ('monthly', 'Monthly Report'), ('custom', 'Custom Report')], max_length=20)),
                ('format', models.CharField(choices=[('pdf', 'PDF'), ('csv', 'CSV'), ('html', 'HTML')], max_length=10)),
                ('period_start', models.DateTimeField()),
                ('period_end', models.DateTimeField()),
                ('file_path', models.FileField(blank=True, null=True, upload_to='reports/')),
                ('file_size', models.IntegerField(default=0, help_text='File size in bytes')),
                ('total_endpoints', models.IntegerField()),
                ('total_measurements', models.IntegerField()),
                ('sla_breaches', models.IntegerField()),
                ('average_sla', models.FloatField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='auth.user')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reports', to='monitor.project')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Webhook',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('webhook_type', models.CharField(choices=[('slack', 'Slack'), ('discord', 'Discord'), ('telegram', 'Telegram'), ('generic', 'Generic')], max_length=20)),
                ('url', models.URLField()),
                ('trigger_type', models.CharField(choices=[('sla_breach', 'SLA Breach'), ('endpoint_down', 'Endpoint Down'), ('error', 'Any Error'), ('all', 'All Events')], default='all', max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='webhooks', to='monitor.project')),
            ],
            options={
                'ordering': ['project', 'name'],
            },
        ),
        migrations.AddIndex(
            model_name='performancemetrics',
            index=models.Index(fields=['endpoint', 'period_start'], name='monitor_per_endpoi_idx'),
        ),
        migrations.AddIndex(
            model_name='performancemetrics',
            index=models.Index(fields=['endpoint', 'period_end'], name='monitor_per_period_idx'),
        ),
        migrations.AddIndex(
            model_name='slatracking',
            index=models.Index(fields=['endpoint', 'date'], name='monitor_sla_endpoi_idx'),
        ),
        migrations.AddIndex(
            model_name='slatracking',
            index=models.Index(fields=['sla_breached', 'date'], name='monitor_sla_breach_idx'),
        ),
        migrations.AddIndex(
            model_name='report',
            index=models.Index(fields=['project', 'report_type', 'created_at'], name='monitor_rep_project_idx'),
        ),
        migrations.AddIndex(
            model_name='report',
            index=models.Index(fields=['format', 'created_at'], name='monitor_rep_format_idx'),
        ),
        migrations.AddConstraint(
            model_name='performancemetrics',
            constraint=models.UniqueConstraint(fields=['endpoint', 'period_start', 'period_end'], name='unique_endpoint_period'),
        ),
        migrations.AddConstraint(
            model_name='slatracking',
            constraint=models.UniqueConstraint(fields=['endpoint', 'date'], name='unique_endpoint_date'),
        ),
    ]
