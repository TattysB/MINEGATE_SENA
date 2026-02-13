from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Notification
from django.db.utils import OperationalError
from datetime import datetime, timedelta


@login_required
def unread_count(request):
	cnt = Notification.objects.filter(user=request.user, read=False).count()
	return JsonResponse({'unread': cnt})


@login_required
def center(request):
	q = request.GET.get('q', '').strip()
	priority = request.GET.get('priority')
	date_from = request.GET.get('date_from', '').strip()
	date_to = request.GET.get('date_to', '').strip()
	try:
		qs = Notification.objects.filter(user=request.user)
		if q:
			qs = qs.filter(Q(title__icontains=q) | Q(message__icontains=q))
		if priority:
			try:
				p = int(priority)
				qs = qs.filter(priority=p)
			except ValueError:
				pass

		# Filtrar por rango de fechas (si se proporcionan)
		if date_from:
			try:
				_from = datetime.strptime(date_from, '%Y-%m-%d')
				qs = qs.filter(created_at__date__gte=_from.date())
			except Exception:
				pass
		if date_to:
			try:
				_to = datetime.strptime(date_to, '%Y-%m-%d')
				qs = qs.filter(created_at__date__lte=_to.date())
			except Exception:
				pass

		context = {'notifications': qs}
	except OperationalError:
		# Database table missing (e.g. migrations not applied). Provide sample notifications
		now = datetime.now()
		sample1 = type('N', (), {
			'id': 1,
			'title': '¡Bienvenido a MineGate!',
			'message': 'Sistema de gestión de visitas iniciado correctamente',
			'priority': 2,
			'read': False,
			'created_at': now - timedelta(minutes=1)
		})
		sample2 = type('N', (), {
			'id': 2,
			'title': 'Documentos pendientes',
			'message': 'Tienes documentos pendientes de revisión',
			'priority': 3,
			'read': False,
			'created_at': now - timedelta(hours=2)
		})
		context = {'notifications': [sample1, sample2], 'db_missing': True}
	# If AJAX request, return only the list fragment (template renamed)
	if request.headers.get('x-requested-with') == 'XMLHttpRequest':
		return render(request, 'notificaciones/notificaciones_lista.html', context)
	return render(request, 'notificaciones/notificaciones.html', context)


@login_required
def detail(request, pk):
	"""Devuelve el HTML con el detalle de una notificación y marca como leída."""
	try:
		n = get_object_or_404(Notification, pk=pk, user=request.user)
		if not n.read:
			n.read = True
			n.save()
		return render(request, 'notificaciones/notificacion_detalle.html', {'n': n})
	except OperationalError:
		# fallback sample detail cuando no hay DB
		now = datetime.now()
		sample = type('N', (), {
			'id': pk,
			'title': 'Notificación de ejemplo',
			'message': 'Detalle de notificación (modo demo).',
			'priority': 2,
			'read': True,
			'created_at': now - timedelta(hours=1)
		})
		return render(request, 'notificaciones/notificacion_detalle.html', {'n': sample, 'db_missing': True})


@login_required
@require_POST
def mark_read(request, pk):
	n = get_object_or_404(Notification, pk=pk, user=request.user)
	n.read = True
	n.save()
	return JsonResponse({'ok': True})


@login_required
def modal(request):
	"""Devuelve el fragmento del modal (envoltorio). La lista se cargará por AJAX desde el cliente."""
	# No forzamos uso de la base aquí; el fragmento contiene el contenedor donde el JS cargará la lista.
	return render(request, 'notificaciones/modal_fragment.html', {})


@login_required
@require_POST
def delete_notification(request, pk):
	n = get_object_or_404(Notification, pk=pk, user=request.user)
	n.delete()
	return JsonResponse({'ok': True})
