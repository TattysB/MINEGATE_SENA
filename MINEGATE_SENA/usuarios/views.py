from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse
from django.db.models import Q
from django.urls import reverse
from .forms import LoginForm, RegistroForm, EditarUsuarioForm, EditarPerfilForm
from .models import PerfilUsuario

# ==================== VISTAS DE AUTENTICACIÓN ====================

@csrf_protect
@never_cache
def login_view(request):
    """
    Vista para el inicio de sesión de usuarios
    Verifica que el usuario esté aprobado antes de permitir el acceso
    """
    # Si el usuario ya está autenticado, redirigir al panel administrativo
    if request.user.is_authenticated:
        return redirect('core:panel_administrativo')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        
        # Obtener valores directamente del POST para validación personalizada
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me', False)
        
        # Validar campos vacíos
        if not username and not password:
            messages.error(request, 'Ingresa tu número de documento y contraseña.')
        elif not username:
            messages.error(request, 'Ingresa tu número de documento.')
        elif not password:
            messages.error(request, 'Ingresa tu contraseña.')
        else:
            # Verificar si el usuario existe
            user_exists = User.objects.filter(username=username).first()
            
            # Autenticar usuario
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                if user.is_active:
                    # Verificar si el usuario está aprobado (excepto superusuarios)
                    if not user.is_superuser:
                        if not hasattr(user, 'perfil') or not user.perfil.aprobado:
                            razon = getattr(user.perfil, 'razon_rechazo', None) if hasattr(user, 'perfil') else None
                            if razon:
                                messages.error(request, f'Tu acceso fue rechazado. Motivo: {razon}')
                            else:
                                messages.warning(request, 'Tu cuenta está pendiente de aprobación. El administrador revisará tu solicitud pronto.')
                            return redirect('usuarios:login')
                    
                    login(request, user)
                    
                    # Configurar duración de la sesión
                    if not remember_me:
                        request.session.set_expiry(0)
                    else:
                        request.session.set_expiry(60 * 60 * 24 * 30)
                    
                    # Guardar el nombre completo en la sesión
                    request.session['welcome_name'] = user.get_full_name() or user.username
                    
                    # Redirigir a la página de bienvenida
                    next_url = request.GET.get('next', 'core:panel_administrativo')
                    request.session['redirect_after_welcome'] = next_url
                    
                    messages.success(request, f'¡Bienvenido {user.get_full_name() or user.username}!')
                    return redirect('usuarios:bienvenida')
                else:
                    messages.error(request, 'Esta cuenta ha sido desactivada. Contacta al administrador.')
            else:
                # Mensajes específicos según el error
                if user_exists:
                    messages.error(request, 'Contraseña incorrecta.')
                else:
                    messages.error(request, 'El número de documento no está registrado.')
    else:
        form = LoginForm()
    
    context = {
        'form': form,
        'titulo': 'Iniciar Sesión'
    }
    return render(request, 'usuarios/login.html', context)


@csrf_protect
def registro_view(request):
    """
    Vista para el registro de nuevos usuarios
    """
    if request.user.is_authenticated:
        return redirect('core:panel_administrativo')
    
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        
        if form.is_valid():
            user = form.save()
            messages.success(
                request, 
                '¡Cuenta creada exitosamente! Ya puedes iniciar sesión con tus credenciales.'
            )
            return redirect('usuarios:login')
        else:
            # Mensajes de error personalizados en español
            if form.errors:
                for field, errors in form.errors.items():
                    for error in errors:
                        if 'password' in field:
                            if 'too similar' in str(error).lower():
                                messages.error(request, 'La contraseña es muy similar a tu información personal. Elige una más diferente.')
                            elif 'too common' in str(error).lower():
                                messages.error(request, 'La contraseña es muy común. Por favor elige una más segura y única.')
                            elif 'numeric' in str(error).lower():
                                messages.error(request, 'La contraseña no puede ser solo números. Incluye letras y caracteres especiales.')
                            elif 'short' in str(error).lower() or 'at least' in str(error).lower():
                                messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
                            elif "didn't match" in str(error).lower() or 'match' in str(error).lower():
                                messages.error(request, 'Las contraseñas no coinciden. Verifica que sean iguales.')
                            else:
                                messages.error(request, f'Contraseña: {error}')
                        elif field == 'username':
                            if 'already exists' in str(error).lower():
                                messages.error(request, 'Este número de documento ya está registrado en el sistema.')
                            elif 'required' in str(error).lower():
                                messages.error(request, 'El número de documento es obligatorio.')
                            elif 'letters' in str(error).lower() or 'alphanumeric' in str(error).lower():
                                messages.error(request, 'El documento solo debe contener números.')
                            else:
                                messages.error(request, f'Documento: {error}')
                        elif field == 'email':
                            if 'already' in str(error).lower():
                                messages.error(request, 'Este correo electrónico ya está registrado. Intenta con otro.')
                            elif 'valid' in str(error).lower():
                                messages.error(request, 'Por favor ingresa un correo electrónico válido.')
                            elif 'required' in str(error).lower():
                                messages.error(request, 'El correo electrónico es obligatorio.')
                            else:
                                messages.error(request, f'Correo: {error}')
                        elif field == '__all__':
                            messages.error(request, str(error))
                        else:
                            messages.error(request, f'{field}: {error}')
            else:
                messages.error(request, 'Por favor revisa los datos ingresados e intenta de nuevo.')
    else:
        form = RegistroForm()
    
    context = {
        'form': form,
        'titulo': 'Registro de Usuario'
    }
    return render(request, 'usuarios/registro.html', context)


