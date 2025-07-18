from django.db import models
from django.utils import timezone


class Conversation(models.Model):
    session_key = models.CharField(max_length=40, db_index=True)
    started_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'Conv {self.pk} ({self.session_key})'


class Message(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]

    conversation = models.ForeignKey(Conversation,
                                     on_delete=models.CASCADE,
                                     related_name='messages')
    role = models.CharField(choices=ROLE_CHOICES, max_length=10)
    content = models.TextField(null=True, blank=True)
    cards_json = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'[{self.role}] {self.content or '(cards)'}'


class Anime(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        db_table = 'anime'
        managed = False
