from django.urls import path
from . import views

app_name = 'calendario'

urlpatterns = [
    path('', views.calendario_mes, name='index'),
    path('<int:year>/<int:month>/', views.calendario_mes, name='mes'),
    path('save/', views.save_availability, name='save_availability'),
    path('day/update/', views.update_day_availability, name='update_day_availability'),
    path('day/delete/', views.delete_day_availability, name='delete_day_availability'),
    path('day/<str:day>/', views.day_availability, name='day_availability'),
    # Nueva visita - calendario de selección
    path('seleccion/', views.calendario_seleccion, name='seleccion'),
    path('seleccion/<int:year>/<int:month>/', views.calendario_seleccion, name='seleccion_mes'),
    path('horarios/<str:day>/', views.horarios_disponibles, name='horarios_disponibles'),
]
