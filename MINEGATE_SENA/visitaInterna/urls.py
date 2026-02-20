from django.urls import path
from . import views

app_name = 'visitaInterna'

urlpatterns = [
    path('visita_interna/', views.visita_interna, name='visita_interna'),
    path('visita_interna/crear/', views.crear_visita, name='crear_visita_interna'),
    path('visita_interna/editar/<int:id>/', views.editar_visita, name='editar_visita_interna'),
    path('visita_interna/eliminar/<int:id>/', views.eliminar_visita, name='eliminar_visita_interna'),
    path('visita_interna/detalle_visita/<int:id>/', views.details, name='detalle_visita_interna'),
]
