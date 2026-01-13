from django.urls import path
from . import views

urlpatterns = [
    path('', views.visita_externa, name='visita_externa'),
    path('crear/', views.crear_visita, name='crear_visita'),
    path('editar/<int:id>/', views.editar_visita, name='editar_visita'),
    path('eliminar/<int:id>/', views.eliminar_visita, name='eliminar_visita'),
    path('detalle_visita/<int:id>/', views.details, name='detalle_visita'),
]