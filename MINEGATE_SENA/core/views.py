from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from django.db.utils import OperationalError, ProgrammingError
from django.urls import reverse
from PIL import Image
from datetime import date, timedelta
import calendar
from usuarios.models import PerfilUsuario
from calendario.models import Availability
from .forms import (
    ContenidoPaginaInformativaForm,
    ElementoEncabezadoInformativoForm,
    ElementoGaleriaInformativaForm,
)
from .models import (
    ContenidoPaginaInformativa,
    ElementoEncabezadoInformativo,
    ElementoGaleriaInformativa,
)
from visitaInterna.models import VisitaInterna
from reportes.views import _obtener_filas_reporte


def es_superusuario(user):
    """Verifica si el usuario es superusuario"""
    return user.is_superuser


def _construir_slides_legacy(contenido):
    if not contenido:
        return []

    slides = []
    if contenido.imagen_principal:
        slides.append(
            {
                "titulo": contenido.titulo_principal,
                "texto": contenido.texto_principal,
                "imagen": contenido.imagen_principal,
                "tipo_legacy": True,
            }
        )
    if contenido.imagen_secundaria:
        slides.append(
            {
                "titulo": "",
                "texto": contenido.texto_secundario,
                "imagen": contenido.imagen_secundaria,
                "tipo_legacy": True,
            }
        )
    if contenido.imagen_terciaria:
        slides.append(
            {
                "titulo": "",
                "texto": contenido.texto_descripcion,
                "imagen": contenido.imagen_terciaria,
                "tipo_legacy": True,
            }
        )
    return slides


def _convertir_a_entero(valor, predeterminado=0):
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return predeterminado


def _aplicar_recorte_imagen(ruta_archivo, x, y, ancho_recorte, alto_recorte):
    if not ruta_archivo or ancho_recorte <= 0 or alto_recorte <= 0:
        return False

    try:
        with Image.open(ruta_archivo) as imagen:
            ancho_img, alto_img = imagen.size

            x = max(0, min(x, max(ancho_img - 1, 0)))
            y = max(0, min(y, max(alto_img - 1, 0)))
            x2 = max(x + 1, min(x + ancho_recorte, ancho_img))
            y2 = max(y + 1, min(y + alto_recorte, alto_img))

            recortada = imagen.crop((x, y, x2, y2))
            recortada.save(ruta_archivo)
        return True
    except Exception:
        return False


def _aplicar_recorte_desde_request(request, prefijo, ruta_archivo):
    x_raw = request.POST.get(f"{prefijo}_crop_x", "")
    y_raw = request.POST.get(f"{prefijo}_crop_y", "")
    w_raw = request.POST.get(f"{prefijo}_crop_w", "")
    h_raw = request.POST.get(f"{prefijo}_crop_h", "")

    if not any([x_raw, y_raw, w_raw, h_raw]):
        return None

    x = _convertir_a_entero(x_raw)
    y = _convertir_a_entero(y_raw)
    ancho_recorte = _convertir_a_entero(w_raw)
    alto_recorte = _convertir_a_entero(h_raw)

    return _aplicar_recorte_imagen(ruta_archivo, x, y, ancho_recorte, alto_recorte)


def index(request):
    contenido_pagina = None
    elementos_galeria = []
    elementos_encabezado = []

    try:
        contenido_pagina = ContenidoPaginaInformativa.obtener()
        elementos_galeria = ElementoGaleriaInformativa.objects.filter(activo=True)
        elementos_encabezado = ElementoEncabezadoInformativo.objects.filter(activo=True)
        if not elementos_encabezado.exists():
            elementos_encabezado = _construir_slides_legacy(contenido_pagina)
    except (OperationalError, ProgrammingError):
        contenido_pagina = None
        elementos_galeria = []
        elementos_encabezado = []

    return render(
        request,
        "core/index.html",
        {
            "contenido_pagina": contenido_pagina,
            "elementos_galeria": elementos_galeria,
            "elementos_encabezado": elementos_encabezado,
        },
    )


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
        "gestion_pagina_informativa",
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
    elif seccion_activa == "gestion_pagina_informativa":
        _agregar_contexto_pagina_informativa(request, context)

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


