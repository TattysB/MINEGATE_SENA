from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from visitaInterna.models import VisitaInterna, AsistenteVisitaInterna
from visitaExterna.models import VisitaExterna, AsistenteVisitaExterna


def login_responsable(request):
    """
    Login para responsables de visitas usando correo y documento.
    """
    if request.method == 'POST':
        correo = request.POST.get('correo', '').strip()
        documento = request.POST.get('documento', '').strip()
        
        # Buscar visitas internas con estas credenciales
        visitas_internas = VisitaInterna.objects.filter(
            correo_responsable__iexact=correo,
            documento_responsable=documento
        )
        
        # Buscar visitas externas con estas credenciales
        visitas_externas = VisitaExterna.objects.filter(
            correo_responsable__iexact=correo,
            documento_responsable=documento
        )
        
        if visitas_internas.exists() or visitas_externas.exists():
            # Guardar credenciales en sesión
            request.session['responsable_correo'] = correo
            request.session['responsable_documento'] = documento
            request.session['responsable_autenticado'] = True
            return redirect('panel_visitante:panel_responsable')
        else:
            messages.error(request, 'No se encontraron visitas con las credenciales proporcionadas.')
    
    return render(request, 'panel_visitante/login_responsable.html')


def logout_responsable(request):
    """
    Cerrar sesión del responsable.
    """
    request.session.pop('responsable_correo', None)
    request.session.pop('responsable_documento', None)
    request.session.pop('responsable_autenticado', None)
    messages.success(request, 'Sesión cerrada correctamente.')
    return redirect('core:visitas')


def panel_responsable(request):
    """
    Panel para que el responsable vea sus visitas y registre asistentes.
    """
    # Verificar si está autenticado
    if not request.session.get('responsable_autenticado'):
        messages.warning(request, 'Debe iniciar sesión para acceder al panel.')
        return redirect('panel_visitante:login_responsable')
    
    correo = request.session.get('responsable_correo')
    documento = request.session.get('responsable_documento')
    
    # Obtener visitas del responsable
    visitas_internas = VisitaInterna.objects.filter(
        correo_responsable__iexact=correo,
        documento_responsable=documento
    ).prefetch_related('asistentes')
    
    visitas_externas = VisitaExterna.objects.filter(
        correo_responsable__iexact=correo,
        documento_responsable=documento
    ).prefetch_related('asistentes')
    
    context = {
        'visitas_internas': visitas_internas,
        'visitas_externas': visitas_externas,
        'correo': correo,
    }
    
    return render(request, 'panel_visitante/panel_responsable.html', context)


def registrar_asistentes(request, tipo, visita_id):
    """
    Formulario para registrar asistentes a una visita aprobada.
    """
    # Verificar autenticación
    if not request.session.get('responsable_autenticado'):
        messages.warning(request, 'Debe iniciar sesión para acceder.')
        return redirect('panel_visitante:login_responsable')
    
    correo = request.session.get('responsable_correo')
    documento = request.session.get('responsable_documento')
    
    # Obtener la visita según el tipo
    if tipo == 'interna':
        visita = get_object_or_404(
            VisitaInterna,
            id=visita_id,
            correo_responsable__iexact=correo,
            documento_responsable=documento
        )
        asistentes = visita.asistentes.all()
        max_asistentes = visita.cantidad_aprendices
    elif tipo == 'externa':
        visita = get_object_or_404(
            VisitaExterna,
            id=visita_id,
            correo_responsable__iexact=correo,
            documento_responsable=documento
        )
        asistentes = visita.asistentes.all()
        max_asistentes = visita.cantidad_visitantes
    else:
        messages.error(request, 'Tipo de visita no válido.')
        return redirect('panel_visitante:panel_responsable')
    
    # Verificar que la visita esté aprobada inicialmente para registro de asistentes
    if visita.estado not in ['aprobada_inicial', 'documentos_enviados', 'en_revision_documentos']:
        messages.error(request, 'Solo puede registrar asistentes en visitas aprobadas.')
        return redirect('panel_visitante:panel_responsable')
    
    # Verificar límite de asistentes
    asistentes_actuales = asistentes.count()
    puede_agregar = asistentes_actuales < max_asistentes
    
    if request.method == 'POST':
        if not puede_agregar:
            messages.error(request, f'Ya se alcanzó el límite de {max_asistentes} asistentes.')
        else:
            nombre = request.POST.get('nombre_completo', '').strip()
            tipo_doc = request.POST.get('tipo_documento', '')
            num_doc = request.POST.get('numero_documento', '').strip()
            correo_asistente = request.POST.get('correo', '').strip()
            telefono = request.POST.get('telefono', '').strip()
            
            if nombre and tipo_doc and num_doc:
                try:
                    if tipo == 'interna':
                        AsistenteVisitaInterna.objects.create(
                            visita=visita,
                            nombre_completo=nombre,
                            tipo_documento=tipo_doc,
                            numero_documento=num_doc,
                            correo=correo_asistente,
                            telefono=telefono
                        )
                    else:
                        AsistenteVisitaExterna.objects.create(
                            visita=visita,
                            nombre_completo=nombre,
                            tipo_documento=tipo_doc,
                            numero_documento=num_doc,
                            correo=correo_asistente,
                            telefono=telefono
                        )
                    messages.success(request, f'Asistente "{nombre}" registrado correctamente.')
                    return redirect('panel_visitante:registrar_asistentes', tipo=tipo, visita_id=visita_id)
                except Exception as e:
                    if 'unique' in str(e).lower():
                        messages.error(request, 'Este documento ya está registrado para esta visita.')
                    else:
                        messages.error(request, f'Error al registrar: {str(e)}')
            else:
                messages.error(request, 'Complete todos los campos obligatorios.')
    
    context = {
        'visita': visita,
        'tipo': tipo,
        'asistentes': asistentes,
        'asistentes_actuales': asistentes_actuales,
        'max_asistentes': max_asistentes,
        'puede_agregar': puede_agregar,
    }
    
    return render(request, 'panel_visitante/registrar_asistentes.html', context)


