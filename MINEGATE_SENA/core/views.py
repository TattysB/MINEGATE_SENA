from io import StringIO
from datetime import date, timedelta, datetime
import calendar
from pathlib import Path
from types import SimpleNamespace

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import ensure_csrf_cookie
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Q
from django.db.utils import OperationalError, ProgrammingError
from django.urls import reverse
from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError
from usuarios.models import PerfilUsuario
from calendario.models import Availability, ReservaHorario
from .forms import (
    ContenidoPaginaInformativaForm,
    ElementoEncabezadoInformativoForm,
    ElementoGaleriaInformativaForm,
)
from .models import (
    ConfiguracionBackupAutomatico,
    ContenidoPaginaInformativa,
    ElementoEncabezadoInformativo,
    ElementoGaleriaInformativa,
)
from visitaInterna.models import VisitaInterna, AsistenteVisitaInterna
from visitaExterna.models import VisitaExterna, AsistenteVisitaExterna
from control_acceso_mina.models import RegistroAccesoMina
from reportes.views import _obtener_filas_reporte


SECCIONES_PANEL_SUPERUSUARIO = {
    "panel_principal",
    "gestion_calendario",
    "gestion_visitas",
    "gestion_documentos",
    "control_acceso",
    "escaneo_documentos",
    "gestion_pagina_informativa",
    "copias_seguridad",
    "configuracion",
    "reportes",
}

SECCIONES_PANEL_SST = {
    "gestion_visitas",
    "gestion_documentos",
    "reportes",
}

ALLOWED_BACKUP_EXTENSIONS = {".dump", ".backup"}


def es_superusuario(user):
    """Verifica si el usuario es superusuario"""
    return user.is_superuser


def es_coordinador(user):
    return user.groups.filter(name="coordinador").exists()


def es_usuario_sst(user):
    return user.is_staff and not user.is_superuser and not es_coordinador(user)


def secciones_permitidas_panel(user):
    if user.is_superuser:
        return SECCIONES_PANEL_SUPERUSUARIO
    if es_usuario_sst(user):
        return SECCIONES_PANEL_SST
    return set()


def _obtener_directorio_backups():
    """Retorna el directorio fijo de backups y lo crea si no existe."""
    directorio = Path(settings.BASE_DIR) / "backups"
    directorio.mkdir(parents=True, exist_ok=True)
    return directorio


def _listar_backups_disponibles():
    """
    Lista backups permitidos (.dump/.backup) para mostrarlos en la interfaz.
    Nunca expone archivos fuera de la carpeta fija backups.
    """
    backups = []
    directorio = _obtener_directorio_backups()

    for archivo in directorio.iterdir():
        if not archivo.is_file():
            continue
        if archivo.suffix.lower() not in ALLOWED_BACKUP_EXTENSIONS:
            continue

        try:
            datos = archivo.stat()
        except OSError:
            continue

        backups.append(
            {
                "nombre": archivo.name,
                "tamano_mb": f"{datos.st_size / (1024 * 1024):.2f}",
                "modificado": datetime.fromtimestamp(datos.st_mtime),
            }
        )

    backups.sort(key=lambda item: item["modificado"], reverse=True)
    return backups


def _resolver_archivo_backup_seguro(nombre_archivo):
    """
    Valida y resuelve un backup dentro de la carpeta protegida.
    Previene path traversal y bloquea extensiones no permitidas.
    """
    nombre_limpio = (nombre_archivo or "").strip()
    if not nombre_limpio:
        return None, "Debes seleccionar un archivo de backup."

    if Path(nombre_limpio).name != nombre_limpio:
        return None, "El nombre del backup es invalido."

    if Path(nombre_limpio).suffix.lower() not in ALLOWED_BACKUP_EXTENSIONS:
        return None, "La extension del archivo no es valida para restauracion/eliminacion."

    directorio = _obtener_directorio_backups().resolve()
    ruta_archivo = (directorio / nombre_limpio).resolve()

    if directorio not in ruta_archivo.parents:
        return None, "Ruta de backup fuera del directorio permitido."

    if not ruta_archivo.exists() or not ruta_archivo.is_file():
        return None, "El archivo de backup seleccionado no existe."

    return ruta_archivo, None


