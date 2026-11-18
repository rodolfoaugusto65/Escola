from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models




class PerfilAcesso(models.Model):
    codigo = models.SlugField(max_length=30, unique=True, verbose_name="Código")
    nome = models.CharField(max_length=80, unique=True, verbose_name="Nome do perfil")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    permissoes = models.JSONField(default=list, blank=True, verbose_name="Áreas gerenciadas")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    AREAS = [("usuarios", "Usuários e perfis"), ("alunos", "Alunos"), ("turmas", "Turmas"), ("frequencia", "Frequência"), ("ocorrencias", "Ocorrências"), ("busca_ativa", "Busca Ativa"), ("avaliacoes", "Avaliações"), ("conselho", "Conselho de Classe"), ("atualizacoes", "Atualizações do sistema")]
    class Meta:
        ordering = ("nome",)
        verbose_name = "Perfil de acesso"
        verbose_name_plural = "Perfis de acesso"
    def __str__(self):
        return self.nome


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
        return self.is_authenticated and (self.is_superuser or self.pode_gerenciar_area("usuarios"))

    def pode_gerenciar_area(self, area):
        if not self.is_authenticated:
            return False
        if self.is_superuser:
            return True
        perfil = PerfilAcesso.objects.filter(codigo=self.perfil, ativo=True).first()
        if perfil:
            return area in (perfil.permissoes or [])
        if self.perfil in self.PERFIS_GERENCIAIS:
            return area in {"usuarios", "alunos", "turmas", "frequencia", "ocorrencias", "busca_ativa", "avaliacoes", "conselho", "atualizacoes"}
        return False

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