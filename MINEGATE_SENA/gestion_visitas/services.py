"""
Servicio para generar QR y PDF con información del asistente.
Proporciona funcionalidad para crear documentos profesionales con QR.
"""

from io import BytesIO
from datetime import datetime
import qrcode
from qrcode.image.pure import PyPNGImage
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import cm, mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, black, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)


class GeneradorQRPDF:
    """
    Clase para generar PDFs profesionales con código QR de asistentes.
    Incluye información del asistente, visita y código QR.
    """
    
    # Colores corporativos SENA
    COLOR_PRIMARIO = HexColor('#39A900')      # Verde institucional SENA
    COLOR_SECUNDARIO = HexColor('#007832')    # Verde oscuro de apoyo
    COLOR_ACENTO = HexColor('#8BC53F')        # Verde claro de apoyo
    COLOR_GRIS_CLARO = HexColor('#F5F5F5')
    COLOR_GRIS_OSCURO = HexColor('#333333')
    
    # Tamaño de página
    ANCHO, ALTO = A4
    
    def __init__(self, asistente, visita, tipo_visita='interna'):
        """
        Inicializa el generador.
        
        Args:
            asistente: Instancia de AsistenteVisitaInterna o AsistenteVisitaExterna
            visita: Instancia de VisitaInterna o VisitaExterna
            tipo_visita: 'interna' o 'externa'
        """
        self.asistente = asistente
        self.visita = visita
        self.tipo_visita = tipo_visita
        self.buffer = BytesIO()
    
    def generar_datos_qr(self):
        """
        Genera los datos para el código QR.
        Formato: SENA|visita_id|documento|nombre|tipo
        """
        datos = f"SENA|{self.visita.id}|{self.asistente.numero_documento}|{self.asistente.nombre_completo}|{self.tipo_visita}"
        return datos
    
    def crear_qr_imagen(self):
        """
        Crea una imagen QR en formato PNG.
        Retorna BytesIO con imagen PNG del QR.
        """
        datos = self.generar_datos_qr()
        
        # Generar QR
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        qr.add_data(datos)
        qr.make(fit=True)
        
        # Crear imagen
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Guardar en BytesIO
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return img_buffer
    
    def generar_pdf_profesional(self):
        """
        Genera un PDF simple con el nombre y el código QR.
        Retorna BytesIO con PDF generado.
        """
        # Crear imagen QR
        qr_imagen = self.crear_qr_imagen()
        
        # Crear PDF
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=A4,
            rightMargin=1.0*cm,
            leftMargin=1.0*cm,
            topMargin=1.0*cm,
            bottomMargin=1.0*cm,
        )
        ancho_util = self.ANCHO - 2*cm
        
        # Estilos
        styles = getSampleStyleSheet()

        nombre_texto = (getattr(self.asistente, 'nombre_completo', '') or '').strip()
        if len(nombre_texto) > 34:
            nombre_partes = nombre_texto.split()
            izquierda, derecha = [], []
            largo_izquierda = 0
            objetivo = max(len(nombre_texto) // 2, 1)
            for parte in nombre_partes:
                candidato = largo_izquierda + len(parte) + (1 if izquierda else 0)
                if candidato <= objetivo or not izquierda:
                    izquierda.append(parte)
                    largo_izquierda = candidato
                else:
                    derecha.append(parte)
            nombre_para_pdf = " ".join(izquierda)
            if derecha:
                nombre_para_pdf += "<br/>" + " ".join(derecha)
        else:
            nombre_para_pdf = nombre_texto

        if len(nombre_texto) > 48:
            tamano_nombre = 22
            interlineado_nombre = 26
        elif len(nombre_texto) > 34:
            tamano_nombre = 26
            interlineado_nombre = 30
        else:
            tamano_nombre = 32
            interlineado_nombre = 36
        
        titulo_style = ParagraphStyle(
            'TituloCustom',
            parent=styles['Heading1'],
            fontSize=28,
            textColor=self.COLOR_PRIMARIO,
            spaceAfter=10,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        subtitulo_style = ParagraphStyle(
            'SubtituloCustom',
            parent=styles['Heading2'],
            fontSize=17,
            textColor=self.COLOR_SECUNDARIO,
            spaceAfter=16,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )

        nombre_style = ParagraphStyle(
            'NombreCustom',
            fontSize=tamano_nombre,
            textColor=self.COLOR_GRIS_OSCURO,
            spaceAfter=14,
            leading=interlineado_nombre,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Construcción del documento
        elementos = []
        
        # Encabezado
        elementos.append(Paragraph("SENA", titulo_style))
        elementos.append(Paragraph("CÓDIGO QR DE ACCESO", subtitulo_style))
        elementos.append(Spacer(1, 0.2*cm))
        
        # Línea divisora
        tabla_linea = Table(
            [[' ']],
            colWidths=[ancho_util],
        )
        tabla_linea.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, -1), 3, self.COLOR_PRIMARIO),
        ]))
        elementos.append(tabla_linea)
        elementos.append(Spacer(1, 0.6*cm))

        elementos.append(Paragraph(nombre_para_pdf, nombre_style))
        elementos.append(Spacer(1, 0.6*cm))

        qr_imagen.seek(0)

        # Tabla con QR
        tabla_qr = Table(
            [[RLImage(qr_imagen, width=13.5*cm, height=13.5*cm)]],
            colWidths=[ancho_util],
        )
        tabla_qr.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('BOX', (0, 0), (-1, -1), 2, self.COLOR_ACENTO),
        ]))
        elementos.append(tabla_qr)
        elementos.append(Spacer(1, 0.45*cm))
        
        # Información adicional
        elementos.append(Paragraph(
            "Presenta este código al ingreso.",
            ParagraphStyle(
                'InfoCustom',
                fontSize=14,
                textColor=self.COLOR_SECUNDARIO,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )
        ))
        
        # Pie de página
        elementos.append(Spacer(1, 0.5*cm))
        elementos.append(Paragraph(
            f"Generado: {datetime.now().strftime('%d/%m/%Y a las %H:%M')}",
            ParagraphStyle(
                'PieCustom',
                fontSize=8,
                textColor=HexColor('#999999'),
                alignment=TA_CENTER,
                fontName='Helvetica'
            )
        ))
        
        # Construir PDF
        doc.build(elementos)
        pdf_buffer.seek(0)
        
        return pdf_buffer
    
    def enviar_por_email(self, correo_remitente=None):
        """
        Genera el PDF y lo envía por correo al asistente.
        
        Args:
            correo_remitente: Dirección de email desde la cual enviar (opcional)
        
        Returns:
            bool: True si se envió exitosamente, False en caso contrario
        """
        try:
            # Generar PDF
            pdf_buffer = self.generar_pdf_profesional()
            
            # Configurar email
            if not correo_remitente:
                correo_remitente = settings.DEFAULT_FROM_EMAIL
            
            asunto = f"Código QR - Visita {self.tipo_visita.capitalize()} SENA"
            
            # Verbo para la visita
            if self.tipo_visita == 'interna':
                programa = self.visita.nombre_programa
                descripcion_visita = f"la ficha {self.visita.numero_ficha} del programa {programa}"
            else:
                descripcion_visita = f"la institución {self.visita.nombre}"
            
            mensaje_texto = f"""
Estimado(a) {self.asistente.nombre_completo},

Te adjuntamos tu código QR de acceso para la visita a {descripcion_visita}.

Por favor, lleva este documento el día de la visita. El código QR será escaneado en la entrada 
para registrar tu asistencia.

Información de la Visita:
- Fecha: {self.visita.fecha_visita.strftime('%d/%m/%Y') if self.visita.fecha_visita else 'Por confirmar'}
- Hora: {self.visita.hora_inicio.strftime('%H:%M') if self.visita.hora_inicio else 'Por confirmar'}

Si tienes alguna pregunta o inconveniente, por favor contacta a coordinación.

Saludos,
Sistema de Gestión de Visitas SENA
            """
            
            # Crear mensaje
            email = EmailMessage(
                subject=asunto,
                body=mensaje_texto,
                from_email=correo_remitente,
                to=[self.asistente.correo],
            )
            
            # Adjuntar PDF
            email.attach(
                f"QR_Visita_{self.asistente.numero_documento}.pdf",
                pdf_buffer.getvalue(),
                "application/pdf"
            )
            
            # Enviar
            resultado = email.send()
            
            if resultado:
                logger.info(f"QR PDF enviado exitosamente a {self.asistente.correo}")
                return True
            else:
                logger.error(f"Error enviando QR PDF a {self.asistente.correo}")
                return False
                
        except Exception as e:
            logger.error(f"Error en enviar_por_email: {str(e)}")
            return False
