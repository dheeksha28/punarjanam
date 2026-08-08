from django.contrib import admin
from .models import Patient, Treatment, Medicine

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('name', 'admission_id', 'age', 'gender', 'diagnosis', 'doctor_name', 'created_at')
    search_fields = ('name', 'diagnosis', 'admission_id')

@admin.register(Treatment)
class TreatmentAdmin(admin.ModelAdmin):
    list_display = ('treatment_name', 'patient', 'treatment_type', 'completed_sessions', 'total_sessions', 'next_session_date')
    search_fields = ('treatment_name', 'patient__name')

@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ('medicine_name', 'patient', 'dosage', 'reminder_time')
    search_fields = ('medicine_name', 'patient__name')