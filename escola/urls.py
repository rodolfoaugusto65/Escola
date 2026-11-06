from django.contrib import admin
from django.urls import path, include
from core import views as core_views
from busca_ativa import views as busca_ativa_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [

    path('admin/', admin.site.urls),

    # Home
    path('', core_views.home_view, name='home'),

    # Rotas do core (buscas, APIs globais etc)
    path('core/', include('core.urls')),

    # Autenticação
    path('usuarios/', include('usuarios.urls')),

    # Apps do sistema
    path('alunos/', include('alunos.urls')),
    path('turmas/', include('turmas.urls')),
    path('ocorrencias/', include('ocorrencias.urls')),
    path('frequencia/', include('frequencia.urls')),
    path("conselho/", include("conselho.urls")),
    path("busca-ativa/", include("busca_ativa.urls")),
    path("consulta-frequencia/", busca_ativa_views.consulta_por_codigo, name="consulta_frequencia_codigo"),
    path("consulta-frequencia/<str:token>/", busca_ativa_views.consulta_publica, name="consulta_frequencia_publica"),
    path("transferencias/", include("transferencias.urls")),
]

