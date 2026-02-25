from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


# ======================================================
# 🔐 MANAGER CUSTOMIZADO
# ======================================================

class UsuarioManager(BaseUserManager):

    def create_user(self, cpf, first_name, last_name, perfil, password=None, **extra_fields):
        if not cpf:
            raise ValueError("O CPF é obrigatório.")

        cpf = ''.join(filter(str.isdigit, cpf))

        user = self.model(
            cpf=cpf,
            username=cpf,
            first_name=first_name,
            last_name=last_name,
            perfil=perfil,
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, cpf, first_name, last_name, perfil, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser precisa ter is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser precisa ter is_superuser=True.")

        return self.create_user(
            cpf,
            first_name,
            last_name,
            perfil,
            password,
            **extra_fields
        )


# ======================================================
# 👤 MODELO USUÁRIO
# ======================================================

class Usuario(AbstractUser):

    objects = UsuarioManager()

    PERFIS = [
        ('DIRECAO', 'Direção'),
        ('COORD', 'Coordenador(a)'),
        ('SECRETARIA', 'Secretária(o)'),
        ('TEC_ADM', 'Técnico Administrativo'),
        ('PROF', 'Professor(a)'),
    ]

    PERFIS_GERENCIAIS = ('DIRECAO', 'COORD', 'SECRETARIA')

    perfil = models.CharField(
        max_length=20,
        choices=PERFIS,
        default='PROF',
        verbose_name="Perfil do Usuário"
    )

    perfil_gerencial = models.BooleanField(
        default=False,
        editable=False,
        verbose_name="Usuário com perfil gerencial"
    )

    cpf = models.CharField(
        max_length=11,
        unique=True,
        verbose_name="CPF"
    )

    telefone = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        verbose_name="Telefone"
    )

    endereco = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Endereço"
    )

    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'cpf'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'perfil']

    # ======================================================
    # 🔐 PERMISSÃO CENTRALIZADA
    # ======================================================

    @property
    def pode_gerenciar_usuarios(self):
        return self.is_authenticated and self.perfil_gerencial

    # ======================================================
    # 🔄 SAVE AUTOMÁTICO INTELIGENTE
    # ======================================================

    def save(self, *args, **kwargs):

        self.perfil_gerencial = self.perfil in self.PERFIS_GERENCIAIS

        if self.cpf:
            self.cpf = ''.join(filter(str.isdigit, self.cpf))

        self.username = self.cpf

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_full_name()} - {self.get_perfil_display()}"

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"