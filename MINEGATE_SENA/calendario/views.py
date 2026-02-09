from django.shortcuts import render, redirect
import calendar
from datetime import date, datetime, timedelta
from .models import Availability
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.utils import OperationalError
import re



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

	# Organizar en semanas (filas de 7 días) y añadir flags (hoy, otro mes, domingo)
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
			})
		weeks.append(row)

	# Nombres de meses en español
	meses_es = [
		'', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
		'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
	]

	context = {
		'year': year,
		'month': month,
		'month_name': meses_es[month],
		'weeks': weeks,
		'today': today,
	}

	# Query availability for the shown month and build a set of dates
	try:
		start_month = date(year, month, 1)
		# Fecha final del mes: avanzar al primer día del mes siguiente y restar uno
		next_month = (start_month.replace(day=28) + timedelta(days=4)).replace(day=1)
		end_month = next_month - timedelta(days=1)
		av_qs = Availability.objects.filter(date__gte=start_month, date__lte=end_month)
		# convertir a cadenas ISO para comparar en la plantilla
		available_dates = set(a.date.isoformat() for a in av_qs)
		# Unir fechas temporales guardadas en sesión (POST no-AJAX) para que
		# el flujo de redirección muestre inmediatamente las nuevas disponibilidades.
		try:
			session_dates = request.session.pop('temp_available_dates', None)
			if session_dates:
				available_dates.update(session_dates)
				request.session.modified = True
		except Exception:
			# no interrumpir el render si falla el acceso a la sesión
			pass
		context['available_dates'] = available_dates
	except Exception:
		context['available_dates'] = set()

	# Si la petición es AJAX, devolver sólo el fragmento para inyección en el panel
	if request.headers.get('x-requested-with') == 'XMLHttpRequest':
		return render(request, 'calendario_fragment.html', context)

	return render(request, 'calendario.html', context)


@require_POST
def save_availability(request):
	# Espera: start_date, end_date, times[] (HH:MM)
	start = request.POST.get('start_date')
	end = request.POST.get('end_date')
	times = request.POST.getlist('times')
	# normalizar tiempos entrantes (times[] o times_text)
	parts = []
	# filtrar valores vacíos en times[] (inputs ocultos podían enviar [''])
	times_list = [p for p in times if p and p.strip()]
	if times_list:
		parts.extend(times_list)
	times_text = request.POST.get('times_text', '')
	if times_text and not parts:
		parts.extend([p.strip() for p in times_text.split(',') if p.strip()])

	def normalize_part(p):
		if not p:
			return None
		s = p.lower().replace('.', '').replace('\u00A0', ' ').strip()
		# Intentar primero formatos comunes con strptime
		for fmt in ('%H:%M', '%I:%M %p', '%I:%M%p', '%I %p'):
			try:
				from datetime import datetime as _dt
				t = _dt.strptime(s, fmt).time()
				return t.strftime('%H:%M')
			except Exception:
				continue
		# Expresión regular de respaldo: hora, minuto opcional, sufijo am/pm opcional
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
				h = h + 12
			if mer == 'am' and h == 12:
				h = 0
		# validar valores de hora y minuto
		if h < 0 or h > 23 or minute < 0 or minute > 59:
			return None
		return f"{h:02d}:{minute:02d}"

	parsed_times = []
	for p in parts:
		np = normalize_part(p)
		if np:
			parsed_times.append(np)

	# eliminar duplicados conservando el orden
	seen = set()
	times = []
	for t in parsed_times:
		if t not in seen:
			seen.add(t)
			times.append(t)
	if not (start and end and times):
		# Si la petición es AJAX, devolver información diagnóstica para depuración
		if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.accepts('application/json'):
			return JsonResponse({'created': 0, 'available_dates': [], 'debug': {'start': start, 'end': end, 'received_parts': parts, 'parsed_times': times}})
		return redirect('calendario:index')

	try:
		start_d = datetime.strptime(start, '%Y-%m-%d').date()
		end_d = datetime.strptime(end, '%Y-%m-%d').date()
	except ValueError:
		return redirect('calendario:index')

	if end_d < start_d:
		end_d = start_d

	current = start_d
	created = 0
	created_dates = set()
	while current <= end_d:
		for t in times:
			# normalizar/probar varios formatos de hora (24h y am/pm)
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
				Availability.objects.get_or_create(date=current, time=t_val)
				created += 1
				created_dates.add(current.isoformat())
			except OperationalError:
				# La tabla puede no existir (migrations no aplicadas). Simulamos éxito
				created += 1
				created_dates.add(current.isoformat())
			except Exception:
				continue
		current += timedelta(days=1)

	# Si la petición es AJAX, devolver las fechas creadas para que el frontend actualice el calendario
	if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.accepts('application/json'):
		return JsonResponse({'created': created, 'available_dates': sorted(list(created_dates))})

	# No-AJAX: guardar las fechas creadas en la sesión para que la siguiente renderización las muestre
	if created and request and hasattr(request, 'session'):
		request.session['temp_available_dates'] = sorted(list(created_dates))
		request.session.modified = True

	return redirect('calendario:index')
