from django.urls import path

from . import views

app_name = "reportes"

urlpatterns = [
	path("", views.index, name="index"),
	path("descargar/pdf/", views.descargar_pdf, name="descargar_pdf"),
	path("descargar/excel/", views.descargar_excel, name="descargar_excel"),
	path("descargar/pdf/<str:tipo>/<int:id_visita>/", views.descargar_pdf_individual, name="descargar_pdf_individual"),
	path("descargar/excel/<str:tipo>/<int:id_visita>/", views.descargar_excel_individual, name="descargar_excel_individual"),
]
