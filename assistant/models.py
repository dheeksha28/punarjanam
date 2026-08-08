import uuid
from django.db import models
from patients.models import Patient


class ChatSession(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='chat_sessions')
    title = models.CharField(max_length=100, default='New chat')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=[('user', 'User'), ('ai', 'AI')])
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


class DoctorMessage(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='doctor_messages')
    question = models.TextField()
    reply = models.TextField(blank=True)
    is_replied = models.BooleanField(default=False)
    reply_token = models.CharField(max_length=40, unique=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    replied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']