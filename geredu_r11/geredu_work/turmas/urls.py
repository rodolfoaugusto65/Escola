from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_turmas, name='lista_turmas'),
    path('nova/', views.cadastrar_turma, name='cadastrar_turma'),
    path('<int:id>/editar/', views.editar_turma, name='editar_turma'),
    path('<int:pk>/excluir/', views.excluir_turma, name='excluir_turma'),
    path('relatorio/', views.relatorio_turmas, name='relatorio_turmas'),
]
