from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.dateparse import parse_date
from django.utils.html import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from visitaExterna.models import VisitaExterna
from visitaInterna.models import VisitaInterna


def _es_admin(user):
	return user.is_authenticated and (user.is_superuser or user.is_staff)


def _normalizar_filtros(request):
	tipo = request.GET.get("tipo", "todas").strip().lower()
	if tipo not in {"todas", "interna", "externa"}:
		tipo = "todas"

	estado = request.GET.get("estado", "").strip().lower()
	fecha_desde = parse_date(request.GET.get("fecha_desde", ""))
	fecha_hasta = parse_date(request.GET.get("fecha_hasta", ""))

	return {
		"tipo": tipo,
		"estado": estado,
		"fecha_desde": fecha_desde,
		"fecha_hasta": fecha_hasta,
		"fecha_desde_raw": request.GET.get("fecha_desde", ""),
		"fecha_hasta_raw": request.GET.get("fecha_hasta", ""),
	}


def _obtener_filas_reporte(request):
	filtros = _normalizar_filtros(request)

	visitas_internas = VisitaInterna.objects.all().prefetch_related('asistentes')
	visitas_externas = VisitaExterna.objects.all().prefetch_related('asistentes')

	if filtros["estado"]:
		visitas_internas = visitas_internas.filter(estado=filtros["estado"])
		visitas_externas = visitas_externas.filter(estado=filtros["estado"])

	if filtros["fecha_desde"]:
		visitas_internas = visitas_internas.filter(
			fecha_solicitud__date__gte=filtros["fecha_desde"]
		)
		visitas_externas = visitas_externas.filter(
			fecha_solicitud__date__gte=filtros["fecha_desde"]
		)

	if filtros["fecha_hasta"]:
		visitas_internas = visitas_internas.filter(
			fecha_solicitud__date__lte=filtros["fecha_hasta"]
		)
		visitas_externas = visitas_externas.filter(
			fecha_solicitud__date__lte=filtros["fecha_hasta"]
		)

	filas = []

	if filtros["tipo"] in {"todas", "interna"}:
		for visita in visitas_internas:
			# Obtener lista de asistentes
			asistentes = []
			for asistente in visita.asistentes.all():
				asistentes.append({
					"nombre": asistente.nombre_completo,
					"tipo_documento": asistente.get_tipo_documento_display(),
					"numero_documento": asistente.numero_documento,
					"correo": asistente.correo,
					"telefono": asistente.telefono,
					"estado": asistente.get_estado_display(),
				})
			
			filas.append(
				{
					"tipo": "Interna",
					"id": visita.id,
					"nombre": visita.nombre_programa,
					"responsable": visita.responsable,
					"documento": visita.documento_responsable,
					"correo": visita.correo_responsable,
					"telefono": visita.telefono_responsable,
					"cantidad": visita.cantidad_aprendices,
					"fecha_solicitud": visita.fecha_solicitud,
					"fecha_visita": visita.fecha_visita,
					"estado": visita.get_estado_display(),
					"asistentes": asistentes,
				}
			)

	if filtros["tipo"] in {"todas", "externa"}:
		for visita in visitas_externas:
			# Obtener lista de asistentes
			asistentes = []
			for asistente in visita.asistentes.all():
				asistentes.append({
					"nombre": asistente.nombre_completo,
					"tipo_documento": asistente.get_tipo_documento_display(),
					"numero_documento": asistente.numero_documento,
					"correo": asistente.correo,
					"telefono": asistente.telefono,
					"estado": asistente.get_estado_display(),
				})
			
			filas.append(
				{
					"tipo": "Externa",
					"id": visita.id,
					"nombre": visita.nombre,
					"responsable": visita.nombre_responsable,
					"documento": visita.documento_responsable,
					"correo": visita.correo_responsable,
					"telefono": visita.telefono_responsable,
					"cantidad": visita.cantidad_visitantes,
					"fecha_solicitud": visita.fecha_solicitud,
					"fecha_visita": visita.fecha_visita,
					"estado": visita.get_estado_display(),
					"asistentes": asistentes,
				}
			)

	filas.sort(key=lambda item: item["fecha_solicitud"], reverse=True)
	return filas, filtros


