"""
Формы приложения API Monitor Pro

Этот модуль содержит все формы для регистрации, входа и управления проектами.
Все формы используют Bootstrap CSS классы для стилизации.

Автор: API Monitor Pro Team
Версия: 1.0
"""

from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import re
from .models import Project, Endpoint


class RegisterForm(forms.ModelForm):
    """
    Форма регистрации нового пользователя.
    
    Включает валидацию пароля с требованиями безопасности:
    - Минимум 8 символов
    - Минимум одна прописная буква (A-Z)
    - Минимум одна строчная буква (a-z)
    - Минимум одна цифра (0-9)
    - Минимум один спецсимвол (!@#$%^&*)
    
    Также проверяет уникальность username и email.
    """
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Пароль'}),
        label='Пароль',
        help_text='Мин. 8 символов, прописные, строчные буквы, цифры и спецсимволы'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Подтвердите пароль'}),
        label='Подтвердите пароль'
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя пользователя'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Фамилия'}),
        }
        labels = {
            'username': 'Имя пользователя',
            'email': 'Email',
            'first_name': 'Имя',
            'last_name': 'Фамилия',
        }
    
    def validate_password_strength(self, password):
        """
        Проверяет надёжность пароля и требует:
        - Минимум 8 символов
        - Прописные буквы (A-Z)
        - Строчные буквы (a-z)
        - Цифры (0-9)
        - Спецсимволы (!@#$%^&*)
        
        Args:
            password (str): Пароль для проверки
            
        Raises:
            ValidationError: Если пароль не соответствует требованиям
        """
        errors = []
        
        if len(password) < 8:
            errors.append('Минимум 8 символов')
        if not re.search(r'[A-Z]', password):
            errors.append('Должна быть прописная буква (A-Z)')
        if not re.search(r'[a-z]', password):
            errors.append('Должна быть строчная буква (a-z)')
        if not re.search(r'[0-9]', password):
            errors.append('Должна быть цифра (0-9)')
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'\",./<>?\|`~]', password):
            errors.append('Должен быть спецсимвол (!@#$%^&*)')
        
        if errors:
            raise ValidationError(errors)
    
    def clean_username(self):
        """
        Проверяет, что username уникален в БД.
        
        Returns:
            str: Уникальное имя пользователя
            
        Raises:
            ValidationError: Если пользователь с таким username уже существует
        """
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError('Пользователь с таким логином уже существует')
        return username
    
    def clean_email(self):
        """
        Проверяет, что email уникален в БД.
        
        Returns:
            str: Уникальный email
            
        Raises:
            ValidationError: Если пользователь с таким email уже существует
        """
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Пользователь с таким email уже существует')
        return email
    
    def clean(self):
        """
        Переопределённый метод clean для валидации на уровне формы.
        
        Проверяет:
        1. Совпадение паролей
        2. Надёжность пароля
        
        Returns:
            dict: Очищенные данные формы
            
        Raises:
            ValidationError: Если пароли не совпадают или пароль ненадёжный
        """
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm:
            if password != password_confirm:
                raise ValidationError('Пароли не совпадают')
            try:
                self.validate_password_strength(password)
            except ValidationError as e:
                self.add_error('password', e)
        
        return cleaned_data


class LoginForm(forms.Form):
    """
    Простая форма входа с проверкой username и password.
    
    Поля:
        username: Имя пользователя (max 150 символов)
        password: Пароль
        
    Используется вместе с методом authenticate() из django.contrib.auth
    для проверки учётных данных пользователя.
    """
    username = forms.CharField(
        max_length=150,
        label='Имя пользователя',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя пользователя'})
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Пароль'})
    )


class ProjectForm(forms.ModelForm):
    """
    Форма для создания и редактирования проекта.
    
    Поля:
        name: Название проекта (строка)
        url: Base URL для мониторинга (URL)
        
    Проект связывается с текущим пользователем через owner field.
    """
    class Meta:
        model = Project
        fields = ['name', 'url']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название проекта'}),
            'url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://api.example.com'}),
        }
        labels = {
            'name': 'Название проекта',
            'url': 'Base URL API',
        }


class EndpointForm(forms.ModelForm):
    """
    Форма для создания и редактирования API эндпоинта.
    
    Поля:
        method: HTTP метод (GET, POST, PUT, DELETE и т.д.)
        path: Путь к эндпоинту (например /api/users)
        sla_latency_ms: SLA по времени отклика в миллисекундах
        sla_error_rate: SLA по проценту ошибок (0-1)
        
    Эндпоинт связывается с проектом через project field.
    """
    class Meta:
        model = Endpoint
        fields = ['method', 'path', 'sla_latency_ms', 'sla_error_rate']
        widgets = {
            'method': forms.Select(attrs={'class': 'form-control'}),
            'path': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '/api/users'}),
            'sla_latency_ms': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '200'}),
            'sla_error_rate': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.05', 'step': '0.01'}),
        }
        labels = {
            'method': 'HTTP метод',
            'path': 'Path',
            'sla_latency_ms': 'SLA Latency (мс)',
            'sla_error_rate': 'SLA Error Rate (%)',
        }