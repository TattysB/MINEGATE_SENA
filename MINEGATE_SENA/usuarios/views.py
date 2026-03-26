from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group, User
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse
from PIL import Image
from django.db.models import Q
from django.urls import reverse
from django.conf import settings
from .forms import LoginForm, RegistroForm, EditarUsuarioForm, EditarPerfilForm
from .models import PerfilUsuario

# ==================== VISTAS DE AUTENTICACIÓN ====================

AUTH_ADMIN_MESSAGE_TAG = "auth_admin"


def resolver_panel_por_rol(user):
    if user.groups.filter(name="instructor_interno").exists():
        return "panel_instructor_interno:panel"
    if user.groups.filter(name="instructor_externo").exists():
        return "panel_instructor_externo:panel"
    if user.groups.filter(name="coordinador").exists():
        return "coordinador:panel"
    if user.is_superuser or user.is_staff:
        return "core:panel_administrativo"
    return "core:index"


def _contexto_rol_panel(user):
    es_coordinador = user.groups.filter(name="coordinador").exists()
    solo_sst = user.is_staff and not user.is_superuser and not es_coordinador

    if user.is_superuser:
        panel_role_label = "Administrador"
    elif es_coordinador:
        panel_role_label = "Coordinador"
    elif solo_sst:
        panel_role_label = "SST"
    else:
        panel_role_label = "Usuario"

    return {
        "es_superusuario": user.is_superuser,
        "solo_sst": solo_sst,
        "solo_coordinador": es_coordinador,
        "panel_role_label": panel_role_label,
    }


def _etiqueta_rol_usuario(user):
    """Retorna una etiqueta legible del rol principal del usuario."""
    if user.is_superuser:
        return "Administrador"
    if user.groups.filter(name="coordinador").exists():
        return "Coordinador"
    if user.groups.filter(name="instructor_interno").exists():
        return "Instructor Interno"
    if user.groups.filter(name="instructor_externo").exists():
        return "Instructor Externo"
    if user.groups.filter(name="sst").exists() or user.is_staff:
        return "SST"
    return "Usuario"


@csrf_protect
@never_cache
def login_view(request):
    """
    Vista para el inicio de sesión de usuarios
    Verifica que el usuario esté aprobado antes de permitir el acceso
    """
    # Si el usuario ya está autenticado, redirigir según rol
    if request.user.is_authenticated:
        return redirect(resolver_panel_por_rol(request.user))

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)

        # Obtener valores directamente del POST para validación personalizada
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        remember_me = request.POST.get("remember_me", False)

        # Validar campos vacíos
        if not username and not password:
            messages.error(
                request,
                "Ingresa tu número de documento y contraseña.",
                extra_tags=AUTH_ADMIN_MESSAGE_TAG,
            )
        elif not username:
            messages.error(
                request,
                "Ingresa tu número de documento.",
                extra_tags=AUTH_ADMIN_MESSAGE_TAG,
            )
        elif not password:
            messages.error(
                request,
                "Ingresa tu contraseña.",
                extra_tags=AUTH_ADMIN_MESSAGE_TAG,
            )
        else:
            # Verificar si el usuario existe
            user_exists = User.objects.filter(username=username).first()

            # Autenticar usuario
            user = authenticate(request, username=username, password=password)

            if user is not None:
                if user.is_active:
                    login(request, user)

                    # Configurar duración de la sesión
                    if not remember_me:
                        request.session.set_expiry(0)
                    else:
                        request.session.set_expiry(60 * 60 * 24 * 30)

                    # Guardar el nombre completo en la sesión
                    request.session["welcome_name"] = (
                        user.get_full_name() or user.username
                    )

                    # Redirigir a la página de bienvenida según rol
                    next_url = request.GET.get("next") or resolver_panel_por_rol(user)
                    request.session["redirect_after_welcome"] = next_url

                    messages.success(
                        request,
                        f"¡Bienvenido {user.get_full_name() or user.username}!",
                        extra_tags=AUTH_ADMIN_MESSAGE_TAG,
                    )
                    return redirect("usuarios:bienvenida")
                else:
                    messages.error(
                        request,
                        "Esta cuenta ha sido desactivada. Contacta al administrador.",
                        extra_tags=AUTH_ADMIN_MESSAGE_TAG,
                    )
            else:
                # Mensajes específicos según el error
                if user_exists:
                    messages.error(
                        request,
                        "Contraseña incorrecta.",
                        extra_tags=AUTH_ADMIN_MESSAGE_TAG,
                    )
                else:
                    messages.error(
                        request,
                        "El número de documento no está registrado.",
                        extra_tags=AUTH_ADMIN_MESSAGE_TAG,
                    )
    else:
        form = LoginForm()

    context = {"form": form, "titulo": "Iniciar Sesión"}
    return render(request, "usuarios/login.html", context)


