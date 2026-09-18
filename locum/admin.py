from django.contrib import admin
from locum.models import Locum,Job,LocumAvailability,AppliedJob
# Register your models here.
admin.site.register(Locum)
admin.site.register(Job)
admin.site.register(AppliedJob)
admin.site.register(LocumAvailability)