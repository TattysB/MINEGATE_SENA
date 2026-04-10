"""
Signals para manejar eventos automáticos de las visitas.
Dispara la generación y envío de QR cuando un asistente es aprobado.
"""

from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.db.models import Q
from django.dispatch import receiver
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils.formats import date_format
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.urls import reverse
from visitaInterna.models import AsistenteVisitaInterna
from visitaExterna.models import AsistenteVisitaExterna
from visitaInterna.models import VisitaInterna
from visitaExterna.models import VisitaExterna
from gestion_visitas.services import GeneradorQRPDF
import logging

logger = logging.getLogger(__name__)


def _obtener_login_url():
    login_path = reverse("usuarios:login")
    base_url = getattr(settings, "APP_BASE_URL", "").strip().rstrip("/")

    if not base_url:
        trusted_origins = getattr(settings, "CSRF_TRUSTED_ORIGINS", [])
        if trusted_origins:
            base_url = str(trusted_origins[0]).rstrip("/")

    return f"{base_url}{login_path}" if base_url else login_path


def _formatear_resumen_visita(instance, tipo_visita):
    fecha_txt = date_format(instance.fecha_solicitud, "d/m/Y H:i") if instance.fecha_solicitud else "N/A"

    if tipo_visita == "interna":
        entidad = instance.nombre_programa
        responsable = instance.responsable
        cantidad = instance.cantidad_aprendices
    else:
        entidad = instance.nombre
        responsable = instance.nombre_responsable
        cantidad = instance.cantidad_visitantes

    return (
        f"ID de visita: {instance.id}\n"
        f"Tipo: {tipo_visita.capitalize()}\n"
        f"Entidad/Programa: {entidad}\n"
        f"Responsable: {responsable}\n"
        f"Correo responsable: {instance.correo_responsable}\n"
        f"Cantidad estimada de asistentes: {cantidad}\n"
        f"Fecha de solicitud: {fecha_txt}\n"
        f"Estado actual: {instance.get_estado_display()}\n"
    )


def _construir_contexto_nueva_visita(instance, tipo_visita):
    fecha_solicitud_txt = (
        date_format(instance.fecha_solicitud, "d/m/Y H:i")
        if instance.fecha_solicitud
        else "N/A"
    )
    fecha_visita_txt = (
        date_format(instance.fecha_visita, "d/m/Y")
        if getattr(instance, "fecha_visita", None)
        else "Por definir"
    )
    hora_inicio = getattr(instance, "hora_inicio", None)
    hora_fin = getattr(instance, "hora_fin", None)
    if hora_inicio and hora_fin:
        hora_txt = f"{hora_inicio.strftime('%H:%M')} - {hora_fin.strftime('%H:%M')}"
    elif hora_inicio:
        hora_txt = hora_inicio.strftime("%H:%M")
    else:
        hora_txt = "Por definir"

    if tipo_visita == "interna":
        entidad = instance.nombre_programa
        responsable = instance.responsable
        documento = instance.documento_responsable
        cantidad = instance.cantidad_aprendices
    else:
        entidad = instance.nombre
        responsable = instance.nombre_responsable
        documento = instance.documento_responsable
        cantidad = instance.cantidad_visitantes

    return {
        "visita_id": instance.id,
        "tipo_visita": tipo_visita.capitalize(),
        "entidad": entidad,
        "responsable": responsable,
        "documento_responsable": documento,
        "correo_responsable": instance.correo_responsable,
        "cantidad_asistentes": cantidad,
        "fecha_solicitud": fecha_solicitud_txt,
        "fecha_visita": fecha_visita_txt,
        "hora_visita": hora_txt,
        "estado": instance.get_estado_display(),
        "login_url": _obtener_login_url(),
    }


def _obtener_correos_coordinadores():
    return list(
        User.objects.filter(
            is_active=True,
            groups__name="coordinador",
        )
        .exclude(email="")
        .values_list("email", flat=True)
        .distinct()
    )


def _obtener_correos_administradores():
    return list(
        User.objects.filter(
            is_active=True,
        )
        .filter(Q(is_superuser=True) | (Q(is_staff=True) & ~Q(groups__name="coordinador")))
        .exclude(email="")
        .values_list("email", flat=True)
        .distinct()
    )


