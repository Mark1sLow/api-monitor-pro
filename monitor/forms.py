from django import forms
from .models import Project, Endpoint

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'url']

class EndpointForm(forms.ModelForm):
    class Meta:
        model = Endpoint
        fields = ['method', 'path', 'sla_latency_ms', 'sla_error_rate']