def _agregar_contexto_pagina_informativa(request, context):
    if not request.user.is_superuser:
        messages.error(
            request,
            "Solo el superusuario puede gestionar la página informativa.",
        )
        context["sin_permiso_gestion_pagina"] = True
        return

    try:
        contenido = ContenidoPaginaInformativa.obtener()
        elementos_encabezado = list(ElementoEncabezadoInformativo.objects.all())
        elementos_galeria = list(ElementoGaleriaInformativa.objects.all())
    except (OperationalError, ProgrammingError):
        context["error_gestion_pagina"] = (
            "Falta aplicar migraciones del módulo de página informativa. Ejecuta: python manage.py migrate"
        )
        return

    editar_slide_id = request.GET.get("editar_slide")
    slide_en_edicion = None
    if editar_slide_id:
        slide_en_edicion = ElementoEncabezadoInformativo.objects.filter(
            pk=editar_slide_id
        ).first()
        if not slide_en_edicion:
            messages.warning(request, "La diapositiva seleccionada no existe.")

    editar_galeria_id = request.GET.get("editar_galeria")
    galeria_en_edicion = None
    if editar_galeria_id:
        galeria_en_edicion = ElementoGaleriaInformativa.objects.filter(
            pk=editar_galeria_id
        ).first()
        if not galeria_en_edicion:
            messages.warning(request, "El elemento de galería seleccionado no existe.")

    abrir_seccion = request.GET.get("abrir", "")

    form_contenido = ContenidoPaginaInformativaForm(instance=contenido)
    form_slide = ElementoEncabezadoInformativoForm(instance=slide_en_edicion)
    form_elemento = ElementoGaleriaInformativaForm(instance=galeria_en_edicion)

    if request.method == "POST":
        accion = request.POST.get("accion")

        if accion == "actualizar_contenido":
            form_contenido = ContenidoPaginaInformativaForm(
                request.POST,
                request.FILES,
                instance=contenido,
            )
            form_slide = ElementoEncabezadoInformativoForm(instance=slide_en_edicion)
            form_elemento = ElementoGaleriaInformativaForm(instance=galeria_en_edicion)
            if form_contenido.is_valid():
                form_contenido.save()
                messages.success(
                    request,
                    "Configuración general actualizada correctamente.",
                )
                return redirect(
                    "core:panel_administrativo_seccion",
                    seccion="gestion_pagina_informativa",
                )
            errores = []
            for campo, lista in form_contenido.errors.items():
                nombre = "general" if campo == "__all__" else campo
                errores.append(f"{nombre}: {', '.join(lista)}")
            messages.error(
                request,
                "No se pudo guardar la configuración general. " + " | ".join(errores),
            )

        elif accion == "guardar_slide":
            slide_id = request.POST.get("slide_id")
            instancia_slide = None
            if slide_id:
                instancia_slide = get_object_or_404(
                    ElementoEncabezadoInformativo, pk=slide_id
                )

            form_contenido = ContenidoPaginaInformativaForm(instance=contenido)
            form_slide = ElementoEncabezadoInformativoForm(
                request.POST,
                request.FILES,
                instance=instancia_slide,
            )
            form_elemento = ElementoGaleriaInformativaForm(instance=galeria_en_edicion)

            if form_slide.is_valid():
                orden_objetivo = form_slide.cleaned_data.get("orden")
                confirmar_reemplazo = (
                    request.POST.get("confirmar_reemplazo_slide") == "1"
                )

                conflictos = ElementoEncabezadoInformativo.objects.filter(
                    orden=orden_objetivo
                )
                if instancia_slide:
                    conflictos = conflictos.exclude(pk=instancia_slide.pk)

                total_conflictos = conflictos.count()
                if total_conflictos and not confirmar_reemplazo:
                    form_slide.add_error(
                        "orden",
                        "Esta posición ya está ocupada. Confirma reemplazo para continuar.",
                    )
                    messages.warning(
                        request,
                        f"La posición {orden_objetivo} ya tiene una diapositiva. Elige reemplazar o usa otra posición.",
                    )
                else:
                    if total_conflictos and confirmar_reemplazo:
                        conflictos.delete()
                        messages.info(
                            request,
                            f"Se reemplazó {total_conflictos} diapositiva(s) en la posición {orden_objetivo}.",
                        )

                    slide_guardado = form_slide.save()

                    if "imagen" in request.FILES and slide_guardado.imagen:
                        resultado_recorte = _aplicar_recorte_desde_request(
                            request,
                            prefijo="slide",
                            ruta_archivo=slide_guardado.imagen.path,
                        )
                        if resultado_recorte is False:
                            messages.warning(
                                request,
                                "La diapositiva se guardó, pero no se pudo aplicar el ajuste de recorte.",
                            )

                    messages.success(request, "Diapositiva del encabezado guardada correctamente.")
                    destino = reverse(
                        "core:panel_administrativo_seccion",
                        kwargs={"seccion": "gestion_pagina_informativa"},
                    )
                    return redirect(f"{destino}?abrir=encabezado&enfocar=gpi-encabezado-lista")
            errores = []
            for campo, lista in form_slide.errors.items():
                nombre = "encabezado" if campo == "__all__" else campo
                errores.append(f"{nombre}: {', '.join(lista)}")
            messages.error(
                request,
                "No se pudo guardar la diapositiva del encabezado. " + " | ".join(errores),
            )

        elif accion == "eliminar_slide":
            slide_id = request.POST.get("slide_id")
            slide = get_object_or_404(ElementoEncabezadoInformativo, pk=slide_id)
            slide.delete()
            messages.success(request, "Diapositiva del encabezado eliminada correctamente.")
            abrir_destino = request.POST.get("abrir_seccion") or "encabezado"
            destino = reverse(
                "core:panel_administrativo_seccion",
                kwargs={"seccion": "gestion_pagina_informativa"},
            )
            return redirect(f"{destino}?abrir={abrir_destino}&enfocar=gpi-encabezado-lista")

        elif accion == "guardar_elemento":
            elemento_id = request.POST.get("elemento_id")
            instancia = None
            if elemento_id:
                instancia = get_object_or_404(ElementoGaleriaInformativa, pk=elemento_id)

            form_contenido = ContenidoPaginaInformativaForm(instance=contenido)
            form_slide = ElementoEncabezadoInformativoForm(instance=slide_en_edicion)
            form_elemento = ElementoGaleriaInformativaForm(
                request.POST,
                request.FILES,
                instance=instancia,
            )
            if form_elemento.is_valid():
                orden_objetivo = form_elemento.cleaned_data.get("orden")
                confirmar_reemplazo = (
                    request.POST.get("confirmar_reemplazo_galeria") == "1"
                )

                conflictos = ElementoGaleriaInformativa.objects.filter(orden=orden_objetivo)
                if instancia:
                    conflictos = conflictos.exclude(pk=instancia.pk)

                total_conflictos = conflictos.count()
                if total_conflictos and not confirmar_reemplazo:
                    form_elemento.add_error(
                        "orden",
                        "Esta posición ya está ocupada. Confirma reemplazo para continuar.",
                    )
                    messages.warning(
                        request,
                        f"La posición {orden_objetivo} ya tiene un elemento de galería. Elige reemplazar o usa otra posición.",
                    )
                else:
                    if total_conflictos and confirmar_reemplazo:
                        conflictos.delete()
                        messages.info(
                            request,
                            f"Se reemplazó {total_conflictos} elemento(s) de galería en la posición {orden_objetivo}.",
                        )

                    elemento_guardado = form_elemento.save()

                    if (
                        "archivo" in request.FILES
                        and elemento_guardado.tipo == ElementoGaleriaInformativa.TIPO_IMAGEN
                        and elemento_guardado.archivo
                    ):
                        resultado_recorte = _aplicar_recorte_desde_request(
                            request,
                            prefijo="galeria",
                            ruta_archivo=elemento_guardado.archivo.path,
                        )
                        if resultado_recorte is False:
                            messages.warning(
                                request,
                                "El elemento se guardó, pero no se pudo aplicar el ajuste de recorte.",
                            )

                    messages.success(
                        request,
                        "Elemento de galería guardado correctamente.",
                    )
                    destino = reverse(
                        "core:panel_administrativo_seccion",
                        kwargs={"seccion": "gestion_pagina_informativa"},
                    )
                    return redirect(f"{destino}?abrir=galeria&enfocar=gpi-galeria-lista")
            errores = []
            for campo, lista in form_elemento.errors.items():
                nombre = "galería" if campo == "__all__" else campo
                errores.append(f"{nombre}: {', '.join(lista)}")
            messages.error(
                request,
                "No se pudo guardar el elemento de galería. " + " | ".join(errores),
            )

        elif accion == "eliminar_elemento":
            elemento_id = request.POST.get("elemento_id")
            elemento = get_object_or_404(ElementoGaleriaInformativa, pk=elemento_id)
            elemento.delete()
            messages.success(request, "Elemento de galería eliminado correctamente.")
            abrir_destino = request.POST.get("abrir_seccion") or "galeria"
            destino = reverse(
                "core:panel_administrativo_seccion",
                kwargs={"seccion": "gestion_pagina_informativa"},
            )
            return redirect(f"{destino}?abrir={abrir_destino}&enfocar=gpi-galeria-lista")

    context.update(
        {
            "form_contenido_pagina": form_contenido,
            "form_elemento_encabezado": form_slide,
            "form_elemento_galeria": form_elemento,
            "elementos_encabezado_admin": elementos_encabezado,
            "elementos_galeria_admin": elementos_galeria,
            "slide_en_edicion": slide_en_edicion,
            "galeria_en_edicion": galeria_en_edicion,
            "abrir_seccion": abrir_seccion,
            "slide_base_preview": (
                slide_en_edicion or (elementos_encabezado[0] if elementos_encabezado else None)
            ),
            "galeria_base_preview": (
                galeria_en_edicion or (elementos_galeria[0] if elementos_galeria else None)
            ),
        }
    )


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


def visitas(request):
    """Renderiza la página de Registro de Visitas."""
    return render(request, 'core/visitas.html')


def error_404(request, exception=None):
    """Maneja errores 404 - Página no encontrada"""
    return render(request, '404.html', status=404)
