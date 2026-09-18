"""LocumSmart URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from structure.views import LandingPageView
from django.conf.urls.static import static
from django.conf import settings
from structure.views import handler403, handler404
handler403 = 'structure.views.handler403'
handler404 = 'structure.views.handler404'


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', LandingPageView.as_view(), name='LandingPage'),
    path('', include('structure.urls')),
    path('appAdmin/', include('appAdmin.urls')),
    path('locum/', include('locum.urls'))
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
