from django.db import migrations


def publicar_nota(apps, schema_editor):
    Comunicado = apps.get_model("busca_ativa", "ComunicadoSistema")
    titulo = "Mapeamento da Aprendizagem disponível no GerEdu"
    texto = (
        "O módulo Mapeamento da Aprendizagem foi integrado ao menu do GerEdu.\\n\\n"
        "1. Acesso para usuários autenticados pelo menu Acompanhamento Pedagógico.\\n"
        "2. Seleção de ano letivo, turma e estudantes vinculados ao cadastro oficial.\\n"
        "3. Registro de PAEDE, situação, professores, diagnóstico e níveis bimestrais de Língua Portuguesa e Matemática.\\n"
        "4. Exportação para a aba Mapeamento da planilha de monitoramento, preservando as demais abas e a estrutura do arquivo.\\n"
        "5. A identificação dos estudantes e das turmas vem dos cadastros do GerEdu; não é necessário redigitar nome, matrícula ou turma."
    )
    Comunicado.objects.get_or_create(
        versao="2026.11.17.27",
        defaults={"titulo": titulo, "texto": texto, "ativo": True},
    )


class Migration(migrations.Migration):
    dependencies = [
        ("busca_ativa", "0008_merge_20261110"),
        ("mapeamento_aprendizagem", "0001_initial"),
    ]
    operations = [migrations.RunPython(publicar_nota, migrations.RunPython.noop)]