@login_required
def logout_view(request):
    """
    Vista para cerrar sesión
    """
    username = request.user.get_full_name() or request.user.username
    logout(request)
    messages.success(
        request,
        f"¡Hasta pronto, {username}! Tu sesión fue cerrada correctamente.",
        extra_tags=AUTH_ADMIN_MESSAGE_TAG,
    )
    return redirect("usuarios:login")


# ==================== PANEL DE ADMINISTRACIÓN ====================


def es_staff(user):
    """Función auxiliar para verificar si el usuario es staff o superusuario"""
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(es_staff, login_url="usuarios:login")
def lista_usuarios_view(request):
    """
    Vista para listar todos los usuarios
    """
    # Obtener parámetros de búsqueda y filtrado
    busqueda = request.GET.get("buscar", "")
    filtro_activo = request.GET.get("activo", "")
    filtro_staff = request.GET.get("staff", "")

    # Query base
    usuarios = User.objects.select_related("perfil").all()

    # Aplicar filtros
    if busqueda:
        usuarios = usuarios.filter(
            Q(username__icontains=busqueda)
            | Q(first_name__icontains=busqueda)
            | Q(last_name__icontains=busqueda)
            | Q(email__icontains=busqueda)
            | Q(perfil__documento__icontains=busqueda)
        )

    if filtro_activo:
        usuarios = usuarios.filter(is_active=filtro_activo == "true")

    if filtro_staff:
        usuarios = usuarios.filter(is_staff=filtro_staff == "true")

    # Ordenar
    usuarios = usuarios.order_by("-date_joined")

    context = {
        "titulo": "Gestión de Usuarios",
        "usuarios": usuarios,
        "busqueda": busqueda,
        "filtro_activo": filtro_activo,
        "filtro_staff": filtro_staff,
    }
    return render(request, "usuarios/panel_admin/lista_usuarios.html", context)


# ==================== REGISTRO DE NUEVO USUARIO ====================


@login_required
@user_passes_test(es_staff, login_url="usuarios:login")
def crear_usuario_view(request):
    """
    Vista para crear un nuevo usuario desde el panel admin
    """
    if request.method == "POST":
        form = RegistroForm(request.POST)

        if form.is_valid():
            user = form.save()
            messages.success(
                request, f"Usuario {user.get_full_name()} creado exitosamente."
            )
            return redirect("usuarios:lista_usuarios")
        else:
            messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        form = RegistroForm()

    context = {"titulo": "Crear Nuevo Usuario", "form": form, "accion": "Crear"}
    return render(request, "usuarios/panel_admin/crear_usuario.html", context)


# ==================== EDITAR USUARIO ====================


@login_required
@user_passes_test(es_staff, login_url="usuarios:login")
def editar_usuario_view(request, user_id):
    """
    Vista para editar un usuario existente
    """
    usuario = get_object_or_404(User, id=user_id)

    # Determinar URL de retorno
    next_url = request.GET.get("next", request.POST.get("next", ""))

    if request.method == "POST":
        form_usuario = EditarUsuarioForm(request.POST, instance=usuario)
        form_perfil = EditarPerfilForm(
            request.POST, request.FILES, instance=usuario.perfil
        )

        if form_usuario.is_valid() and form_perfil.is_valid():
            form_usuario.save()
            form_perfil.save()
            messages.success(
                request, f"Usuario {usuario.get_full_name()} actualizado exitosamente."
            )
            # Redirigir a la URL de retorno o a gestionar_permisos
            if next_url:
                return redirect(next_url)
            return redirect("usuarios:gestionar_permisos")
        else:
            messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        form_usuario = EditarUsuarioForm(instance=usuario)
        form_perfil = EditarPerfilForm(instance=usuario.perfil)

    context = {
        "titulo": f"Editar Usuario: {usuario.get_full_name()}",
        "form_usuario": form_usuario,
        "form_perfil": form_perfil,
        "usuario": usuario,
        "accion": "Actualizar",
        "es_perfil_propio": False,
        "next_url": next_url,
    }
    return render(request, "usuarios/editar_usuario.html", context)


