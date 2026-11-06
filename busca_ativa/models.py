import secrets
from django.conf import settings
from django.db import models
from django.utils import timezone
from alunos.models import Aluno


def ano_letivo_atual():
    return timezone.localdate().year


class ImportacaoInfrequencia(models.Model):
    arquivo = models.CharField(max_length=255)
    ano_letivo = models.PositiveSmallIntegerField(default=ano_letivo_atual)
    importado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    criado_em = models.DateTimeField(auto_now_add=True)
    total_registros = models.PositiveIntegerField(default=0)
    vinculados = models.PositiveIntegerField(default=0)
    nao_vinculados = models.PositiveIntegerField(default=0)
    observacao = models.TextField(blank=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Importação de infrequência"
        verbose_name_plural = "Importações de infrequência"

    def __str__(self):
        return f"{self.arquivo} ({self.criado_em:%d/%m/%Y %H:%M})"


class SituacaoInfrequencia(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name="situacoes_infrequencia")
    codigo_fonte = models.CharField(max_length=30, db_index=True)
    codigo_ged = models.CharField(max_length=30, blank=True)
    ano_letivo = models.PositiveSmallIntegerField()
    importacao = models.ForeignKey(ImportacaoInfrequencia, on_delete=models.SET_NULL, null=True, related_name="situacoes")
    percentual_geral = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    percentual_geral_final = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    percentual_1_bim = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    percentual_2_bim = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    percentual_3_bim = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    percentual_4_bim = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    percentual_relatorio_25 = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    consta_relatorio_25 = models.BooleanField(default=False)
    faltas_geral = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    faltas_final = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    carga_horaria = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    paed_na_fonte = models.CharField(max_length=10, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("aluno", "ano_letivo")
        ordering = ["-percentual_geral_final", "aluno__nome"]
        verbose_name = "Situação de infrequência"
        verbose_name_plural = "Situações de infrequência"

    @property
    def percentual_considerado(self):
        return float(max(self.percentual_geral_final or 0, self.percentual_geral or 0, self.percentual_relatorio_25 or 0))

    @property
    def faixa_alerta(self):
        p = self.percentual_considerado
        return "critico" if p >= 25 else ("atencao" if p >= 10 else "regular")


class AcessoConsultaAluno(models.Model):
    aluno = models.OneToOneField(Aluno, on_delete=models.CASCADE, related_name="acesso_consulta_frequencia")
    token = models.CharField(max_length=64, unique=True, db_index=True, editable=False)
    ativo = models.BooleanField(default=True)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    criado_em = models.DateTimeField(auto_now_add=True)
    ultimo_acesso = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def renovar(self, usuario=None):
        self.token = secrets.token_urlsafe(32)
        self.ativo = True
        self.criado_por = usuario
        self.save(update_fields=["token", "ativo", "criado_por"])
        return self.token


class AcaoBuscaAtiva(models.Model):
    TIPOS = [
        ("Contato telefônico", "Contato telefônico"),
        ("Mensagem ao responsável", "Mensagem ao responsável"),
        ("Convocação do responsável", "Convocação do responsável"),
        ("Reunião com responsável", "Reunião com responsável"),
        ("Atendimento ao estudante", "Atendimento ao estudante"),
        ("Visita domiciliar", "Visita domiciliar"),
        ("Compensação de Ausências", "Compensação de Ausências"),
        ("Afastamento Administrativo", "Afastamento Administrativo"),
        ("Transferência Administrativa", "Transferência Administrativa"),
        ("Encaminhamento ao Conselho Tutelar", "Encaminhamento ao Conselho Tutelar"),
        ("Encaminhamento à rede de proteção", "Encaminhamento à rede de proteção"),
        ("Busca ativa escolar", "Busca ativa escolar"),
        ("Acompanhamento pedagógico", "Acompanhamento pedagógico"),
        ("Plano de recomposição", "Plano de recomposição"),
        ("Justificativa de ausência", "Justificativa de ausência"),
        ("Retorno do estudante", "Retorno do estudante"),
        ("Outra providência", "Outra providência"),
    ]
    STATUS = [
        ("Aberta", "Aberta"),
        ("Em andamento", "Em andamento"),
        ("Aguardando retorno", "Aguardando retorno"),
        ("Concluída", "Concluída"),
        ("Cancelada", "Cancelada"),
    ]
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name="acoes_busca_ativa")
    data = models.DateField(default=timezone.localdate)
    tipo = models.CharField(max_length=60, choices=TIPOS)
    descricao = models.TextField()
    resultado = models.TextField(blank=True)
    proxima_acao = models.CharField(max_length=255, blank=True)
    prazo = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=25, choices=STATUS, default="Em andamento")
    responsavel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="acoes_busca_ativa")
    responsavel_origem = models.CharField(max_length=150, blank=True, help_text="Responsável informado no banco local importado, quando diferente do usuário que realizou a integração.")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-data", "-criado_em"]
        verbose_name = "Ação de Busca Ativa"
        verbose_name_plural = "Ações de Busca Ativa"

    def __str__(self):
        return f"{self.aluno.nome} - {self.tipo} ({self.data:%d/%m/%Y})"

class ConsultaFrequenciaLog(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name="consultas_frequencia")
    consultado_em = models.DateTimeField(auto_now_add=True, db_index=True)
    origem = models.CharField(max_length=20, default="codigo")

    class Meta:
        ordering = ["-consultado_em"]
        verbose_name = "Consulta de frequência"
        verbose_name_plural = "Consultas de frequência"


class ComunicadoSistema(models.Model):
    titulo = models.CharField(max_length=180)
    versao = models.CharField(max_length=30, unique=True)
    texto = models.TextField()
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Comunicado do sistema"
        verbose_name_plural = "Comunicados do sistema"

    def __str__(self):
        return f"{self.titulo} ({self.versao})"


class LeituraComunicado(models.Model):
    comunicado = models.ForeignKey(ComunicadoSistema, on_delete=models.CASCADE, related_name="leituras")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="leituras_comunicados")
    lido_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("comunicado", "usuario")
        verbose_name = "Leitura de comunicado"
        verbose_name_plural = "Leituras de comunicados"


class CalendarioEscolar(models.Model):
    nome = models.CharField(max_length=100, default="Calendário letivo")
    data_fim_letivo = models.DateField()
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Calendário escolar"
        verbose_name_plural = "Calendários escolares"

    def __str__(self):
        return f"{self.nome} — até {self.data_fim_letivo:%d/%m/%Y}"


class DiaNaoLetivo(models.Model):
    calendario = models.ForeignKey(CalendarioEscolar, on_delete=models.CASCADE, related_name="dias_nao_letivos")
    data = models.DateField()
    descricao = models.CharField(max_length=120, blank=True)

    class Meta:
        unique_together = ("calendario", "data")
        ordering = ["data"]
        verbose_name = "Dia não letivo"
        verbose_name_plural = "Dias não letivos"
