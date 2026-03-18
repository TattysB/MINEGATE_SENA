import calendar
from datetime import date

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from calendario.models import ReservaHorario
from visitaExterna.models import (
	HistorialAccionVisitaExterna,
	HistorialReprogramacion as HistorialReprogramacionExterna,
	VisitaExterna,
)
from visitaInterna.models import (
	HistorialAccionVisitaInterna,
	HistorialReprogramacion as HistorialReprogramacionInterna,
	VisitaInterna,
)
from .models import AprobacionRegistro
from django.contrib.auth.decorators import permission_required


def _formatear_fecha_local(fecha_dt):
	if not fecha_dt:
		return "N/A"
	if timezone.is_aware(fecha_dt):
		fecha_dt = timezone.localtime(fecha_dt)
	return fecha_dt.strftime("%d/%m/%Y %H:%M")


def _formatear_fecha_local_am_pm(fecha_dt):
	if not fecha_dt:
		return "N/A"
	if timezone.is_aware(fecha_dt):
		fecha_dt = timezone.localtime(fecha_dt)
	return fecha_dt.strftime("%d/%m/%Y %I:%M %p")


def es_coordinador(user):
	return user.is_authenticated and user.groups.filter(name="coordinador").exists()


@login_required(login_url="usuarios:login")
@user_passes_test(es_coordinador, login_url="core:panel_administrativo")
def panel_coordinador(request):
	context = {
		"solo_coordinador": True,
		"panel_role_label": "Coordinador",
		"perfil": getattr(request.user, "perfil", None),
	}
	return render(request, "coordinador/panel_coordinador.html", context)


@login_required(login_url="usuarios:login")
@user_passes_test(es_coordinador, login_url="core:panel_administrativo")
def calendario_coordinador(request, year=None, month=None):
	today = date.today()
	year = int(year) if year else today.year
	month = int(month) if month else today.month

	cal = calendar.Calendar(firstweekday=6)
	month_days = list(cal.itermonthdates(year, month))

	weeks_raw = [month_days[i:i + 7] for i in range(0, len(month_days), 7)]
	weeks = []
	for week in weeks_raw:
		row = []
		for day in week:
			row.append(
				{
					"date": day,
					"is_other_month": day.month != month,
					"is_today": day == today,
					"is_sunday": day.weekday() == 6,
				}
			)
		weeks.append(row)

	meses_es = [
		"", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
		"Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
	]

	reservas_mes = ReservaHorario.objects.filter(fecha__year=year, fecha__month=month)
	fechas_pendientes = set(
		r.fecha.isoformat() for r in reservas_mes if r.estado == "pendiente"
	)
	fechas_confirmadas = set(
		r.fecha.isoformat() for r in reservas_mes if r.estado == "confirmada"
	)

	context = {
		"year": year,
		"month": month,
		"month_name": meses_es[month],
		"weeks": weeks,
		"today": today,
		"fechas_pendientes": fechas_pendientes,
		"fechas_confirmadas": fechas_confirmadas,
		"include_assets": request.headers.get("x-requested-with") != "XMLHttpRequest",
	}
	return render(request, "coordinador/calendario_coordinador.html", context)


