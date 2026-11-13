from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("busca_ativa", "0003_acoes_locais_e_tipos"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ImportacaoLote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("arquivo", models.CharField(max_length=255)),
                ("tipo", models.CharField(choices=[("geral", "Base geral"), ("25mais", "Relatório 25%+")], max_length=20)),
                ("ano_letivo", models.PositiveSmallIntegerField(default=2026)),
                ("dados", models.JSONField(blank=True, default=list)),
                ("total", models.PositiveIntegerField(default=0)),
                ("processados", models.PositiveIntegerField(default=0)),
                ("vinculados", models.PositiveIntegerField(default=0)),
                ("nao_vinculados", models.PositiveIntegerField(default=0)),
                ("pendentes", models.JSONField(blank=True, default=list)),
                ("status", models.CharField(choices=[("pendente", "Pendente"), ("processando", "Processando"), ("concluida", "Concluída"), ("erro", "Erro")], default="pendente", max_length=20)),
                ("erro", models.TextField(blank=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("importacao", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="lotes", to="busca_ativa.importacaoinfrequencia")),
                ("usuario", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Processamento de importação", "verbose_name_plural": "Processamentos de importação", "ordering": ["-criado_em"]},
        ),
    ]
