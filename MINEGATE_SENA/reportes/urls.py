from django.urls import path

from . import views

app_name = "reportes"

urlpatterns = [
	path("", views.index, name="index"),
	path("descargar/pdf/", views.descargar_pdf, name="descargar_pdf"),
	path("descargar/excel/", views.descargar_excel, name="descargar_excel"),
]
