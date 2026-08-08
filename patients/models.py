import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, datetime


class Patient(models.Model):
    user_account = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='patient_profile')
    admission_id = models.CharField(max_length=20, unique=True, blank=True)
    doctor_name = models.CharField(max_length=200, blank=True)
    doctor_email = models.EmailField(blank=True)
    name = models.CharField(max_length=200)
    age = models.PositiveIntegerField()
    gender = models.CharField(
        max_length=10,
        choices=[
            ('M', 'Male'),
            ('F', 'Female'),
            ('O', 'Other'),
        ],
    )
    diagnosis = models.CharField(max_length=300)
    contact_number = models.CharField(max_length=15, blank=True)
    hanuman_chalisa_enabled = models.BooleanField(default=False)
    hanuman_chalisa_time = models.TimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.admission_id:
            self.admission_id = uuid.uuid4().hex[:8].upper()
        if not self.user_account:
            username = f"patient_{self.admission_id}"
            user = User.objects.create_user(username=username, password=self.admission_id)
            self.user_account = user
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Treatment(models.Model):
    TREATMENT_TYPES = [
        ('chemo', 'Chemotherapy'),
        ('immuno', 'Immunotherapy'),
        ('other', 'Other'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='treatments')
    treatment_name = models.CharField(max_length=200)
    treatment_type = models.CharField(max_length=10, choices=TREATMENT_TYPES, default='other')
    total_sessions = models.PositiveIntegerField(default=1)
    completed_sessions = models.PositiveIntegerField(default=0)
    date_administered = models.DateField()
    next_session_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.treatment_name} - {self.patient.name}"

    def sessions_remaining(self):
        return self.total_sessions - self.completed_sessions

    def progress_percent(self):
        if self.total_sessions == 0:
            return 0
        return int((self.completed_sessions / self.total_sessions) * 100)

    def is_overdue(self):
        if self.next_session_date:
            return self.next_session_date < timezone.now().date()
        return False

    def is_due_soon(self):
        if self.next_session_date:
            today = timezone.now().date()
            return today <= self.next_session_date <= today + timedelta(days=3)
        return False


class Medicine(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medicines')
    medicine_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100, blank=True)
    reminder_time = models.TimeField(help_text="First dose time of the day")
    frequency_hours = models.PositiveIntegerField(default=24, help_text="Repeat every X hours (e.g. 1, 2, 4, 6, 24)")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.medicine_name} - {self.patient.name}"

    def schedule_times(self):
        times = []
        current = datetime.combine(datetime.today(), self.reminder_time)
        end = current.replace(hour=23, minute=59)
        while current <= end:
            times.append(current.time())
            current += timedelta(hours=self.frequency_hours)
        return times