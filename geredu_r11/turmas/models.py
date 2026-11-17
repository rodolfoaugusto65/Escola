from django.db import models
from django.conf import settings


class Turma(models.Model):
    ETAPAS = [
        ('EF', 'Ensino Fundamental'),
        ('EM', 'Ensino Médio'),
        ('EJA', 'EJA'),
        ('TEC', 'Ensino Técnico'),
    ]

    TURNOS = [
        ('MAT', 'Matutino'),
        ('VES', 'Vespertino'),
        ('NOT', 'Noturno'),
        ('INT', 'Integral'),
    ]

    ano_letivo = models.IntegerField()
    etapa = models.CharField(max_length=10, choices=ETAPAS)

    # ✅ novos campos com defaults seguros
    ano_escolar = models.CharField(
        max_length=20,
        verbose_name="Ano Escolar",
        help_text="Ex: 6º Ano, 3º Ano EM",
        default="99º"
    )

    nome = models.CharField(
        max_length=20,
        verbose_name="Nome da Turma",
        help_text="Ex: A, B, C, ALFA, BETA",
        default="AA"
    )

    turno = models.CharField(
        max_length=10,
        choices=TURNOS,
        verbose_name="Turno",
        default="MAT"
    )

    max_alunos = models.PositiveIntegerField(
        default=35,
        verbose_name="Máximo de Alunos"
    )

    professor_conselheiro = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='turmas_conselheiro'
    )

    aluno_lider = models.ForeignKey(
        'alunos.Aluno',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lider_de_turma'
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-ano_letivo', 'etapa']

    def __str__(self):
        return f"{self.etapa} - {self.ano_escolar} {self.nome} ({self.get_turno_display()}) - {self.ano_letivo}"
