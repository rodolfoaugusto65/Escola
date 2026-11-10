# Generated to join two independent migration branches in busca_ativa.
# This migration intentionally has no schema/data operations: it only tells
# Django that both 0007 branches must be applied before continuing.
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("busca_ativa", "0007_alter_importacaolote_ano_letivo"),
        ("busca_ativa", "0007_comunicado_integracao_historico_upload"),
    ]

    operations = []
