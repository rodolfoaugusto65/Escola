# Generated for GerEdu: retain the source timestamp of each completed assessment.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('acompanhamento_avaliacoes', '0003_rename_acompanhame_importa_1c58b4_idx_acompanhame_importa_a44784_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='registroparticipacao',
            name='realizado_em',
            field=models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='Data e hora da realização'),
        ),
    ]