# ==================== ELIMINAR USUARIO ====================


@login_required
@user_passes_test(es_staff, login_url="usuarios:login")
def eliminar_usuario_view(request, user_id):
    """
    Vista para eliminar (desactivar) un usuario
    """
    usuario = get_object_or_404(User, id=user_id)

    # No permitir eliminar al superusuario
    if usuario.is_superuser:
        messages.error(request, "No se puede eliminar un superusuario.")
        return redirect("usuarios:lista_usuarios")

    # No permitir que se elimine a sí mismo
    if usuario == request.user:
        messages.error(request, "No puedes eliminarte a ti mismo.")
        return redirect("usuarios:lista_usuarios")

    if request.method == "POST":
        usuario.is_active = False
        usuario.save()
        messages.success(
            request, f"Usuario {usuario.get_full_name()} desactivado exitosamente."
        )
        return redirect("usuarios:lista_usuarios")

    context = {"titulo": "Eliminar Usuario", "usuario": usuario}
    return render(request, "usuarios/panel_admin/eliminar_usuario.html", context)


@login_required
def perfil_view(request):
    """
    Vista para que el usuario vea/edite su propio perfil
    """
    usuario = request.user

    # Crear el perfil si no existe
    perfil, created = PerfilUsuario.objects.get_or_create(user=usuario)

    if request.method == "POST":
        form_usuario = EditarUsuarioForm(request.POST, instance=usuario)
        form_perfil = EditarPerfilForm(request.POST, request.FILES, instance=perfil)

        if form_usuario.is_valid() and form_perfil.is_valid():
            hubo_cambios = form_usuario.has_changed() or form_perfil.has_changed()

            if hubo_cambios:
                form_usuario.save()
                perfil_actualizado = form_perfil.save()

                # Recortar imagen si vienen coordenadas
                try:
                    crop_x = int(float(request.POST.get("crop_x", 0)))
                    crop_y = int(float(request.POST.get("crop_y", 0)))
                    crop_w = int(float(request.POST.get("crop_w", 0)))
                    crop_h = int(float(request.POST.get("crop_h", 0)))

                    if perfil_actualizado.foto_perfil and crop_w > 0 and crop_h > 0:
                        image_path = perfil_actualizado.foto_perfil.path
                        with Image.open(image_path) as image:
                            cropped = image.crop(
                                (crop_x, crop_y, crop_x + crop_w, crop_y + crop_h)
                            )
                            cropped.save(image_path)
                except Exception:
                    pass

                messages.success(request, "Perfil actualizado exitosamente.")
            else:
                messages.info(
                    request,
                    "No se detectaron cambios. La información ya está guardada.",
                )
            return redirect("usuarios:perfil")
    else:
        form_usuario = EditarUsuarioForm(instance=usuario)
        form_perfil = EditarPerfilForm(instance=perfil)

    context = {
        "titulo": "Mi Perfil",
        "form_usuario": form_usuario,
        "form_perfil": form_perfil,
        "perfil": perfil,
        "usuario": usuario,
        "es_perfil_propio": True,
    }
    context.update(_contexto_rol_panel(usuario))
    return render(request, "usuarios/editar_usuario.html", context)


@login_required
def configuracion_perfil_view(request):
    """
    Vista para mostrar la página de configuración de perfil
    """
    perfil = getattr(request.user, "perfil", None)
    context = {
        "titulo": "Configuración de Perfil",
        "perfil": perfil,
    }
    context.update(_contexto_rol_panel(request.user))
    return render(request, "usuarios/configuracion_perfil.html", context)


