from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_alunos, name='lista_alunos'),
    path('novo/', views.cadastrar_aluno, name='cadastrar_aluno'),
    path('<int:id>/editar/', views.editar_aluno, name='editar_aluno'),
    path('relatorio/', views.relatorio_alunos, name='relatorio_alunos'),
     # NOVA URL: relatório completo por aluno
    path('relatorio/<int:aluno_id>/', views.relatorio_aluno_completo, name='relatorio_aluno_completo'),
    path("excluir/<int:pk>/", views.excluir_aluno, name="excluir_aluno"),
    path("aluno/<int:aluno_id>/laudos/", views.documentos_aluno, name="documentos_aluno"),
    path(
    "laudos/<int:doc_id>/editar/",
    views.editar_documento,
    name="editar_documento"
),

path(
    "laudos/<int:doc_id>/excluir/",
    views.excluir_documento,
    name="excluir_documento"
),

path(
    "laudos/<int:doc_id>/",
    views.detalhe_documento,
    name="detalhe_documento"
),

path(
    "aluno/<int:aluno_id>/paed/",
    views.atualizar_paed,
    name="atualizar_paed"
),
path(
    "upload/laudo/",
    views.gerar_upload_laudo,
    name="gerar_upload_laudo"
),
path(
    "laudos/verificar-orfaos/",
    views.verificar_arquivos_orfaos,
    name="verificar_orfaos"
),
path(
    "laudos/orfaos/excluir/",
    views.excluir_arquivo_orfao,
    name="excluir_orfao"
),
path(
    "resetar-senha-seduc/",
    views.resetar_senha_seduc,
    name="resetar_senha_seduc"
),
]
