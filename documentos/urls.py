from django.urls import path
from . import views

app_name = 'documentos'

urlpatterns = [
    # Registro público con token
    path('registro/interna/<str:token>/', views.registro_publico_asistentes, 
         {'tipo': 'interna'}, name='registro_publico_interna'),
    path('registro/externa/<str:token>/', views.registro_publico_asistentes, 
         {'tipo': 'externa'}, name='registro_publico_externa'),
    
    # Eliminar asistente desde enlace público
    path('eliminar/interna/<str:token>/<int:asistente_id>/', views.eliminar_asistente_publico, 
         {'tipo': 'interna'}, name='eliminar_asistente_publico_interna'),
    path('eliminar/externa/<str:token>/<int:asistente_id>/', views.eliminar_asistente_publico, 
         {'tipo': 'externa'}, name='eliminar_asistente_publico_externa'),
]