@login_required(login_url="usuarios:login")
@user_passes_test(_es_admin, login_url="core:panel_administrativo")
def index(request):
	filas, filtros = _obtener_filas_reporte(request)
	query_string = request.GET.urlencode()
	estados = VisitaInterna.ESTADO_CHOICES

	context = {
		"filas": filas[:100],
		"total_filas": len(filas),
		"filtros": filtros,
		"query_string": query_string,
		"estados": estados,
	}
	return render(request, "reportes/index.html", context)


@login_required(login_url="usuarios:login")
@user_passes_test(_es_admin, login_url="core:panel_administrativo")
def descargar_excel(request):
	filas, _ = _obtener_filas_reporte(request)

	response = HttpResponse(content_type="application/vnd.ms-excel; charset=utf-8")
	response["Content-Disposition"] = 'attachment; filename="reporte_visitas.xls"'
	response.write("\ufeff")

	response.write("<table border='1'>")
	
	# Encabezado principal
	response.write(
		"<tr style='background-color: #39a900; color: white; font-weight: bold;'>"
		"<th>Tipo</th><th>ID</th><th>Nombre/Programa</th><th>Responsable</th>"
		"<th>Documento</th><th>Correo</th><th>Telefono</th><th>Cantidad</th>"
		"<th>Fecha Solicitud</th><th>Fecha Visita</th><th>Estado</th>"
		"</tr>"
	)

	for fila in filas:
		fecha_solicitud = fila["fecha_solicitud"].strftime("%Y-%m-%d %H:%M")
		fecha_visita = fila["fecha_visita"].strftime("%Y-%m-%d") if fila["fecha_visita"] else "-"

		# Encabezado de la visita
		response.write(
			"<tr style='background-color: #e8f5e9;'>"
			f"<td colspan='11'><strong>Visita: {escape(fila['nombre'])} | Código: {fila['id']}</strong></td>"
			"</tr>"
		)
		
		# Fila de la visita
		response.write(
			"<tr>"
			f"<td>{escape(fila['tipo'])}</td>"
			f"<td>{fila['id']}</td>"
			f"<td>{escape(fila['nombre'])}</td>"
			f"<td>{escape(fila['responsable'])}</td>"
			f"<td>{escape(fila['documento'])}</td>"
			f"<td>{escape(fila['correo'])}</td>"
			f"<td>{escape(fila['telefono'])}</td>"
			f"<td>{fila['cantidad']}</td>"
			f"<td>{fecha_solicitud}</td>"
			f"<td>{fecha_visita}</td>"
			f"<td>{escape(fila['estado'])}</td>"
			"</tr>"
		)
		
		# Agregar visitantes inmediatamente debajo si los hay
		if fila['asistentes']:
			response.write(
				"<tr style='background-color: #d4edda;'>"
				"<td colspan='11'><strong>Visitantes Registrados:</strong></td>"
				"</tr>"
			)
			response.write(
				"<tr style='background-color: #39a900; color: white; font-weight: bold;'>"
				"<td></td><td></td>"
				"<th>Nombre</th><th>Tipo Doc</th><th>Número Doc</th>"
				"<th>Correo</th><th>Teléfono</th><th>Estado</th>"
				"<td colspan='3'></td>"
				"</tr>"
			)
			
			# Agregar cada asistente
			for asistente in fila['asistentes']:
				response.write(
					"<tr style='background-color: #f9f9f9;'>"
					"<td></td><td></td>"
					f"<td>{escape(asistente['nombre'])}</td>"
					f"<td>{escape(asistente['tipo_documento'])}</td>"
					f"<td>{escape(asistente['numero_documento'])}</td>"
					f"<td>{escape(asistente['correo'])}</td>"
					f"<td>{escape(asistente['telefono'])}</td>"
					f"<td>{escape(asistente['estado'])}</td>"
					"<td colspan='3'></td>"
					"</tr>"
				)
			
			# Fila separadora
			response.write(
				"<tr style='height: 10px;'>"
				"<td colspan='11' style='background-color: #ffffff; border: none;'></td>"
				"</tr>"
			)

	response.write("</table>")
	return response


