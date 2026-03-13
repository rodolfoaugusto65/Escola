from django.contrib import admin
from django.urls import path, include
from core import views as core_views
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
]

