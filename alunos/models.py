from django.db import models
from django.conf import settings


class Aluno(models.Model):

    # =========================
    # IDENTIFICAÇÃO ACADÊMICA
    # =========================
    matricula = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Matrícula"
    )

    nome = models.CharField(
        max_length=150,
        verbose_name="Nome do aluno"
    )

    data_nascimento = models.DateField(
        verbose_name="Data de nascimento"
    )

    # =========================
    # MATRÍCULA
    # =========================
    data_matricula = models.DateField(
        verbose_name="Data da matrícula",
        help_text="Data manual, pode ser retroativa"
    )

    # =========================
    # TURMA ATUAL
    # =========================
    turma = models.ForeignKey(
        'turmas.Turma',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alunos',
        verbose_name="Turma atual"
    )

    # =========================
    # IDENTIDADE CONGELADA DA TURMA
    # (NO ATO DA MATRÍCULA)
    # =========================
    turma_ano_letivo = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Ano letivo da matrícula"
    )

    turma_etapa = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        verbose_name="Etapa"
    )

    turma_ano_escolar = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Ano/Série"
    )

    turma_nome = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Nome da turma"
    )

    # =========================
    # CONTATO
    # =========================
    email = models.EmailField(
        blank=True,
        null=True
    )

    nome_pai = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )

    nome_mae = models.CharField(
        max_length=150
    )

    telefone_responsavel = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    nome_telefone_responsavel = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    telefone_responsavel2 = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    nome_telefone_responsavel2 = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    # =========================
    # INDICADORES ADMINISTRATIVOS
    # =========================
    possui_dependencia = models.BooleanField(
        default=False,
        verbose_name="Aluno com dependência"
    )

    aluno_trabalhador = models.BooleanField(
        default=False,
        verbose_name="Aluno trabalhador / estagiário / menor aprendiz"
    )

    # =========================
    # PROGRAMAS / ACOMPANHAMENTO
    # =========================
    aluno_paed = models.BooleanField(
        default=False
    )

    observacao_paed = models.TextField(
        blank=True,
        null=True
    )

    aluno_busca_ativa = models.BooleanField(
        default=False
    )

    numero_ficai = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    recomposicao = models.BooleanField(
        default=False
    )

    # =========================
    # SITUAÇÃO ESCOLAR
    # =========================
    transferido = models.BooleanField(
        default=False
    )

    data_transferencia = models.DateField(
        blank=True,
        null=True
    )

    # =========================
    # AUDITORIA
    # =========================
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alunos_criados'
    )

    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alunos_atualizados'
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    atualizado_em = models.DateTimeField(
        auto_now=True
    )

    # =========================
    # META
    # =========================
    class Meta:
        ordering = ['matricula']
        verbose_name = "Aluno"
        verbose_name_plural = "Alunos"

    def __str__(self):
        return f"{self.matricula} - {self.nome}"