@login_required(login_url="usuarios:login")
@user_passes_test(_es_admin, login_url="core:panel_administrativo")
def descargar_pdf(request):
	filas, _ = _obtener_filas_reporte(request)

	response = HttpResponse(content_type="application/pdf")
	response["Content-Disposition"] = 'attachment; filename="reporte_visitas.pdf"'

	documento = SimpleDocTemplate(
		response,
		pagesize=landscape(A4),
		leftMargin=20,
		rightMargin=20,
		topMargin=20,
		bottomMargin=20,
	)

	estilos = getSampleStyleSheet()
	elementos = [
		Paragraph("Reporte de Visitas (Internas y Externas)", estilos["Heading2"]),
		Spacer(1, 10),
	]

	# Iterar por cada visita y agregar sus datos junto con sus visitantes
	for fila in filas:
		elementos.append(
			Paragraph(
				f"<b>Visita: {escape(fila['nombre'][:50])} | Código: {fila['id']}</b>",
				estilos["Heading4"],
			)
		)
		elementos.append(Spacer(1, 4))

		# Tabla de datos de la visita
		data_visita = [
			[
				"Tipo",
				"ID",
				"Nombre/Programa",
				"Responsable",
				"Documento",
				"Fecha Solicitud",
				"Fecha Visita",
				"Cantidad",
				"Estado",
			],
			[
				fila["tipo"],
				str(fila["id"]),
				fila["nombre"][:30],
				fila["responsable"][:28],
				fila["documento"],
				fila["fecha_solicitud"].strftime("%Y-%m-%d"),
				fila["fecha_visita"].strftime("%Y-%m-%d") if fila["fecha_visita"] else "-",
				str(fila["cantidad"]),
				fila["estado"][:20],
			]
		]

		tabla_visita = Table(data_visita)
		tabla_visita.setStyle(
			TableStyle(
				[
					("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#39a900")),
					("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
					("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
					("FONTSIZE", (0, 0), (-1, -1), 8),
					("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
					("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
					("ALIGN", (0, 0), (-1, -1), "CENTER"),
					("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
				]
			)
		)

		elementos.append(tabla_visita)
		
		# Si tiene visitantes, agregarlos inmediatamente debajo
		if fila['asistentes']:
			elementos.append(Spacer(1, 5))
			elementos.append(
				Paragraph(
					f"<b>Visitantes Registrados - {fila['tipo']} ID {fila['id']}: {fila['nombre'][:40]}</b>",
					estilos["Heading4"]
				)
			)
			elementos.append(Spacer(1, 3))
			
			# Crear tabla de asistentes
			data_asistentes = [
				["Nombre", "Tipo Doc", "Número Doc", "Correo", "Teléfono", "Estado"]
			]
			
			for asistente in fila['asistentes']:
				data_asistentes.append([
					asistente['nombre'][:30],
					asistente['tipo_documento'][:15],
					asistente['numero_documento'],
					asistente['correo'][:30],
					asistente['telefono'],
					asistente['estado'][:25],
				])
			
			tabla_asistentes = Table(data_asistentes, repeatRows=1)
			tabla_asistentes.setStyle(
				TableStyle([
					("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#39a900")),
					("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
					("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
					("FONTSIZE", (0, 0), (-1, -1), 7),
					("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
					("BACKGROUND", (0, 1), (-1, -1), colors.beige),
					("ALIGN", (0, 0), (-1, -1), "CENTER"),
					("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
				])
			)
			
			elementos.append(tabla_asistentes)
		
		# Separador entre visitas
		elementos.append(Spacer(1, 15))
	
	documento.build(elementos)
	return response
