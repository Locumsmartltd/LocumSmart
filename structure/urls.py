from django.urls import path
from django.views.generic import TemplateView
from structure.views import *
from . import views
urlpatterns = [
    path('for-pharmacists/', TemplateView.as_view(template_name='for_pharmacists.html'), name='for_pharmacists'),
    path('primary-care/',    TemplateView.as_view(template_name='primary_care.html'),    name='primary_care'),
    path('register/',        TemplateView.as_view(template_name='register.html'),        name='register'),
    path('testimonials/', views.testimonials_view, name='testimonials'),
    path('contactUs/', ContactUsView.as_view(), name='contactus'),
    path('aboutUs/', aboutUsView.as_view(), name='aboutus'),
    path('privacypolicy/', privacypolicyView.as_view(), name='privacypolicy'),
    path('cookiesPolicy/', CookiesView.as_view(), name='cookiespolicy'),
    path('login/', LoginpageView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('locumjobs/', LocumJobs.as_view(), name='locumjobs'),
    path('job/<int:job_id>/', views.JobDetailsView.as_view(), name='job_details'),
    path('check_login/<int:job_id>/', views.check_login, name='check_login'),
    path('send-alert/', SendAlertsView.as_view(), name='send-alert'),
    path('changePassword/<uidb64>/<token>/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('setPassword/<token>/', SetPasswordView.as_view(), name='set_password'),
    path('fpEmail/', FPEmailView.as_view(), name='fpEmail')
]
