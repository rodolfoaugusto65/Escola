from django.conf import settings
from django.db import models


class RegistroMapeamento(models.Model):
    NIVEIS = [(f"Nível {i:02d}", f"Nível {i:02d}") for i in range(1, 6)]
    SITUACOES = [
        ("Matriculado", "Matriculado"),
        ("Transferido", "Transferido"),
        ("Remanejado", "Remanejado"),
        ("Outro", "Outro"),
    ]
    aluno = models.ForeignKey("alunos.Aluno", on_delete=models.PROTECT, related_name="mapeamentos_aprendizagem")
    turma = models.ForeignKey("turmas.Turma", on_delete=models.PROTECT, related_name="mapeamentos_aprendizagem")
    ano_letivo = models.PositiveSmallIntegerField(db_index=True)
    paede = models.CharField(max_length=30, blank=True, default="")
    situacao = models.CharField(max_length=40, choices=SITUACOES, default="Matriculado")

    professor_lp = models.CharField(max_length=150, blank=True)
    diagnostico_lp = models.CharField(max_length=30, blank=True, choices=NIVEIS)
    lp_b1 = models.CharField(max_length=30, blank=True, choices=NIVEIS)
    lp_b2 = models.CharField(max_length=30, blank=True, choices=NIVEIS)
    lp_b3 = models.CharField(max_length=30, blank=True, choices=NIVEIS)
    lp_b4 = models.CharField(max_length=30, blank=True, choices=NIVEIS)

    professor_mt = models.CharField(max_length=150, blank=True)
    diagnostico_mt = models.CharField(max_length=30, blank=True, choices=NIVEIS)
    mt_b1 = models.CharField(max_length=30, blank=True, choices=NIVEIS)
    mt_b2 = models.CharField(max_length=30, blank=True, choices=NIVEIS)
    mt_b3 = models.CharField(max_length=30, blank=True, choices=NIVEIS)
    mt_b4 = models.CharField(max_length=30, blank=True, choices=NIVEIS)

    observacoes = models.TextField(blank=True)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="mapeamentos_criados")
    atualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="mapeamentos_atualizados")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["turma__ano_escolar", "turma__nome", "aluno__nome"]
        constraints = [
            models.UniqueConstraint(fields=["aluno", "ano_letivo"], name="uniq_mapeamento_aluno_ano")
        ]
        verbose_name = "Mapeamento de aprendizagem"
        verbose_name_plural = "Mapeamentos de aprendizagem"

    def __str__(self):
        return f"{self.aluno.nome} · {self.ano_letivo}"
