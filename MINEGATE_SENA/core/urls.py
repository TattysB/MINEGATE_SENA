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
    path(
        "aprobar_usuario/<int:usuario_id>/", views.aprobar_usuario, name="aprobar_usuario"
    ),
    path(
        "rechazar_usuario/<int:usuario_id>/", views.rechazar_usuario, name="rechazar_usuario"
    ),
]
