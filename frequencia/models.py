from django.db import models
from alunos.models import Aluno
from turmas.models import Turma


class Frequencia(models.Model):
    turma = models.ForeignKey(
        Turma,
        on_delete=models.CASCADE,
        related_name='frequencias'
    )
    data = models.DateField()

    class Meta:
        unique_together = ('turma', 'data')
        ordering = ['data']

    def __str__(self):
        return f'{self.turma} - {self.data}'


class FrequenciaAluno(models.Model):
    frequencia = models.ForeignKey(
        Frequencia,
        on_delete=models.CASCADE,
        related_name='registros'
    )
    aluno = models.ForeignKey(
        Aluno,
        on_delete=models.CASCADE
    )
    presente = models.BooleanField(default=True)

    class Meta:
        unique_together = ('frequencia', 'aluno')

    def __str__(self):
        return f'{self.aluno} - {"P" if self.presente else "F"}'
