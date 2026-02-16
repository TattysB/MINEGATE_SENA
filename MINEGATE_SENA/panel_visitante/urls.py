from django.urls import path
from . import views

app_name = 'panel_visitante'

urlpatterns = [
    path('login/', views.login_responsable, name='login_responsable'),
    path('logout/', views.logout_responsable, name='logout_responsable'),
    path('panel/', views.panel_responsable, name='panel_responsable'),
    path('registrar/<str:tipo>/<int:visita_id>/', views.registrar_asistentes, name='registrar_asistentes'),
    path('eliminar/<str:tipo>/<int:asistente_id>/', views.eliminar_asistente, name='eliminar_asistente'),
    path('enviar-solicitud/<str:tipo>/<int:visita_id>/', views.enviar_solicitud_final, name='enviar_solicitud_final'),
]
