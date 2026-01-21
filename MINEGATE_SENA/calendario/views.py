from django.shortcuts import render
import calendar
from datetime import date


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

	# Si la petición es AJAX, devolver sólo el fragmento para inyección en el panel
	if request.headers.get('x-requested-with') == 'XMLHttpRequest':
		return render(request, 'calendario_fragment.html', context)

	return render(request, 'calendario.html', context)
