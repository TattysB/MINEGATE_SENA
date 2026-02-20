from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.decorators.csrf import csrf_protect
from django.urls import reverse
from datetime import datetime
from visitaInterna.models import VisitaInterna, AsistenteVisitaInterna
from visitaExterna.models import VisitaExterna, AsistenteVisitaExterna
from .forms import RegistroVisitanteForm, PasswordResetRequestForm, PasswordResetConfirmForm
from .models import RegistroVisitante
from django.conf import settings


def login_responsable(request):
    """
    Login para responsables de visitas usando solo documento y contraseña.
    """
    if request.method == 'POST':
        documento = request.POST.get('documento', '').strip()
        contrasena = request.POST.get('contrasena', '')

        visitante = RegistroVisitante.objects.filter(
            documento=documento
        ).first()

        if visitante and visitante.check_password(contrasena):
            # Guardar sesión
            request.session['responsable_correo'] = visitante.correo
            request.session['responsable_documento'] = visitante.documento
            request.session['responsable_rol'] = visitante.rol
            request.session['responsable_autenticado'] = True
            request.session.modified = True
            
            messages.success(
                request,
                f'Bienvenido {visitante.correo}. Accediendo a tu panel...'
            )
            return redirect('panel_visitante:panel_responsable')

        messages.error(
            request,
            'Credenciales inválidas. Verifica tu documento y contraseña.',
        )
    
    return render(request, 'login_responsable.html')


def registro_visita(request):
    """
    Registro inicial de visita para responsables.
    """
    # Si ya hay una sesión de responsable activa, redirigir al panel de responsable
    if request.session.get('responsable_autenticado'):
        return redirect('panel_visitante:panel_responsable')

    if request.method == 'POST':
        form = RegistroVisitanteForm(request.POST)

        if form.is_valid():
            visitante = RegistroVisitante(
                correo=form.cleaned_data['correo'],
                documento=form.cleaned_data['documento'],
                rol=form.cleaned_data['rol'],
            )
            visitante.set_password(form.cleaned_data['password1'])
            visitante.save()
            messages.success(
                request,
                f'Cuenta creada exitosamente como usuario {visitante.get_rol_display()}. Ya puedes iniciar sesion con tus credenciales.',
            )
            return redirect('panel_visitante:login_responsable')
    else:
        form = RegistroVisitanteForm()

    return render(
        request,
        'registro_visita.html',
        {'form': form, 'titulo': 'Registro de Usuario'},
    )


def logout_responsable(request):
    """
    Cerrar sesión del responsable.
    """
    request.session.pop('responsable_correo', None)
    request.session.pop('responsable_documento', None)
    request.session.pop('responsable_autenticado', None)
    messages.success(request, 'Sesión cerrada correctamente.')
    return redirect('panel_visitante:login_responsable')


def panel_responsable(request):
    """
    Panel para que el responsable vea sus visitas y registre asistentes.
    """
    # Obtener datos de sesión
    correo = request.session.get('responsable_correo')
    documento = request.session.get('responsable_documento')
    rol = request.session.get('responsable_rol')
    autenticado = request.session.get('responsable_autenticado', False)
    
    # Verificar si está autenticado
    if not autenticado or not correo or not documento:
        messages.warning(request, 'Debe iniciar sesión para acceder al panel.')
        return redirect('panel_visitante:login_responsable')
    
    try:
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
            'rol': rol,
        }
        
        return render(request, 'panel_responsable.html', context)
    
    except Exception as e:
        messages.error(request, f'Error al cargar el panel: {str(e)}')
        return redirect('panel_visitante:login_responsable')


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
    
    return render(request, 'registrar_asistentes.html', context)


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


def restablecer_contraseña(request):
    """
    Vista para mostrar la página de restablecimiento de contraseña.
    Maneja la solicitud de recuperación y el cambio de contraseña.
    """
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']

            # Buscar visitante con ese email
            visitante = RegistroVisitante.objects.filter(correo__iexact=email).first()

            if visitante:
                # Generar token y uid usando Django's default_token_generator
                token = default_token_generator.make_token(visitante)
                uid = urlsafe_base64_encode(force_bytes(visitante.pk))

                # Construir URL de reset usando reverse
                reset_path = reverse(
                    'panel_visitante:restablecer_contraseña_confirm',
                    kwargs={'uidb64': uid, 'token': token}
                )
                reset_url = request.build_absolute_uri(reset_path)

                # Preparar contexto para el template HTML
                email_context = {
                    'nombre': visitante.documento,
                    'reset_url': reset_url,
                    'year': datetime.now().year,
                }

                # Renderizar template HTML
                html_content = render_to_string(
                    'email_restablecer_visitante.html', email_context
                )
                text_content = strip_tags(html_content)

                # Enviar correo HTML
                subject = '🔐 Recuperación de Contraseña - MINEGATE'
                email_msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL or 'noreply@minegate.com',
                    to=[visitante.correo],
                )
                email_msg.attach_alternative(html_content, 'text/html')
                try:
                    email_msg.send()
                    messages.success(
                        request,
                        'Se ha enviado un correo con instrucciones para restablecer tu contraseña.'
                    )
                except Exception as e:
                    messages.warning(
                        request,
                        'El correo no se pudo enviar. Por favor intenta más tarde.'
                    )
                    print(f"Error enviando email: {str(e)}")
            else:
                # Por seguridad, mostrar el mismo mensaje aunque no exista el email
                messages.success(
                    request,
                    'Si el correo existe en nuestro sistema, recibirás instrucciones para restablecer tu contraseña.'
                )
            
            return redirect('panel_visitante:correo_enviado')
    else:
        form = PasswordResetRequestForm()

    context = {'form': form, 'titulo': 'Recuperar Contraseña'}
    return render(request, 'solicitar_recuperacion_visitante.html', context)


def correo_enviado_view(request):
    """
    Vista que se muestra después de enviar el correo de recuperación
    """
    return render(request, 'correo_enviado_visitante.html')


@csrf_protect
def restablecer_contraseña_confirm(request, uidb64, token):
    """
    Vista para confirmar y restablecer la contraseña con token
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        visitante = RegistroVisitante.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, RegistroVisitante.DoesNotExist):
        visitante = None

    if visitante is not None and default_token_generator.check_token(visitante, token):
        if request.method == 'POST':
            form = PasswordResetConfirmForm(request.POST)
            if form.is_valid():
                password = form.cleaned_data['password1']
                visitante.set_password(password)
                visitante.save()

                messages.success(
                    request,
                    '¡Tu contraseña ha sido actualizada exitosamente! Ahora puedes iniciar sesión.',
                )
                return redirect('panel_visitante:contraseña_actualizada')
        else:
            form = PasswordResetConfirmForm()

        context = {
            'form': form,
            'validlink': True,
            'titulo': 'Establecer Nueva Contraseña',
        }
        return render(request, 'restablecer_contraseña_confirm_visitante.html', context)
    else:
        messages.error(request, 'El enlace de recuperación es inválido o ha expirado.')
        context = {'validlink': False, 'titulo': 'Enlace Inválido'}
        return render(request, 'restablecer_contraseña_confirm_visitante.html', context)


def contraseña_actualizada_view(request):
    """
    Vista que se muestra después de actualizar la contraseña
    """
    return render(request, 'contraseña_actualizada_visitante.html')
