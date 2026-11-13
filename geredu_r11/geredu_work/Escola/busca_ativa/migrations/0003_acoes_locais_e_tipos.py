from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("busca_ativa", "0002_consultas_comunicados_calendario")]
    operations = [
        migrations.AddField(
            model_name="acaobuscaativa",
            name="responsavel_origem",
            field=models.CharField(blank=True, help_text="Responsável informado no banco local importado, quando diferente do usuário que realizou a integração.", max_length=150),
        ),
        migrations.AlterField(
            model_name="acaobuscaativa",
            name="tipo",
            field=models.CharField(max_length=60, choices=[
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
            ]),
        ),
    ]