@login_required
def logout_view(request):
    """
    Vista para cerrar sesión
    """
    username = request.user.get_full_name() or request.user.username
    logout(request)
    messages.success(request, f'¡Hasta pronto, {username}! Tu sesión fue cerrada correctamente.')
    return redirect('core:index')


# ==================== PANEL DE ADMINISTRACIÓN ====================

def es_staff(user):
    """Función auxiliar para verificar si el usuario es staff"""
    return user.is_staff



@login_required
@user_passes_test(es_staff, login_url='usuarios:login')
def lista_usuarios_view(request):
    """
    Vista para listar todos los usuarios
    """
    # Obtener parámetros de búsqueda y filtrado
    busqueda = request.GET.get('buscar', '')
    filtro_activo = request.GET.get('activo', '')
    filtro_staff = request.GET.get('staff', '')
    
    # Query base
    usuarios = User.objects.select_related('perfil').all()
    
    # Aplicar filtros
    if busqueda:
        usuarios = usuarios.filter(
            Q(username__icontains=busqueda) |
            Q(first_name__icontains=busqueda) |
            Q(last_name__icontains=busqueda) |
            Q(email__icontains=busqueda) |
            Q(perfil__documento__icontains=busqueda)
        )
    
    if filtro_activo:
        usuarios = usuarios.filter(is_active=filtro_activo == 'true')
    
    if filtro_staff:
        usuarios = usuarios.filter(is_staff=filtro_staff == 'true')
    
    # Ordenar
    usuarios = usuarios.order_by('-date_joined')
    
    context = {
        'titulo': 'Gestión de Usuarios',
        'usuarios': usuarios,
        'busqueda': busqueda,
        'filtro_activo': filtro_activo,
        'filtro_staff': filtro_staff,
    }
    return render(request, 'usuarios/panel_admin/lista_usuarios.html', context)


@login_required
@user_passes_test(es_staff, login_url='usuarios:login')
def crear_usuario_view(request):
    """
    Vista para crear un nuevo usuario desde el panel admin
    """
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Usuario {user.get_full_name()} creado exitosamente.')
            return redirect('usuarios:lista_usuarios')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = RegistroForm()
    
    context = {
        'titulo': 'Crear Nuevo Usuario',
        'form': form,
        'accion': 'Crear'
    }
    return render(request, 'usuarios/panel_admin/crear_usuario.html', context)


@login_required
@user_passes_test(es_staff, login_url='usuarios:login')
def editar_usuario_view(request, user_id):
    """
    Vista para editar un usuario existente
    """
    usuario = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form_usuario = EditarUsuarioForm(request.POST, instance=usuario)
        form_perfil = EditarPerfilForm(request.POST, request.FILES, instance=usuario.perfil)
        
        if form_usuario.is_valid() and form_perfil.is_valid():
            form_usuario.save()
            form_perfil.save()
            messages.success(request, f'Usuario {usuario.get_full_name()} actualizado exitosamente.')
            return redirect('usuarios:lista_usuarios')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form_usuario = EditarUsuarioForm(instance=usuario)
        form_perfil = EditarPerfilForm(instance=usuario.perfil)
    
    context = {
        'titulo': f'Editar Usuario: {usuario.get_full_name()}',
        'form_usuario': form_usuario,
        'form_perfil': form_perfil,
        'usuario': usuario,
        'accion': 'Actualizar'
    }
    return render(request, 'usuarios/panel_admin/editar_usuario.html', context)


@login_required
@user_passes_test(es_staff, login_url='usuarios:login')
def eliminar_usuario_view(request, user_id):
    """
    Vista para eliminar (desactivar) un usuario
    """
    usuario = get_object_or_404(User, id=user_id)
    
    # No permitir eliminar al superusuario
    if usuario.is_superuser:
        messages.error(request, 'No se puede eliminar un superusuario.')
        return redirect('usuarios:lista_usuarios')
    
    # No permitir que se elimine a sí mismo
    if usuario == request.user:
        messages.error(request, 'No puedes eliminarte a ti mismo.')
        return redirect('usuarios:lista_usuarios')
    
    if request.method == 'POST':
        usuario.is_active = False
        usuario.save()
        messages.success(request, f'Usuario {usuario.get_full_name()} desactivado exitosamente.')
        return redirect('usuarios:lista_usuarios')
    
    context = {
        'titulo': 'Eliminar Usuario',
        'usuario': usuario
    }
    return render(request, 'usuarios/panel_admin/eliminar_usuario.html', context)


