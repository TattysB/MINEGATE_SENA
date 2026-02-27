from django.urls import path

from . import views

app_name = "coordinador"

urlpatterns = [
    path("panel/", views.panel_coordinador, name="panel"),
    path("calendario/", views.calendario_coordinador, name="calendario"),
    path("calendario/<int:year>/<int:month>/", views.calendario_coordinador, name="calendario_mes"),
    path("api/resumen-dia/<str:day>/", views.resumen_dia_coordinador, name="resumen_dia"),
    path("api/solicitudes/", views.api_solicitudes_coordinacion, name="api_solicitudes"),
    path(
        "api/solicitudes/<str:tipo>/<int:visita_id>/<str:accion>/",
        views.api_accion_coordinacion,
        name="api_accion",
    ),
]
