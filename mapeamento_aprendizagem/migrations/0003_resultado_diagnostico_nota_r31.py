from django.db import migrations, models
import django.db.models.deletion


def publicar_nota_r30(apps, schema_editor):
    Comunicado = apps.get_model("busca_ativa", "ComunicadoSistema")
    Leitura = apps.get_model("busca_ativa", "LeituraComunicado")
    versao = "2026.11.17-R31"
    titulo = "Painel inicial ampliado e importação de avaliações diagnósticas"
    texto = (
        "O GerEdu recebeu melhorias no painel inicial e no Mapeamento da Aprendizagem.\n\n"
        "• O início agora apresenta indicadores de estudantes, turmas, PAEDE, Busca Ativa, ocorrências, mapeamentos e resultados diagnósticos.\n"
        "• Foram adicionados atalhos para as principais rotinas do sistema.\n"
        "• O Mapeamento da Aprendizagem agora permite importar planilhas .xlsx de avaliação diagnóstica de Língua Portuguesa e Matemática.\n"
        "• A importação considera os registros da EE RODOLFO AUGUSTO TRECHAUD CURVO e utiliza CD_ALUNO_INSTITUCIONAL para localizar a matrícula no GerEdu.\n"
        "• Os grupos 1 a 4 são armazenados como classificação original da planilha, sem conversão automática para os níveis pedagógicos.\n"
        "• Reimportações atualizam o resultado do mesmo estudante, ano e disciplina, evitando duplicidades.\n"
        "• Esta atualização também publica o comunicado no sistema durante a aplicação das migrações."
    )
    comunicado, criado = Comunicado.objects.get_or_create(
        versao=versao,
        defaults={"titulo": titulo, "texto": texto, "ativo": True},
    )
    if not criado and (comunicado.titulo != titulo or comunicado.texto != texto or not comunicado.ativo):
        Leitura.objects.filter(comunicado_id=comunicado.pk).delete()
        comunicado.titulo, comunicado.texto, comunicado.ativo = titulo, texto, True
        comunicado.save(update_fields=["titulo", "texto", "ativo"])


class Migration(migrations.Migration):
    dependencies = [
        ("mapeamento_aprendizagem", "0002_publicar_nota_r27"),
        ("busca_ativa", "0022_comunicado_fila_ultimos_lancamentos_r25"),
    ]
    operations = [
        migrations.CreateModel(
            name="ResultadoDiagnostico",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ano_letivo", models.PositiveSmallIntegerField(db_index=True)),
                ("disciplina", models.CharField(choices=[("LP", "Língua Portuguesa"), ("MT", "Matemática")], db_index=True, max_length=2)),
                ("etapa", models.CharField(blank=True, max_length=20)),
                ("grupo", models.CharField(max_length=20)),
                ("codigo_aluno", models.CharField(blank=True, max_length=40)),
                ("codigo_institucional", models.CharField(blank=True, db_index=True, max_length=40)),
                ("escola", models.CharField(blank=True, max_length=180)),
                ("modalidade", models.CharField(blank=True, max_length=80)),
                ("arquivo_origem", models.CharField(blank=True, max_length=255)),
                ("importado_em", models.DateTimeField(auto_now=True)),
                ("aluno", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="resultados_diagnostico", to="alunos.aluno")),
                ("turma", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="resultados_diagnostico", to="turmas.turma")),
            ],
            options={"ordering": ["disciplina", "aluno__nome"], "verbose_name": "Resultado de diagnóstico", "verbose_name_plural": "Resultados de diagnóstico"},
        ),
        migrations.AddConstraint(
            model_name="resultadodiagnostico",
            constraint=models.UniqueConstraint(fields=("aluno", "ano_letivo", "disciplina"), name="uniq_resultado_diag_aluno_ano_disc"),
        ),
        migrations.RunPython(publicar_nota_r30, migrations.RunPython.noop),
    ]
