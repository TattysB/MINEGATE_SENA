from django import template

register = template.Library()


@register.inclusion_tag('accessibility/widget.html')
def accessibility_widget():
    """
    Template tag para incluir el widget de accesibilidad en cualquier página.
    
    Uso en templates:
        {% load accessibility_tags %}
        {% accessibility_widget %}
    """
    return {}