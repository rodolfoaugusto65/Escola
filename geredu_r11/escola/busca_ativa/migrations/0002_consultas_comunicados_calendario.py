# Generated for GerEdu consultation metrics, system notices and school calendar.
import datetime
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def seed_defaults(apps, schema_editor):
    Comunicado = apps.get_model('busca_ativa', 'ComunicadoSistema')
    Calendario = apps.get_model('busca_ativa', 'CalendarioEscolar')
    Comunicado.objects.get_or_create(
        versao='2026.11.1',
        defaults={
            'titulo': 'Novidades no GerEdu — Consulta de frequência e Busca Ativa',
            'texto': (
                'O GerEdu recebeu melhorias para apoiar o acompanhamento da frequência escolar.\n\n'
                '1. Consulta do estudante: agora existe uma página pública para consultar a situação de frequência pelo código escolar.\n'
                '2. Privacidade: as estatísticas de consultas ficam restritas aos usuários gerenciais.\n'
                '3. Busca Ativa: as providências, responsáveis, prazos e histórico permanecem registrados no sistema.\n'
                '4. Importação: a base geral deve ser enviada em Excel e o relatório complementar de 25% ou mais em CSV.\n'
                '5. Fontes de dados: os percentuais dos relatórios são mantidos separadamente dos lançamentos diários de frequência.\n\n'
                'Confira os dados importados e as correspondências de matrícula antes de iniciar qualquer providência. '
                'Em caso de divergência, valide a informação na fonte oficial.'
            ),
            'ativo': True,
        },
    )
    Calendario.objects.get_or_create(
        nome='Calendário escolar 2026',
        defaults={'data_fim_letivo': datetime.date(2026, 12, 18), 'ativo': True},
    )


class Migration(migrations.Migration):
    dependencies = [
        ('busca_ativa', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.AddField(
            model_name='situacaoinfrequencia', name='percentual_relatorio_25',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=6),
        ),
        migrations.AddField(
            model_name='situacaoinfrequencia', name='consta_relatorio_25',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='ConsultaFrequenciaLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('consultado_em', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('origem', models.CharField(default='codigo', max_length=20)),
                ('aluno', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='consultas_frequencia', to='alunos.aluno')),
            ],
            options={'verbose_name': 'Consulta de frequência', 'verbose_name_plural': 'Consultas de frequência', 'ordering': ['-consultado_em']},
        ),
        migrations.CreateModel(
            name='ComunicadoSistema',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=180)),
                ('versao', models.CharField(max_length=30, unique=True)),
                ('texto', models.TextField()),
                ('ativo', models.BooleanField(default=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
            ],
            options={'verbose_name': 'Comunicado do sistema', 'verbose_name_plural': 'Comunicados do sistema', 'ordering': ['-criado_em']},
        ),
        migrations.CreateModel(
            name='CalendarioEscolar',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(default='Calendário letivo', max_length=100)),
                ('data_fim_letivo', models.DateField()),
                ('ativo', models.BooleanField(default=True)),
            ],
            options={'verbose_name': 'Calendário escolar', 'verbose_name_plural': 'Calendários escolares'},
        ),
        migrations.CreateModel(
            name='LeituraComunicado',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lido_em', models.DateTimeField(auto_now_add=True)),
                ('comunicado', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='leituras', to='busca_ativa.comunicadosistema')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='leituras_comunicados', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Leitura de comunicado', 'verbose_name_plural': 'Leituras de comunicados', 'unique_together': {('comunicado', 'usuario')}},
        ),
        migrations.CreateModel(
            name='DiaNaoLetivo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.DateField()),
                ('descricao', models.CharField(blank=True, max_length=120)),
                ('calendario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dias_nao_letivos', to='busca_ativa.calendarioescolar')),
            ],
            options={'verbose_name': 'Dia não letivo', 'verbose_name_plural': 'Dias não letivos', 'ordering': ['data'], 'unique_together': {('calendario', 'data')}},
        ),
        migrations.RunPython(seed_defaults, migrations.RunPython.noop),
    ]