def eliminar_asistente(request, tipo, asistente_id):
    """
    Eliminar un asistente de una visita.
    """
    # Verificar autenticación
    if not request.session.get('responsable_autenticado'):
        return redirect('panel_visitante:login_responsable')
    
    correo = request.session.get('responsable_correo')
    documento = request.session.get('responsable_documento')
    
    if tipo == 'interna':
        asistente = get_object_or_404(AsistenteVisitaInterna, id=asistente_id)
        visita = asistente.visita
        # Verificar que el responsable tenga acceso a esta visita
        if visita.correo_responsable.lower() != correo.lower() or visita.documento_responsable != documento:
            messages.error(request, 'No tiene permiso para esta acción.')
            return redirect('panel_visitante:panel_responsable')
        visita_id = visita.id
        asistente.delete()
    elif tipo == 'externa':
        asistente = get_object_or_404(AsistenteVisitaExterna, id=asistente_id)
        visita = asistente.visita
        if visita.correo_responsable.lower() != correo.lower() or visita.documento_responsable != documento:
            messages.error(request, 'No tiene permiso para esta acción.')
            return redirect('panel_visitante:panel_responsable')
        visita_id = visita.id
        asistente.delete()
    else:
        messages.error(request, 'Tipo de visita no válido.')
        return redirect('panel_visitante:panel_responsable')
    
    messages.success(request, 'Asistente eliminado correctamente.')
    return redirect('panel_visitante:registrar_asistentes', tipo=tipo, visita_id=visita_id)


def enviar_solicitud_final(request, tipo, visita_id):
    """
    Vista para que el responsable envíe la solicitud final de aprobación.
    Cambia el estado de la visita a 'documentos_enviados' para revisión de documentos.
    """
    # Verificar autenticación
    if not request.session.get('responsable_autenticado'):
        return redirect('panel_visitante:login_responsable')
    
    correo = request.session.get('responsable_correo')
    documento = request.session.get('responsable_documento')
    
    # Obtener la visita
    if tipo == 'interna':
        visita = get_object_or_404(VisitaInterna, id=visita_id)
        if visita.correo_responsable.lower() != correo.lower() or visita.documento_responsable != documento:
            messages.error(request, 'No tiene permiso para esta acción.')
            return redirect('panel_visitante:panel_responsable')
    elif tipo == 'externa':
        visita = get_object_or_404(VisitaExterna, id=visita_id)
        if visita.correo_responsable.lower() != correo.lower() or visita.documento_responsable != documento:
            messages.error(request, 'No tiene permiso para esta acción.')
            return redirect('panel_visitante:panel_responsable')
    else:
        messages.error(request, 'Tipo de visita no válido.')
        return redirect('panel_visitante:panel_responsable')
    
    # Verificar que la visita esté en estado aprobada_inicial
    if visita.estado != 'aprobada_inicial':
        messages.error(request, 'Solo puede enviar la solicitud final cuando la visita esté aprobada inicialmente.')
        return redirect('panel_visitante:panel_responsable')
    
    # Verificar que haya al menos un asistente registrado
    if visita.asistentes.count() == 0:
        messages.error(request, 'Debe registrar al menos un asistente antes de enviar la solicitud final.')
        return redirect('panel_visitante:panel_responsable')
    
    # Cambiar el estado a documentos_enviados
    visita.estado = 'documentos_enviados'
    visita.save()
    
    messages.success(request, '¡Solicitud final enviada correctamente! El administrador revisará los documentos de los asistentes.')
    return redirect('panel_visitante:panel_responsable')
