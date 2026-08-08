from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from .models import Patient, Treatment, Medicine
from .forms import PatientForm, TreatmentForm, MedicineForm
import random
import json
from django.contrib.auth.decorators import login_required
from .forms import PatientRegistrationForm
from django.contrib.auth import login

def is_admin(user):
    return user.is_staff or user.is_superuser

@login_required
def patient_dashboard(request):
    try:
        patient = request.user.patient_profile
    except Patient.DoesNotExist:
        return redirect('patient_list')
    return render(request, 'patients/patient_dashboard.html', {'patient': patient})

def patient_register(request):
    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            patient = Patient.objects.create(
                user_account=user,
                name=user.username,
                age=0,
                gender='O',
                diagnosis='Not specified yet',
            )
            login(request, user)
            return redirect('patient_dashboard')
    else:
        form = PatientRegistrationForm()
    return render(request, 'patients/register.html', {'form': form})

MOTIVATION_MESSAGES = [
    "Every day is a new beginning. Take a deep breath and start again.",
    "You are stronger than you think.",
    "Healing is not linear, but every step forward counts.",
    "Believe in the process. Recovery takes time, and that's okay.",
    "ಪ್ರತಿ ದಿನವೂ ಹೊಸ ಆರಂಭ. ಆಳವಾದ ಉಸಿರು ತೆಗೆದುಕೊಂಡು ಮತ್ತೆ ಪ್ರಾರಂಭಿಸಿ.",
    "ನೀವು ಯೋಚಿಸುವುದಕ್ಕಿಂತ ಬಲಶಾಲಿಯಾಗಿದ್ದೀರಿ.",
    "ಗುಣಮುಖವಾಗುವುದು ನೇರವಾದ ದಾರಿಯಲ್ಲ, ಆದರೆ ಪ್ರತಿ ಹೆಜ್ಜೆಯೂ ಮುಖ್ಯ.",
    "ಪ್ರಕ್ರಿಯೆಯಲ್ಲಿ ನಂಬಿಕೆ ಇಡಿ. ಚೇತರಿಕೆಗೆ ಸಮಯ ಬೇಕು, ಅದು ಸರಿ.",
]

DAILY_POPUP_MESSAGES = [
    "You woke up today. That's a victory. Keep going.",
    "Your strength today will be someone else's hope tomorrow.",
    "This battle is hard, but so are you.",
    "Every sunrise is proof that you're still fighting, and still winning.",
    "ನೀವು ಇಂದು ಎಚ್ಚರಗೊಂಡಿದ್ದೀರಿ. ಅದೇ ಒಂದು ಗೆಲುವು. ಮುಂದುವರಿಯಿರಿ.",
    "ನಿಮ್ಮ ಶಕ್ತಿ ಇಂದು, ನಾಳೆ ಇನ್ನೊಬ್ಬರ ಭರವಸೆ.",
    "ಈ ಯುದ್ಧ ಕಠಿಣವಾಗಿದೆ, ಆದರೆ ನೀವು ಸಹ ಕಠಿಣರಾಗಿದ್ದೀರಿ.",
    "ಪ್ರತಿ ಸೂರ್ಯೋದಯವೂ ನೀವು ಇನ್ನೂ ಹೋರಾಡುತ್ತಿದ್ದೀರಿ, ಮತ್ತು ಇನ್ನೂ ಗೆಲ್ಲುತ್ತಿದ್ದೀರಿ ಎಂಬುದಕ್ಕೆ ಸಾಕ್ಷಿಯಾಗಿದೆ.",
]

@login_required
def daily_motivation(request):
    message = random.choice(MOTIVATION_MESSAGES)
    return render(request, 'patients/motivation.html', {'message': message})


@login_required
def patient_list(request):
    if hasattr(request.user, 'patient_profile'):
        return redirect('patient_dashboard')
    query = request.GET.get('q', '')
    if query:
        patients = Patient.objects.filter(name__icontains=query)
    else:
        patients = Patient.objects.all()
    return render(request, 'patients/patient_list.html', {
        'patients': patients,
        'motivation_messages_json': json.dumps(DAILY_POPUP_MESSAGES),
        'query': query,
    })

@login_required
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    return render(request, 'patients/patient_detail.html', {'patient': patient})

@login_required
def patient_create(request):
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('patient_list')
    else:
        form = PatientForm()
    return render(request, 'patients/patient_form.html', {'form': form})

