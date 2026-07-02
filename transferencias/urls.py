from django.urls import path
from . import views

app_name = "transferencias"

urlpatterns = [
    path("", views.lista_transferencias, name="lista"),
    path("nova/", views.criar_transferencia, name="nova"),
    path("<int:pk>/assumir/", views.assumir_transferencia, name="assumir"),
    path("<int:pk>/concluir/", views.concluir_transferencia, name="concluir"),
]