@login_required
def cambiar_contraseña_view(request):
    """
    Vista para cambiar la contraseña del usuario
    """
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "¡Tu contraseña ha sido cambiada exitosamente!")
            return redirect("usuarios:perfil")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = PasswordChangeForm(request.user)

    context = {
        "titulo": "Cambiar Contraseña",
        "form": form,
    }
    context.update(_contexto_rol_panel(request.user))
    return render(request, "usuarios/cambiar_contrasena.html", context)


# ==================== VISTA DE BIENVENIDA ====================


@login_required
def bienvenida_view(request):
    """
    Vista de bienvenida después del login exitoso
    Muestra un mensaje de bienvenida con animación y redirige automáticamente
    """
    nombre_usuario = request.session.get(
        "welcome_name", request.user.get_full_name() or request.user.username
    )
    redirect_url_name = request.session.get(
        "redirect_after_welcome", resolver_panel_por_rol(request.user)
    )

    # Convertir el nombre de la URL a una URL absoluta
    try:
        redirect_url = reverse(redirect_url_name)
    except:
        redirect_url = reverse(resolver_panel_por_rol(request.user))

    # Limpiar las variables de sesión
    if "welcome_name" in request.session:
        del request.session["welcome_name"]
    if "redirect_after_welcome" in request.session:
        del request.session["redirect_after_welcome"]

    context = {
        "nombre_usuario": nombre_usuario,
        "redirect_url": redirect_url,
    }
    return render(request, "usuarios/bienvenida.html", context)


# ==================== VISTAS DE RECUPERACIÓN DE CONTRASEÑA ====================

from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from datetime import datetime
from .forms import PasswordResetRequestForm, PasswordResetConfirmForm


@csrf_protect
def password_reset_request_view(request):
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]

            # Buscar usuarios con ese email
            users = User.objects.filter(email__iexact=email)

            for user in users:
                # Generar token y uid
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))

                # Construir URL de reset
                reset_url = request.build_absolute_uri(
                    reverse(
                        "usuarios:restablecer_contraseña",
                        kwargs={"uidb64": uid, "token": token},
                    )
                )

                # Preparar contexto para el template HTML
                email_context = {
                    "nombre": user.first_name or user.username,
                    "reset_url": reset_url,
                    "year": datetime.now().year,
                }

                # Renderizar template HTML
                html_content = render_to_string(
                    "usuarios/email_recuperacion.html", email_context
                )
                text_content = strip_tags(html_content)

                # Enviar correo HTML
                subject = "🔐 Recuperación de Contraseña - MineGate SENA"
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[user.email],
                )
                email.attach_alternative(html_content, "text/html")
                email.send()

            messages.success(
                request,
                "Se ha enviado un correo con instrucciones para restablecer tu contraseña.",
            )
            return redirect("usuarios:correo_enviado")
    else:
        form = PasswordResetRequestForm()

    context = {"form": form, "titulo": "Recuperar Contraseña"}
    return render(request, "usuarios/solicitar_recuperacion.html", context)


def password_reset_done_view(request):
    return render(request, "usuarios/correo_enviado.html")


@csrf_protect
def password_reset_confirm_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == "POST":
            form = PasswordResetConfirmForm(request.POST)
            if form.is_valid():
                password = form.cleaned_data["password1"]
                user.set_password(password)
                user.save()

                messages.success(
                    request,
                    "¡Tu contraseña ha sido actualizada exitosamente! Ahora puedes iniciar sesión.",
                )
                return redirect("usuarios:contraseña_actualizada")
        else:
            form = PasswordResetConfirmForm()

        context = {
            "form": form,
            "validlink": True,
            "titulo": "Establecer Nueva Contraseña",
        }
        return render(request, "usuarios/restablecer_contrasena.html", context)
    else:
        messages.error(request, "El enlace de recuperación es inválido o ha expirado.")
        context = {"validlink": False, "titulo": "Enlace Inválido"}
        return render(request, "usuarios/restablecer_contrasena.html", context)