@login_required
def perfil_view(request):
    """
    Vista para que el usuario vea/edite su propio perfil
    """
    usuario = request.user
    
    if request.method == 'POST':
        form_usuario = EditarUsuarioForm(request.POST, instance=usuario)
        form_perfil = EditarPerfilForm(request.POST, request.FILES, instance=usuario.perfil)
        
        if form_usuario.is_valid() and form_perfil.is_valid():
            form_usuario.save()
            form_perfil.save()
            messages.success(request, 'Perfil actualizado exitosamente.')
            return redirect('usuarios:perfil')
    else:
        form_usuario = EditarUsuarioForm(instance=usuario)
        form_perfil = EditarPerfilForm(instance=usuario.perfil)
    
    context = {
        'titulo': 'Mi Perfil',
        'form_usuario': form_usuario,
        'form_perfil': form_perfil,
    }
    return render(request, 'usuarios/perfil.html', context)


# ==================== VISTA DE BIENVENIDA ====================

@login_required
def bienvenida_view(request):
    """
    Vista de bienvenida después del login exitoso
    Muestra un mensaje de bienvenida con animación y redirige automáticamente
    """
    nombre_usuario = request.session.get('welcome_name', request.user.get_full_name() or request.user.username)
    redirect_url_name = request.session.get('redirect_after_welcome', 'core:panel_administrativo')
    
    # Convertir el nombre de la URL a una URL absoluta
    try:
        redirect_url = reverse(redirect_url_name)
    except:
        redirect_url = reverse('core:panel_administrativo')
    
    # Limpiar las variables de sesión
    if 'welcome_name' in request.session:
        del request.session['welcome_name']
    if 'redirect_after_welcome' in request.session:
        del request.session['redirect_after_welcome']
    
    context = {
        'nombre_usuario': nombre_usuario,
        'redirect_url': redirect_url,
    }
    return render(request, 'usuarios/bienvenida.html', context)


# ==================== VISTAS DE RECUPERACIÓN DE CONTRASEÑA ====================

from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .forms import PasswordResetRequestForm, PasswordResetConfirmForm

@csrf_protect
def password_reset_request_view(request):
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            
            # Buscar usuarios con ese email
            users = User.objects.filter(email=email)
            
            if users.exists():
                for user in users:
                    # Generar token y uid
                    token = default_token_generator.make_token(user)
                    uid = urlsafe_base64_encode(force_bytes(user.pk))
                    
                    # Construir URL de reset
                    reset_url = request.build_absolute_uri(
                        reverse('usuarios:restablecer_contraseña', kwargs={'uidb64': uid, 'token': token})
                    )
                    
                    # Enviar correo
                    subject = 'Recuperación de Contraseña - MineGate SENA'
                    message = f'''
Hola {user.get_full_name() or user.username},

Has solicitado restablecer tu contraseña en MineGate SENA.

Para crear una nueva contraseña, haz clic en el siguiente enlace:
{reset_url}

Si no solicitaste este cambio, puedes ignorar este correo.

Este enlace expirará en 24 horas.

Saludos,
El equipo de MineGate SENA
                    '''
                    
                    send_mail(
                        subject,
                        message,
                        'noreply@minegate.com',
                        [user.email],
                        fail_silently=False,
                    )
                
                messages.success(request, 'Se ha enviado un correo con instrucciones para restablecer tu contraseña.')
                return redirect('usuarios:correo_enviado')
            else:
                # Por seguridad, mostrar el mismo mensaje aunque no exista el email
                messages.success(request, 'Si el correo existe en nuestro sistema, recibirás instrucciones para restablecer tu contraseña.')
                return redirect('usuarios:correo_enviado')
    else:
        form = PasswordResetRequestForm()
    
    context = {
        'form': form,
        'titulo': 'Recuperar Contraseña'
    }
    return render(request, 'usuarios/solicitar_recuperacion.html', context)


def password_reset_done_view(request):
    return render(request, 'usuarios/correo_enviado.html')


@csrf_protect
def password_reset_confirm_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = PasswordResetConfirmForm(request.POST)
            if form.is_valid():
                password = form.cleaned_data['password1']
                user.set_password(password)
                user.save()
                
                messages.success(request, '¡Tu contraseña ha sido actualizada exitosamente! Ahora puedes iniciar sesión.')
                return redirect('usuarios:contraseña_actualizada')
        else:
            form = PasswordResetConfirmForm()
        
        context = {
            'form': form,
            'validlink': True,
            'titulo': 'Establecer Nueva Contraseña'
        }
        return render(request, 'usuarios/restablecer_contraseña.html', context)
    else:
        messages.error(request, 'El enlace de recuperación es inválido o ha expirado.')
        context = {
            'validlink': False,
            'titulo': 'Enlace Inválido'
        }
        return render(request, 'usuarios/restablecer_contraseña.html', context)


def password_reset_complete_view(request):
    return render(request, 'usuarios/contraseña_actualizada.html')
