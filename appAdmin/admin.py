from django.contrib import admin
from appAdmin.models import CustomUser,Admin,Employer
# Register your models here.
admin.site.register(CustomUser)
admin.site.register(Admin)
admin.site.register(Employer)