def _validar_password_operacion_sensible(request):
    """Exige contraseña del usuario autenticado antes de ejecutar acciones críticas."""
    password_confirmacion = (request.POST.get("confirm_password") or "").strip()

    if not password_confirmacion:
        messages.error(
            request,
            "Debes confirmar tu contraseña para ejecutar esta acción.",
        )
        return False

    if not request.user.check_password(password_confirmacion):
        messages.error(request, "La contraseña ingresada no es correcta.")
        return False

    return True


def _obtener_horas_frecuencia_backup(frecuencia):
    try:
        return int(str(frecuencia).replace("h", ""))
    except (TypeError, ValueError):
        return 24


def _obtener_proxima_ejecucion_backup(config):
    if not config.activo:
        return None

    horas = _obtener_horas_frecuencia_backup(config.frecuencia)
    base = config.ultima_ejecucion or config.actualizado_en
    if not base:
        return None

    return base + timedelta(hours=horas)


def _guardar_configuracion_backup_automatico(request):
    config = ConfiguracionBackupAutomatico.obtener()

    activo_anterior = config.activo
    frecuencia_anterior = config.frecuencia

    activo = request.POST.get("auto_backup_activo") == "on"
    frecuencia = (request.POST.get("auto_backup_frecuencia") or "").strip()

    frecuencias_validas = {
        valor for valor, _ in ConfiguracionBackupAutomatico.FRECUENCIAS
    }
    if frecuencia not in frecuencias_validas:
        messages.error(request, "La frecuencia seleccionada no es válida.")
        return

    config.activo = activo
    config.frecuencia = frecuencia

    if activo and (
        not activo_anterior
        or frecuencia_anterior != frecuencia
        or config.ultima_ejecucion is None
    ):
        config.ultima_ejecucion = timezone.now()

    config.save()

    if config.activo:
        messages.success(
            request,
            "Programación automática guardada correctamente.",
        )
    else:
        messages.info(request, "El backup automático quedó desactivado.")


def _ejecutar_backup_automatico_si_corresponde(request, config):
    if not config.activo:
        return

    proxima = _obtener_proxima_ejecucion_backup(config)
    ahora = timezone.now()

    if proxima and ahora < proxima:
        return

    salida = StringIO()
    errores = StringIO()

    try:
        call_command("backupdb", stdout=salida, stderr=errores)
        config.ultima_ejecucion = ahora
        config.save()
        messages.info(
            request,
            "Se ejecutó una copia de seguridad automática según la programación.",
        )
    except CommandError as exc:
        detalle = errores.getvalue().strip() or str(exc)
        # Evita repetir intento en cada recarga inmediata cuando hay error.
        config.ultima_ejecucion = ahora
        config.save()
        messages.warning(
            request,
            f"El backup automático no pudo ejecutarse. Detalle: {detalle}",
        )


def _ejecutar_backup_desde_panel(request):
    """Llama al command backupdb desde la vista protegida."""
    salida = StringIO()
    errores = StringIO()

    try:
        call_command("backupdb", stdout=salida, stderr=errores)
    except CommandError as exc:
        detalle = errores.getvalue().strip() or str(exc)
        messages.error(
            request,
            f"No fue posible generar la copia de seguridad. Detalle: {detalle}",
        )
        return

    resumen = salida.getvalue().strip()
    if resumen:
        messages.success(request, f"Copia generada correctamente. {resumen}")
    else:
        messages.success(request, "Copia generada correctamente.")


def _ejecutar_restore_desde_panel(request):
    """Llama al command restoredb desde la vista protegida."""
    archivo = (request.POST.get("backup_file") or "").strip()
    archivo_resuelto, error_validacion = _resolver_archivo_backup_seguro(archivo)
    if error_validacion:
        messages.error(request, error_validacion)
        return

    kwargs_restore = {
        "file": archivo_resuelto.name,
        "target": "default",
    }

    salida = StringIO()
    errores = StringIO()

    try:
        call_command("restoredb", stdout=salida, stderr=errores, **kwargs_restore)
    except CommandError as exc:
        detalle = errores.getvalue().strip() or str(exc)
        messages.error(
            request,
            f"No fue posible restaurar la base de datos. Detalle: {detalle}",
        )
        return

    resumen = salida.getvalue().strip()
    if resumen:
        messages.success(request, f"Restauracion ejecutada correctamente. {resumen}")
    else:
        messages.success(request, "Restauracion ejecutada correctamente.")


