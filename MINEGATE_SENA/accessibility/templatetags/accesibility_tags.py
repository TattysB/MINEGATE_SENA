from django import template

register = template.Library()


ESTADOS_VISITA_LEGIBLES = {
    "pendiente": "Pendiente",
    "enviada_coordinacion": "En coordinacion",
    "aprobada_inicial": "Aprobada inicial",
    "documentos_enviados": "Documentos enviados",
    "en_revision_documentos": "En revision de documentos",
    "reprogramacion_solicitada": "Reprogramacion solicitada",
    "confirmada": "Confirmada",
    "rechazada": "Rechazada",
}


@register.inclusion_tag('accessibility/widget.html')
def accessibility_widget():
    """
    Template tag para incluir el widget de accesibilidad en cualquier página.
    
    Uso en templates:
        {% load accessibility_tags %}
        {% accessibility_widget %}
    """
    return {}


@register.filter(name="estado_legible")
def estado_legible(valor):
    estado = str(valor or "").strip()
    if not estado:
        return ""
    if estado in ESTADOS_VISITA_LEGIBLES:
        return ESTADOS_VISITA_LEGIBLES[estado]
    return estado.replace("_", " ").title()