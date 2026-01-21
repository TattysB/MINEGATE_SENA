from django.urls import path
from . import views

app_name = 'calendario'

urlpatterns = [
    path('', views.calendario_mes, name='index'),
    path('<int:year>/<int:month>/', views.calendario_mes, name='mes'),
]