def _eliminar_backup_desde_panel(request):
    """Elimina un backup permitido de la carpeta protegida."""
    archivo = (request.POST.get("backup_file") or "").strip()
    archivo_resuelto, error_validacion = _resolver_archivo_backup_seguro(archivo)
    if error_validacion:
        messages.error(request, error_validacion)
        return

    try:
        archivo_resuelto.unlink()
    except OSError as exc:
        messages.error(
            request,
            f"No fue posible eliminar la copia de seguridad. Detalle: {exc}",
        )
        return

    messages.success(
        request,
        f"Copia eliminada correctamente: {archivo_resuelto.name}",
    )


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


def _obtener_parametros_guardado(ruta_archivo, imagen):
    extension = Path(ruta_archivo or "").suffix.lower()

    if extension in {".jpg", ".jpeg"}:
        formato = "JPEG"
        if imagen.mode not in ("RGB", "L"):
            imagen = imagen.convert("RGB")
        return imagen, formato, {"quality": 90, "optimize": True}

    if extension == ".png":
        return imagen, "PNG", {}

    if extension == ".webp":
        return imagen, "WEBP", {}

    if imagen.mode not in ("RGB", "L"):
        imagen = imagen.convert("RGB")
    return imagen, "JPEG", {"quality": 90, "optimize": True}


def _aplicar_recorte_imagen(ruta_archivo, x, y, ancho_recorte, alto_recorte):
    if not ruta_archivo or ancho_recorte <= 0 or alto_recorte <= 0:
        return False

    try:
        with Image.open(ruta_archivo) as imagen_original:
            imagen = ImageOps.exif_transpose(imagen_original)
            ancho_img, alto_img = imagen.size

            x = max(0, min(x, max(ancho_img - 1, 0)))
            y = max(0, min(y, max(alto_img - 1, 0)))
            x2 = max(x + 1, min(x + ancho_recorte, ancho_img))
            y2 = max(y + 1, min(y + alto_recorte, alto_img))

            recortada = imagen.crop((x, y, x2, y2))
            recortada, formato, kwargs_guardado = _obtener_parametros_guardado(
                ruta_archivo,
                recortada,
            )
            recortada.save(ruta_archivo, format=formato, **kwargs_guardado)
        return True
    except (UnidentifiedImageError, OSError, ValueError):
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


@ensure_csrf_cookie
def index(request):
    contenido_pagina = None
    elementos_galeria = []
    elementos_encabezado = []

    try:
        contenido_pagina = ContenidoPaginaInformativa.obtener()
        # Evita inconsistencias visuales si existen filas sin archivo asociado.
        elementos_galeria = ElementoGaleriaInformativa.objects.filter(
            activo=True
        ).exclude(archivo="")
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


@login_required(login_url="usuarios:login")
def panel_administrativo(request):
    seccion_inicial = "gestion_visitas" if es_usuario_sst(request.user) else "panel_principal"
    return _render_panel_administrativo(request, seccion_activa=seccion_inicial)


@login_required(login_url="usuarios:login")
def panel_administrativo_seccion(request, seccion):
    if seccion not in SECCIONES_PANEL_SUPERUSUARIO:
        messages.warning(request, "La sección solicitada no existe.")
        return redirect("core:panel_administrativo")

    permitidas = secciones_permitidas_panel(request.user)
    if permitidas and seccion not in permitidas:
        messages.error(request, "No tienes permisos para acceder a esa sección.")
        if es_usuario_sst(request.user):
            return redirect("core:panel_administrativo_seccion", seccion="gestion_visitas")
        return redirect("core:panel_administrativo")

    return _render_panel_administrativo(request, seccion_activa=seccion)


