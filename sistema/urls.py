from django.urls import path
from . import views

urlpatterns = [
    path("", views.lista_modulos, name="lista_modulos"),
    path("novo/", views.criar_modulo, name="criar_modulo"),
    path("editar/<int:pk>/", views.editar_modulo, name="editar_modulo"),
]
