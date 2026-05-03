from django.db import models
from django.contrib.auth.models import User

class Project(models.Model):
    name = models.CharField(max_length=100)
    url = models.URLField(help_text="Base URL, e.g. https://api.example.com")
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Endpoint(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    method = models.CharField(max_length=10, choices=[
        ('GET', 'GET'), ('POST', 'POST'), ('PUT', 'PUT'), ('DELETE', 'DELETE')
    ])
    path = models.CharField(max_length=255, help_text="/users, /health")
    sla_latency_ms = models.PositiveIntegerField(default=500, help_text="Max acceptable latency (ms)")
    sla_error_rate = models.FloatField(default=0.05, help_text="Max error rate (e.g. 0.05 = 5%)")

    class Meta:
        unique_together = ('project', 'method', 'path')

    def __str__(self):
        return f"{self.method} {self.path} @ {self.project}"

class Measurement(models.Model):
    endpoint = models.ForeignKey(Endpoint, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    response_time_ms = models.FloatField()
    status_code = models.IntegerField()
    is_error = models.BooleanField()
    sla_breached = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.endpoint} | {self.response_time_ms}ms | {self.status_code}"