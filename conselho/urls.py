from django.urls import path
from . import views

app_name = "conselho"

urlpatterns = [
    path("", views.lista_conselhos, name="lista"),
    path("novo/", views.criar_conselho, name="criar"),
    path("<int:pk>/", views.detalhe_conselho, name="detalhe"),
    path("<int:pk>/ata/", views.gerar_ata, name="ata"),
    path("<int:pk>/preencher/", views.preencher_conselho, name="preencher"),
    path("<int:pk>/ata/pdf/", views.gerar_ata_pdf, name="ata_pdf"),
    path("<int:pk>/relatorio/", views.relatorio_pedagogico, name="relatorio_pedagogico"),
    path("relatorio/bimestre/<int:bimestre>/<int:ano>/",
     views.relatorio_bimestre,
     name="relatorio_bimestre"),
]