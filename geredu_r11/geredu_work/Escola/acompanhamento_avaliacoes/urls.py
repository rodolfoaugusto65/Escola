from django.urls import path
from . import views

app_name = 'acompanhamento_avaliacoes'
urlpatterns = [
    path('', views.painel, name='painel'),
    path('importar/', views.importar, name='importar'),
    path('historico/', views.historico, name='historico'),
    path('importacao/<int:pk>/', views.detalhe_importacao, name='detalhe_importacao'),
]
