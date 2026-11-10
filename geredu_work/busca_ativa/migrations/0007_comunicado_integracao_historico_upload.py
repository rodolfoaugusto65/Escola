from django.db import migrations


def criar_comunicado(apps, schema_editor):
    ComunicadoSistema = apps.get_model('busca_ativa', 'ComunicadoSistema')
    versao = '2026.11.10.2'
    ComunicadoSistema.objects.get_or_create(
        versao=versao,
        defaults={
            'titulo': 'Melhorias nas importações, histórico e desempenho',
            'ativo': True,
            'texto': (
                'O GerEdu recebeu melhorias importantes:\n\n'
                '• Importação de avaliações: validação mais rigorosa de arquivos, '
                'tratamento de campos vazios e confirmação do armazenamento dos originais.\n'
                '• Busca Ativa: validação de integridade do banco SQLite antes da integração, '
                'compatibilidade com bancos de versões anteriores e preservação do histórico.\n'
                '• Segurança dos dados: os registros anteriores não são apagados; arquivos '
                'incompatíveis ou incompletos são rejeitados antes da integração.\n'
                '• Diagnóstico: falhas passam a registrar detalhes técnicos nos logs do servidor, '
                'sem expor informações internas na mensagem apresentada ao usuário.\n\n'
                'Após a atualização, recomenda-se realizar um backup e testar a importação '
                'com uma cópia dos arquivos antes de iniciar os lançamentos oficiais.'
            ),
        },
    )


class Migration(migrations.Migration):
    dependencies = [('busca_ativa', '0006_proteger_historico_importacao')]
    operations = [migrations.RunPython(criar_comunicado, migrations.RunPython.noop)]
