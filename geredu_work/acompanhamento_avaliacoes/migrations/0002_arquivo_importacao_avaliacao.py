from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("acompanhamento_avaliacoes", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="ArquivoImportacaoAvaliacao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome_original", models.CharField(max_length=255)),
                ("arquivo_original", models.FileField(upload_to="avaliacoes/importacoes/%Y/%m/")),
                ("sha256", models.CharField(db_index=True, max_length=64)),
                ("tamanho_bytes", models.PositiveBigIntegerField(default=0)),
                ("enviado_em", models.DateTimeField(auto_now_add=True)),
                ("importacao", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="arquivos_originais", to="acompanhamento_avaliacoes.importacaoavaliacao")),
            ],
            options={"verbose_name": "Arquivo original de avaliação", "verbose_name_plural": "Arquivos originais de avaliação", "ordering": ["enviado_em"]},
        ),
    ]
