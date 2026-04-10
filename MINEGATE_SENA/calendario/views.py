from django.shortcuts import render, redirect
import calendar
from datetime import date, datetime, timedelta
from .models import Availability, ReservaHorario
from django.views.decorators.http import require_POST, require_GET
from django.http import JsonResponse
from django.db.utils import OperationalError
from django.db.models import Count
import re
import traceback


def _serialize_day_ranges_simple(records):
	"""Serializa los rangos de un día para mostrar al visitante"""
	ranges = []
	for rec in records:
		start_label = rec.time.strftime('%H:%M')
		if rec.end_time:
			end_label = rec.end_time.strftime('%H:%M')
			ranges.append({'start': start_label, 'end': end_label, 'label': f"{start_label} - {end_label}"})
		else:
			ranges.append({'start': start_label, 'end': start_label, 'label': start_label})
	return sorted(ranges, key=lambda r: r['start'])


def _serialize_free_ranges_for_day(day_date):
	"""Devuelve rangos libres del día excluyendo reservas superpuestas."""
	records = list(Availability.objects.filter(date=day_date).order_by('time', 'end_time'))
	reservas = list(ReservaHorario.objects.filter(fecha=day_date))
	ranges_disponibles = []

	for rec in records:
		start_time = rec.time
		end_time = rec.end_time or rec.time

		horario_libre = True
		for reserva in reservas:
			if start_time < reserva.hora_fin and end_time > reserva.hora_inicio:
				horario_libre = False
				break

		if horario_libre:
			start_label = start_time.strftime('%H:%M')
			if rec.end_time:
				end_label = rec.end_time.strftime('%H:%M')
				ranges_disponibles.append(
					{
						'start': start_label,
						'end': end_label,
						'label': f"{start_label} - {end_label}",
					}
				)
			else:
				ranges_disponibles.append(
					{
						'start': start_label,
						'end': start_label,
						'label': start_label,
					}
				)

	return sorted(ranges_disponibles, key=lambda r: r['start'])


def _format_date_es(day_date):
	meses = [
		'',
		'enero',
		'febrero',
		'marzo',
		'abril',
		'mayo',
		'junio',
		'julio',
		'agosto',
		'septiembre',
		'octubre',
		'noviembre',
		'diciembre',
	]
	return f"{day_date.day} de {meses[day_date.month]} de {day_date.year}"


@require_GET
def day_summary(request, day):
	"""Resumen del día para panel lateral del calendario administrativo."""
	try:
		day_date = datetime.strptime(day.strip(), '%Y-%m-%d').date()
	except Exception:
		return JsonResponse({'ok': False, 'error': 'Fecha inválida'}, status=400)

	reservas = list(
		ReservaHorario.objects.filter(fecha=day_date)
		.select_related('visita_interna', 'visita_externa')
		.order_by('hora_inicio')
	)
	ranges_libres = _serialize_free_ranges_for_day(day_date)

	visitas = []
	for reserva in reservas:
		if reserva.visita_interna:
			tipo = 'interna'
			nombre = reserva.visita_interna.nombre_programa or 'Visita interna'
			responsable = reserva.visita_interna.responsable or 'Sin responsable'
			documento = reserva.visita_interna.documento_responsable or ''
		elif reserva.visita_externa:
			tipo = 'externa'
			nombre = reserva.visita_externa.nombre or 'Visita externa'
			responsable = reserva.visita_externa.nombre_responsable or 'Sin responsable'
			documento = reserva.visita_externa.documento_responsable or ''
		else:
			tipo = 'sin_tipo'
			nombre = 'Visita'
			responsable = 'Sin responsable'
			documento = ''

		visitas.append(
			{
				'id_reserva': reserva.id,
				'tipo': tipo,
				'titulo': nombre,
				'responsable': responsable,
				'documento_responsable': documento,
				'estado': reserva.estado,
				'estado_label': 'Pendiente por revisar'
				if reserva.estado == 'pendiente'
				else 'Confirmada',
				'horario': f"{reserva.hora_inicio.strftime('%H:%M')} - {reserva.hora_fin.strftime('%H:%M')}",
			}
		)

	has_confirmadas = any(r.estado == 'confirmada' for r in reservas)
	has_pendientes = any(r.estado == 'pendiente' for r in reservas)
	has_available = len(ranges_libres) > 0

	if has_confirmadas:
		day_state = 'occupied'
	elif has_pendientes:
		day_state = 'pending'
	elif has_available:
		day_state = 'available'
	else:
		day_state = 'no-available'

	return JsonResponse(
		{
			'ok': True,
			'date': day_date.isoformat(),
			'date_formatted': _format_date_es(day_date),
			'day_state': day_state,
			'available_ranges': ranges_libres,
			'visitas': visitas,
			'stats': {
				'total_visitas': len(visitas),
				'pendientes': len([v for v in visitas if v['estado'] == 'pendiente']),
				'confirmadas': len([v for v in visitas if v['estado'] == 'confirmada']),
				'horarios_disponibles': len(ranges_libres),
			},
		}
	)


