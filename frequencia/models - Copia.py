from django.db import models
from alunos.models import Aluno
from turmas.models import Turma


class Frequencia(models.Model):
    """
    Registro diário de frequência por turma
    """
    turma = models.ForeignKey(
        Turma,
        on_delete=models.CASCADE,
        related_name='frequencias',
        verbose_name="Turma"
    )

    data = models.DateField(
        verbose_name="Data da aula"
    )

    observacao = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observações gerais"
    )

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('turma', 'data')
        ordering = ['-data']
        verbose_name = "Frequência"
        verbose_name_plural = "Frequências"

    def __str__(self):
        return f"{self.turma} - {self.data}"


class FrequenciaAluno(models.Model):
    """
    Presença / falta de cada aluno
    """
    frequencia = models.ForeignKey(
        Frequencia,
        on_delete=models.CASCADE,
        related_name='registros'
    )

    aluno = models.ForeignKey(
        Aluno,
        on_delete=models.CASCADE,
        related_name='frequencias'
    )

    presente = models.BooleanField(
        default=True,
        verbose_name="Presente?"
    )

    class Meta:
        unique_together = ('frequencia', 'aluno')
        verbose_name = "Registro de Frequência"
        verbose_name_plural = "Registros de Frequência"

    def __str__(self):
        return f"{self.aluno} - {'Presente' if self.presente else 'Falta'}"
