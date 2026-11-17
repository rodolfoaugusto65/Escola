from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def criar_snapshot_base_existente(apps, schema_editor):
    """Cria uma fotografia inicial dos dados atuais antes de qualquer nova importação."""
    Importacao = apps.get_model("busca_ativa", "ImportacaoInfrequencia")
    Situacao = apps.get_model("busca_ativa", "SituacaoInfrequencia")
    Historico = apps.get_model("busca_ativa", "HistoricoSituacaoInfrequencia")
    Aluno = apps.get_model("alunos", "Aluno")
    from decimal import Decimal

    baseline_por_ano = {}
    baseline_counts = {}
    pendentes = []
    campos = ("codigo_fonte", "codigo_ged", "percentual_geral", "percentual_geral_final",
              "percentual_1_bim", "percentual_2_bim", "percentual_3_bim", "percentual_4_bim",
              "percentual_relatorio_25", "consta_relatorio_25", "faltas_geral", "faltas_final",
              "carga_horaria", "paed_na_fonte")
    for sit in Situacao.objects.all().iterator(chunk_size=500):
        if sit.importacao_id:
            importacao_id = sit.importacao_id
        else:
            if sit.ano_letivo not in baseline_por_ano:
                imp, _ = Importacao.objects.get_or_create(
                    arquivo=f"Base anterior à implantação do histórico - {sit.ano_letivo}",
                    ano_letivo=sit.ano_letivo,
                    observacao="Fotografia inicial dos dados existentes antes da implantação do histórico por importação.",
                    defaults={"total_registros": 0, "vinculados": 0},
                )
                baseline_por_ano[sit.ano_letivo] = imp.id
            importacao_id = baseline_por_ano[sit.ano_letivo]
            baseline_counts[importacao_id] = baseline_counts.get(importacao_id, 0) + 1
        aluno = Aluno.objects.filter(pk=sit.aluno_id).values("matricula").first()
        matricula = str((aluno or {}).get("matricula") or sit.codigo_fonte or sit.aluno_id)
        dados = {}
        for campo in campos:
            valor = getattr(sit, campo)
            dados[campo] = str(valor) if isinstance(valor, Decimal) else valor
        percentual = max(Decimal(str(sit.percentual_geral_final or 0)),
                         Decimal(str(sit.percentual_geral or 0)),
                         Decimal(str(sit.percentual_relatorio_25 or 0)))
        faixa = "critico" if percentual >= 25 else "atencao" if percentual >= 10 else "regular"
        pendentes.append(Historico(
            importacao_id=importacao_id, aluno_id=sit.aluno_id, matricula=matricula[:30],
            ano_letivo=sit.ano_letivo, dados=dados, percentual_considerado=percentual,
            faixa_alerta=faixa, apareceu_novamente=False, mudou_desde_anterior=False,
        ))
        if len(pendentes) >= 500:
            Historico.objects.bulk_create(pendentes, batch_size=500)
            pendentes = []
    if pendentes:
        Historico.objects.bulk_create(pendentes, batch_size=500)
    for importacao_id, quantidade in baseline_counts.items():
        Importacao.objects.filter(pk=importacao_id).update(total_registros=quantidade, vinculados=quantidade)


class Migration(migrations.Migration):
    dependencies = [
        ("alunos", "0006_aluno_historico_aluno_reclassificado_aluno_situacao_and_more"),
        ("busca_ativa", "0004_importacao_lote"),
    ]

    operations = [
        migrations.AddField(
            model_name="importacaoinfrequencia",
            name="arquivo_original",
            field=models.FileField(blank=True, null=True, upload_to="busca_ativa/importacoes/%Y/%m/"),
        ),
        migrations.AddField(
            model_name="importacaoinfrequencia",
            name="sha256",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="importacaoinfrequencia",
            name="estudantes_repetidos",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.CreateModel(
            name="HistoricoSituacaoInfrequencia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("matricula", models.CharField(db_index=True, max_length=30)),
                ("ano_letivo", models.PositiveSmallIntegerField(db_index=True)),
                ("dados", models.JSONField(blank=True, default=dict)),
                ("percentual_considerado", models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ("faixa_alerta", models.CharField(blank=True, max_length=15)),
                ("apareceu_novamente", models.BooleanField(db_index=True, default=False)),
                ("mudou_desde_anterior", models.BooleanField(default=False)),
                ("importado_em", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("aluno", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="historico_infrequencia_importada", to="alunos.aluno")),
                ("importacao", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="historico_estudantes", to="busca_ativa.importacaoinfrequencia")),
            ],
            options={"verbose_name": "Histórico de infrequência importada", "verbose_name_plural": "Históricos de infrequência importada", "ordering": ["-importado_em"]},
        ),
        migrations.AddIndex(
            model_name="historicosituacaoinfrequencia",
            index=models.Index(fields=["aluno", "ano_letivo", "-importado_em"], name="busca_hist_aluno__7d8d10_idx"),
        ),
        migrations.AddIndex(
            model_name="historicosituacaoinfrequencia",
            index=models.Index(fields=["importacao", "apareceu_novamente"], name="busca_hist_import_5d8e25_idx"),
        ),
        migrations.RunPython(criar_snapshot_base_existente, migrations.RunPython.noop),
    ]
