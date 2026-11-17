import os
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()


@receiver(post_migrate)
def criar_usuario_root(sender, **kwargs):
    """Cria usuário inicial somente quando credenciais forem configuradas no ambiente."""
    cpf_root = os.environ.get("GEREDU_ROOT_CPF", "").strip()
    password_root = os.environ.get("GEREDU_ROOT_PASSWORD", "")
    email_root = os.environ.get("GEREDU_ROOT_EMAIL", "root@sistema.com")
    if not cpf_root or not password_root:
        return
    if not User.objects.filter(cpf=cpf_root).exists():
        User.objects.create_superuser(
            cpf=cpf_root,
            first_name="Administrador",
            last_name="GerEdu",
            perfil="DIRECAO",
            password=password_root,
            email=email_root,
        )
        print("Usuario administrador inicial criado a partir das variaveis de ambiente.")
