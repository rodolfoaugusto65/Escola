from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("frequencia", "0002_initial")]
    operations = [
        migrations.AlterField(model_name="frequencia", name="data", field=models.DateField(db_index=True)),
        migrations.AddIndex(model_name="frequenciaaluno", index=models.Index(fields=["frequencia", "presente"], name="freq_frequencia_pres_idx")),
        migrations.AddIndex(model_name="frequenciaaluno", index=models.Index(fields=["aluno", "presente"], name="freq_aluno_pres_idx")),
    ]
