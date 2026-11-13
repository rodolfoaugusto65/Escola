from django.db import models
from django.conf import settings
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

import os
import uuid


# =========================
# FUNÇÕES DE UPLOAD
# =========================

def foto_aluno_path(instance, filename):
    ext = filename.split('.')[-1].lower()
    return f"alunos/fotos/{instance.matricula}.{ext}"


def caminho_laudo(instance, filename):
    extensao = os.path.splitext(filename)[1]

    aluno = instance.aluno.matricula if instance.aluno else "aluno"

    nome_unico = (
        f"Laudo-{aluno}-{uuid.uuid4().hex}{extensao}"
    )

    return f"alunos/laudos/{nome_unico}"


# =========================
# MODELO ALUNO
# =========================

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

    turma_ano_letivo = models.IntegerField(
        null=True,
        blank=True
    )

    turma_etapa = models.CharField(
        max_length=30,
        null=True,
        blank=True
    )

    turma_ano_escolar = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    turma_nome = models.CharField(
        max_length=20,
        null=True,
        blank=True
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
    # INDICADORES
    # =========================
    possui_dependencia = models.BooleanField(
        default=False
    )

    aluno_trabalhador = models.BooleanField(
        default=False
    )

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
    situacao = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Situação Escolar"
    )

    transferido = models.BooleanField(
        default=False,
        verbose_name="Aluno transferido"
    )

    data_transferencia = models.DateField(
        blank=True,
        null=True,
        verbose_name="Data da transferência"
    )

    reclassificado = models.BooleanField(
        default=False,
        verbose_name="Aluno reclassificado"
    )

    historico = models.TextField(
        blank=True,
        null=True,
        verbose_name="Histórico do aluno",
        help_text=(
            "Registro de movimentações, "
            "transferências e observações."
        )
    )

    # =========================
    # FOTO
    # =========================
    foto = models.ImageField(
        upload_to=foto_aluno_path,
        blank=True,
        null=True,
        verbose_name="Foto do aluno"
    )

    foto_thumb = models.ImageField(
        upload_to="alunos/thumbs/",
        blank=True,
        null=True,
        editable=False
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

    class Meta:
        ordering = ['matricula']
        verbose_name = "Aluno"
        verbose_name_plural = "Alunos"

    def __str__(self):
        return f"{self.matricula} - {self.nome}"

    @property
    def foto_url(self):
        if self.foto:
            return self.foto.url

        return (
            f"{settings.STATIC_URL}"
            f"{settings.FOTO_PADRAO_ALUNO}"
        )

    @property
    def foto_thumb_url(self):
        if self.foto_thumb:
            return self.foto_thumb.url

        if self.foto:
            return self.foto.url

        return (
            f"{settings.STATIC_URL}"
            f"{settings.FOTO_PADRAO_ALUNO}"
        )

    @property
    def eh_lider_de_turma(self):
        if not self.turma:
            return False

        return (
            getattr(
                self.turma,
                "aluno_lider_id",
                None
            ) == self.id
        )

    def save(self, *args, **kwargs):

        if self.pk:
            try:
                antigo = Aluno.objects.get(pk=self.pk)

                if (
                    antigo.foto
                    and antigo.foto != self.foto
                ):
                    default_storage.delete(
                        antigo.foto.name
                    )

                if (
                    antigo.foto_thumb
                    and antigo.foto_thumb != self.foto_thumb
                ):
                    default_storage.delete(
                        antigo.foto_thumb.name
                    )

            except Aluno.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        if self.foto and not self.foto_thumb:
            try:
                img = Image.open(self.foto)
                img = img.convert("RGB")
                img.thumbnail((128, 128))

                thumb_io = BytesIO()

                img.save(
                    thumb_io,
                    format="JPEG",
                    quality=70,
                    optimize=True
                )

                nome_thumb = (
                    self.foto.name.split("/")[-1]
                )

                self.foto_thumb.save(
                    nome_thumb,
                    ContentFile(
                        thumb_io.getvalue()
                    ),
                    save=False
                )

                super().save(
                    update_fields=["foto_thumb"]
                )

            except Exception:
                pass

    def delete(self, *args, **kwargs):
        if self.foto:
            default_storage.delete(
                self.foto.name
            )

        if self.foto_thumb:
            default_storage.delete(
                self.foto_thumb.name
            )

        super().delete(*args, **kwargs)


# =========================
# DOCUMENTOS / LAUDOS
# =========================

class DocumentoAluno(models.Model):

    aluno = models.ForeignKey(
        Aluno,
        on_delete=models.CASCADE,
        related_name="documentos"
    )

    arquivo = models.FileField(
        upload_to=caminho_laudo,
        verbose_name="Arquivo do laudo"
    )

    tipo_laudo = models.CharField(
        max_length=150,
        verbose_name="Tipo de laudo"
    )

    data_laudo = models.DateField(
        verbose_name="Data do laudo",
        null=True,
        blank=True
    )

    descricao = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observação do laudo"
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Documento do aluno"
        verbose_name_plural = "Documentos dos alunos"
        ordering = ['-data_laudo']

    def __str__(self):
        return (
            f"{self.aluno.nome} - "
            f"{self.tipo_laudo}"
        )


# =========================
# HISTÓRICO DE MOVIMENTAÇÃO
# =========================

class HistoricoMovimentacao(models.Model):

    TIPO_CHOICES = (
        ("MATRICULA", "Matrícula"),
        ("TRANSFERENCIA_TURMA", "Transferência de Turma"),
        ("TRANSFERENCIA_ESCOLA", "Transferência de Escola"),
        ("RECLASSIFICACAO", "Reclassificação"),
        ("REMANEJAMENTO", "Remanejamento"),
        ("CANCELAMENTO", "Cancelamento"),
    )

    aluno = models.ForeignKey(
        Aluno,
        on_delete=models.CASCADE,
        related_name="movimentacoes"
    )

    turma_origem = models.ForeignKey(
        'turmas.Turma',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )

    turma_destino = models.ForeignKey(
        'turmas.Turma',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )

    tipo = models.CharField(
        max_length=30,
        choices=TIPO_CHOICES
    )

    data = models.DateField()

    observacao = models.TextField(
        blank=True,
        null=True
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-data']
        verbose_name = "Movimentação"
        verbose_name_plural = "Movimentações"

    def __str__(self):
        return (
            f"{self.aluno.nome} - "
            f"{self.get_tipo_display()} - "
            f"{self.data:%d/%m/%Y}"
        )