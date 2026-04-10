from django.urls import path
from . import views

app_name: str = 'control_acceso_mina'

urlpatterns = [
    path('registrar/', views.registrar_acceso, name='registrar_acceso'),
    path('visitas-hoy/', views.visitas_hoy, name='visitas_hoy'),
    path('visita/<str:tipo_visita>/<int:visita_id>/', views.porteria_visita, name='porteria_visita'),
    path('visita/<str:tipo_visita>/<int:visita_id>/datos/', views.datos_visita, name='datos_visita'),
]