def password_reset_complete_view(request):
    return render(request, "usuarios/contrasena_actualizada.html")


# ==================== VISTAS DE EDITAR PERFIL DE ADMINISRADOR ====================


from django.http import HttpResponse
from django.template import loader
from .models import PerfilUsuario

from .forms import RegistroForm
from django.views import generic
from django.urls import reverse_lazy
from django.contrib import messages


class PerfilUsuarioUpdateView(generic.UpdateView):
    """Vista para actualizar un usuario existente"""

    model = PerfilUsuario
    form_class = RegistroForm
    template_name = "editar_aprendiz.html"
    success_url = reverse_lazy("aprendices:aprendices")
    pk_url_kwarg = "aprendiz_id"

    def form_valid(self, form):
        """Mostrar mensaje de éxito al actualizar"""
        messages.success(
            self.request,
            f"El aprendiz {form.instance.nombre_completo()} ha sido actualizado exitosamente.",
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        """Mostrar mensaje de error si el formulario es inválido"""
        messages.error(self.request, "Por favor, corrija los errores en el formulario.")
        return super().form_invalid(form)
        return render(request, "usuarios/contrasena_actualizada.html")


# ==================== VISTAS DE GESTIÓN DE PERMISOS ====================


def es_superusuario(user):
    """Verifica si el usuario es superusuario"""
    return user.is_superuser


@login_required(login_url="usuarios:login")
@user_passes_test(es_superusuario, login_url="core:panel_administrativo")
def gestionar_permisos_view(request):
    """
    Vista para que el administrador gestione los permisos de acceso de los usuarios
    Solo accesible por superusuarios
    """
    # Obtener filtros
    filtro_actual = request.GET.get("filtro", "todos")
    buscar = request.GET.get("buscar", "")

    # Obtener todos los perfiles (excluyendo superusuarios)
    perfiles = PerfilUsuario.objects.select_related("user").exclude(
        user__is_superuser=True
    )

    # Aplicar filtros
    if filtro_actual == "activos":
        perfiles = perfiles.filter(user__is_active=True)
    elif filtro_actual == "inactivos":
        perfiles = perfiles.filter(user__is_active=False)

    # Aplicar búsqueda
    if buscar:
        perfiles = perfiles.filter(
            Q(user__username__icontains=buscar)
            | Q(user__email__icontains=buscar)
            | Q(user__first_name__icontains=buscar)
            | Q(user__last_name__icontains=buscar)
            | Q(documento__icontains=buscar)
        )

    # Ordenar por fecha de registro
    perfiles = perfiles.order_by("-user__date_joined")

    # Agregar etiqueta de rol para mostrar en la tabla.
    for perfil in perfiles:
        perfil.rol_label = _etiqueta_rol_usuario(perfil.user)

    # Estadísticas
    total_usuarios = PerfilUsuario.objects.exclude(user__is_superuser=True).count()
    usuarios_activos = (
        PerfilUsuario.objects.filter(user__is_active=True)
        .exclude(user__is_superuser=True)
        .count()
    )
    usuarios_inactivos = (
        PerfilUsuario.objects.filter(user__is_active=False)
        .exclude(user__is_superuser=True)
        .count()
    )

    context = {
        "perfiles": perfiles,
        "filtro_actual": filtro_actual,
        "buscar": buscar,
        "total_usuarios": total_usuarios,
        "usuarios_activos": usuarios_activos,
        "usuarios_inactivos": usuarios_inactivos,
        "es_superusuario": request.user.is_superuser,
        "perfil": getattr(request.user, "perfil", None),
        "perfil_panel": getattr(request.user, "perfil", None),
        "panel_role_label": "Administrador",
    }

    return render(request, "usuarios/gestionar_permisos.html", context)


@login_required(login_url="usuarios:login")
@user_passes_test(es_superusuario, login_url="core:panel_administrativo")
def eliminar_usuario_permisos_view(request, usuario_id):
    """
    Elimina permanentemente un usuario del sistema
    Solo accesible por superusuarios
    """
    from django.http import JsonResponse

    usuario = get_object_or_404(User, id=usuario_id)

    # No permitir eliminar superusuarios
    if usuario.is_superuser:
        messages.error(request, "❌ No se puede eliminar un superusuario.")
        return redirect("core:panel_administrativo")

    # No permitir que se elimine a sí mismo
    if usuario == request.user:
        messages.error(request, "❌ No puedes eliminarte a ti mismo.")
        return redirect("core:panel_administrativo")

    if request.method == "POST":
        nombre_usuario = usuario.get_full_name() or usuario.username

        # Eliminar el usuario (esto también eliminará el perfil por CASCADE)
        usuario.delete()

        messages.success(
            request, f"🗑️ Usuario {nombre_usuario} eliminado permanentemente."
        )

        # Si es AJAX, retornar JSON
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True, "message": "Usuario eliminado"})

    return redirect("core:panel_administrativo")


