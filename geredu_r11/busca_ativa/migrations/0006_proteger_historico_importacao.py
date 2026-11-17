from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("busca_ativa", "0005_historico_importacoes")]
    operations = [
        migrations.AlterField(
            model_name="historicosituacaoinfrequencia", name="importacao",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="historico_estudantes", to="busca_ativa.importacaoinfrequencia"),
        ),
    ]
