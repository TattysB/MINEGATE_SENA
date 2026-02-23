from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from visitaExterna.models import VisitaExterna
from .forms import VisitaExternaInstructorForm


# ==================== AUTENTICACIÓN POR SESIÓN ====================

def get_sesion_instructor(request):
    """
    Lee los datos de sesión del panel_visitante.
    Retorna (correo, documento) o (None, None) si no está autenticado como externo.
    """
    if not request.session.get('responsable_autenticado'):
        return None, None
    if request.session.get('responsable_rol') != 'externo':
        return None, None
    correo = request.session.get('responsable_correo')
    documento = request.session.get('responsable_documento')
    if not correo or not documento:
        return None, None
    return correo, documento


def instructor_externo_required(view_func):
    """
    Decorador: verifica sesión de panel_visitante con rol externo.
    """
    def wrapper(request, *args, **kwargs):
        correo, documento = get_sesion_instructor(request)
        if not correo:
            messages.warning(request, 'Debes iniciar sesión como usuario externo para acceder a este panel.')
            return redirect('panel_visitante:login_responsable')
        return view_func(request, *args, **kwargs)
    return wrapper


# ==================== PANEL PRINCIPAL ====================

@instructor_externo_required
def panel_instructor_externo(request):
    correo, documento = get_sesion_instructor(request)
    visitas = VisitaExterna.objects.filter(
        correo_responsable__iexact=correo
    ).order_by('-fecha_solicitud')
    context = {
        'correo': correo,
        'documento': documento,
        'visitas': visitas,
        'total_visitas': visitas.count(),
        'visitas_pendientes': visitas.filter(estado='pendiente').count(),
        'visitas_confirmadas': visitas.filter(estado='confirmada').count(),
    }
    return render(request, 'panel_instructor_externo/panel.html', context)


# ==================== MÓDULO: RESERVAR VISITA EXTERNA ====================

@instructor_externo_required
def reservar_visita_externa(request):
    correo, documento = get_sesion_instructor(request)
    if request.method == 'POST':
        form = VisitaExternaInstructorForm(request.POST)
        if form.is_valid():
            visita = form.save(commit=False)
            visita.correo_responsable = correo
            visita.documento_responsable = documento
            visita.estado = 'pendiente'
            visita.save()
            messages.success(request, '✅ Solicitud de visita externa enviada. Queda pendiente de revisión.')
            return redirect('panel_instructor_externo:panel')
    else:
        form = VisitaExternaInstructorForm(initial={
            'correo_responsable': correo,
            'documento_responsable': documento,
        })
    context = {'form': form, 'correo': correo, 'titulo': 'Reservar Visita Externa'}
    return render(request, 'panel_instructor_externo/reservar_visita.html', context)


@instructor_externo_required
def detalle_visita_externa(request, pk):
    correo, _ = get_sesion_instructor(request)
    visita = get_object_or_404(VisitaExterna, pk=pk, correo_responsable__iexact=correo)
    return render(request, 'panel_instructor_externo/detalle_visita.html', {'visita': visita, 'correo': correo})
