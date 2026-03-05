from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from django.urls import reverse
from datetime import date, timedelta
import calendar
from usuarios.models import PerfilUsuario
from calendario.models import Availability
from visitaInterna.models import VisitaInterna
from reportes.views import _obtener_filas_reporte


def es_superusuario(user):
    """Verifica si el usuario es superusuario"""
    return user.is_superuser


def index(request):
    return render(request, "core/index.html")


@login_required(login_url='usuarios:login')
def panel_administrativo(request):
    return _render_panel_administrativo(request, seccion_activa="panel_principal")


@login_required(login_url='usuarios:login')
def panel_administrativo_seccion(request, seccion):
    secciones_validas = {
        "panel_principal",
        "gestion_calendario",
        "gestion_visitas",
        "gestion_documentos",
        "escaneo_documentos",
        "configuracion",
        "reportes",
    }

    if seccion not in secciones_validas:
        messages.warning(request, "La sección solicitada no existe.")
        return redirect("core:panel_administrativo")

    return _render_panel_administrativo(request, seccion_activa=seccion)


def _agregar_contexto_calendario(context):
    today = date.today()
    year = today.year
    month = today.month

    cal = calendar.Calendar(firstweekday=6)
    month_days = list(cal.itermonthdates(year, month))
    weeks_raw = [month_days[i:i + 7] for i in range(0, len(month_days), 7)]

    weeks = []
    for week in weeks_raw:
        row = []
        for day_obj in week:
            row.append(
                {
                    "date": day_obj,
                    "is_other_month": day_obj.month != month,
                    "is_today": day_obj == today,
                    "is_sunday": day_obj.weekday() == 6,
                    "is_past": day_obj < today,
                }
            )
        weeks.append(row)

    meses_es = [
        "",
        "Enero",
        "Febrero",
        "Marzo",
        "Abril",
        "Mayo",
        "Junio",
        "Julio",
        "Agosto",
        "Septiembre",
        "Octubre",
        "Noviembre",
        "Diciembre",
    ]

    try:
        start_month = date(year, month, 1)
        next_month = (start_month.replace(day=28) + timedelta(days=4)).replace(day=1)
        end_month = next_month - timedelta(days=1)
        available_dates = set(
            a.date.isoformat()
            for a in Availability.objects.filter(date__gte=today, date__lte=end_month)
        )
    except Exception:
        available_dates = set()

    context.update(
        {
            "year": year,
            "month": month,
            "month_name": meses_es[month],
            "weeks": weeks,
            "today": today,
            "available_dates": available_dates,
        }
    )


def _render_panel_administrativo(request, seccion_activa="panel_principal"):
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
        "seccion_activa": seccion_activa,
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

    if seccion_activa == "gestion_calendario":
        _agregar_contexto_calendario(context)

    if seccion_activa == "reportes":
        filas, filtros = _obtener_filas_reporte(request)
        context.update(
            {
                "filas_reportes": filas[:100],
                "total_filas_reportes": len(filas),
                "filtros_reportes": filtros,
                "query_string_reportes": request.GET.urlencode(),
                "estados_reportes": VisitaInterna.ESTADO_CHOICES,
            }
        )

    return render(request, "core/panel_administrativo.html", context)


@login_required(login_url="usuarios:login")
@user_passes_test(es_superusuario, login_url="core:panel_administrativo")
def gestionar_permisos(request):
    """Redirige a la gestión de permisos unificada en usuarios."""
    destino = reverse("usuarios:gestionar_permisos")
    query_string = request.META.get("QUERY_STRING", "")
    if query_string:
        destino = f"{destino}?{query_string}"
    return redirect(destino)


@login_required(login_url="usuarios:login")
@user_passes_test(es_superusuario, login_url="core:panel_administrativo")
def aprobar_usuario(request, usuario_id):
    """Ruta legacy: redirige a gestión de permisos unificada en usuarios."""
    messages.info(
        request,
        "La aprobación de usuarios fue centralizada en el módulo de usuarios.",
    )
    return redirect("usuarios:gestionar_permisos")


@login_required(login_url="usuarios:login")
@user_passes_test(es_superusuario, login_url="core:panel_administrativo")
def rechazar_usuario(request, usuario_id):
    """Ruta legacy: redirige a gestión de permisos unificada en usuarios."""
    messages.info(
        request,
        "El rechazo de usuarios fue centralizado en el módulo de usuarios.",
    )
    return redirect("usuarios:gestionar_permisos")
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
