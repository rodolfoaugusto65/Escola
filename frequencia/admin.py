from django.contrib import admin
from .models import Frequencia, FrequenciaAluno


class FrequenciaAlunoInline(admin.TabularInline):
    model = FrequenciaAluno
    extra = 0


@admin.register(Frequencia)
class FrequenciaAdmin(admin.ModelAdmin):
    list_display = ('turma', 'data')
    list_filter = ('turma', 'data')
    inlines = [FrequenciaAlunoInline]
