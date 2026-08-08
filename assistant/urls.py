from django.urls import path
from . import views

urlpatterns = [
    path('', views.ai_search, name='ai_search'),
    path('patient-chat/', views.patient_ai_chat, name='patient_ai_chat'),
    path('patient-chat/<int:session_id>/', views.patient_ai_chat, name='patient_ai_chat_session'),
    path('doctor-reply/<str:token>/', views.doctor_reply, name='doctor_reply'),
]