from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from visitaInterna.models import VisitaInterna, AsistenteVisitaInterna
from visitaExterna.models import VisitaExterna, AsistenteVisitaExterna


def registro_publico_asistentes(request, token, tipo):
    """
    Vista pública para registro de asistentes usando enlace único con token.
    No requiere autenticación, solo el token válido.
    """
    # Obtener la visita según el tipo y token
    if tipo == 'interna':
        visita = get_object_or_404(VisitaInterna, token_acceso=token)
        asistentes = visita.asistentes.all()
        max_asistentes = visita.cantidad_aprendices
    elif tipo == 'externa':
        visita = get_object_or_404(VisitaExterna, token_acceso=token)
        asistentes = visita.asistentes.all()
        max_asistentes = visita.cantidad_visitantes
    else:
        messages.error(request, 'Tipo de visita no válido.')
        return redirect('core:index')
    
    # Verificar que la visita esté aprobada inicialmente para registro de asistentes
    if visita.estado not in ['aprobada_inicial', 'documentos_enviados', 'en_revision_documentos']:
        context = {
            'visita': visita,
            'tipo': tipo,
            'estado_no_aprobado': True,
        }
        return render(request, 'documentos/registro_publico_asistentes.html', context)
    
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
            documento_identidad = request.FILES.get('documento_identidad')
            documento_adicional = request.FILES.get('documento_adicional')
            
            if nombre and tipo_doc and num_doc:
                try:
                    if tipo == 'interna':
                        nuevo_asistente = AsistenteVisitaInterna(
                            visita=visita,
                            nombre_completo=nombre,
                            tipo_documento=tipo_doc,
                            numero_documento=num_doc,
                            correo=correo_asistente,
                            telefono=telefono,
                            estado='pendiente_documentos'
                        )
                        if documento_identidad:
                            nuevo_asistente.documento_identidad = documento_identidad
                        if documento_adicional:
                            nuevo_asistente.documento_adicional = documento_adicional
                        nuevo_asistente.save()
                    else:
                        nuevo_asistente = AsistenteVisitaExterna(
                            visita=visita,
                            nombre_completo=nombre,
                            tipo_documento=tipo_doc,
                            numero_documento=num_doc,
                            correo=correo_asistente,
                            telefono=telefono,
                            estado='pendiente_documentos'
                        )
                        if documento_identidad:
                            nuevo_asistente.documento_identidad = documento_identidad
                        if documento_adicional:
                            nuevo_asistente.documento_adicional = documento_adicional
                        nuevo_asistente.save()
                    
                    messages.success(request, f'¡Asistente "{nombre}" registrado correctamente! Estado: Pendiente de revisión de documentos.')
                    
                    # Redirigir según el tipo
                    if tipo == 'interna':
                        return redirect('documentos:registro_publico_interna', token=token)
                    else:
                        return redirect('documentos:registro_publico_externa', token=token)
                        
                except Exception as e:
                    if 'unique' in str(e).lower():
                        messages.error(request, 'Este número de documento ya está registrado para esta visita.')
                    else:
                        messages.error(request, f'Error al registrar: {str(e)}')
            else:
                messages.error(request, 'Complete todos los campos obligatorios (nombre, tipo y número de documento).')
    
    # Generar enlace completo para compartir
    enlace_registro = request.build_absolute_uri()
    
    context = {
        'visita': visita,
        'tipo': tipo,
        'token': token,
        'asistentes': asistentes,
        'asistentes_actuales': asistentes_actuales,
        'max_asistentes': max_asistentes,
        'puede_agregar': puede_agregar,
        'enlace_registro': enlace_registro,
        'estado_no_aprobado': False,
    }
    
    return render(request, 'documentos/registro_publico_asistentes.html', context)


def eliminar_asistente_publico(request, tipo, token, asistente_id):
    """
    Eliminar un asistente desde el enlace público.
    """
    if tipo == 'interna':
        visita = get_object_or_404(VisitaInterna, token_acceso=token)
        asistente = get_object_or_404(AsistenteVisitaInterna, id=asistente_id, visita=visita)
        asistente.delete()
        messages.success(request, 'Asistente eliminado correctamente.')
        return redirect('documentos:registro_publico_interna', token=token)
    elif tipo == 'externa':
        visita = get_object_or_404(VisitaExterna, token_acceso=token)
        asistente = get_object_or_404(AsistenteVisitaExterna, id=asistente_id, visita=visita)
        asistente.delete()
        messages.success(request, 'Asistente eliminado correctamente.')
        return redirect('documentos:registro_publico_externa', token=token)
    else:
        messages.error(request, 'Tipo de visita no válido.')
        return redirect('core:index')
