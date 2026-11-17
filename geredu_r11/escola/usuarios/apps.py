from django.apps import AppConfig
from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "usuarios"

    def ready(self):
        import usuarios.signals
