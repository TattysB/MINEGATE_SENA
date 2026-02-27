from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from visitaInterna.models import VisitaInterna
from .models import Ficha, Programa
from .forms import VisitaInternaInstructorForm, ProgramaForm, FichaForm


# ==================== AUTENTICACIÓN POR SESIÓN ====================

def get_sesion_instructor(request):
    """
    Lee los datos de sesión del panel_visitante.
    Retorna (correo, documento) o (None, None) si no está autenticado como interno.
    """
    if not request.session.get('responsable_autenticado'):
        return None, None
    if request.session.get('responsable_rol') != 'interno':
        return None, None
    correo = request.session.get('responsable_correo')
    documento = request.session.get('responsable_documento')
    if not correo or not documento:
        return None, None
    return correo, documento


def instructor_interno_required(view_func):
    """
    Decorador: verifica sesión de panel_visitante con rol interno.
    """
    def wrapper(request, *args, **kwargs):
        correo, documento = get_sesion_instructor(request)
        if not correo:
            messages.warning(request, 'Debes iniciar sesión como usuario interno para acceder a este panel.')
            return redirect('panel_visitante:login_responsable')
        return view_func(request, *args, **kwargs)
    return wrapper


# ==================== PANEL PRINCIPAL ====================

@instructor_interno_required
def panel_instructor_interno(request):
    correo, documento = get_sesion_instructor(request)
    visitas = VisitaInterna.objects.filter(
        correo_responsable__iexact=correo
    ).order_by('-fecha_solicitud')
    context = {
        'correo': correo,
        'documento': documento,
        'nombre': request.session.get('responsable_nombre', ''),
        'apellido': request.session.get('responsable_apellido', ''),
        'visitas': visitas[:5],
        'total_programas': Programa.objects.filter(activo=True).count(),
        'total_fichas': Ficha.objects.filter(activa=True).count(),
        'total_visitas': visitas.count(),
    }
    return render(request, 'panel_instructor_interno/panel.html', context)


# ==================== MÓDULO: RESERVAR VISITA INTERNA ====================

@instructor_interno_required
def reservar_visita_interna(request):
    correo, documento = get_sesion_instructor(request)
    
    # Obtener datos adicionales de la sesión
    nombre = request.session.get('responsable_nombre', '')
    apellido = request.session.get('responsable_apellido', '')
    tipo_documento = request.session.get('responsable_tipo_documento', 'CC')
    telefono = request.session.get('responsable_telefono', '')
    nombre_completo = f"{nombre} {apellido}".strip()
    
    if request.method == 'POST':
        form = VisitaInternaInstructorForm(request.POST)
        if form.is_valid():
            visita = form.save(commit=False)
            visita.correo_responsable = correo
            visita.documento_responsable = documento
            visita.estado = 'enviada_coordinacion'
            visita.save()
            messages.success(request, '✅ Solicitud de visita interna enviada. Queda pendiente de aprobación por coordinación.')
            return redirect('panel_instructor_interno:mis_visitas')
    else:
        form = VisitaInternaInstructorForm(initial={
            'responsable': nombre_completo,
            'tipo_documento_responsable': tipo_documento,
            'documento_responsable': documento,
            'correo_responsable': correo,
            'telefono_responsable': telefono,
        })
    fichas = Ficha.objects.filter(activa=True).select_related('programa')    
    programas = Programa.objects.filter(activo=True)
    context = {
        'form': form, 'fichas': fichas, 'programas': programas,
        'correo': correo, 'titulo': 'Reservar Visita Interna',
    }
    return render(request, 'panel_instructor_interno/reservar_visita.html', context)


@instructor_interno_required
def mis_visitas_internas(request):
    correo, _ = get_sesion_instructor(request)
    visitas = VisitaInterna.objects.filter(correo_responsable__iexact=correo).order_by('-fecha_solicitud')
    estado = request.GET.get('estado', '')
    if estado:
        visitas = visitas.filter(estado=estado)
    buscar = request.GET.get('buscar', '')
    if buscar:
        visitas = visitas.filter(Q(nombre_programa__icontains=buscar) | Q(numero_ficha__icontains=buscar))
    context = {
        'visitas': visitas, 'correo': correo,
        'estado_filtrado': estado, 'buscar': buscar,
        'estados': VisitaInterna.ESTADO_CHOICES,
    }
    return render(request, 'panel_instructor_interno/mis_visitas.html', context)


@instructor_interno_required
def detalle_visita_interna(request, pk):
    correo, _ = get_sesion_instructor(request)
    visita = get_object_or_404(VisitaInterna, pk=pk, correo_responsable__iexact=correo)
    return render(request, 'panel_instructor_interno/detalle_visita.html', {'visita': visita, 'correo': correo})


