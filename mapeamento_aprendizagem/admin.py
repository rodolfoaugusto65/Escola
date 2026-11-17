from django.contrib import admin
from .models import RegistroMapeamento


@admin.register(RegistroMapeamento)
class RegistroMapeamentoAdmin(admin.ModelAdmin):
    list_display = ("aluno", "turma", "ano_letivo", "paede", "situacao", "atualizado_em")
    list_filter = ("ano_letivo", "turma__turno", "turma", "situacao", "paede")
    search_fields = ("aluno__nome", "aluno__matricula")
    autocomplete_fields = ("aluno", "turma")
