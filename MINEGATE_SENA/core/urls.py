from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.index, name="index"),
    path(
        "panel_administrativo/", views.panel_administrativo, name="panel_administrativo"
    ),
    path(
        "gestionar_permisos/", views.gestionar_permisos, name="gestionar_permisos"
    ),
    path('protocolos/', views.protocolos, name='protocolos'),
    path('visitas/', views.visitas, name='visitas'),
]