@login_required(login_url="usuarios:login")
@user_passes_test(es_superusuario, login_url="core:panel_administrativo")
def gestionar_permisos_ajax_view(request):
    """
    Vista AJAX para filtrar usuarios sin recargar la página
    Retorna datos JSON para actualizar la tabla dinámicamente
    """
    from django.http import JsonResponse

    # Obtener filtros
    filtro_actual = request.GET.get("filtro", "todos")
    buscar = request.GET.get("buscar", "")

    # Obtener todos los perfiles (excluyendo superusuarios)
    perfiles = PerfilUsuario.objects.select_related("user").exclude(
        user__is_superuser=True
    )

    # Aplicar filtros
    if filtro_actual == "activos":
        perfiles = perfiles.filter(user__is_active=True)
    elif filtro_actual == "inactivos":
        perfiles = perfiles.filter(user__is_active=False)

    # Aplicar búsqueda
    if buscar:
        perfiles = perfiles.filter(
            Q(user__username__icontains=buscar)
            | Q(user__email__icontains=buscar)
            | Q(user__first_name__icontains=buscar)
            | Q(user__last_name__icontains=buscar)
            | Q(documento__icontains=buscar)
        )

    # Ordenar por fecha de registro
    perfiles = perfiles.order_by("-user__date_joined")

    # Estadísticas
    total_usuarios = PerfilUsuario.objects.exclude(user__is_superuser=True).count()
    usuarios_activos = (
        PerfilUsuario.objects.filter(user__is_active=True)
        .exclude(user__is_superuser=True)
        .count()
    )
    usuarios_inactivos = (
        PerfilUsuario.objects.filter(user__is_active=False)
        .exclude(user__is_superuser=True)
        .count()
    )

    # Preparar datos de usuarios
    usuarios_data = []
    for perfil in perfiles:
        usuarios_data.append(
            {
                "id": perfil.user.id,
                "nombre": perfil.user.get_full_name() or perfil.user.username,
                "username": perfil.user.username,
                "documento": perfil.documento,
                "email": perfil.user.email,
                "rol": _etiqueta_rol_usuario(perfil.user),
                "telefono": perfil.telefono or "No especificado",
                "fecha_registro": perfil.user.date_joined.strftime("%d/%m/%Y %H:%M"),
                "is_active": perfil.user.is_active,
            }
        )

    return JsonResponse(
        {
            "success": True,
            "usuarios": usuarios_data,
            "estadisticas": {
                "total": total_usuarios,
                "activos": usuarios_activos,
                "inactivos": usuarios_inactivos,
            },
        }
    )


# ==================== CREAR USUARIO DESDE GESTIÓN DE PERMISOS ====================


