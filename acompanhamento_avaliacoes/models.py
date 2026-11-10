from django.conf import settings
from django.db import models
from django.utils import timezone

class Avaliacao(models.Model):
    nome = models.CharField(max_length=255, db_index=True)
    ano_letivo = models.PositiveSmallIntegerField(default=timezone.localdate().year, db_index=True)
    etapa = models.CharField(max_length=40, blank=True, db_index=True)
    bimestre = models.CharField(max_length=30, blank=True)
    prova = models.CharField(max_length=180, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-ano_letivo', 'nome']
        constraints = [models.UniqueConstraint(fields=['nome', 'ano_letivo'], name='uniq_avaliacao_nome_ano')]

    def __str__(self):
        return self.nome

class ImportacaoAvaliacao(models.Model):
    STATUS = [('concluida', 'Concluída'), ('parcial', 'Concluída com divergências')]
    avaliacao = models.ForeignKey(Avaliacao, on_delete=models.PROTECT, related_name='importacoes')
    arquivo = models.CharField(max_length=255)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)
    total_registros = models.PositiveIntegerField(default=0)
    realizados = models.PositiveIntegerField(default=0)
    pendentes = models.PositiveIntegerField(default=0)
    nao_vinculados = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS, default='concluida')
    observacoes = models.TextField(blank=True)

    class Meta:
        ordering = ['-criado_em']

    @property
    def percentual(self):
        return round(self.realizados * 100 / self.total_registros, 1) if self.total_registros else 0

    def __str__(self):
        return f'{self.arquivo} - {self.criado_em:%d/%m/%Y %H:%M}'


class ArquivoImportacaoAvaliacao(models.Model):
    importacao = models.ForeignKey(ImportacaoAvaliacao, on_delete=models.CASCADE, related_name="arquivos_originais")
    nome_original = models.CharField(max_length=255)
    arquivo_original = models.FileField(upload_to="avaliacoes/importacoes/%Y/%m/")
    sha256 = models.CharField(max_length=64, db_index=True)
    tamanho_bytes = models.PositiveBigIntegerField(default=0)
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["enviado_em"]
        verbose_name = "Arquivo original de avaliação"
        verbose_name_plural = "Arquivos originais de avaliação"


class RegistroParticipacao(models.Model):
    SITUACOES = [('realizado', 'Realizado'), ('pendente', 'Aguardando participação'), ('ausente', 'Ausente'), ('outro', 'Outra situação')]
    importacao = models.ForeignKey(ImportacaoAvaliacao, on_delete=models.CASCADE, related_name='registros')
    aluno = models.ForeignKey('alunos.Aluno', null=True, blank=True, on_delete=models.SET_NULL, related_name='participacoes_avaliacoes')
    matricula = models.CharField(max_length=30, db_index=True)
    nome_aluno = models.CharField(max_length=180)
    turma = models.CharField(max_length=100, blank=True, db_index=True)
    ano_serie = models.CharField(max_length=50, blank=True, db_index=True)
    prova = models.CharField(max_length=180, blank=True)
    participacao = models.CharField(max_length=80, blank=True)
    situacao = models.CharField(max_length=20, choices=SITUACOES, default='outro', db_index=True)
    entregue_em = models.CharField(max_length=80, blank=True)
    tempo_prova = models.CharField(max_length=50, blank=True)
    dados_originais = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['ano_serie', 'turma', 'nome_aluno']
        indexes = [models.Index(fields=['importacao', 'situacao']), models.Index(fields=['importacao', 'turma'])]

    def __str__(self):
        return f'{self.nome_aluno} - {self.get_situacao_display()}'
