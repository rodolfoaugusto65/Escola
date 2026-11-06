from django.contrib import admin
from .models import (ImportacaoInfrequencia, SituacaoInfrequencia, AcessoConsultaAluno,
    AcaoBuscaAtiva, ConsultaFrequenciaLog, ComunicadoSistema, LeituraComunicado,
    CalendarioEscolar, DiaNaoLetivo, ImportacaoLote)

@admin.register(ConsultaFrequenciaLog)
class ConsultaFrequenciaLogAdmin(admin.ModelAdmin):
    list_display = ("aluno", "consultado_em", "origem")
    list_filter = ("origem", "consultado_em")
    search_fields = ("aluno__nome", "aluno__matricula")
    readonly_fields = ("aluno", "consultado_em", "origem")

@admin.register(ComunicadoSistema)
class ComunicadoSistemaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "versao", "ativo", "criado_em")
    list_filter = ("ativo",)

class DiaNaoLetivoInline(admin.TabularInline):
    model = DiaNaoLetivo
    extra = 1

@admin.register(CalendarioEscolar)
class CalendarioEscolarAdmin(admin.ModelAdmin):
    list_display = ("nome", "data_fim_letivo", "ativo")
    inlines = [DiaNaoLetivoInline]

admin.site.register(ImportacaoInfrequencia)
admin.site.register(SituacaoInfrequencia)
admin.site.register(AcessoConsultaAluno)
admin.site.register(AcaoBuscaAtiva)
admin.site.register(LeituraComunicado)


@admin.register(ImportacaoLote)
class ImportacaoLoteAdmin(admin.ModelAdmin):
    list_display = ("arquivo", "tipo", "ano_letivo", "status", "processados", "total", "vinculados", "nao_vinculados", "criado_em")
    list_filter = ("tipo", "status", "ano_letivo")
    search_fields = ("arquivo", "usuario__username")
    readonly_fields = ("arquivo", "tipo", "ano_letivo", "usuario", "importacao", "dados", "total", "processados", "vinculados", "nao_vinculados", "pendentes", "status", "erro", "criado_em", "atualizado_em")