def _notificar_nueva_visita_por_rol(instance, tipo_visita):
    resumen = _formatear_resumen_visita(instance, tipo_visita)
    contexto = _construir_contexto_nueva_visita(instance, tipo_visita)

    correos_coordinador = _obtener_correos_coordinadores()
    correos_administrador = _obtener_correos_administradores()

    if correos_coordinador:
        subject = f"[Coordinacion] Nueva visita {tipo_visita} registrada"
        html_content = render_to_string(
            "emails/notificacion_nueva_visita_coordinador.html", contexto
        )
        text_content = strip_tags(html_content)

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=correos_coordinador,
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=True)

    if correos_administrador:
        subject = f"[Administracion] Nueva visita {tipo_visita} registrada"
        html_content = render_to_string(
            "emails/notificacion_nueva_visita_administrador.html", contexto
        )
        text_content = strip_tags(html_content)

        msg = EmailMultiAlternatives(
            subject=subject,
            body=(
                f"{text_content}\n\n"
                "Contexto adicional:\n"
                "Esta visita iniciara revision por coordinacion y luego pasara a validacion administrativa.\n\n"
                f"{resumen}"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=correos_administrador,
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=True)


@receiver(post_save, sender=VisitaInterna)
def notificar_nueva_visita_interna(sender, instance, created, **kwargs):
    """Envía notificaciones por correo a coordinadores y administradores al crear una visita interna."""
    if not created:
        return

    try:
        _notificar_nueva_visita_por_rol(instance, "interna")
    except Exception as e:
        logger.error(f"Error notificando nueva visita interna #{instance.id}: {str(e)}")


@receiver(post_save, sender=VisitaExterna)
def notificar_nueva_visita_externa(sender, instance, created, **kwargs):
    """Envía notificaciones por correo a coordinadores y administradores al crear una visita externa."""
    if not created:
        return

    try:
        _notificar_nueva_visita_por_rol(instance, "externa")
    except Exception as e:
        logger.error(f"Error notificando nueva visita externa #{instance.id}: {str(e)}")


@receiver(post_save, sender=AsistenteVisitaInterna)
def generar_qr_asistente_interno(sender, instance, created, update_fields, **kwargs):
    """
    Signal que se dispara cuando se cambia el estado de un asistente interno
    a "documentos_aprobados" y la visita ya esta "confirmada".
    """
    if update_fields and 'estado' not in update_fields:
        return
    
    if (instance.estado == 'documentos_aprobados' and 
        instance.visita.estado == 'confirmada' and
        not instance.qr_generado and 
        instance.correo):
        
        try:
            generador = GeneradorQRPDF(
                asistente=instance,
                visita=instance.visita,
                tipo_visita='interna'
            )
            
            if generador.enviar_por_email():
                instance.qr_generado = True
                instance.fecha_envio_qr = timezone.now()
                instance.email_qr_enviado = True
                AsistenteVisitaInterna.objects.filter(pk=instance.pk).update(
                    qr_generado=True,
                    fecha_envio_qr=timezone.now(),
                    email_qr_enviado=True
                )
                logger.info(f"QR generado y enviado para asistente interno: {instance.nombre_completo}")
            else:
                logger.warning(f"Error al generar QR para asistente interno: {instance.nombre_completo}")
        
        except Exception as e:
            logger.error(f"Error en signal generar_qr_asistente_interno: {str(e)}")


@receiver(post_save, sender=AsistenteVisitaExterna)
def generar_qr_asistente_externo(sender, instance, created, update_fields, **kwargs):
    """
    Signal que se dispara cuando se cambia el estado de un asistente externo
    a "documentos_aprobados" y la visita ya esta "confirmada".
    """
    if update_fields and 'estado' not in update_fields:
        return
    
    if (instance.estado == 'documentos_aprobados' and 
        instance.visita.estado == 'confirmada' and
        not instance.qr_generado and 
        instance.correo):
        
        try:
            generador = GeneradorQRPDF(
                asistente=instance,
                visita=instance.visita,
                tipo_visita='externa'
            )
            
            if generador.enviar_por_email():
                instance.qr_generado = True
                instance.fecha_envio_qr = timezone.now()
                instance.email_qr_enviado = True
                AsistenteVisitaExterna.objects.filter(pk=instance.pk).update(
                    qr_generado=True,
                    fecha_envio_qr=timezone.now(),
                    email_qr_enviado=True
                )
                logger.info(f"QR generado y enviado para asistente externo: {instance.nombre_completo}")
            else:
                logger.warning(f"Error al generar QR para asistente externo: {instance.nombre_completo}")
        
        except Exception as e:
            logger.error(f"Error en signal generar_qr_asistente_externo: {str(e)}")