def calendario_seleccion(request, year=None, month=None):
	"""Vista del calendario para seleccionar una fecha disponible para nueva visita"""
	today = date.today()
	if year is None:
		year = today.year
	else:
		year = int(year)
	if month is None:
		month = today.month
	else:
		month = int(month)

	cal = calendar.Calendar(firstweekday=6)
	month_days = list(cal.itermonthdates(year, month))

	weeks_raw = [month_days[i:i+7] for i in range(0, len(month_days), 7)]
	weeks = []
	for week in weeks_raw:
		row = []
		for d in week:
			row.append({
				'date': d,
				'is_other_month': d.month != month,
				'is_today': d == today,
				'is_sunday': d.weekday() == 6,
				'is_past': d < today,
			})
		weeks.append(row)

	meses_es = [
		'', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
		'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
	]

	is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

	try:
		start_month = date(year, month, 1)
		next_month = (start_month.replace(day=28) + timedelta(days=4)).replace(day=1)
		end_month = next_month - timedelta(days=1)
		av_qs = Availability.objects.filter(date__gte=today, date__lte=end_month)
		available_dates = set(a.date.isoformat() for a in av_qs)
		
		reservas_qs = ReservaHorario.objects.filter(
			fecha__gte=today,
			fecha__lte=end_month
		)
		
		reservas_por_fecha = {}
		for reserva in reservas_qs:
			fecha_str = reserva.fecha.isoformat()
			if fecha_str not in reservas_por_fecha:
				reservas_por_fecha[fecha_str] = []
			reservas_por_fecha[fecha_str].append(reserva)
		
		fechas_completamente_ocupadas = set()
		for fecha_str in list(available_dates):
			if fecha_str in reservas_por_fecha:
				fecha_date = datetime.strptime(fecha_str, '%Y-%m-%d').date()
				disponibilidades = list(Availability.objects.filter(date=fecha_date))
				reservas_del_dia = reservas_por_fecha[fecha_str]
				
				todos_ocupados = True
				for disp in disponibilidades:
					start_time = disp.time
					end_time = disp.end_time or disp.time
					
					horario_libre = True
					for reserva in reservas_del_dia:
						if start_time < reserva.hora_fin and end_time > reserva.hora_inicio:
							horario_libre = False
							break
					
					if horario_libre:
						todos_ocupados = False
						break
				
				if todos_ocupados:
					fechas_completamente_ocupadas.add(fecha_str)
		
		available_dates = available_dates - fechas_completamente_ocupadas
		
	except Exception:
		available_dates = set()

	context = {
		'year': year,
		'month': month,
		'month_name': meses_es[month],
		'weeks': weeks,
		'today': today,
		'available_dates': available_dates,
		'include_assets': not is_ajax,
		'modo_seleccion': True,
	}

	if is_ajax:
		return render(request, 'calendario_seleccion.html', context)
	return render(request, 'calendario_seleccion.html', context)


@require_GET
def horarios_disponibles(request, day):
	"""Devuelve los horarios disponibles para un día específico, excluyendo los ya reservados"""
	try:
		day_date = datetime.strptime(day.strip(), '%Y-%m-%d').date()
	except Exception:
		return JsonResponse({'ok': False, 'error': 'Fecha inválida'}, status=400)

	if day_date < date.today():
		return JsonResponse({'ok': False, 'error': 'No se puede seleccionar fechas pasadas'}, status=400)

	ranges = _serialize_free_ranges_for_day(day_date)
	
	return JsonResponse({
		'ok': True,
		'date': day_date.isoformat(),
		'date_formatted': _format_date_es(day_date),
		'ranges': ranges,
		'has_availability': len(ranges) > 0
	})



