import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("alunos", "0006_aluno_historico_aluno_reclassificado_aluno_situacao_and_more"),
        ("turmas", "0002_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="RegistroMapeamento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ano_letivo", models.PositiveSmallIntegerField(db_index=True)),
                ("paede", models.CharField(blank=True, default="", max_length=30)),
                ("situacao", models.CharField(choices=[("Matriculado", "Matriculado"), ("Transferido", "Transferido"), ("Remanejado", "Remanejado"), ("Outro", "Outro")], default="Matriculado", max_length=40)),
                ("professor_lp", models.CharField(blank=True, max_length=150)),
                ("diagnostico_lp", models.CharField(blank=True, choices=[(f"Nível {i:02d}", f"Nível {i:02d}") for i in range(1, 6)], max_length=30)),
                ("lp_b1", models.CharField(blank=True, choices=[(f"Nível {i:02d}", f"Nível {i:02d}") for i in range(1, 6)], max_length=30)),
                ("lp_b2", models.CharField(blank=True, choices=[(f"Nível {i:02d}", f"Nível {i:02d}") for i in range(1, 6)], max_length=30)),
                ("lp_b3", models.CharField(blank=True, choices=[(f"Nível {i:02d}", f"Nível {i:02d}") for i in range(1, 6)], max_length=30)),
                ("lp_b4", models.CharField(blank=True, choices=[(f"Nível {i:02d}", f"Nível {i:02d}") for i in range(1, 6)], max_length=30)),
                ("professor_mt", models.CharField(blank=True, max_length=150)),
                ("diagnostico_mt", models.CharField(blank=True, choices=[(f"Nível {i:02d}", f"Nível {i:02d}") for i in range(1, 6)], max_length=30)),
                ("mt_b1", models.CharField(blank=True, choices=[(f"Nível {i:02d}", f"Nível {i:02d}") for i in range(1, 6)], max_length=30)),
                ("mt_b2", models.CharField(blank=True, choices=[(f"Nível {i:02d}", f"Nível {i:02d}") for i in range(1, 6)], max_length=30)),
                ("mt_b3", models.CharField(blank=True, choices=[(f"Nível {i:02d}", f"Nível {i:02d}") for i in range(1, 6)], max_length=30)),
                ("mt_b4", models.CharField(blank=True, choices=[(f"Nível {i:02d}", f"Nível {i:02d}") for i in range(1, 6)], max_length=30)),
                ("observacoes", models.TextField(blank=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("aluno", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="mapeamentos_aprendizagem", to="alunos.aluno")),
                ("turma", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="mapeamentos_aprendizagem", to="turmas.turma")),
                ("criado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="mapeamentos_criados", to=settings.AUTH_USER_MODEL)),
                ("atualizado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="mapeamentos_atualizados", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["turma__ano_escolar", "turma__nome", "aluno__nome"], "verbose_name": "Mapeamento de aprendizagem", "verbose_name_plural": "Mapeamentos de aprendizagem"},
        ),
        migrations.AddConstraint(model_name="registromapeamento", constraint=models.UniqueConstraint(fields=("aluno", "ano_letivo"), name="uniq_mapeamento_aluno_ano")),
    ]
