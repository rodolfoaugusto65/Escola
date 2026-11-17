"""Verificação rápida pós-deploy: python verificar_mapeamento_r27.py"""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "escola.settings")
import django
django.setup()
from django.conf import settings
from django.urls import reverse
from mapeamento_aprendizagem.models import RegistroMapeamento
from busca_ativa.models import ComunicadoSistema

assert "mapeamento_aprendizagem" in settings.INSTALLED_APPS
assert reverse("mapeamento_aprendizagem:painel") == "/mapeamento-aprendizagem/"
assert ComunicadoSistema.objects.filter(versao="2026.11.17.27", ativo=True).exists()
print("OK: app registrado, rota resolvida, modelo carregado e comunicado r27 publicado.")
