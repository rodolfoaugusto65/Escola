from django.urls import path
from . import views

app_name = "mapeamento_aprendizagem"
urlpatterns = [
    path("", views.painel, name="painel"),
    path("exportar/", views.exportar, name="exportar"),
    path("importar-diagnostico/", views.importar_diagnostico, name="importar_diagnostico"),
]
