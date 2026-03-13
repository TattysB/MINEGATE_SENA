from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.dateparse import parse_date
from django.utils.html import escape
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from visitaExterna.models import VisitaExterna
from visitaInterna.models import VisitaInterna


def _es_admin(user):
	return user.is_authenticated and (user.is_superuser or user.is_staff)


def _normalizar_filtros(request):
	tipo = request.GET.get("tipo", "todas").strip().lower()
	if tipo not in {"todas", "interna", "externa"}:
		tipo = "todas"

	estado = request.GET.get("estado", "").strip().lower()
	fecha_desde_raw = request.GET.get("fecha_desde", "")
	fecha_hasta_raw = request.GET.get("fecha_hasta", "")
	fecha_desde = parse_date(fecha_desde_raw)
	fecha_hasta = parse_date(fecha_hasta_raw)

	if fecha_desde and fecha_hasta and fecha_hasta < fecha_desde:
		fecha_hasta = fecha_desde
		fecha_hasta_raw = fecha_desde_raw

	return {
		"tipo": tipo,
		"estado": estado,
		"fecha_desde": fecha_desde,
		"fecha_hasta": fecha_hasta,
		"fecha_desde_raw": fecha_desde_raw,
		"fecha_hasta_raw": fecha_hasta_raw,
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
		topMargin=22,
		bottomMargin=20,
	)

	def _txt(valor, limite=60):
		texto = str(valor or "-").strip()
		if len(texto) <= limite:
			return texto
		return f"{texto[: limite - 3]}..."

	estilos = getSampleStyleSheet()
	color_marca = colors.HexColor("#39a900")
	color_titulo_visita = colors.HexColor("#0f766e")
	color_borde = colors.HexColor("#9ca3af")
	color_fondo = colors.HexColor("#f9fafb")

	elementos = [
		Paragraph("<b>Reporte General de Visitas</b>", estilos["Title"]),
		Spacer(1, 4),
		Paragraph(
			f"Generado: {timezone.localtime().strftime('%d/%m/%Y %H:%M')} | Total de visitas: {len(filas)}",
			estilos["Normal"],
		),
		Spacer(1, 10),
	]

	if not filas:
		elementos.append(Paragraph("No hay visitas para los filtros seleccionados.", estilos["Normal"]))
		documento.build(elementos)
		return response

	for indice, fila in enumerate(filas, start=1):
		titulo_visita = Table(
			[[f"Visita {indice}: {_txt(fila['nombre'], 80)} ({fila['tipo']} #{fila['id']})"]],
			colWidths=[780],
		)
		titulo_visita.setStyle(
			TableStyle(
				[
					("BACKGROUND", (0, 0), (-1, -1), color_titulo_visita),
					("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
					("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
					("FONTSIZE", (0, 0), (-1, -1), 10),
					("LEFTPADDING", (0, 0), (-1, -1), 10),
					("TOPPADDING", (0, 0), (-1, -1), 6),
					("BOTTOMPADDING", (0, 0), (-1, -1), 6),
				]
			)
		)
		elementos.append(titulo_visita)
		elementos.append(Spacer(1, 5))

		detalle_visita = [
			["Nombre/Programa", _txt(fila["nombre"], 90), "Tipo", _txt(fila["tipo"], 20)],
			["Responsable", _txt(fila["responsable"], 70), "Documento", _txt(fila["documento"], 30)],
			["Correo", _txt(fila["correo"], 70), "Estado", _txt(fila["estado"], 40)],
			[
				"Fecha Solicitud",
				fila["fecha_solicitud"].strftime("%d/%m/%Y %H:%M"),
				"Fecha Visita",
				fila["fecha_visita"].strftime("%d/%m/%Y") if fila["fecha_visita"] else "-",
			],
			["Cantidad Visitantes", str(fila["cantidad"]), "Codigo", str(fila["id"])],
		]

		tabla_visita = Table(detalle_visita, colWidths=[110, 250, 110, 210])
		tabla_visita.setStyle(
			TableStyle(
				[
					("GRID", (0, 0), (-1, -1), 0.4, color_borde),
					("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e5f3dd")),
					("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#e5f3dd")),
					("BACKGROUND", (1, 0), (1, -1), color_fondo),
					("BACKGROUND", (3, 0), (3, -1), color_fondo),
					("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
					("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
					("FONTSIZE", (0, 0), (-1, -1), 8),
					("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
					("LEFTPADDING", (0, 0), (-1, -1), 7),
					("RIGHTPADDING", (0, 0), (-1, -1), 7),
					("TOPPADDING", (0, 0), (-1, -1), 5),
					("BOTTOMPADDING", (0, 0), (-1, -1), 5),
				]
			)
		)
		elementos.append(tabla_visita)

		if fila["asistentes"]:
			elementos.append(Spacer(1, 7))
			elementos.append(Paragraph(f"<b>Visitantes Registrados ({len(fila['asistentes'])})</b>", estilos["Heading4"]))
			elementos.append(Spacer(1, 3))

			data_asistentes = [["Nombre", "Tipo Doc", "Numero Doc", "Correo", "Telefono", "Estado"]]
			for asistente in fila["asistentes"]:
				data_asistentes.append(
					[
						_txt(asistente["nombre"], 32),
						_txt(asistente["tipo_documento"], 18),
						_txt(asistente["numero_documento"], 16),
						_txt(asistente["correo"], 34),
						_txt(asistente["telefono"], 18),
						_txt(asistente["estado"], 24),
					]
				)

			tabla_asistentes = Table(
				data_asistentes,
				colWidths=[150, 90, 90, 180, 90, 120],
				repeatRows=1,
			)
			tabla_asistentes.setStyle(
				TableStyle(
					[
						("BACKGROUND", (0, 0), (-1, 0), color_marca),
						("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
						("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
						("FONTSIZE", (0, 0), (-1, 0), 8),
						("FONTSIZE", (0, 1), (-1, -1), 7),
						("GRID", (0, 0), (-1, -1), 0.35, color_borde),
						("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#fcfcfc"), colors.HexColor("#f3f4f6")]),
						("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
						("ALIGN", (2, 1), (2, -1), "CENTER"),
						("LEFTPADDING", (0, 0), (-1, -1), 6),
						("RIGHTPADDING", (0, 0), (-1, -1), 6),
						("TOPPADDING", (0, 0), (-1, -1), 4),
						("BOTTOMPADDING", (0, 0), (-1, -1), 4),
					]
				)
			)
			elementos.append(tabla_asistentes)
		else:
			elementos.append(Spacer(1, 6))
			elementos.append(Paragraph("No hay visitantes registrados para esta visita.", estilos["Normal"]))

		if indice < len(filas):
			elementos.append(PageBreak())
		else:
			elementos.append(Spacer(1, 10))

	documento.build(elementos)
	return response


@login_required(login_url="usuarios:login")
@user_passes_test(_es_admin, login_url="core:panel_administrativo")
def descargar_pdf_individual(request, tipo, id_visita):
	"""Descarga un reporte en PDF de una visita individual"""
	from django.shortcuts import get_object_or_404
	
	if tipo == "interna":
		visita = get_object_or_404(VisitaInterna.objects.prefetch_related('asistentes'), id=id_visita)
		datos_visita = {
			"tipo": "Interna",
			"id": visita.id,
			"nombre": visita.nombre_programa,
			"responsable": visita.responsable,
			"tipo_documento": visita.get_tipo_documento_responsable_display(),
			"documento": visita.documento_responsable,
			"correo": visita.correo_responsable,
			"telefono": visita.telefono_responsable,
			"cantidad": visita.cantidad_aprendices,
			"fecha_solicitud": visita.fecha_solicitud,
			"fecha_visita": visita.fecha_visita,
			"hora_inicio": visita.hora_inicio,
			"hora_fin": visita.hora_fin,
			"estado": visita.get_estado_display(),
			"observaciones": visita.observaciones,
		}
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
	elif tipo == "externa":
		visita = get_object_or_404(VisitaExterna.objects.prefetch_related('asistentes'), id=id_visita)
		datos_visita = {
			"tipo": "Externa",
			"id": visita.id,
			"nombre": visita.nombre,
			"responsable": visita.nombre_responsable,
			"tipo_documento": visita.get_tipo_documento_responsable_display(),
			"documento": visita.documento_responsable,
			"correo": visita.correo_responsable,
			"telefono": visita.telefono_responsable,
			"cantidad": visita.cantidad_visitantes,
			"fecha_solicitud": visita.fecha_solicitud,
			"fecha_visita": visita.fecha_visita,
			"hora_inicio": visita.hora_inicio,
			"hora_fin": visita.hora_fin,
			"estado": visita.get_estado_display(),
			"observaciones": visita.observacion if hasattr(visita, 'observacion') else "",
		}
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
	else:
		from django.http import HttpResponseBadRequest
		return HttpResponseBadRequest("Tipo de visita inválido")
	
	response = HttpResponse(content_type="application/pdf")
	response["Content-Disposition"] = f'attachment; filename="reporte_visita_{tipo}_{id_visita}.pdf"'

	documento = SimpleDocTemplate(
		response,
		pagesize=A4,
		leftMargin=30,
		rightMargin=30,
		topMargin=30,
		bottomMargin=30,
	)

	estilos = getSampleStyleSheet()
	elementos = []
	
	# Título
	elementos.append(
		Paragraph(f"<b>Reporte de Visita {datos_visita['tipo']}</b>", estilos["Heading1"])
	)
	elementos.append(Spacer(1, 20))
	
	# Datos de la visita
	elementos.append(Paragraph("<b>Información General</b>", estilos["Heading2"]))
	elementos.append(Spacer(1, 10))
	
	data_general = [
		["Campo", "Valor"],
		["Código de Visita", str(datos_visita["id"])],
		["Tipo de Visita", datos_visita["tipo"]],
		["Nombre/Programa", datos_visita["nombre"]],
		["Estado", datos_visita["estado"]],
		["Fecha de Solicitud", datos_visita["fecha_solicitud"].strftime("%d/%m/%Y %H:%M")],
		["Fecha de Visita", datos_visita["fecha_visita"].strftime("%d/%m/%Y") if datos_visita["fecha_visita"] else "No asignada"],
		["Hora de Inicio", datos_visita["hora_inicio"].strftime("%H:%M") if datos_visita["hora_inicio"] else "-"],
		["Hora de Fin", datos_visita["hora_fin"].strftime("%H:%M") if datos_visita["hora_fin"] else "-"],
		["Cantidad de Visitantes", str(datos_visita["cantidad"])],
	]
	
	if datos_visita["observaciones"]:
		data_general.append(["Observaciones", datos_visita["observaciones"][:100]])
	
	tabla_general = Table(data_general, colWidths=[150, 350])
	tabla_general.setStyle(
		TableStyle([
			("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#39a900")),
			("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
			("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
			("FONTSIZE", (0, 0), (-1, -1), 9),
			("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
			("BACKGROUND", (0, 1), (0, -1), colors.lightgrey),
			("ALIGN", (0, 0), (-1, -1), "LEFT"),
			("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
			("LEFTPADDING", (0, 0), (-1, -1), 10),
			("RIGHTPADDING", (0, 0), (-1, -1), 10),
		])
	)
	elementos.append(tabla_general)
	elementos.append(Spacer(1, 20))
	
	# Datos del responsable
	elementos.append(Paragraph("<b>Datos del Responsable</b>", estilos["Heading2"]))
	elementos.append(Spacer(1, 10))
	
	data_responsable = [
		["Campo", "Valor"],
		["Nombre", datos_visita["responsable"]],
		["Tipo de Documento", datos_visita["tipo_documento"]],
		["Número de Documento", datos_visita["documento"]],
		["Correo Electrónico", datos_visita["correo"]],
		["Teléfono", datos_visita["telefono"]],
	]
	
	tabla_responsable = Table(data_responsable, colWidths=[150, 350])
	tabla_responsable.setStyle(
		TableStyle([
			("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#39a900")),
			("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
			("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
			("FONTSIZE", (0, 0), (-1, -1), 9),
			("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
			("BACKGROUND", (0, 1), (0, -1), colors.lightgrey),
			("ALIGN", (0, 0), (-1, -1), "LEFT"),
			("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
			("LEFTPADDING", (0, 0), (-1, -1), 10),
			("RIGHTPADDING", (0, 0), (-1, -1), 10),
		])
	)
	elementos.append(tabla_responsable)
	elementos.append(Spacer(1, 20))
	
	# Listado de asistentes/visitantes
	if asistentes:
		elementos.append(Paragraph(f"<b>Listado de Visitantes Registrados ({len(asistentes)})</b>", estilos["Heading2"]))
		elementos.append(Spacer(1, 10))
		
		data_asistentes = [
			["Nombre", "Tipo Doc.", "Núm. Doc.", "Correo", "Teléfono", "Estado"]
		]
		
		for asistente in asistentes:
			data_asistentes.append([
				asistente["nombre"][:25],
				asistente["tipo_documento"][:10],
				asistente["numero_documento"],
				asistente["correo"][:22],
				asistente["telefono"],
				asistente["estado"][:15],
			])
		
		tabla_asistentes = Table(data_asistentes, colWidths=[90, 50, 70, 95, 65, 80])
		tabla_asistentes.setStyle(
			TableStyle([
				("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#39a900")),
				("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
				("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
				("FONTSIZE", (0, 0), (-1, -1), 7),
				("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
				("BACKGROUND", (0, 1), (-1, -1), colors.beige),
				("ALIGN", (0, 0), (-1, -1), "CENTER"),
				("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
			])
		)
		elementos.append(tabla_asistentes)
	else:
		elementos.append(Paragraph("<i>No hay visitantes registrados para esta visita.</i>", estilos["Normal"]))
	
	documento.build(elementos)
	return response


@login_required(login_url="usuarios:login")
@user_passes_test(_es_admin, login_url="core:panel_administrativo")
def descargar_excel_individual(request, tipo, id_visita):
	"""Descarga un reporte en Excel de una visita individual"""
	from django.shortcuts import get_object_or_404
	
	if tipo == "interna":
		visita = get_object_or_404(VisitaInterna.objects.prefetch_related('asistentes'), id=id_visita)
		datos_visita = {
			"tipo": "Interna",
			"id": visita.id,
			"nombre": visita.nombre_programa,
			"responsable": visita.responsable,
			"tipo_documento": visita.get_tipo_documento_responsable_display(),
			"documento": visita.documento_responsable,
			"correo": visita.correo_responsable,
			"telefono": visita.telefono_responsable,
			"cantidad": visita.cantidad_aprendices,
			"fecha_solicitud": visita.fecha_solicitud,
			"fecha_visita": visita.fecha_visita,
			"hora_inicio": visita.hora_inicio,
			"hora_fin": visita.hora_fin,
			"estado": visita.get_estado_display(),
			"observaciones": visita.observaciones,
		}
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
	elif tipo == "externa":
		visita = get_object_or_404(VisitaExterna.objects.prefetch_related('asistentes'), id=id_visita)
		datos_visita = {
			"tipo": "Externa",
			"id": visita.id,
			"nombre": visita.nombre,
			"responsable": visita.nombre_responsable,
			"tipo_documento": visita.get_tipo_documento_responsable_display(),
			"documento": visita.documento_responsable,
			"correo": visita.correo_responsable,
			"telefono": visita.telefono_responsable,
			"cantidad": visita.cantidad_visitantes,
			"fecha_solicitud": visita.fecha_solicitud,
			"fecha_visita": visita.fecha_visita,
			"hora_inicio": visita.hora_inicio,
			"hora_fin": visita.hora_fin,
			"estado": visita.get_estado_display(),
			"observaciones": visita.observacion if hasattr(visita, 'observacion') else "",
		}
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
	else:
		from django.http import HttpResponseBadRequest
		return HttpResponseBadRequest("Tipo de visita inválido")
	
	response = HttpResponse(content_type="application/vnd.ms-excel; charset=utf-8")
	response["Content-Disposition"] = f'attachment; filename="reporte_visita_{tipo}_{id_visita}.xls"'
	response.write("\ufeff")

	response.write("<table border='1'>")
	
	# Título
	response.write(
		"<tr style='background-color: #39a900; color: white; font-weight: bold;'>"
		f"<th colspan='2'>Reporte de Visita {datos_visita['tipo']} - Código: {datos_visita['id']}</th>"
		"</tr>"
	)
	
	# Información General
	response.write(
		"<tr style='background-color: #d4edda;'>"
		"<td colspan='2'><strong>INFORMACIÓN GENERAL</strong></td>"
		"</tr>"
	)
	response.write(f"<tr><td><strong>Código de Visita</strong></td><td>{datos_visita['id']}</td></tr>")
	response.write(f"<tr><td><strong>Tipo de Visita</strong></td><td>{escape(datos_visita['tipo'])}</td></tr>")
	response.write(f"<tr><td><strong>Nombre/Programa</strong></td><td>{escape(datos_visita['nombre'])}</td></tr>")
	response.write(f"<tr><td><strong>Estado</strong></td><td>{escape(datos_visita['estado'])}</td></tr>")
	response.write(f"<tr><td><strong>Fecha de Solicitud</strong></td><td>{datos_visita['fecha_solicitud'].strftime('%d/%m/%Y %H:%M')}</td></tr>")
	fecha_visita_str = datos_visita["fecha_visita"].strftime("%d/%m/%Y") if datos_visita["fecha_visita"] else "No asignada"
	response.write(f"<tr><td><strong>Fecha de Visita</strong></td><td>{fecha_visita_str}</td></tr>")
	hora_inicio_str = datos_visita["hora_inicio"].strftime("%H:%M") if datos_visita["hora_inicio"] else "-"
	hora_fin_str = datos_visita["hora_fin"].strftime("%H:%M") if datos_visita["hora_fin"] else "-"
	response.write(f"<tr><td><strong>Hora de Inicio</strong></td><td>{hora_inicio_str}</td></tr>")
	response.write(f"<tr><td><strong>Hora de Fin</strong></td><td>{hora_fin_str}</td></tr>")
	response.write(f"<tr><td><strong>Cantidad de Visitantes</strong></td><td>{datos_visita['cantidad']}</td></tr>")
	
	if datos_visita["observaciones"]:
		response.write(f"<tr><td><strong>Observaciones</strong></td><td>{escape(datos_visita['observaciones'])}</td></tr>")
	
	# Información del Responsable
	response.write(
		"<tr style='background-color: #d4edda;'>"
		"<td colspan='2'><strong>DATOS DEL RESPONSABLE</strong></td>"
		"</tr>"
	)
	response.write(f"<tr><td><strong>Nombre</strong></td><td>{escape(datos_visita['responsable'])}</td></tr>")
	response.write(f"<tr><td><strong>Tipo de Documento</strong></td><td>{escape(datos_visita['tipo_documento'])}</td></tr>")
	response.write(f"<tr><td><strong>Número de Documento</strong></td><td>{escape(datos_visita['documento'])}</td></tr>")
	response.write(f"<tr><td><strong>Correo Electrónico</strong></td><td>{escape(datos_visita['correo'])}</td></tr>")
	response.write(f"<tr><td><strong>Teléfono</strong></td><td>{escape(datos_visita['telefono'])}</td></tr>")
	
	# Listado de asistentes
	if asistentes:
		response.write(
			"<tr style='background-color: #d4edda;'>"
			f"<td colspan='2'><strong>LISTADO DE VISITANTES REGISTRADOS ({len(asistentes)})</strong></td>"
			"</tr>"
		)
		response.write(
			"<tr style='background-color: #39a900; color: white; font-weight: bold;'>"
			"<th>Nombre</th><th>Tipo Doc</th><th>Número Doc</th>"
			"<th>Correo</th><th>Teléfono</th><th>Estado</th>"
			"</tr>"
		)
		
		for asistente in asistentes:
			response.write(
				"<tr>"
				f"<td>{escape(asistente['nombre'])}</td>"
				f"<td>{escape(asistente['tipo_documento'])}</td>"
				f"<td>{escape(asistente['numero_documento'])}</td>"
				f"<td>{escape(asistente['correo'])}</td>"
				f"<td>{escape(asistente['telefono'])}</td>"
				f"<td>{escape(asistente['estado'])}</td>"
				"</tr>"
			)
	else:
		response.write(
			"<tr style='background-color: #d4edda;'>"
			"<td colspan='2'><strong>LISTADO DE VISITANTES REGISTRADOS</strong></td>"
			"</tr>"
		)
		response.write(
			"<tr>"
			"<td colspan='2'><i>No hay visitantes registrados para esta visita.</i></td>"
			"</tr>"
		)
	
	response.write("</table>")
	return response
