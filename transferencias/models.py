from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Transferencia(models.Model):

    TIPO_CHOICES = [
        ("TURMA", "Troca de turma"),
        ("ESCOLA", "Transferência de escola"),
        ("INTERNA", "Dentro da escola"),
        ("INTERESTADUAL", "Fora do estado"),
    ]

    STATUS_CHOICES = [
        ("ABERTA", "Aberta"),
        ("EM_ANALISE", "Em análise"),
        ("CONCLUIDA", "Concluída"),
        ("ATRASADA", "Atrasada"),
    ]

    aluno = models.CharField(max_length=255)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)

    escola_origem = models.CharField(max_length=255)
    escola_destino = models.CharField(max_length=255, blank=True, null=True)

    data_lancamento = models.DateTimeField(default=timezone.now)
    prazo_limite = models.DateTimeField(blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ABERTA")

    criado_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transferencias_criadas")
    resolvido_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="transferencias_resolvidas")

    data_conclusao = models.DateTimeField(null=True, blank=True)

    observacoes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if not self.prazo_limite:
            self.prazo_limite = self.data_lancamento + timezone.timedelta(days=5)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.aluno} - {self.tipo}"