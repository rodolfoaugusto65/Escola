from django.db import models
from django.conf import settings
from alunos.models import Aluno
from turmas.models import Turma


class Ocorrencia(models.Model):

    TIPOS = [
        ('DISC', 'Disciplinar'),
        ('ATRA', 'Atraso'),
        ('UNIF', 'Uniforme'),
        ('OUT', 'Outros'),
    ]

    STATUS = [
        ('ABERTA', 'Aberta'),
        ('RESOLVIDA', 'Resolvida'),
        ('ANDAMENTO', 'Em andamento'),
    ]

    codigo = models.CharField(max_length=20, unique=True, blank=True)

    aluno = models.ForeignKey(
        Aluno,
        on_delete=models.CASCADE,
        related_name="ocorrencias"
    )

    # 👉 Guarda a turma no momento da ocorrência (histórico)
    turma = models.ForeignKey(
        Turma,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    tipo_ocorrencia = models.CharField(max_length=10, choices=TIPOS)

    status = models.CharField(
        max_length=15,
        choices=STATUS,
        default="ABERTA"
    )

    descricao = models.TextField()
    providencias = models.TextField(blank=True)

    data = models.DateField()
    criado_em = models.DateTimeField(auto_now_add=True)

    # FICAI (versão simples)
    ficai = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        verbose_name="Nº FICAI"
    )

    # FICAI controle completo
    ficai_aberta = models.BooleanField(default=False)
    ficai_numero = models.CharField(max_length=30, blank=True, null=True)
    ficai_data = models.DateField(blank=True, null=True)

    def save(self, *args, **kwargs):

        # 🔥 AUTO CÓDIGO
        if not self.codigo:
            ultimo = Ocorrencia.objects.order_by('-id').first()
            numero = (ultimo.id + 1) if ultimo else 1
            self.codigo = f"OCO-{numero:04d}"

        # 🔥 SEMPRE assumir turma atual do aluno
        if self.aluno and hasattr(self.aluno, "turma"):
            self.turma = self.aluno.turma

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.aluno.nome}"
