from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, PerfilAcesso

@admin.register(PerfilAcesso)
class PerfilAcessoAdmin(admin.ModelAdmin):
    list_display = ("nome", "codigo", "ativo", "atualizado_em")
    list_filter = ("ativo",)
    search_fields = ("nome", "codigo", "descricao")

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("cpf", "username", "first_name", "last_name", "perfil", "is_active", "is_staff", "is_superuser")
    search_fields = ("cpf", "first_name", "last_name", "username")
    list_filter = ("perfil", "is_active", "is_staff", "is_superuser")
    fieldsets = ((None, {"fields": ("cpf", "username", "password")}), ("Informações pessoais", {"fields": ("first_name", "last_name", "email", "telefone", "endereco", "perfil")}), ("Permissões", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}), ("Datas importantes", {"fields": ("last_login", "date_joined")}))
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("cpf", "username", "first_name", "last_name", "perfil", "password1", "password2")}),)
