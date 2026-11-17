from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class CPFBackend(ModelBackend):
    """Permite login via CPF (sem pontuação) ou username."""
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        username = username.replace('.', '').replace('-', '')

        try:
            user = User.objects.get(cpf=username)
        except User.DoesNotExist:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
