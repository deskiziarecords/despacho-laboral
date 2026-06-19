from django.apps import AppConfig


class ExpedientesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'expedientes'
    verbose_name = 'Expedientes'

    def ready(self):
        import expedientes.signals  # noqa
