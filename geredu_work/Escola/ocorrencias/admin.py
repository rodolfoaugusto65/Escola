from django.contrib import admin
from .models import Ocorrencia


@admin.register(Ocorrencia)
class OcorrenciaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'aluno', 'tipo_ocorrencia', 'status', 'data')
    search_fields = ('codigo', 'aluno__nome')
