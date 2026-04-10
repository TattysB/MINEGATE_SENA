from django.apps import AppConfig


class GestionVisitasConfig(AppConfig):
    name = 'gestion_visitas'
    
    def ready(self):
        """Registra los signals cuando la app está lista"""
        import gestion_visitas.signals  # noqa
