from django.urls import path
from . import views

urlpatterns = [

    path(
        "buscar-alunos/",
        views.buscar_alunos_autocomplete,
        name="buscar_alunos_autocomplete"
    ),

]