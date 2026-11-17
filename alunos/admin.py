from django.contrib import admin
from .models import Aluno


@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    list_display = (
        'matricula', 'nome',
        'turma_ano_escolar', 'turma_nome', 'turma_ano_letivo'
    )

    # Necessário para autocomplete_fields em outros ModelAdmins.
    # Permite localizar alunos por nome ou matrícula.
    search_fields = ('nome', 'matricula')