def calendario_mes(request, year=None, month=None):
	today = date.today()
	if year is None:
		year = today.year
	else:
		year = int(year)
	if month is None:
		month = today.month
	else:
		month = int(month)

	cal = calendar.Calendar(firstweekday=6)  # semana inicia en Domingo
	month_days = list(cal.itermonthdates(year, month))

	weeks_raw = [month_days[i:i+7] for i in range(0, len(month_days), 7)]
	weeks = []
	for week in weeks_raw:
		row = []
		for d in week:
			row.append({
				'date': d,
				'is_other_month': d.month != month,
				'is_today': d == today,
				'is_past': d < today,
				'is_sunday': d.weekday() == 6,
			})
		weeks.append(row)

	meses_es = [
		'', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
		'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
	]

	is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

	context = {
		'year': year,
		'month': month,
		'month_name': meses_es[month],
		'weeks': weeks,
		'today': today,
		'include_assets': not is_ajax,
	}

	try:
		start_month = date(year, month, 1)
		next_month = (start_month.replace(day=28) + timedelta(days=4)).replace(day=1)
		end_month = next_month - timedelta(days=1)
		av_qs = Availability.objects.filter(date__gte=start_month, date__lte=end_month)
		available_dates = set(a.date.isoformat() for a in av_qs)
		try:
			session_dates = request.session.pop('temp_available_dates', None)
			if session_dates:
				available_dates.update(session_dates)
				request.session.modified = True
		except Exception:
			pass
		context['available_dates'] = available_dates
		
		reservas_qs = ReservaHorario.objects.filter(
			fecha__gte=start_month,
			fecha__lte=end_month
		)
		fechas_pendientes = set()
		fechas_confirmadas = set()
		for reserva in reservas_qs:
			fecha_str = reserva.fecha.isoformat()
			if reserva.estado == 'pendiente':
				fechas_pendientes.add(fecha_str)
			elif reserva.estado == 'confirmada':
				fechas_confirmadas.add(fecha_str)
		
		context['fechas_pendientes'] = fechas_pendientes
		context['fechas_confirmadas'] = fechas_confirmadas
		
	except Exception:
		context['available_dates'] = set()
		context['fechas_pendientes'] = set()
		context['fechas_confirmadas'] = set()

	if is_ajax:
		return render(request, 'calendario.html', context)

	return render(request, 'calendario.html', context)


def _normalize_time_part(p):
	if not p:
		return None
	s = p.lower().replace('.', '').replace('\u00A0', ' ').strip()
	for fmt in ('%H:%M', '%I:%M %p', '%I:%M%p', '%I %p'):
		try:
			from datetime import datetime as _dt
			t = _dt.strptime(s, fmt).time()
			return t.strftime('%H:%M')
		except Exception:
			continue
	m = re.match(r'^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$', s)
	if not m:
		return None
	h = int(m.group(1))
	mm = m.group(2)
	mer = m.group(3)
	minute = int(mm) if mm else 0
	if mer:
		mer = mer.lower()
		if mer == 'pm' and h != 12:
			h += 12
		if mer == 'am' and h == 12:
			h = 0
	if h < 0 or h > 23 or minute < 0 or minute > 59:
		return None
	return f"{h:02d}:{minute:02d}"


def _parse_ranges(ranges_raw):
	ranges = []
	for raw in ranges_raw:
		if '-' not in raw:
			continue
		left, right = raw.split('-', 1)
		start_label = _normalize_time_part(left)
		end_label = _normalize_time_part(right)
		if not start_label or not end_label:
			continue
		start_dt = datetime.strptime(start_label, '%H:%M')
		end_dt = datetime.strptime(end_label, '%H:%M')
		if end_dt <= start_dt:
			continue
		ranges.append((start_label, end_label))

	seen = set()
	ordered_ranges = []
	for start_label, end_label in sorted(ranges):
		key = f"{start_label}-{end_label}"
		if key not in seen:
			seen.add(key)
			ordered_ranges.append((start_label, end_label))
	return ordered_ranges