@login_required(login_url="usuarios:login")
@user_passes_test(es_superusuario, login_url="core:panel_administrativo")
def crear_usuario_permisos_view(request):
    """
    Vista para crear un nuevo usuario desde el módulo de gestión de permisos.
    Similar al registro pero administrado por superusuarios.
    """
    from .forms import RegistroForm

    if request.method == "POST":
        post_data = request.POST.copy()
        # El formulario usa documento como username internamente.
        # Lo seteamos desde la vista para evitar errores de validación del campo oculto.
        if not post_data.get("username"):
            post_data["username"] = post_data.get("documento", "")

        form = RegistroForm(post_data)

        # Obtener si el usuario debe estar activo
        usuario_activo = request.POST.get("usuario_activo", "on") == "on"
        rol_usuario = request.POST.get("rol_usuario", "sst")
        if rol_usuario == "administrador":
            rol_usuario = "sst"

        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = usuario_activo
            user.is_staff = rol_usuario == "sst"
            user.save()

            # Obtener o crear el perfil
            from .models import PerfilUsuario

            try:
                perfil = PerfilUsuario.objects.get(user=user)
            except PerfilUsuario.DoesNotExist:
                perfil = PerfilUsuario.objects.create(
                    user=user,
                    documento=form.cleaned_data.get("documento", ""),
                    telefono=form.cleaned_data.get("telefono", ""),
                )

            # Limpiar grupos de rol y asignar el nuevo
            user.groups.remove(*Group.objects.filter(name__in=["coordinador", "sst"]))
            if rol_usuario == "coordinador":
                group_coordinador, _ = Group.objects.get_or_create(name="coordinador")
                user.groups.add(group_coordinador)
            elif rol_usuario == "sst":
                group_sst, _ = Group.objects.get_or_create(name="sst")
                user.groups.add(group_sst)

            rol_mostrado = "SST" if rol_usuario == "sst" else "Coordinador"

            messages.success(
                request,
                f"✓ Usuario {user.get_full_name() or user.username} creado exitosamente como {rol_mostrado}.",
            )
            return redirect("usuarios:gestionar_permisos")
        else:
            # Exponer errores concretos para evitar el mensaje genérico de "campo faltante".
            for campo, errores in form.errors.items():
                etiqueta = "General" if campo == "__all__" else campo.replace("_", " ").title()
                if campo in form.fields and form.fields[campo].label:
                    etiqueta = form.fields[campo].label
                for error in errores:
                    messages.error(request, f"{etiqueta}: {error}")
    else:
        form = RegistroForm()

    context = {
        "form": form,
        "titulo": "Crear Nuevo Usuario",
        "es_superusuario": request.user.is_superuser,
        "perfil": getattr(request.user, "perfil", None),
        "perfil_panel": getattr(request.user, "perfil", None),
        "panel_role_label": "Administrador",
        "rol_actual": (
            request.POST.get("rol_usuario", "sst")
            if request.method == "POST"
            else "sst"
        ),
    }
    return render(request, "usuarios/crear_usuario_permisos.html", context)


# ==================== VER DETALLE DE USUARIO ====================


@login_required(login_url="usuarios:login")
@user_passes_test(es_superusuario, login_url="core:panel_administrativo")
def detalle_usuario_permisos_view(request, usuario_id):
    """
    Vista para ver todos los detalles de un usuario.
    Retorna JSON si es una petición AJAX.
    """
    usuario = get_object_or_404(User, id=usuario_id)

    try:
        perfil = usuario.perfil
    except PerfilUsuario.DoesNotExist:
        perfil = None

    # Si es una petición AJAX, retornar JSON
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        datos_usuario = {
            "id": usuario.id,
            "username": usuario.username,
            "nombre_completo": usuario.get_full_name() or usuario.username,
            "first_name": usuario.first_name,
            "last_name": usuario.last_name,
            "email": usuario.email,
            "is_active": usuario.is_active,
            "is_staff": usuario.is_staff,
            "is_superuser": usuario.is_superuser,
            "date_joined": usuario.date_joined.strftime("%d/%m/%Y %H:%M"),
            "last_login": (
                usuario.last_login.strftime("%d/%m/%Y %H:%M")
                if usuario.last_login
                else "Nunca"
            ),
        }

        if perfil:
            datos_usuario.update(
                {
                    "documento": perfil.documento,
                    "telefono": perfil.telefono or "No especificado",
                    "direccion": perfil.direccion or "No especificada",
                    "fecha_nacimiento": (
                        perfil.fecha_nacimiento.strftime("%d/%m/%Y")
                        if perfil.fecha_nacimiento
                        else "No especificada"
                    ),
                    "foto_perfil": perfil.foto_perfil.url if perfil.foto_perfil else "",
                }
            )

        return JsonResponse({"success": True, "usuario": datos_usuario})

    # Si no es AJAX, renderizar template
    context = {
        "usuario": usuario,
        "perfil": perfil,
        "perfil_panel": getattr(request.user, "perfil", None),
        "panel_role_label": "Administrador",
        "titulo": f"Detalles de {usuario.get_full_name() or usuario.username}",
    }
    return render(request, "usuarios/detalle_usuario_permisos.html", context)


