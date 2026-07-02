from django.contrib import admin
from .models import Transferencia

@admin.register(Transferencia)
class TransferenciaAdmin(admin.ModelAdmin):
    list_display = ("aluno", "tipo", "status", "data_lancamento", "prazo_limite")
    list_filter = ("status", "tipo")
    search_fields = ("aluno",)