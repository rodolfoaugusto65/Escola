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
]