# ==================== MÓDULO: GESTIONAR PROGRAMAS ====================

@instructor_interno_required
def gestionar_programas(request):
    correo, _ = get_sesion_instructor(request)
    programas = Programa.objects.all().order_by('nombre')
    buscar = request.GET.get('buscar', '')
    if buscar:
        programas = programas.filter(nombre__icontains=buscar)
    return render(request, 'panel_instructor_interno/gestionar_programas.html', {
        'programas': programas, 'buscar': buscar, 'total': programas.count(), 'correo': correo,
    })


@instructor_interno_required
def crear_programa(request):
    correo, _ = get_sesion_instructor(request)
    if request.method == 'POST':
        form = ProgramaForm(request.POST)
        if form.is_valid():
            programa = form.save()
            messages.success(request, f'✅ Programa "{programa.nombre}" creado correctamente.')
            return redirect('panel_instructor_interno:gestionar_programas')
    else:
        form = ProgramaForm()
    return render(request, 'panel_instructor_interno/form_programa.html', {
        'form': form, 'titulo': 'Crear Programa', 'accion': 'Crear', 'correo': correo,
    })


@instructor_interno_required
def editar_programa(request, pk):
    correo, _ = get_sesion_instructor(request)
    programa = get_object_or_404(Programa, pk=pk)
    if request.method == 'POST':
        form = ProgramaForm(request.POST, instance=programa)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Programa "{programa.nombre}" actualizado.')
            return redirect('panel_instructor_interno:gestionar_programas')
    else:
        form = ProgramaForm(instance=programa)
    return render(request, 'panel_instructor_interno/form_programa.html', {
        'form': form, 'programa': programa, 'titulo': 'Editar Programa', 'accion': 'Actualizar', 'correo': correo,
    })


@instructor_interno_required
def eliminar_programa(request, pk):
    correo, _ = get_sesion_instructor(request)
    programa = get_object_or_404(Programa, pk=pk)
    if request.method == 'POST':
        nombre = programa.nombre
        try:
            programa.delete()
            messages.success(request, f'🗑️ Programa "{nombre}" eliminado.')
        except Exception:
            messages.error(request, f'❌ No se puede eliminar "{nombre}" porque tiene fichas asociadas.')
        return redirect('panel_instructor_interno:gestionar_programas')
    return render(request, 'panel_instructor_interno/confirmar_eliminar_programa.html', {
        'programa': programa, 'correo': correo,
    })


# ==================== MÓDULO: GESTIONAR FICHAS ====================

@instructor_interno_required
def gestionar_fichas(request):
    correo, _ = get_sesion_instructor(request)
    fichas = Ficha.objects.select_related('programa').all()
    buscar = request.GET.get('buscar', '')
    if buscar:
        fichas = fichas.filter(Q(numero__icontains=buscar) | Q(programa__nombre__icontains=buscar))
    return render(request, 'panel_instructor_interno/gestionar_fichas.html', {
        'fichas': fichas, 'buscar': buscar, 'total': fichas.count(), 'correo': correo,
    })


@instructor_interno_required
def crear_ficha(request):
    correo, _ = get_sesion_instructor(request)
    if request.method == 'POST':
        form = FichaForm(request.POST)
        if form.is_valid():
            ficha = form.save()
            messages.success(request, f'✅ Ficha {ficha.numero} creada correctamente.')
            return redirect('panel_instructor_interno:gestionar_fichas')
    else:
        form = FichaForm()
    return render(request, 'panel_instructor_interno/form_ficha.html', {
        'form': form, 'titulo': 'Crear Ficha', 'accion': 'Crear', 'correo': correo,
    })


@instructor_interno_required
def editar_ficha(request, pk):
    correo, _ = get_sesion_instructor(request)
    ficha = get_object_or_404(Ficha, pk=pk)
    if request.method == 'POST':
        form = FichaForm(request.POST, instance=ficha)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Ficha {ficha.numero} actualizada.')
            return redirect('panel_instructor_interno:gestionar_fichas')
    else:
        form = FichaForm(instance=ficha)
    return render(request, 'panel_instructor_interno/form_ficha.html', {
        'form': form, 'ficha': ficha, 'titulo': 'Editar Ficha', 'accion': 'Actualizar', 'correo': correo,
    })


@instructor_interno_required
def eliminar_ficha(request, pk):
    correo, _ = get_sesion_instructor(request)
    ficha = get_object_or_404(Ficha, pk=pk)
    if request.method == 'POST':
        numero = ficha.numero
        ficha.delete()
        messages.success(request, f'🗑️ Ficha {numero} eliminada.')
        return redirect('panel_instructor_interno:gestionar_fichas')
    return render(request, 'panel_instructor_interno/confirmar_eliminar_ficha.html', {
        'ficha': ficha, 'correo': correo,
    })
