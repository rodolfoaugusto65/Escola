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
]