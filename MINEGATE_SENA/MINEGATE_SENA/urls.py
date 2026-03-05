"""
URL configuration for MINEGATE_SENA project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView
from core.views import error_404

urlpatterns = [
    path('admin/', admin.site.urls),
    path('',include('core.urls')),
    path('auth/',include('usuarios.urls')),
    # Nuevas apps organizadas
    path('gestion/', include('gestion_visitas.urls')),
    path('visitante/', include('panel_visitante.urls')),
    path('documentos/', include('documentos.urls')),
    path('calendario/', include('calendario.urls')),
    path('visita_interna/', include('visitaInterna.urls')),
    path('visita_externa/', include('visitaExterna.urls')),
    # Paneles de instructores
    path('instructor/interno/', include('panel_instructor_interno.urls')),
    path('instructor/externo/', include('panel_instructor_externo.urls')),    
    path('coordinador/', include('coordinador.urls')),
    path('reportes/', include('reportes.urls')),
    
    path('favicon.ico', RedirectView.as_view(url='/static/img/LogoMine.png')), # Usar el logo como favicon temporal
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

