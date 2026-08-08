from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from .rag_engine import get_answer
from .models import ChatSession, ChatMessage, DoctorMessage
from patients.models import Patient


@login_required
def ai_search(request):
    answer = None
    question = None
    if request.method == 'POST':
        question = request.POST.get('question')
        answer = get_answer(question)
    return render(request, 'assistant/ai_search.html', {'answer': answer, 'question': question})


@login_required
def patient_ai_chat(request, session_id=None):
    try:
        patient = request.user.patient_profile
    except Patient.DoesNotExist:
        return redirect('patient_list')

    action = None

    if session_id:
        session = get_object_or_404(ChatSession, id=session_id, patient=patient)
    else:
        session = ChatSession.objects.create(patient=patient)
        return redirect('patient_ai_chat_session', session_id=session.id)

    if request.method == 'POST':
        if 'contact_doctor' in request.POST:
            last_question = request.POST.get('last_question', 'General question about my care')
            contact_doctor(request, patient, last_question)
            action = 'doctor_contacted'
        else:
            question = request.POST.get('question')
            q_lower = question.lower()

            ChatMessage.objects.create(session=session, role='user', content=question)

            if session.title == 'New chat':
                session.title = question[:50]
                session.save()

            if 'chalisa' in q_lower or 'chalis' in q_lower:
                action = 'play_chalisa'
                answer = "Sure, playing the Hanuman Chalisa for you now."
            elif 'motivation' in q_lower or 'motivate' in q_lower:
                action = 'play_motivation'
                answer = "Here's something to lift your spirits."
            else:
                answer = get_answer(question, patient=patient)

            ChatMessage.objects.create(session=session, role='ai', content=answer)

    messages = session.messages.all()
    last_user_message = messages.filter(role='user').last()
    all_sessions = patient.chat_sessions.all()

    return render(request, 'assistant/patient_ai_chat.html', {
        'messages': messages, 'patient': patient, 'action': action,
        'last_question': last_user_message.content if last_user_message else '',
        'session': session, 'all_sessions': all_sessions
    })


def contact_doctor(request, patient, question):
    if not patient.doctor_email:
        return

    doc_msg = DoctorMessage.objects.create(patient=patient, question=question)

    report_url = settings.SITE_URL + reverse('patient_report', args=[patient.pk])
    reply_url = settings.SITE_URL + reverse('doctor_reply', args=[doc_msg.reply_token])

    subject = f"Question from patient: {patient.name}"
    message = f"""Hello Dr. {patient.doctor_name},

Your patient {patient.name} (Admission ID: {patient.admission_id}) has a question they'd like your help with:

"{question}"

View their full report here:
{report_url}

Reply to your patient here:
{reply_url}

- Punarjanam, Patient Care Tracker"""

    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [patient.doctor_email])


def doctor_reply(request, token):
    doc_msg = get_object_or_404(DoctorMessage, reply_token=token)

    if request.method == 'POST':
        doc_msg.reply = request.POST.get('reply')
        doc_msg.is_replied = True
        from django.utils import timezone
        doc_msg.replied_at = timezone.now()
        doc_msg.save()
        return render(request, 'assistant/doctor_reply_sent.html', {'patient': doc_msg.patient})

    return render(request, 'assistant/doctor_reply_form.html', {'doc_msg': doc_msg})