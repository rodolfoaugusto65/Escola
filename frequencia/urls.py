from django.urls import path
from . import views

urlpatterns = [

    path('', views.lista_frequencias, name='lista_frequencia'),

    path('lancar/', views.criar_frequencia, name='criar_frequencia'),

    path('lancamentos/', views.lista_lancamentos, name='lista_lancamentos'),

    path('<int:pk>/', views.detalhe_frequencia, name='frequencia_detalhe'),

    path('<int:pk>/editar/', views.editar_frequencia, name='editar_frequencia'),

    path('<int:pk>/excluir/', views.excluir_frequencia, name='excluir_frequencia'),

    path('detalhado/', views.frequencia_detalhada, name='frequencia_detalhada'),

    path('aluno/<int:aluno_id>/', views.frequencia_aluno, name='frequencia_aluno'),

    path('imprimir/', views.imprimir_frequencia, name='imprimir_frequencia'),
    
    path(
    "por-aluno/",
    views.frequencia_por_aluno,
    name="frequencia_por_aluno"
),
    path(
        "aluno/<int:aluno_id>/",
        views.frequencia_aluno,
        name="frequencia_aluno"
    ),
    path(
    "imprimir/",
    views.frequencia_imprimir,
    name="frequencia_imprimir"
),
]