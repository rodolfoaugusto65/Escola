# Generated for the GerEdu Busca Ativa integration.
import django.db.models.deletion
import django.utils.timezone
import busca_ativa.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("alunos", "0006_aluno_historico_aluno_reclassificado_aluno_situacao_and_more"),
    ]
    operations = [
        migrations.CreateModel(
            name="ImportacaoInfrequencia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("arquivo", models.CharField(max_length=255)),
                ("ano_letivo", models.PositiveSmallIntegerField(default=busca_ativa.models.ano_letivo_atual)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("total_registros", models.PositiveIntegerField(default=0)),
                ("vinculados", models.PositiveIntegerField(default=0)),
                ("nao_vinculados", models.PositiveIntegerField(default=0)),
                ("observacao", models.TextField(blank=True)),
                ("importado_por", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Importação de infrequência", "verbose_name_plural": "Importações de infrequência", "ordering": ["-criado_em"]},
        ),
        migrations.CreateModel(
            name="AcessoConsultaAluno",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token", models.CharField(db_index=True, editable=False, max_length=64, unique=True)),
                ("ativo", models.BooleanField(default=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("ultimo_acesso", models.DateTimeField(blank=True, null=True)),
                ("aluno", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="acesso_consulta_frequencia", to="alunos.aluno")),
                ("criado_por", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="SituacaoInfrequencia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo_fonte", models.CharField(db_index=True, max_length=30)),
                ("codigo_ged", models.CharField(blank=True, max_length=30)),
                ("ano_letivo", models.PositiveSmallIntegerField()),
                ("percentual_geral", models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ("percentual_geral_final", models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ("percentual_1_bim", models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ("percentual_2_bim", models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ("percentual_3_bim", models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ("percentual_4_bim", models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ("faltas_geral", models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ("faltas_final", models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ("carga_horaria", models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ("paed_na_fonte", models.CharField(blank=True, max_length=10)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("aluno", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="situacoes_infrequencia", to="alunos.aluno")),
                ("importacao", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="situacoes", to="busca_ativa.importacaoinfrequencia")),
            ],
            options={"verbose_name": "Situação de infrequência", "verbose_name_plural": "Situações de infrequência", "ordering": ["-percentual_geral_final", "aluno__nome"], "unique_together": [("aluno", "ano_letivo")]},
        ),
        migrations.CreateModel(
            name="AcaoBuscaAtiva",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("data", models.DateField(default=django.utils.timezone.localdate)),
                ("tipo", models.CharField(choices=[("Contato telefônico", "Contato telefônico"), ("Mensagem ao responsável", "Mensagem ao responsável"), ("Reunião com responsável", "Reunião com responsável"), ("Atendimento ao estudante", "Atendimento ao estudante"), ("Visita domiciliar", "Visita domiciliar"), ("Encaminhamento à rede de proteção", "Encaminhamento à rede de proteção"), ("Compensação de ausências", "Compensação de ausências"), ("Outra providência", "Outra providência")], max_length=60)),
                ("descricao", models.TextField()),
                ("resultado", models.TextField(blank=True)),
                ("proxima_acao", models.CharField(blank=True, max_length=255)),
                ("prazo", models.DateField(blank=True, null=True)),
                ("status", models.CharField(choices=[("Aberta", "Aberta"), ("Em andamento", "Em andamento"), ("Aguardando retorno", "Aguardando retorno"), ("Concluída", "Concluída"), ("Cancelada", "Cancelada")], default="Em andamento", max_length=25)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("aluno", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="acoes_busca_ativa", to="alunos.aluno")),
                ("responsavel", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="acoes_busca_ativa", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Ação de Busca Ativa", "verbose_name_plural": "Ações de Busca Ativa", "ordering": ["-data", "-criado_em"]},
        ),
    ]
