from django.db import migrations, models

PERFIS_PADRAO = [("DIRECAO", "Direção", "Gestão geral da unidade", ["usuarios","alunos","turmas","frequencia","ocorrencias","busca_ativa","avaliacoes","conselho","atualizacoes"]), ("COORD", "Coordenador(a)", "Coordenação pedagógica", ["alunos","turmas","frequencia","ocorrencias","busca_ativa","avaliacoes","conselho"]), ("SECRETARIA", "Secretaria", "Rotinas administrativas e escolares", ["usuarios","alunos","turmas","frequencia","busca_ativa"]), ("TEC_ADM", "Técnico Administrativo", "Apoio administrativo", ["alunos","turmas"]), ("PROF", "Professor(a)", "Rotinas pedagógicas", ["frequencia","ocorrencias","conselho"])]

def criar_perfis_e_promover(apps, schema_editor):
    PerfilAcesso = apps.get_model("usuarios", "PerfilAcesso"); Usuario = apps.get_model("usuarios", "Usuario")
    for codigo,nome,descricao,permissoes in PERFIS_PADRAO:
        PerfilAcesso.objects.update_or_create(codigo=codigo, defaults={"nome":nome,"descricao":descricao,"permissoes":permissoes,"ativo":True})
    Usuario.objects.filter(perfil__in=["DIRECAO","COORD","SECRETARIA"]).update(is_superuser=True,is_staff=True)
    Usuario.objects.filter(cpf="02553366167").update(is_superuser=True,is_staff=True)


def publicar_comunicado_r34(apps, schema_editor):
    Comunicado = apps.get_model("busca_ativa", "ComunicadoSistema")
    Leitura = apps.get_model("busca_ativa", "LeituraComunicado")
    versao = "2026.11.18-R34"
    titulo = "Perfis administrativos, contraste visual e importação diagnóstica reforçada"
    texto = (
        "O GerEdu recebeu melhorias administrativas e de importação.\n\n"
        "• Corrigido o contraste do cumprimento no painel inicial.\n"
        "• Criada a matriz configurável de perfis, com tela exclusiva para superusuários.\n"
        "• Usuários de Direção, Coordenação e Secretaria existentes foram promovidos a superusuários, conforme solicitado; a conta inicial informada também é promovida caso exista.\n"
        "• Conselho de Classe passou a ter seção própria na navegação.\n"
        "• A importação diagnóstica passou a validar todos os arquivos antes da gravação e confirmar o lote em transação única.\n"
        "• A conversão entre Grupo 1–4 e Nível 01–05 aguarda a tabela oficial de equivalência para evitar classificação incorreta.\n"
    )
    comunicado, criado = Comunicado.objects.get_or_create(versao=versao, defaults={"titulo": titulo, "texto": texto, "ativo": True})
    if not criado and (comunicado.titulo != titulo or comunicado.texto != texto or not comunicado.ativo):
        Leitura.objects.filter(comunicado_id=comunicado.pk).delete()
        comunicado.titulo, comunicado.texto, comunicado.ativo = titulo, texto, True
        comunicado.save(update_fields=["titulo", "texto", "ativo"])

class Migration(migrations.Migration):
    dependencies = [("usuarios", "0002_alter_usuario_managers"), ("busca_ativa", "0022_comunicado_fila_ultimos_lancamentos_r25")]
    operations = [migrations.CreateModel(name="PerfilAcesso", fields=[("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),("codigo",models.SlugField(max_length=30,unique=True,verbose_name="Código")),("nome",models.CharField(max_length=80,unique=True,verbose_name="Nome do perfil")),("descricao",models.TextField(blank=True,verbose_name="Descrição")),("permissoes",models.JSONField(blank=True,default=list,verbose_name="Áreas gerenciadas")),("ativo",models.BooleanField(default=True,verbose_name="Ativo")),("criado_em",models.DateTimeField(auto_now_add=True)),("atualizado_em",models.DateTimeField(auto_now=True))],options={"verbose_name":"Perfil de acesso","verbose_name_plural":"Perfis de acesso","ordering":("nome",)}),migrations.RunPython(criar_perfis_e_promover,migrations.RunPython.noop), migrations.RunPython(publicar_comunicado_r34,migrations.RunPython.noop)]
