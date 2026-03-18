from django.urls import path
from . import views

app_name = 'panel_visitante'

urlpatterns = [
    path('login/', views.login_responsable, name='login_responsable'),
    path('registro/', views.registro_visita, name='registro_visita'),
    path('logout/', views.logout_responsable, name='logout_responsable'),
    path('panel/', views.panel_responsable, name='panel_responsable'),
    path('actualizar-perfil/', views.actualizar_perfil, name='actualizar_perfil'),
    path('registrar/<str:tipo>/<int:visita_id>/', views.registrar_asistentes, name='registrar_asistentes'),
    path('eliminar/<str:tipo>/<int:asistente_id>/', views.eliminar_asistente, name='eliminar_asistente'),
    path('actualizar-documento/<str:tipo>/<int:asistente_id>/', views.actualizar_documento_asistente, name='actualizar_documento_asistente'),
    path('actualizar-info/<str:tipo>/<int:asistente_id>/', views.actualizar_info_asistente, name='actualizar_info_asistente'),
    path('copiar-asistente/<str:tipo>/<int:visita_id>/<int:asistente_previo_id>/', views.copiar_asistente_previo, name='copiar_asistente_previo'),
    path('enviar-solicitud/<str:tipo>/<int:visita_id>/', views.enviar_solicitud_final, name='enviar_solicitud_final'),
    # Recuperación de contraseña - Nuevo patrón
    path('restablecer-contraseña/', views.restablecer_contraseña, name='restablecer_contraseña'),
    path('restablecer-contraseña/correo-enviado/', views.correo_enviado_view, name='correo_enviado'),
    path('restablecer-contraseña/<uidb64>/<token>/', views.restablecer_contraseña_confirm, name='restablecer_contraseña_confirm'),
    path('restablecer-contraseña/completado/', views.contraseña_actualizada_view, name='contraseña_actualizada'),
]
