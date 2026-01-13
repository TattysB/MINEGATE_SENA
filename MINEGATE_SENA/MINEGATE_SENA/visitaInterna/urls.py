from django.urls import path
from . import views

urlpatterns = [
    path('', views.visita_interna, name='visita_interna'),
    path('crear/', views.crear_visita, name='crear_visita_interna'),
    path('editar/<int:id>/', views.editar_visita, name='editar_visita_interna'),
    path('eliminar/<int:id>/', views.eliminar_visita, name='eliminar_visita_interna'),
    path('detalle_visita/<int:id>/', views.details, name='detalle_visita_interna'),
]
