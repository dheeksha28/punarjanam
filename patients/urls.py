from django.urls import path
from . import views

from django.urls import path
from . import views

urlpatterns = [
    path('', views.patient_list, name='patient_list'),
    path('add/', views.patient_create, name='patient_create'),
    path('<int:pk>/', views.patient_detail, name='patient_detail'),
    path('<int:pk>/edit/', views.patient_update, name='patient_update'),
    path('<int:pk>/delete/', views.patient_delete, name='patient_delete'),
    path('<int:patient_pk>/treatments/add/', views.treatment_create, name='treatment_create'),
    path('treatments/<int:pk>/edit/', views.treatment_update, name='treatment_update'),
    path('treatments/<int:pk>/delete/', views.treatment_delete, name='treatment_delete'),
    path('<int:pk>/report/', views.patient_report, name='patient_report'),
    path('<int:patient_pk>/medicines/add/', views.medicine_create, name='medicine_create'),
    path('motivation/', views.daily_motivation, name='daily_motivation'),
    path('medicines/<int:pk>/edit/', views.medicine_update, name='medicine_update'),
    path('medicines/<int:pk>/delete/', views.medicine_delete, name='medicine_delete'),
    path('register/', views.patient_register, name='patient_register'),
    path('dashboard/', views.patient_dashboard, name='patient_dashboard'),
]