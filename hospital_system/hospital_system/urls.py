"""
URL configuration for hospital_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
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
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('departments/', include('departments.urls')),
    path('doctors/', include('doctors.urls')),
    path('appointments/', include('appointments.urls')),
    path('', include(('corepages.urls', 'core'), namespace='core')),
    path('', include(('corepages.urls', 'corepages'), namespace='corepages')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler400 = 'corepages.views.custom_bad_request_view'
handler403 = 'corepages.views.custom_permission_denied_view'
handler404 = 'corepages.views.custom_page_not_found_view'
handler500 = 'corepages.views.custom_server_error_view'