def _serialize_day_ranges(records):
	ranges = []
	legacy_times = []
	for rec in records:
		start_label = rec.time.strftime('%H:%M')
		if rec.end_time:
			end_label = rec.end_time.strftime('%H:%M')
			ranges.append({'start': start_label, 'end': end_label, 'label': f"{start_label}-{end_label}"})
		else:
			legacy_times.append(start_label)

	if legacy_times:
		legacy_times_sorted = sorted(set(legacy_times))
		if legacy_times_sorted:
			group_start = legacy_times_sorted[0]
			group_prev_dt = datetime.strptime(group_start, '%H:%M')
			for label in legacy_times_sorted[1:]:
				current_dt = datetime.strptime(label, '%H:%M')
				if current_dt - group_prev_dt == timedelta(minutes=30):
					group_prev_dt = current_dt
					continue
				end_label = (group_prev_dt + timedelta(minutes=30)).strftime('%H:%M')
				ranges.append({'start': group_start, 'end': end_label, 'label': f"{group_start}-{end_label}"})
				group_start = label
				group_prev_dt = current_dt
			end_label = (group_prev_dt + timedelta(minutes=30)).strftime('%H:%M')
			ranges.append({'start': group_start, 'end': end_label, 'label': f"{group_start}-{end_label}"})

	ranges_sorted = sorted(ranges, key=lambda r: (r['start'], r['end']))
	return ranges_sorted


def _parse_day(day_str):
	try:
		return datetime.strptime(day_str.strip(), '%Y-%m-%d').date()
	except Exception:
		return None


@require_GET
def day_availability(request, day):
	day_date = _parse_day(day)
	if not day_date:
		return JsonResponse({'ok': False, 'error': 'Fecha inválida'}, status=400)

	qs = list(Availability.objects.filter(date=day_date).order_by('time', 'end_time'))
	ranges = _serialize_day_ranges(qs)
	return JsonResponse({'ok': True, 'date': day_date.isoformat(), 'ranges': ranges, 'is_available': len(ranges) > 0})


@require_POST
def update_day_availability(request):
	day_str = request.POST.get('date', '')
	day_date = _parse_day(day_str)
	if not day_date:
		return JsonResponse({'ok': False, 'error': 'Fecha inválida'}, status=400)

	if day_date < date.today():
		return JsonResponse({'ok': False, 'error': 'No se puede habilitar disponibilidad en fechas pasadas'}, status=400)

	if day_date.weekday() == 6:
		return JsonResponse({'ok': False, 'error': 'No se puede configurar domingo'}, status=400)

	ranges_raw = [r.strip() for r in request.POST.getlist('ranges') if r and r.strip()]
	parsed_ranges = _parse_ranges(ranges_raw)

	try:
		Availability.objects.filter(date=day_date).delete()
		for start_label, end_label in parsed_ranges:
			start_value = datetime.strptime(start_label, '%H:%M').time()
			end_value = datetime.strptime(end_label, '%H:%M').time()
			Availability.objects.get_or_create(date=day_date, time=start_value, end_time=end_value)
	except OperationalError as e:
		print(f"DB Error en update_day_availability: {e}")
		traceback.print_exc()
		return JsonResponse({'ok': False, 'error': f'Error de base de datos: {e}'}, status=500)

	records = list(Availability.objects.filter(date=day_date).order_by('time', 'end_time'))
	ranges = _serialize_day_ranges(records)

	return JsonResponse({
		'ok': True,
		'date': day_date.isoformat(),
		'ranges': ranges,
		'is_available': len(ranges) > 0,
		'available_dates': [day_date.isoformat()] if ranges else []
	})


@require_POST
def delete_day_availability(request):
	day_str = request.POST.get('date', '')
	day_date = _parse_day(day_str)
	if not day_date:
		return JsonResponse({'ok': False, 'error': 'Fecha inválida'}, status=400)

	range_str = request.POST.get('range', '').strip()
	try:
		if range_str and '-' in range_str:
			left, right = range_str.split('-', 1)
			start_label = _normalize_time_part(left)
			end_label = _normalize_time_part(right)
			if not start_label or not end_label:
				return JsonResponse({'ok': False, 'error': 'Rango inválido'}, status=400)
			start_value = datetime.strptime(start_label, '%H:%M').time()
			end_value = datetime.strptime(end_label, '%H:%M').time()
			deleted_count, _ = Availability.objects.filter(date=day_date, time=start_value, end_time=end_value).delete()
			if not deleted_count:
				Availability.objects.filter(date=day_date, end_time__isnull=True, time__gte=start_value, time__lt=end_value).delete()
		else:
			Availability.objects.filter(date=day_date).delete()
	except OperationalError as e:
		print(f"DB Error en delete_day_availability: {e}")
		traceback.print_exc()
		return JsonResponse({'ok': False, 'error': f'Error de base de datos: {e}'}, status=500)

	remaining_records = list(Availability.objects.filter(date=day_date).order_by('time', 'end_time'))
	ranges = _serialize_day_ranges(remaining_records)
	is_available = len(ranges) > 0
	return JsonResponse({
		'ok': True,
		'date': day_date.isoformat(),
		'ranges': ranges,
		'is_available': is_available,
		'available_dates': [day_date.isoformat()] if is_available else []
	})


