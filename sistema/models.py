from django.db import models
from usuarios.models import Usuario


class AppModulo(models.Model):
    nome = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    descricao = models.TextField(blank=True)

    ativo = models.BooleanField(default=True)

    # Perfis que podem acessar
    perfis_permitidos = models.JSONField(
        default=list,
        help_text="Ex: ['ADMIN','COORD','PROF']"
    )

    criado_em = models.DateTimeField(auto_now_add=True)

    def pode_acessar(self, usuario: Usuario):
        if usuario.perfil == "ADMIN":
            return True

        return usuario.perfil in self.perfis_permitidos

    def __str__(self):
        return self.nome
