from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from usuarios.models import PerfilUsuario
from django.http import JsonResponse
from datetime import datetime


def es_superusuario(user):
    """Verifica si el usuario es superusuario"""
    return user.is_superuser


def index(request):
    return render(request, "core/index.html")


@login_required(login_url='usuarios:login')
def panel_administrativo(request):
    """
    Panel administrativo principal
    Incluye gestión de permisos solo para superusuarios
    """
    # Verificar que el usuario esté activo (excepto superusuarios)
    if not request.user.is_superuser:
        if not request.user.is_active:
            messages.error(request, "Tu cuenta está inactiva. Contacta al administrador.")
            return redirect("usuarios:login")

    # Redirigir instructores a sus paneles correspondientes
    if request.user.groups.filter(name='coordinador').exists():
        return redirect('coordinador:panel')
    if request.user.groups.filter(name='instructor_interno').exists():
        return redirect('panel_instructor_interno:panel')
    if request.user.groups.filter(name='instructor_externo').exists():
        return redirect('panel_instructor_externo:panel')

    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, "No tienes permisos para acceder al panel administrativo.")
        return redirect("core:index")

    context = {
        "es_superusuario": request.user.is_superuser,
        "perfil": getattr(request.user, "perfil", None),
    }

    # Si es superusuario, agregar datos para gestión de permisos
    if request.user.is_superuser:
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

        context.update(
            {
                "perfiles": perfiles,
                "filtro_actual": filtro_actual,
                "buscar": buscar,
                "total_usuarios": total_usuarios,
                "usuarios_activos": usuarios_activos,
                "usuarios_inactivos": usuarios_inactivos,
            }
        )

    return render(request, "core/panel_administrativo.html", context)


@login_required(login_url="usuarios:login")
@user_passes_test(es_superusuario, login_url="core:panel_administrativo")
def gestionar_permisos(request):
    """
    Vista para que el administrador gestione los permisos de acceso de los usuarios
    Solo accesible por superusuarios
    """
    # Obtener estadísticas
    total_usuarios = PerfilUsuario.objects.count()
    usuarios_activos = PerfilUsuario.objects.filter(user__is_active=True).count()
    usuarios_inactivos = PerfilUsuario.objects.filter(user__is_active=False).count()

    # Obtener filtros
    filtro = request.GET.get("filtro", "todos")
    buscar = request.GET.get("buscar", "")

    # Filtrar perfiles
    perfiles = PerfilUsuario.objects.all().select_related("user")

    if filtro == "activos":
        perfiles = perfiles.filter(user__is_active=True)
    elif filtro == "inactivos":
        perfiles = perfiles.filter(user__is_active=False)

    # Búsqueda
    if buscar:
        perfiles = (
            perfiles.filter(
                user__username__icontains=buscar,
            )
            | perfiles.filter(
                documento__icontains=buscar,
            )
            | perfiles.filter(
                user__email__icontains=buscar,
            )
            | perfiles.filter(
                user__first_name__icontains=buscar,
            )
        )

    # Ordenar
    perfiles = perfiles.order_by("-user__date_joined")

    context = {
        "perfiles": perfiles,
        "total_usuarios": total_usuarios,
        "usuarios_activos": usuarios_activos,
        "usuarios_inactivos": usuarios_inactivos,
        "filtro_actual": filtro,
        "buscar": buscar,
    }

    return render(request, "core/gestionar_permisos.html", context)


@login_required(login_url="usuarios:login")
@user_passes_test(es_superusuario, login_url="core:panel_administrativo")
def aprobar_usuario(request, usuario_id):
    """
    Aprueba un usuario para acceder al sistema
    """
    perfil = get_object_or_404(PerfilUsuario, user_id=usuario_id)

    if request.method == "POST":
        perfil.aprobado = True
        perfil.razon_rechazo = None
        perfil.fecha_aprobacion = datetime.now()
        perfil.save()

        messages.success(
            request, f"✓ Usuario {perfil.user.username} aprobado exitosamente."
        )

        # Si es AJAX, retornar JSON
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True, "message": "Usuario aprobado"})

    return redirect("core:gestionar_permisos")


@login_required(login_url="usuarios:login")
@user_passes_test(es_superusuario, login_url="core:panel_administrativo")
def rechazar_usuario(request, usuario_id):
    """
    Rechaza un usuario y no le permite acceder al sistema
    """
    perfil = get_object_or_404(PerfilUsuario, user_id=usuario_id)

    if request.method == "POST":
        razon = request.POST.get("razon", "No se proporcionó razón")

        perfil.aprobado = False
        perfil.razon_rechazo = razon
        perfil.fecha_aprobacion = None
        perfil.save()

        messages.warning(request, f"✗ Usuario {perfil.user.username} rechazado.")

        # Si es AJAX, retornar JSON
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True, "message": "Usuario rechazado"})

    return redirect("core:gestionar_permisos")

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Usuario rechazado'})

    return redirect('core:gestionar_permisos')  
def protocolos(request):
    """Renderiza la página de Protocolos de Seguridad."""
    return render(request, 'protocolos.html')
def protocolos(request):
    """Renderiza la página de Protocolos de Seguridad."""
    return render(request, 'protocolos.html')


def visitas(request):
    """Renderiza la página de Registro de Visitas."""
    return render(request, 'core/visitas.html')


def error_404(request, exception=None):
    """Maneja errores 404 - Página no encontrada"""
    return render(request, '404.html', status=404)