@require_POST
def save_availability(request):
	is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.accepts('application/json')
	today = date.today()

	def json_or_redirect(payload):
		if is_ajax:
			return JsonResponse(payload)
		return redirect('calendario:index')

	def normalize_part(p):
		return _normalize_time_part(p)

	dates_raw = [d for d in request.POST.getlist('dates') if d and d.strip()]
	ranges_raw = [r for r in request.POST.getlist('ranges') if r and r.strip()]

	if dates_raw and ranges_raw:
		parsed_dates = []
		for ds in dates_raw:
			try:
				d = datetime.strptime(ds.strip(), '%Y-%m-%d').date()
			except ValueError:
				continue
			if d < today:
				continue
			if d.weekday() == 6:
				continue
			parsed_dates.append(d)

		parsed_ranges = _parse_ranges(ranges_raw)

		if not parsed_dates or not parsed_ranges:
			return json_or_redirect({'created': 0, 'available_dates': [], 'debug': {'received_dates': dates_raw, 'received_ranges': ranges_raw}})

		created = 0
		created_dates = set()
		for current_date in sorted(set(parsed_dates)):
			for start_label, end_label in parsed_ranges:
				try:
					start_value = datetime.strptime(start_label, '%H:%M').time()
					end_value = datetime.strptime(end_label, '%H:%M').time()
					_, was_created = Availability.objects.get_or_create(date=current_date, time=start_value, end_time=end_value)
					if was_created:
						created += 1
					created_dates.add(current_date.isoformat())
				except OperationalError as e:
					print(f"DB Error al guardar: {e}")
					traceback.print_exc()
				except Exception as e:
					print(f"Error al guardar disponibilidad: {e}")
					traceback.print_exc()

		if is_ajax:
			return JsonResponse({'created': created, 'available_dates': sorted(list(created_dates))})

		if created and hasattr(request, 'session'):
			request.session['temp_available_dates'] = sorted(list(created_dates))
			request.session.modified = True

		return redirect('calendario:index')

	start = request.POST.get('start_date')
	end = request.POST.get('end_date')
	times = request.POST.getlist('times')
	parts = []
	times_list = [p for p in times if p and p.strip()]
	if times_list:
		parts.extend(times_list)
	times_text = request.POST.get('times_text', '')
	if times_text and not parts:
		parts.extend([p.strip() for p in times_text.split(',') if p.strip()])

	parsed_times = []
	for p in parts:
		np = normalize_part(p)
		if np:
			parsed_times.append(np)

	seen = set()
	times = []
	for t in parsed_times:
		if t not in seen:
			seen.add(t)
			times.append(t)

	if not (start and end and times):
		return json_or_redirect({'created': 0, 'available_dates': [], 'debug': {'start': start, 'end': end, 'received_parts': parts, 'parsed_times': times}})

	try:
		start_d = datetime.strptime(start, '%Y-%m-%d').date()
		end_d = datetime.strptime(end, '%Y-%m-%d').date()
	except ValueError:
		return redirect('calendario:index')

	if end_d < start_d:
		end_d = start_d

	if end_d < today:
		return json_or_redirect({'created': 0, 'available_dates': [], 'debug': {'start': start, 'end': end, 'error': 'Rango en fechas pasadas'}})

	if start_d < today:
		start_d = today

	current = start_d
	created = 0
	created_dates = set()
	while current <= end_d:
		for t in times:
			t_val = None
			if not t:
				continue
			p = t.strip().replace('.', '').replace('\u00A0', ' ')
			for fmt in ('%H:%M', '%I:%M %p', '%I:%M%p'):
				try:
					_tt = datetime.strptime(p, fmt).time()
					t_val = _tt
					break
				except Exception:
					continue
			if not t_val:
				continue
			try:
				_, was_created = Availability.objects.get_or_create(date=current, time=t_val, end_time=None)
				if was_created:
					created += 1
				created_dates.add(current.isoformat())
			except OperationalError:
				created += 1
				created_dates.add(current.isoformat())
			except Exception:
				continue
		current += timedelta(days=1)

	if is_ajax:
		return JsonResponse({'created': created, 'available_dates': sorted(list(created_dates))})

	if created and request and hasattr(request, 'session'):
		request.session['temp_available_dates'] = sorted(list(created_dates))
		request.session.modified = True

	return redirect('calendario:index')