@login_required(login_url="usuarios:login")
@user_passes_test(es_coordinador, login_url="core:panel_administrativo")
def resumen_dia_coordinador(request, day):
	try:
		selected_day = date.fromisoformat(day)
	except ValueError:
		return JsonResponse({"ok": False, "error": "Fecha inválida"}, status=400)

	reservas = ReservaHorario.objects.filter(fecha=selected_day).order_by("hora_inicio")

	visitas = []
	for reserva in reservas:
		if reserva.visita_interna:
			visita = reserva.visita_interna
			visitas.append(
				{
					"visita_id": visita.id,
					"tipo_slug": "interna",
					"tipo": "Interna",
					"estado_codigo": reserva.estado,
					"estado": reserva.get_estado_display(),
					"responsable": visita.responsable,
					"institucion_programa": visita.nombre_programa,
					"hora": f"{reserva.hora_inicio.strftime('%H:%M')} - {reserva.hora_fin.strftime('%H:%M')}",
				}
			)
		elif reserva.visita_externa:
			visita = reserva.visita_externa
			visitas.append(
				{
					"visita_id": visita.id,
					"tipo_slug": "externa",
					"tipo": "Externa",
					"estado_codigo": reserva.estado,
					"estado": reserva.get_estado_display(),
					"responsable": visita.nombre_responsable,
					"institucion_programa": visita.nombre,
					"hora": f"{reserva.hora_inicio.strftime('%H:%M')} - {reserva.hora_fin.strftime('%H:%M')}",
				}
			)

	return JsonResponse(
		{
			"ok": True,
			"day": selected_day.isoformat(),
			"visitas": visitas,
		}
	)


@login_required(login_url="usuarios:login")
@user_passes_test(es_coordinador, login_url="core:panel_administrativo")
def api_solicitudes_coordinacion(request):
	tipo = request.GET.get("tipo", "internas")
	buscar = request.GET.get("buscar", "").strip()

	visitas_data = []

	if tipo == "internas":
		visitas = VisitaInterna.objects.filter(estado="enviada_coordinacion").order_by(
			"-fecha_solicitud", "-id"
		)
		if buscar:
			visitas = visitas.filter(responsable__icontains=buscar)

		for visita in visitas:
			visitas_data.append(
				{
					"id": visita.id,
					"tipo": "interna",
					"tipo_display": "Interna (SENA)",
					"responsable": visita.responsable,
					"institucion": visita.nombre_programa or "N/A",
					"correo": visita.correo_responsable,
					"cantidad": visita.cantidad_aprendices,
					"fecha_solicitud": _formatear_fecha_local(visita.fecha_solicitud),
					"fecha_solicitud_orden": visita.fecha_solicitud.isoformat() if visita.fecha_solicitud else "",
				}
			)
	elif tipo == "externas":
		visitas = VisitaExterna.objects.filter(estado="enviada_coordinacion").order_by(
			"-fecha_solicitud", "-id"
		)
		if buscar:
			visitas = visitas.filter(nombre_responsable__icontains=buscar)

		for visita in visitas:
			visitas_data.append(
				{
					"id": visita.id,
					"tipo": "externa",
					"tipo_display": "Externa (Institución)",
					"responsable": visita.nombre_responsable,
					"institucion": visita.nombre or "N/A",
					"correo": visita.correo_responsable,
					"cantidad": visita.cantidad_visitantes,
					"fecha_solicitud": _formatear_fecha_local(visita.fecha_solicitud),
					"fecha_solicitud_orden": visita.fecha_solicitud.isoformat() if visita.fecha_solicitud else "",
				}
			)
	else:
		# tipo == 'todas' o cualquier otro valor: combinar internas y externas
		visitas_int = VisitaInterna.objects.filter(estado="enviada_coordinacion").order_by("-fecha_solicitud", "-id")
		visitas_ext = VisitaExterna.objects.filter(estado="enviada_coordinacion").order_by("-fecha_solicitud", "-id")
		if buscar:
			visitas_int = visitas_int.filter(responsable__icontains=buscar)
			visitas_ext = visitas_ext.filter(nombre_responsable__icontains=buscar)

		for visita in visitas_int:
			visitas_data.append(
				{
					"id": visita.id,
					"tipo": "interna",
					"tipo_display": "Interna (SENA)",
					"responsable": visita.responsable,
					"institucion": visita.nombre_programa or "N/A",
					"correo": visita.correo_responsable,
					"cantidad": visita.cantidad_aprendices,
					"fecha_solicitud": _formatear_fecha_local(visita.fecha_solicitud),
					"fecha_solicitud_orden": visita.fecha_solicitud.isoformat() if visita.fecha_solicitud else "",
				}
			)
		for visita in visitas_ext:
			visitas_data.append(
				{
					"id": visita.id,
					"tipo": "externa",
					"tipo_display": "Externa (Institución)",
					"responsable": visita.nombre_responsable,
					"institucion": visita.nombre or "N/A",
					"correo": visita.correo_responsable,
					"cantidad": visita.cantidad_visitantes,
					"fecha_solicitud": _formatear_fecha_local(visita.fecha_solicitud),
					"fecha_solicitud_orden": visita.fecha_solicitud.isoformat() if visita.fecha_solicitud else "",
				}
			)

		# Mantener el orden correcto por fecha en la vista combinada.
		visitas_data.sort(
			key=lambda item: item.get("fecha_solicitud_orden", ""),
			reverse=True,
		)

	return JsonResponse({"visitas": visitas_data})


