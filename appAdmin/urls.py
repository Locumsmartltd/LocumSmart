from django.urls import path
from appAdmin.views import *
from locum.views import *
from . import views

urlpatterns = [
    # REMOVE IT ITS JUST dummy
    path('admin/', AdminView.as_view(), name='admin'),
    path('employerRequests/', EmployerRequestsView.as_view(),
         name='employerRequests'),
    path('approve-job/<int:job_id>/',
         ApproveJobView.as_view(), name='approve_job'),
    path('disapprove-job/<int:job_id>/',
         DisapproveJobView.as_view(), name='disapprove_job'),
    path('registerEmployer/', RegisterEmployer.as_view(), name='registerEmployer'),
    path('deleteLocum/', DeleteLocum.as_view(), name='deleteLocum'),
    path('acceptLocum/', AcceptLocum.as_view(), name='acceptLocum'),
    path('locums/', LocumListView.as_view(), name='seeLocum'),
    path('locumRequests/', LocumRequestsListView.as_view(), name='locumRequests'),
    path('employersList/', EmployerListView.as_view(), name='employersList'),
    path('locums/<int:pk>/', LocumDetailView.as_view(), name='locum_detail'),
    path('registerStaff/', RegisterStaff.as_view(), name='registerStaff'),
    path('staffList/', StaffListView.as_view(), name='staffList'),
    path('job-applications/', views.job_applications, name='job_applications'),
    # Define URL patterns for approving and rejecting jobs
    path('approveappliedjob-job/<int:applied_job_id>/',
         views.approveappliedjob, name='approveappliedjob'),
    path('reject-job/<int:applied_job_id>/',
         views.reject_job, name='reject_job'),
    path('calander/', JobListView.as_view(), name='calander'),
    path('update-job/<int:job_id>/', UpdateJobView.as_view(), name='update_job'),
    path('locums/<int:locum_id>/edit/',
         LocumEditView.as_view(), name='edit_locum'),
    path('post-job/<int:employer_id>/',
         EmployerRequestView.as_view(), name='post_job'),
    path('editEmployer/<int:employer_id>/',
         EditEmployer.as_view(), name='edit_employer'),
    path('deleteEmployer/<int:employer_id>/',
         DeleteEmployer.as_view(), name='delete_employer'),
    path('email-tracking-log/',
         EmailTrackingLogView.as_view(), name='email_tracking_log'),
    path('system-logs/', SystemLogsView.as_view(), name='system_logs'),
    path('media/<path:file_path>/', AdminMediaView.as_view(), name='admin_media'),
    path('send-email/<int:job_id>/', 
         send_email_to_locums, name='send_email_to_locums'),
    path('testimonials/', views.testimonials_list, name='testimonials_list'),
    path('testimonials/add_or_edit/', views.add_or_edit_testimonial, name='add_or_edit_testimonial'),
    path('testimonials/delete/<int:id>/', views.delete_testimonial, name='delete_testimonial'),
]
