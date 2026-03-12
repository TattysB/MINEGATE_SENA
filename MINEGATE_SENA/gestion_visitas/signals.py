"""
Signals para manejar eventos automáticos de las visitas.
Dispara la generación y envío de QR cuando un asistente es aprobado.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from visitaInterna.models import AsistenteVisitaInterna
from visitaExterna.models import AsistenteVisitaExterna
from gestion_visitas.services import GeneradorQRPDF
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=AsistenteVisitaInterna)
def generar_qr_asistente_interno(sender, instance, created, update_fields, **kwargs):
    """
    Signal que se dispara cuando se cambia el estado de un asistente interno
    a "documentos_aprobados" y la visita ya esta "confirmada".
    """
    # Verificar si es una actualización del estado
    if update_fields and 'estado' not in update_fields:
        return
    
    # Verificar estado aprobado, visita confirmada y que no exista QR previo
    if (instance.estado == 'documentos_aprobados' and 
        instance.visita.estado == 'confirmada' and
        not instance.qr_generado and 
        instance.correo):
        
        try:
            # Generar QR y enviar por correo
            generador = GeneradorQRPDF(
                asistente=instance,
                visita=instance.visita,
                tipo_visita='interna'
            )
            
            if generador.enviar_por_email():
                # Actualizar campos de registro
                instance.qr_generado = True
                instance.fecha_envio_qr = timezone.now()
                instance.email_qr_enviado = True
                # Usar update para evitar recursión
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
    # Verificar si es una actualización del estado
    if update_fields and 'estado' not in update_fields:
        return
    
    # Verificar estado aprobado, visita confirmada y que no exista QR previo
    if (instance.estado == 'documentos_aprobados' and 
        instance.visita.estado == 'confirmada' and
        not instance.qr_generado and 
        instance.correo):
        
        try:
            # Generar QR y enviar por correo
            generador = GeneradorQRPDF(
                asistente=instance,
                visita=instance.visita,
                tipo_visita='externa'
            )
            
            if generador.enviar_por_email():
                # Actualizar campos de registro
                instance.qr_generado = True
                instance.fecha_envio_qr = timezone.now()
                instance.email_qr_enviado = True
                # Usar update para evitar recursión
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
