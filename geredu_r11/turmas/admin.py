from django.contrib import admin
from .models import Turma


@admin.register(Turma)
class TurmaAdmin(admin.ModelAdmin):
    list_display = (
        'etapa',
        'ano_letivo',
        'professor_conselheiro',
        'aluno_lider',
        'criado_em',
    )

    list_filter = (
        'etapa',
        'ano_letivo',
    )

    search_fields = (
        'etapa',
    )
