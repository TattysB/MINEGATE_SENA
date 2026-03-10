import calendar
from datetime import date

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from calendario.models import ReservaHorario
from visitaExterna.models import HistorialAccionVisitaExterna, VisitaExterna
from visitaInterna.models import HistorialAccionVisitaInterna, VisitaInterna


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
					"fecha_solicitud": (
						visita.fecha_solicitud.strftime("%d/%m/%Y %H:%M")
						if visita.fecha_solicitud
						else "N/A"
					),
				}
			)
	else:
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
					"fecha_solicitud": (
						visita.fecha_solicitud.strftime("%d/%m/%Y %H:%M")
						if visita.fecha_solicitud
						else "N/A"
					),
				}
			)

	return JsonResponse({"visitas": visitas_data})


@login_required(login_url="usuarios:login")
@user_passes_test(es_coordinador, login_url="core:panel_administrativo")
def api_accion_coordinacion(request, tipo, visita_id, accion):
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
		return JsonResponse(
			{
				"success": True,
				"message": "✅ Solicitud aprobada. Enviada al administrador para la segunda aprobación.",
			}
		)

	if accion == "rechazar":
		observaciones = request.POST.get("observaciones", "").strip()
		visita.estado = "rechazada"
		visita.save(update_fields=["estado"])
		ReservaHorario.liberar_reserva(visita, tipo)
		registrar(
			f"Solicitud rechazada por coordinación ({request.user.username}). Motivo: {observaciones}"
			if observaciones
			else f"Solicitud rechazada por coordinación ({request.user.username})."
		)
		return JsonResponse({"success": True, "message": "❌ Solicitud rechazada por coordinación."})

	return JsonResponse({"success": False, "error": "Acción no válida"}, status=400)
