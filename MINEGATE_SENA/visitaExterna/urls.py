from django.urls import path
from . import views

app_name = 'visitaExterna'

urlpatterns = [
    path('visita_externa/', views.visita_externa, name='visita_externa'),
    path('visita_externa/crear/', views.crear_visita, name='crear_visita'),
    path('visita_externa/editar/<int:id>/', views.editar_visita, name='editar_visita'),
    path('visita_externa/eliminar/<int:id>/', views.eliminar_visita, name='eliminar_visita'),
    path('visita_externa/detalle_visita/<int:id>/', views.details, name='detalle_visita'),
]