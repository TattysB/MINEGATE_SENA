from django.urls import path
from . import views

app_name = 'gestion_visitas'

urlpatterns = [
    # APIs para gestión de visitas en el panel administrativo
    path('api/visitas/', views.api_listar_visitas, name='api_listar_visitas'),
    path('api/visitas/<str:tipo>/<int:visita_id>/', views.api_detalle_visita, name='api_detalle_visita'),
    path('api/visitas/<str:tipo>/<int:visita_id>/<str:accion>/', views.api_accion_visita, name='api_accion_visita'),
    path('api/asistentes/<str:tipo>/<int:asistente_id>/<str:accion>/', views.api_revisar_documento_asistente, name='api_revisar_documento_asistente'),
]
