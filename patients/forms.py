from django import forms
from .models import Patient, Treatment, Medicine
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['name', 'age', 'gender', 'diagnosis', 'contact_number', 'doctor_name', 'doctor_email', 'hanuman_chalisa_enabled', 'hanuman_chalisa_time']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'age': forms.NumberInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'diagnosis': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'doctor_name': forms.TextInput(attrs={'class': 'form-control'}),
            'doctor_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'hanuman_chalisa_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'hanuman_chalisa_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }


class PatientRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']


class TreatmentForm(forms.ModelForm):
    class Meta:
        model = Treatment
        fields = ['treatment_name', 'treatment_type', 'total_sessions', 'completed_sessions', 'date_administered', 'next_session_date', 'notes']
        widgets = {
            'treatment_name': forms.TextInput(attrs={'class': 'form-control'}),
            'treatment_type': forms.Select(attrs={'class': 'form-select'}),
            'total_sessions': forms.NumberInput(attrs={'class': 'form-control'}),
            'completed_sessions': forms.NumberInput(attrs={'class': 'form-control'}),
            'date_administered': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'next_session_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = ['medicine_name', 'dosage', 'reminder_time', 'frequency_hours', 'notes']
        widgets = {
            'medicine_name': forms.TextInput(attrs={'class': 'form-control'}),
            'dosage': forms.TextInput(attrs={'class': 'form-control'}),
            'reminder_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'frequency_hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }