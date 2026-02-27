from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(post_migrate)
def criar_usuario_root(sender, **kwargs):
    """
    Cria automaticamente um usuário Root se não existir.
    """

    cpf_root = "12345678901"

    if not User.objects.filter(cpf=cpf_root).exists():
        User.objects.create_superuser(
            cpf=cpf_root,
            first_name="Root",
            last_name="Administrador",
            perfil="DIRECAO",
            password="SuperRoot@123",
            email="root@sistema.com",
        )

        print("✅ Usuário ROOT criado automaticamente.")