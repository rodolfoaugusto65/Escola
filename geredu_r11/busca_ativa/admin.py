from django.contrib import admin
from .models import (ImportacaoInfrequencia, SituacaoInfrequencia, AcessoConsultaAluno,
    AcaoBuscaAtiva, ConsultaFrequenciaLog, ComunicadoSistema, LeituraComunicado,
    CalendarioEscolar, DiaNaoLetivo, ImportacaoLote, HistoricoSituacaoInfrequencia)

@admin.register(ConsultaFrequenciaLog)
class ConsultaFrequenciaLogAdmin(admin.ModelAdmin):
    list_display = ("aluno", "consultado_em", "origem")
    list_filter = ("origem", "consultado_em")
    search_fields = ("aluno__nome", "aluno__matricula")
    readonly_fields = ("aluno", "consultado_em", "origem")

@admin.register(ComunicadoSistema)
class ComunicadoSistemaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "versao", "ativo", "criado_em", "total_leituras")
    list_filter = ("ativo", "criado_em")
    search_fields = ("titulo", "versao", "texto")
    readonly_fields = ("criado_em",)

    @admin.display(description="Leituras confirmadas")
    def total_leituras(self, obj):
        return obj.leituras.count()

class DiaNaoLetivoInline(admin.TabularInline):
    model = DiaNaoLetivo
    extra = 1

@admin.register(CalendarioEscolar)
class CalendarioEscolarAdmin(admin.ModelAdmin):
    list_display = ("nome", "data_fim_letivo", "ativo")
    inlines = [DiaNaoLetivoInline]

@admin.register(ImportacaoInfrequencia)
class ImportacaoInfrequenciaAdmin(admin.ModelAdmin):
    list_display = ("arquivo", "ano_letivo", "total_registros", "vinculados", "nao_vinculados", "estudantes_repetidos", "criado_em")
    list_filter = ("ano_letivo", "criado_em")
    search_fields = ("arquivo", "sha256")
    readonly_fields = tuple(field.name for field in ImportacaoInfrequencia._meta.fields)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

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


@admin.register(HistoricoSituacaoInfrequencia)
class HistoricoSituacaoInfrequenciaAdmin(admin.ModelAdmin):
    list_display = ("matricula", "aluno", "ano_letivo", "percentual_considerado", "faixa_alerta", "apareceu_novamente", "importado_em")
    list_filter = ("ano_letivo", "faixa_alerta", "apareceu_novamente", "importado_em")
    search_fields = ("matricula", "aluno__nome", "importacao__arquivo")
    readonly_fields = tuple(field.name for field in HistoricoSituacaoInfrequencia._meta.fields)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
