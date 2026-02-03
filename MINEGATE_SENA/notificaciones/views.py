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
@require_POST
def mark_read(request, pk):
	n = get_object_or_404(Notification, pk=pk, user=request.user)
	n.read = True
	n.save()
	return JsonResponse({'ok': True})


@login_required
@require_POST
def delete_notification(request, pk):
	n = get_object_or_404(Notification, pk=pk, user=request.user)
	n.delete()
	return JsonResponse({'ok': True})