@login_required(login_url="usuarios:login")
@staff_member_required(login_url="usuarios:login")
def panel_copias_seguridad(request):
    """
    Vista protegida para respaldos/restauraciones.
    Requisito: solo superadmin puede usar este modulo.
    """
    if not request.user.is_superuser:
        messages.error(request, "Solo el superadmin puede gestionar copias de seguridad.")
        return redirect("core:panel_administrativo")

    if request.method == "POST":
        accion = (request.POST.get("accion") or "").strip()

        if accion == "configurar_backup_automatico":
            try:
                _guardar_configuracion_backup_automatico(request)
            except (OperationalError, ProgrammingError):
                messages.error(
                    request,
                    "No se encontró la tabla de configuración automática. Ejecuta migrate para habilitar esta opción.",
                )
        elif accion == "generar_backup":
            if _validar_password_operacion_sensible(request):
                _ejecutar_backup_desde_panel(request)
        elif accion == "restaurar_backup":
            if _validar_password_operacion_sensible(request):
                _ejecutar_restore_desde_panel(request)
        elif accion == "eliminar_backup":
            if _validar_password_operacion_sensible(request):
                _eliminar_backup_desde_panel(request)
        else:
            messages.error(request, "Accion no valida para el modulo de backups.")

        return redirect("core:panel_copias_seguridad")

    try:
        config_backup_auto = ConfiguracionBackupAutomatico.obtener()
        _ejecutar_backup_automatico_si_corresponde(request, config_backup_auto)
        config_backup_auto.refresh_from_db()
        frecuencias_backup = ConfiguracionBackupAutomatico.FRECUENCIAS
        proxima_ejecucion = _obtener_proxima_ejecucion_backup(config_backup_auto)
    except (OperationalError, ProgrammingError):
        config_backup_auto = SimpleNamespace(
            activo=False,
            frecuencia=ConfiguracionBackupAutomatico.FRECUENCIA_24H,
            ultima_ejecucion=None,
        )
        frecuencias_backup = ConfiguracionBackupAutomatico.FRECUENCIAS
        proxima_ejecucion = None
        messages.warning(
            request,
            "La configuración automática estará disponible después de ejecutar migrate.",
        )

    contexto_backups = {
        "backups_disponibles": _listar_backups_disponibles(),
        "ruta_backups": str(_obtener_directorio_backups()),
        "config_backup_auto": config_backup_auto,
        "frecuencias_backup_auto": frecuencias_backup,
        "proxima_ejecucion_backup": proxima_ejecucion,
    }

    return _render_panel_administrativo(
        request,
        seccion_activa="copias_seguridad",
        extra_context=contexto_backups,
    )


def _agregar_contexto_calendario(context):
    today = date.today()
    year = today.year
    month = today.month

    cal = calendar.Calendar(firstweekday=6)
    month_days = list(cal.itermonthdates(year, month))
    weeks_raw = [month_days[i : i + 7] for i in range(0, len(month_days), 7)]

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

        reservas_qs = ReservaHorario.objects.filter(
            fecha__gte=start_month,
            fecha__lte=end_month,
        )
        fechas_pendientes = set()
        fechas_confirmadas = set()
        for reserva in reservas_qs:
            fecha_str = reserva.fecha.isoformat()
            if reserva.estado == "pendiente":
                fechas_pendientes.add(fecha_str)
            elif reserva.estado == "confirmada":
                fechas_confirmadas.add(fecha_str)
    except Exception:
        available_dates = set()
        fechas_pendientes = set()
        fechas_confirmadas = set()

    context.update(
        {
            "year": year,
            "month": month,
            "month_name": meses_es[month],
            "weeks": weeks,
            "today": today,
            "available_dates": available_dates,
            "fechas_pendientes": fechas_pendientes,
            "fechas_confirmadas": fechas_confirmadas,
        }
    )


