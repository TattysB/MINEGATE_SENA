from django.urls import path
from . import views

app_name = 'panel_instructor_externo'

urlpatterns = [
    path('', views.panel_instructor_externo, name='panel'),

    path('reservar/', views.reservar_visita_externa, name='reservar_visita'),
    path('visitas/<int:pk>/', views.detalle_visita_externa, name='detalle_visita'),
]