@login_required(login_url="usuarios:login")
@user_passes_test(es_coordinador, login_url="core:panel_administrativo")
def api_accion_coordinacion(request, tipo, visita_id, accion):
	if accion == "detalle" and request.method == "GET":
		if tipo == "interna":
			visita = get_object_or_404(VisitaInterna, pk=visita_id)
			detalle = {
				"id": visita.id,
				"tipo": "Interna (SENA)",
				"estado": visita.get_estado_display(),
				"responsable": visita.responsable,
				"tipo_documento": visita.get_tipo_documento_responsable_display() if visita.tipo_documento_responsable else "N/A",
				"documento": visita.documento_responsable or "N/A",
				"correo": visita.correo_responsable or "N/A",
				"telefono": visita.telefono_responsable or "N/A",
				"institucion_programa": visita.nombre_programa or "N/A",
				"ficha": str(visita.numero_ficha) if visita.numero_ficha else "N/A",
				"cantidad": visita.cantidad_aprendices,
				"fecha_solicitud": _formatear_fecha_local_am_pm(visita.fecha_solicitud),
				"fecha_visita": visita.fecha_visita.strftime("%d/%m/%Y") if visita.fecha_visita else "N/A",
				"hora_inicio": visita.hora_inicio.strftime("%I:%M %p") if visita.hora_inicio else "N/A",
				"hora_fin": visita.hora_fin.strftime("%I:%M %p") if visita.hora_fin else "N/A",
				"observaciones": visita.observaciones or "Sin observaciones",
			}
		else:
			visita = get_object_or_404(VisitaExterna, pk=visita_id)
			detalle = {
				"id": visita.id,
				"tipo": "Externa (Institución)",
				"estado": visita.get_estado_display(),
				"responsable": visita.nombre_responsable,
				"tipo_documento": visita.get_tipo_documento_responsable_display() if visita.tipo_documento_responsable else "N/A",
				"documento": visita.documento_responsable or "N/A",
				"correo": visita.correo_responsable or "N/A",
				"telefono": visita.telefono_responsable or "N/A",
				"institucion_programa": visita.nombre or "N/A",
				"ficha": "N/A",
				"cantidad": visita.cantidad_visitantes,
				"fecha_solicitud": _formatear_fecha_local_am_pm(visita.fecha_solicitud),
				"fecha_visita": visita.fecha_visita.strftime("%d/%m/%Y") if visita.fecha_visita else "N/A",
				"hora_inicio": visita.hora_inicio.strftime("%I:%M %p") if visita.hora_inicio else "N/A",
				"hora_fin": visita.hora_fin.strftime("%I:%M %p") if visita.hora_fin else "N/A",
				"observaciones": visita.observacion or "Sin observaciones",
			}

		return JsonResponse({"ok": True, "detalle": detalle})

	if request.method != "POST":
		return JsonResponse({"success": False, "error": "Método no permitido"}, status=405)

	if tipo == "interna":
		visita = get_object_or_404(VisitaInterna, pk=visita_id)

		def registrar(descripcion):
			HistorialAccionVisitaInterna.objects.create(
				visita=visita,
				usuario=request.user,
				tipo_accion="aprobacion" if accion == "aprobar" else "rechazo",
				descripcion=descripcion,
				ip_address=request.META.get("REMOTE_ADDR"),
			)

	else:
		visita = get_object_or_404(VisitaExterna, pk=visita_id)

		def registrar(descripcion):
			HistorialAccionVisitaExterna.objects.create(
				visita=visita,
				usuario=request.user,
				tipo_accion="aprobacion" if accion == "aprobar" else "rechazo",
				descripcion=descripcion,
				ip_address=request.META.get("REMOTE_ADDR"),
			)

	if visita.estado != "enviada_coordinacion":
		return JsonResponse(
			{
				"success": False,
				"error": "La visita ya no está pendiente de revisión por coordinación",
			}
		)

	if accion == "aprobar":
		visita.estado = "pendiente"
		visita.save(update_fields=["estado"])
		registrar(
			f"Solicitud aprobada por coordinación ({request.user.username}). Pendiente aprobación administrativa."
		)
		# Registrar en el log de aprobaciones para el panel de Registro
		try:
			if tipo == 'interna':
				AprobacionRegistro.objects.create(
					visita_id=visita.id,
					visita_tipo='interna',
					responsable=visita.responsable,
					institucion=visita.nombre_programa or '',
					correo=visita.correo_responsable or '',
					cantidad=getattr(visita, 'cantidad_aprendices', None),
					aprobado_por=request.user,
				)
			else:
				AprobacionRegistro.objects.create(
					visita_id=visita.id,
					visita_tipo='externa',
					responsable=visita.nombre_responsable,
					institucion=visita.nombre or '',
					correo=visita.correo_responsable or '',
					cantidad=getattr(visita, 'cantidad_visitantes', None),
					aprobado_por=request.user,
				)
		except Exception:
			# No bloquear la operación si el registro falla
			pass
		return JsonResponse(
			{
				"success": True,
				"message": "✅ Solicitud aprobada. Enviada al administrador para la segunda aprobación.",
			}
		)

	if accion == "rechazar":
		observaciones = request.POST.get("observaciones", "").strip()
		fecha_anterior = timezone.now()
		if getattr(visita, "fecha_visita", None) and getattr(visita, "hora_inicio", None):
			fecha_anterior = timezone.datetime.combine(visita.fecha_visita, visita.hora_inicio)

		if tipo == "interna":
			HistorialReprogramacionInterna.objects.create(
				visita_interna=visita,
				fecha_anterior=fecha_anterior,
				motivo=observaciones or "Reprogramación solicitada por coordinación.",
				solicitado_por=request.user,
				tipo="coordinador",
				completada=False,
			)
		else:
			HistorialReprogramacionExterna.objects.create(
				visita_externa=visita,
				fecha_anterior=fecha_anterior,
				motivo=observaciones or "Reprogramación solicitada por coordinación.",
				solicitado_por=request.user,
				tipo="coordinador",
				completada=False,
			)

		visita.estado = "reprogramacion_solicitada"
		visita.save(update_fields=["estado"])
		ReservaHorario.liberar_reserva(visita, tipo)
		registrar(
			f"Solicitud enviada a reprogramación por coordinación ({request.user.username}). Motivo: {observaciones}"
			if observaciones
			else f"Solicitud enviada a reprogramación por coordinación ({request.user.username})."
		)
		return JsonResponse({"success": True, "message": "🔄 Solicitud enviada a reprogramación. El instructor deberá elegir una nueva fecha."})


@login_required(login_url="usuarios:login")
@user_passes_test(es_coordinador, login_url="core:panel_administrativo")
def registro_coordinacion(request):
	registros = AprobacionRegistro.objects.all()[:100]
	return render(request, "coordinador/registro_coordinacion.html", {"registros": registros})