def _agregar_contexto_panel_principal(context):
    hoy = date.today()
    inicio_mes_actual = hoy.replace(day=1)
    fin_mes_anterior = inicio_mes_actual - timedelta(days=1)
    inicio_mes_anterior = fin_mes_anterior.replace(day=1)

    def _variacion_porcentual(actual, anterior):
        if anterior <= 0:
            return 100.0 if actual > 0 else 0.0
        return round(((actual - anterior) / anterior) * 100.0, 1)

    try:
        visitas_int_qs = VisitaInterna.objects.all()
        visitas_ext_qs = VisitaExterna.objects.all()

        total_internas = visitas_int_qs.count()
        total_externas = visitas_ext_qs.count()
        total_visitas = total_internas + total_externas

        pendientes_total = (
            visitas_int_qs.filter(estado="pendiente").count()
            + visitas_ext_qs.filter(estado="pendiente").count()
        )
        confirmadas_total = (
            visitas_int_qs.filter(estado="aprobada_final").count()
            + visitas_ext_qs.filter(estado="aprobada_final").count()
        )
        rechazadas_total = (
            visitas_int_qs.filter(estado="rechazada").count()
            + visitas_ext_qs.filter(estado="rechazada").count()
        )
        reprogramaciones_total = (
            visitas_int_qs.filter(estado="reprogramacion_solicitada").count()
            + visitas_ext_qs.filter(estado="reprogramacion_solicitada").count()
        )

        asistentes_total = (
            AsistenteVisitaInterna.objects.count()
            + AsistenteVisitaExterna.objects.count()
        )

        accesos_hoy_entradas = RegistroAccesoMina.objects.filter(
            fecha_hora__date=hoy, tipo="ENTRADA"
        ).count()
        accesos_hoy_salidas = RegistroAccesoMina.objects.filter(
            fecha_hora__date=hoy, tipo="SALIDA"
        ).count()

        visitas_mes_actual = (
            visitas_int_qs.filter(fecha_solicitud__date__gte=inicio_mes_actual).count()
            + visitas_ext_qs.filter(fecha_solicitud__date__gte=inicio_mes_actual).count()
        )
        visitas_mes_anterior = (
            visitas_int_qs.filter(
                fecha_solicitud__date__gte=inicio_mes_anterior,
                fecha_solicitud__date__lte=fin_mes_anterior,
            ).count()
            + visitas_ext_qs.filter(
                fecha_solicitud__date__gte=inicio_mes_anterior,
                fecha_solicitud__date__lte=fin_mes_anterior,
            ).count()
        )

        variacion_mes_pct = _variacion_porcentual(
            visitas_mes_actual,
            visitas_mes_anterior,
        )

        tendencia_7_dias = []
        max_tendencia = 1
        for offset in range(6, -1, -1):
            dia = hoy - timedelta(days=offset)
            internas_dia = visitas_int_qs.filter(fecha_solicitud__date=dia).count()
            externas_dia = visitas_ext_qs.filter(fecha_solicitud__date=dia).count()
            total_dia = internas_dia + externas_dia

            tendencia_7_dias.append(
                {
                    "fecha": dia,
                    "label": dia.strftime("%d/%m"),
                    "internas": internas_dia,
                    "externas": externas_dia,
                    "total": total_dia,
                }
            )
            max_tendencia = max(max_tendencia, total_dia)

        for item in tendencia_7_dias:
            item["pct"] = round((item["total"] / max_tendencia) * 100, 1)

        visitas_recientes = []
        for visita in visitas_int_qs.order_by("-fecha_solicitud")[:6]:
            visitas_recientes.append(
                {
                    "id": visita.id,
                    "tipo": "Interna",
                    "responsable": visita.responsable,
                    "entidad": visita.nombre_programa,
                    "estado": visita.estado,
                    "estado_label": visita.estado.replace("_", " ").capitalize(),
                    "fecha_solicitud": visita.fecha_solicitud,
                }
            )

        for visita in visitas_ext_qs.order_by("-fecha_solicitud")[:6]:
            visitas_recientes.append(
                {
                    "id": visita.id,
                    "tipo": "Externa",
                    "responsable": visita.nombre_responsable,
                    "entidad": visita.nombre,
                    "estado": visita.estado,
                    "estado_label": visita.estado.replace("_", " ").capitalize(),
                    "fecha_solicitud": visita.fecha_solicitud,
                }
            )

        visitas_recientes.sort(
            key=lambda item: item.get("fecha_solicitud") or timezone.now() - timedelta(days=36500),
            reverse=True,
        )

        context.update(
            {
                "dashboard": {
                    "total_visitas": total_visitas,
                    "total_internas": total_internas,
                    "total_externas": total_externas,
                    "pendientes_total": pendientes_total,
                    "confirmadas_total": confirmadas_total,
                    "rechazadas_total": rechazadas_total,
                    "reprogramaciones_total": reprogramaciones_total,
                    "asistentes_total": asistentes_total,
                    "accesos_hoy_entradas": accesos_hoy_entradas,
                    "accesos_hoy_salidas": accesos_hoy_salidas,
                    "visitas_mes_actual": visitas_mes_actual,
                    "visitas_mes_anterior": visitas_mes_anterior,
                    "variacion_mes_pct": variacion_mes_pct,
                    "tendencia_7_dias": tendencia_7_dias,
                    "visitas_recientes": visitas_recientes[:8],
                }
            }
        )
    except (OperationalError, ProgrammingError):
        context.update(
            {
                "dashboard": {
                    "total_visitas": 0,
                    "total_internas": 0,
                    "total_externas": 0,
                    "pendientes_total": 0,
                    "confirmadas_total": 0,
                    "rechazadas_total": 0,
                    "reprogramaciones_total": 0,
                    "asistentes_total": 0,
                    "accesos_hoy_entradas": 0,
                    "accesos_hoy_salidas": 0,
                    "visitas_mes_actual": 0,
                    "visitas_mes_anterior": 0,
                    "variacion_mes_pct": 0,
                    "tendencia_7_dias": [],
                    "visitas_recientes": [],
                },
                "dashboard_error": "Faltan migraciones o tablas para cargar las estadísticas del panel principal.",
            }
        )


