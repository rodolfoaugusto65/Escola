from django.urls import path, include
from . import views

urlpatterns = [

    path('', views.lista_ocorrencias, name='lista_ocorrencias'),
    path('nova/', views.criar_ocorrencia, name='criar_ocorrencia'),
    path('<int:pk>/', views.detalhe_ocorrencia, name='detalhe_ocorrencia'),
    path('<int:pk>/editar/', views.editar_ocorrencia, name='editar_ocorrencia'),
    path('<int:pk>/imprimir/', views.imprimir_ocorrencia, name='imprimir_ocorrencia'),
    path("imprimir/aluno/<int:aluno_id>/", views.imprimir_por_aluno, name='imprimir_por_aluno'),
 # ULTRA PRO MAX
    path("dashboard/", views.dashboard_ocorrencias, name="dashboard_ocorrencias"),
    path("relatorio/", views.relatorio_ocorrencias, name="relatorio_ocorrencias"),
    path("enterprise/dashboard/", views.dashboard_enterprise, name="dashboard_enterprise"),
    path("enterprise/export-excel/", views.export_excel_ocorrencias, name="export_excel_ocorrencias"),
    path("enterprise/print-all/", views.imprimir_pdf_enterprise, name="imprimir_pdf_enterprise"),
    path("exportar-excel/",views.export_excel_ocorrencias, name="export_excel_ocorrencias"),
    path("get-alunos/",views.get_alunos_por_turma, name="get_alunos_por_turma"),
    path("buscar-aluno/", views.buscar_aluno, name="buscar_aluno"),
    path("excluir/<int:pk>/", views.excluir_ocorrencia, name="excluir_ocorrencia"),
    ]
