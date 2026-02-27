from django.contrib import admin
from django.urls import path, include
from core import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Página inicial (home)
    path('', core_views.home_view, name='home'),

    # 🔐 Rotas de autenticação (ficam dentro do app usuarios)
    path('usuarios/', include('usuarios.urls')),

    # Outros apps
    path('alunos/', include('alunos.urls')),
    path('turmas/', include('turmas.urls')),
    path('ocorrencias/', include('ocorrencias.urls')),
    path('frequencia/', include('frequencia.urls')),
    ]