def _render_panel_administrativo(
    request,
    seccion_activa="panel_principal",
    extra_context=None,
):
    """
    Panel administrativo principal
    Incluye gestión de permisos solo para superusuarios
    """
    # Verificar que el usuario esté activo (excepto superusuarios)
    if not request.user.is_superuser:
        if not request.user.is_active:
            messages.error(
                request, "Tu cuenta está inactiva. Contacta al administrador."
            )
            return redirect("usuarios:login")

    # Redirigir instructores a sus paneles correspondientes
    if request.user.groups.filter(name="coordinador").exists():
        return redirect("coordinador:panel")
    if request.user.groups.filter(name="instructor_interno").exists():
        return redirect("panel_instructor_interno:panel")
    if request.user.groups.filter(name="instructor_externo").exists():
        return redirect("panel_instructor_externo:panel")

    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(
            request, "No tienes permisos para acceder al panel administrativo."
        )
        return redirect("core:index")

    usuario_sst = es_usuario_sst(request.user)
    if usuario_sst and seccion_activa == "panel_principal":
        seccion_activa = "gestion_visitas"

    permitidas = secciones_permitidas_panel(request.user)
    if permitidas and seccion_activa not in permitidas:
        messages.error(request, "No tienes permisos para acceder a esa sección.")
        return redirect("core:panel_administrativo_seccion", seccion="gestion_visitas")

    context = {
        "es_superusuario": request.user.is_superuser,
        "solo_sst": usuario_sst,
        "perfil": getattr(request.user, "perfil", None),
        "perfil_panel": getattr(request.user, "perfil", None),
        "panel_role_label": "Administrador" if request.user.is_superuser else "SST",
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

    if seccion_activa == "panel_principal":
        _agregar_contexto_panel_principal(context)
    elif seccion_activa == "gestion_calendario":
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

    if extra_context:
        context.update(extra_context)

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
        elementos_encabezado = list(
            ElementoEncabezadoInformativo.objects.all().order_by("orden", "id")
        )
        elementos_galeria = list(
            ElementoGaleriaInformativa.objects.all().order_by("orden", "id")
        )
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

    destino_gpi = reverse(
        "core:panel_administrativo_seccion",
        kwargs={"seccion": "gestion_pagina_informativa"},
    )

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
                destino = reverse(
                    "core:panel_administrativo_seccion",
                    kwargs={"seccion": "gestion_pagina_informativa"},
                )
                return redirect(f"{destino}?recargar={int(timezone.now().timestamp())}")
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
                instancia_slide = ElementoEncabezadoInformativo.objects.filter(
                    pk=slide_id
                ).first()
                if not instancia_slide:
                    messages.warning(
                        request,
                        "La diapositiva que intentas editar ya no existe. Recarga la sección y vuelve a intentar.",
                    )
                    return redirect(f"{destino_gpi}?abrir=encabezado")

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

                    messages.success(
                        request, "Diapositiva del encabezado guardada correctamente."
                    )
                    return redirect(
                        f"{destino_gpi}?abrir=encabezado&enfocar=gpi-encabezado-lista&recargar={int(timezone.now().timestamp())}"
                    )
            errores = []
            for campo, lista in form_slide.errors.items():
                nombre = "encabezado" if campo == "__all__" else campo
                errores.append(f"{nombre}: {', '.join(lista)}")
            messages.error(
                request,
                "No se pudo guardar la diapositiva del encabezado. "
                + " | ".join(errores),
            )

        elif accion == "eliminar_slide":
            slide_id = request.POST.get("slide_id")
            slide = ElementoEncabezadoInformativo.objects.filter(pk=slide_id).first()
            if not slide:
                messages.warning(
                    request,
                    "La diapositiva que intentas eliminar ya no existe.",
                )
                return redirect(f"{destino_gpi}?abrir=encabezado")
            slide.delete()
            messages.success(
                request, "Diapositiva del encabezado eliminada correctamente."
            )
            abrir_destino = request.POST.get("abrir_seccion") or "encabezado"
            return redirect(
                f"{destino_gpi}?abrir={abrir_destino}&enfocar=gpi-encabezado-lista&recargar={int(timezone.now().timestamp())}"
            )

        elif accion == "guardar_elemento":
            elemento_id = request.POST.get("elemento_id")
            instancia = None
            if elemento_id:
                instancia = ElementoGaleriaInformativa.objects.filter(
                    pk=elemento_id
                ).first()
                if not instancia:
                    messages.warning(
                        request,
                        "El elemento de galería que intentas editar ya no existe. Recarga la sección y vuelve a intentar.",
                    )
                    return redirect(f"{destino_gpi}?abrir=galeria")

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

                conflictos = ElementoGaleriaInformativa.objects.filter(
                    orden=orden_objetivo
                )
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
                        and elemento_guardado.tipo
                        == ElementoGaleriaInformativa.TIPO_IMAGEN
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
                    return redirect(
                        f"{destino_gpi}?abrir=galeria&enfocar=gpi-galeria-lista&recargar={int(timezone.now().timestamp())}"
                    )
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
            elemento = ElementoGaleriaInformativa.objects.filter(pk=elemento_id).first()
            if not elemento:
                messages.warning(
                    request,
                    "El elemento de galería que intentas eliminar ya no existe.",
                )
                return redirect(f"{destino_gpi}?abrir=galeria")
            elemento.delete()
            messages.success(request, "Elemento de galería eliminado correctamente.")
            abrir_destino = request.POST.get("abrir_seccion") or "galeria"
            return redirect(
                f"{destino_gpi}?abrir={abrir_destino}&enfocar=gpi-galeria-lista&recargar={int(timezone.now().timestamp())}"
            )

    # Refresca listas desde BD para evitar que el render use datos antiguos.
    elementos_encabezado = list(
        ElementoEncabezadoInformativo.objects.all().order_by("orden", "id")
    )
    elementos_galeria = list(
        ElementoGaleriaInformativa.objects.all().order_by("orden", "id")
    )

    galeria_con_archivo = [
        item for item in elementos_galeria if getattr(item, "archivo", None)
    ]
    galeria_activa_con_archivo = [item for item in galeria_con_archivo if item.activo]
    galeria_base_preview = (
        galeria_en_edicion
        or (galeria_activa_con_archivo[0] if galeria_activa_con_archivo else None)
        or (galeria_con_archivo[0] if galeria_con_archivo else None)
        or (elementos_galeria[0] if elementos_galeria else None)
    )

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
                slide_en_edicion
                or (elementos_encabezado[0] if elementos_encabezado else None)
            ),
            "galeria_base_preview": galeria_base_preview,
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
    return render(request, "protocolos.html")


def visitas(request):
    """Renderiza la página de Registro de Visitas."""
    return render(request, "core/visitas.html")


def error_404(request, exception=None):
    """Maneja errores 404 - Página no encontrada"""
    return render(request, "404.html", status=404)


@login_required(login_url="usuarios:login")
@user_passes_test(es_superusuario, login_url="core:panel_administrativo")
def api_galeria_informativa(request):
    elementos = ElementoGaleriaInformativa.objects.all().order_by("orden", "id")
    payload = []

    for item in elementos:
        archivo_url = ""
        if item.archivo:
            try:
                archivo_url = (
                    f"{item.archivo.url}?v={int(item.actualizado_en.timestamp())}"
                )
            except (ValueError, OSError, AttributeError):
                archivo_url = ""

        payload.append(
            {
                "id": item.id,
                "tipo": item.tipo,
                "tipo_display": item.get_tipo_display(),
                "titulo": item.titulo or "",
                "descripcion": item.descripcion or "",
                "orden": item.orden,
                "activo": item.activo,
                "mime": item.mime_type,
                "archivo_url": archivo_url,
            }
        )

    return JsonResponse({"items": payload})
