from django.urls import path
from . import views

app_name = "busca_ativa"

urlpatterns = [
    path("", views.painel, name="painel"),
    path("relatorio-25-mais/", views.relatorio_25mais, name="relatorio_25mais"),
    path("lancamentos-atuais/", views.lancamentos_atuais, name="lancamentos_atuais"),
    path("alertas-operacionais/", views.painel_alertas, name="alertas_operacionais"),
    path("aluno/<int:aluno_id>/", views.ficha_aluno, name="ficha"),
    path("aluno/<int:aluno_id>/acao/", views.registrar_acao, name="acao"),
    path("aluno/<int:aluno_id>/acao/<int:acao_id>/status/", views.atualizar_status_acao, name="status_acao"),
    path("aluno/<int:aluno_id>/acesso/", views.gerenciar_acesso, name="acesso"),
    path("importar/", views.importar_planilha, name="importar"),
    path("importar/processar/<int:job_id>/", views.processar_importacao, name="processar_importacao"),
    path("importacao/<int:importacao_id>/historico/", views.historico_importacao, name="historico_importacao"),
    path("backup/importar/", views.importar_backup_local, name="importar_backup"),
    path("backup/baixar/", views.baixar_backup_busca_ativa, name="baixar_backup"),
    path("relatorios/", views.relatorio_acoes, name="relatorio"),
    path("acompanhamentos/", views.acompanhamentos, name="acompanhamentos"),
    path("compensacao/", views.compensacao_ausencias, name="compensacao"),
    path("relatorios-personalizados/", views.relatorios_personalizados, name="relatorios_personalizados"),
    path("consultas/", views.estatisticas_consultas, name="estatisticas_consultas"),
    path("calendario-letivo/", views.calendario_letivo, name="calendario_letivo"),
    path("consulta/<str:token>/", views.consulta_publica, name="consulta_publica"),
    path("comunicado/<int:comunicado_id>/lido/", views.confirmar_comunicado, name="confirmar_comunicado"),
    path("atualizacao-txt/", views.importar_comunicado_txt, name="atualizacao_txt"),
    path("assistente-natalino/dispensar/", views.dispensar_assistente_natalino, name="dispensar_natalino"),
]