@login_required
def patient_update(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            return redirect('patient_detail', pk=patient.pk)
    else:
        form = PatientForm(instance=patient)
    return render(request, 'patients/patient_form.html', {'form': form})

@login_required
def patient_delete(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        patient.delete()
        return redirect('patient_list')
    return render(request, 'patients/patient_confirm_delete.html', {'patient': patient})

@login_required
def treatment_create(request, patient_pk):
    patient = get_object_or_404(Patient, pk=patient_pk)
    if request.method == 'POST':
        form = TreatmentForm(request.POST)
        if form.is_valid():
            treatment = form.save(commit=False)
            treatment.patient = patient
            treatment.save()
            return redirect('patient_detail', pk=patient.pk)
    else:
        form = TreatmentForm()
    return render(request, 'patients/treatment_form.html', {'form': form, 'patient': patient})

@login_required
def treatment_update(request, pk):
    treatment = get_object_or_404(Treatment, pk=pk)
    if request.method == 'POST':
        form = TreatmentForm(request.POST, instance=treatment)
        if form.is_valid():
            form.save()
            return redirect('patient_detail', pk=treatment.patient.pk)
    else:
        form = TreatmentForm(instance=treatment)
    return render(request, 'patients/treatment_form.html', {'form': form, 'patient': treatment.patient})

@login_required
def treatment_delete(request, pk):
    treatment = get_object_or_404(Treatment, pk=pk)
    patient_pk = treatment.patient.pk
    if request.method == 'POST':
        treatment.delete()
        return redirect('patient_detail', pk=patient_pk)
    return render(request, 'patients/treatment_confirm_delete.html', {'treatment': treatment})

@login_required
def medicine_create(request, patient_pk):
    patient = get_object_or_404(Patient, pk=patient_pk)
    if request.method == 'POST':
        form = MedicineForm(request.POST)
        if form.is_valid():
            medicine = form.save(commit=False)
            medicine.patient = patient
            medicine.save()
            return redirect('patient_detail', pk=patient.pk)
    else:
        form = MedicineForm()
    return render(request, 'patients/medicine_form.html', {'form': form, 'patient': patient})

@login_required
def medicine_update(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    if request.method == 'POST':
        form = MedicineForm(request.POST, instance=medicine)
        if form.is_valid():
            form.save()
            return redirect('patient_detail', pk=medicine.patient.pk)
    else:
        form = MedicineForm(instance=medicine)
    return render(request, 'patients/medicine_form.html', {'form': form, 'patient': medicine.patient})

@login_required
def medicine_delete(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    patient_pk = medicine.patient.pk
    if request.method == 'POST':
        medicine.delete()
        return redirect('patient_detail', pk=patient_pk)
    return render(request, 'patients/medicine_confirm_delete.html', {'medicine': medicine})

@login_required
def patient_report(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{patient.name}_report.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    y = height - 50
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, f"Patient Report: {patient.name}")

    y -= 30
    p.setFont("Helvetica", 12)
    p.drawString(50, y, f"Admission ID: {patient.admission_id}")
    y -= 20
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, y, f"App Login Username: patient_{patient.admission_id}")
    y -= 15
    p.drawString(50, y, f"App Login Password: {patient.admission_id}")
    p.setFont("Helvetica", 12)
    y -= 20
    p.drawString(50, y, f"Age: {patient.age}")
    y -= 20
    p.drawString(50, y, f"Gender: {patient.get_gender_display()}")
    y -= 20
    p.drawString(50, y, f"Diagnosis: {patient.diagnosis}")
    y -= 20
    p.drawString(50, y, f"Contact: {patient.contact_number}")
    if patient.doctor_name:
        y -= 20
        p.drawString(50, y, f"Doctor: {patient.doctor_name}")

    y -= 40
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Treatments")
    y -= 20
    p.setFont("Helvetica", 11)

    for treatment in patient.treatments.all():
        p.drawString(50, y, f"{treatment.get_treatment_type_display()}: {treatment.treatment_name} — {treatment.completed_sessions}/{treatment.total_sessions} sessions")
        y -= 15
        if treatment.next_session_date:
            p.drawString(70, y, f"Next session: {treatment.next_session_date}")
            y -= 15
        if treatment.notes:
            p.drawString(70, y, f"Notes: {treatment.notes}")
            y -= 15
        y -= 5
        if y < 100:
            p.showPage()
            y = height - 50

    y -= 20
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Medicines")
    y -= 20
    p.setFont("Helvetica", 11)

    for medicine in patient.medicines.all():
        times_str = ", ".join([t.strftime('%I:%M %p') for t in medicine.schedule_times()])
        p.drawString(50, y, f"{medicine.medicine_name} — {medicine.dosage}")
        y -= 15
        p.drawString(70, y, f"Every {medicine.frequency_hours}h: {times_str}")
        y -= 15
        if medicine.notes:
            p.drawString(70, y, f"Notes: {medicine.notes}")
            y -= 15
        y -= 5
        if y < 100:
            p.showPage()
            y = height - 50

    p.showPage()
    p.save()
    return response