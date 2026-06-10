"""
Django signals для автоматического создания связанных объектов

Этот модуль содержит signals для:
- Автоматического создания Schedule при создании Project
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Project, Schedule


@receiver(post_save, sender=Project)
def create_schedule(sender, instance, created, **kwargs):
    """Автоматически создаёт расписание при создании нового проекта"""
    if created:
        Schedule.objects.get_or_create(
            project=instance,
            defaults={'interval_minutes': '5', 'is_active': True}
        )
