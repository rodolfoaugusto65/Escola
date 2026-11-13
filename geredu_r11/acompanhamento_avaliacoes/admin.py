from django.contrib import admin
from .models import Avaliacao, ImportacaoAvaliacao, RegistroParticipacao

class RegistroInline(admin.TabularInline):
    model = RegistroParticipacao
    extra = 0
    show_change_link = True

@admin.register(Avaliacao)
class AvaliacaoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ano_letivo', 'etapa', 'bimestre')
    search_fields = ('nome',)

@admin.register(ImportacaoAvaliacao)
class ImportacaoAdmin(admin.ModelAdmin):
    list_display = ('arquivo', 'avaliacao', 'criado_em', 'total_registros', 'realizados', 'pendentes', 'status')
    list_filter = ('status', 'avaliacao__ano_letivo')
    inlines = [RegistroInline]

@admin.register(RegistroParticipacao)
class RegistroAdmin(admin.ModelAdmin):
    list_display = ('nome_aluno', 'matricula', 'ano_serie', 'turma', 'situacao', 'importacao')
    search_fields = ('nome_aluno', 'matricula', 'turma')
    list_filter = ('situacao', 'ano_serie')
