from django.db import models
from turmas.models import Turma
from alunos.models import Aluno
from django.conf import settings


class ConselhoClasse(models.Model):
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE)
    bimestre = models.IntegerField()
    ano = models.IntegerField()

    data_conselho = models.DateField(null=True, blank=True)

    STATUS = [
        ("rascunho", "Rascunho"),
        ("finalizado", "Finalizado"),
    ]
    status = models.CharField(max_length=20, choices=STATUS, default="rascunho")

    criado_em = models.DateTimeField(auto_now_add=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    resumo_geral = models.TextField(blank=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.turma} - {self.bimestre}º Bimestre ({self.ano})"


class ConselhoAluno(models.Model):

    # 🔗 RELACIONAMENTOS
    conselho = models.ForeignKey(
        ConselhoClasse,
        on_delete=models.CASCADE,
        related_name="alunos"
    )

    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE)

    # 📊 DADOS AUTOMÁTICOS
    media = models.FloatField(null=True, blank=True)
    frequencia = models.FloatField(null=True, blank=True)
    total_ocorrencias = models.IntegerField(default=0)

    classificacao = models.CharField(max_length=20)
    diagnostico = models.TextField()
    prioridade = models.CharField(max_length=20)
    sugestao = models.TextField()

    # 🧠 DADOS DO CONSELHO (INTERATIVO)

    FALTAS = [
        ("freq", "Frequente"),
        ("faltoso", "Faltoso"),
        ("gravida", "Grávida"),
        ("atestado", "Atestado"),
    ]

    DISCIPLINA = [
        ("ind", "Indisciplinado"),
        ("reg", "Regular"),
    ]

    APRENDIZAGEM = [
        ("ok", "Acompanha"),
        ("nao", "Não faz atividades"),
    ]

    SIM_NAO = [
        ("sim", "Sim"),
        ("nao", "Não"),
    ]

    faltas = models.CharField(max_length=20, choices=FALTAS, blank=True)
    disciplina = models.CharField(max_length=20, choices=DISCIPLINA, blank=True)
    aprendizagem = models.CharField(max_length=20, choices=APRENDIZAGEM, blank=True)

    apa = models.CharField(max_length=3, choices=SIM_NAO, blank=True)
    chamar_familia = models.CharField(max_length=3, choices=SIM_NAO, blank=True)
    reclassificacao = models.CharField(max_length=3, choices=SIM_NAO, blank=True)

    observacao = models.TextField(blank=True)

    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("conselho", "aluno")
        ordering = ["aluno"]

    def __str__(self):
        return f"{self.aluno} - {self.classificacao}"