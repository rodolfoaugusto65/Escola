from django.urls import path
from . import views

urlpatterns = [
    # Tela principal (relatórios + filtros)
    path('', views.lista_frequencias, name='lista_frequencia'),

    # Lançar frequência
    path('lancar/', views.criar_frequencia, name='criar_frequencia'),

    # Lista de lançamentos (edição / exclusão / impressão)
    path('lancamentos/', views.lista_lancamentos, name='lista_lancamentos'),

    # Relatório detalhado (datas nas colunas)
    path('detalhado/', views.frequencia_detalhada, name='frequencia_detalhada'),

    # Impressão genérica (usa filtros GET)
    path('imprimir/', views.imprimir_frequencia, name='imprimir_frequencia'),

    path('<int:pk>/', views.detalhe_frequencia, name='frequencia_detalhe'),

    path('<int:pk>/editar/', views.editar_frequencia, name='frequencia_editar'),

    path('<int:pk>/excluir/', views.excluir_frequencia, name='frequencia_excluir'),

     # 🔥 ESTA É A QUE ESTAVA FALTANDO
    path('aluno/<int:aluno_id>/', views.frequencia_aluno, name='frequencia_aluno'),

    path('imprimir/', views.frequencia_imprimir, name='frequencia_imprimir'), 
]

