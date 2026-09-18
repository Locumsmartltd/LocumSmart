from django.urls import path
from . import views
from locum.views import *
urlpatterns = [
    path('employerRequest/', EmployerRequestView.as_view(), name='employerrequest'),
     path('locumTypes/', locumTypesView.as_view(), name='locumtypes'),
     path('pharmacistRegister/', PharmacistRegisterView.as_view(), name='pharmacistRegister'),
    path('gpRegistration/', GPRegisterView.as_view(), name='gpRegistration'),
    path('techRegistration/', TechDesRegisterView.as_view(), name='techRegistration'),
    path('nurseRegistration/', NursesRegisterView.as_view(), name='nurseRegistration'),
    path('locumProfile/', LocumProfile.as_view(), name='locumProfile'),
    path('locum/<int:locum_id>/jobs/', views.locum_jobs, name='locum_jobs'),
    path('job/<int:job_id>/generate_receipt/', views.generate_receipt_form, name='generate_receipt_form'),
    path('job/<int:job_id>/generate_pdf_receipt/', views.generate_pdf_receipt, name='generate_pdf_receipt'),
    path('locumcalendar/<int:user_id>/', views.locum_calander, name='locum_calander'),
    path('avail_added/<int:user_id>/', views.avail_added, name='avail_added'),
    path('addPharmacistManual/', views.addPharmacistManual, name='addPharmacistManual'),
    path('addtechManual/', views.addtechManual, name='addtechManual'),
    path('emailPharmacistManual/', views.sendEmailsToPharmacist, name='sendEmailsToPharmacist'),
    path('emailtechManual/', views.sendEmailsToTech, name='sendEmailsToTech'),
]