# ==================== EDITAR USUARIO (AJAX MODAL) ====================


@login_required(login_url="usuarios:login")
@user_passes_test(es_superusuario, login_url="core:panel_administrativo")
def editar_usuario_ajax_view(request, usuario_id):
    """
    Vista AJAX para obtener y actualizar datos de usuario desde el modal de gestión de permisos.
    GET: Retorna datos del usuario en JSON para pre-llenar el formulario del modal.
    POST: Valida y guarda los cambios, devuelve JSON con resultado.
    """
    usuario = get_object_or_404(User, id=usuario_id)
    try:
        perfil = usuario.perfil
    except PerfilUsuario.DoesNotExist:
        perfil = None

    if request.method == "GET":
        datos = {
            "id": usuario.id,
            "first_name": usuario.first_name,
            "last_name": usuario.last_name,
            "email": usuario.email,
            "telefono": (perfil.telefono or "") if perfil else "",
        }
        return JsonResponse({"success": True, "usuario": datos})

    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        telefono = request.POST.get("telefono", "").strip()

        errores = {}
        if not first_name:
            errores["first_name"] = "El nombre es obligatorio."
        if not last_name:
            errores["last_name"] = "El apellido es obligatorio."
        if not email:
            errores["email"] = "El correo es obligatorio."
        elif User.objects.exclude(pk=usuario.pk).filter(email__iexact=email).exists():
            errores["email"] = "Este correo ya está en uso por otro usuario."

        if errores:
            return JsonResponse({"success": False, "errors": errores})

        usuario.first_name = first_name
        usuario.last_name = last_name
        usuario.email = email
        usuario.save()

        if perfil:
            perfil.telefono = telefono
            perfil.save()

        return JsonResponse(
            {
                "success": True,
                "message": f"Usuario {usuario.get_full_name()} actualizado correctamente.",
                "nombre_completo": usuario.get_full_name(),
            }
        )

    return JsonResponse(
        {"success": False, "message": "Método no permitido."}, status=405
    )


# ==================== CAMBIAR ESTADO ACTIVO/INACTIVO ====================


@login_required(login_url="usuarios:login")
@user_passes_test(es_superusuario, login_url="core:panel_administrativo")
def toggle_estado_usuario_view(request, usuario_id):
    """
    Cambia el estado activo/inactivo de un usuario.
    """
    usuario = get_object_or_404(User, id=usuario_id)

    # No permitir cambiar estado de superusuarios
    if usuario.is_superuser:
        messages.error(request, "❌ No se puede cambiar el estado de un superusuario.")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "success": False,
                    "message": "No se puede cambiar el estado de un superusuario.",
                }
            )
        return redirect("usuarios:gestionar_permisos")

    # No permitir que se desactive a sí mismo
    if usuario == request.user:
        messages.error(request, "❌ No puedes desactivar tu propia cuenta.")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"success": False, "message": "No puedes desactivar tu propia cuenta."}
            )
        return redirect("usuarios:gestionar_permisos")

    if request.method == "POST":
        # Toggle el estado
        usuario.is_active = not usuario.is_active
        usuario.save()

        estado = "activado" if usuario.is_active else "desactivado"
        emoji = "✓" if usuario.is_active else "⏸️"
        messages.success(
            request,
            f"{emoji} Usuario {usuario.get_full_name() or usuario.username} {estado} exitosamente.",
        )

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "success": True,
                    "message": f"Usuario {estado}",
                    "nuevo_estado": usuario.is_active,
                }
            )

    return redirect("usuarios:gestionar_permisos")
