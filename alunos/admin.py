from django.contrib import admin
from .models import Aluno

@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    list_display = (
        'matricula', 'nome',
        'turma_ano_escolar', 'turma_nome', 'turma_ano_letivo'
    )
