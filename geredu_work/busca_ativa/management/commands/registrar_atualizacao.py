from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from busca_ativa.models import ComunicadoSistema


class Command(BaseCommand):
    """Registra uma versão implantada no histórico persistente de comunicados."""
    help = (
        "Registra uma atualização do GerEdu no histórico do sistema. "
        "O comunicado aparece aos usuários até a confirmação de leitura."
    )

    def add_arguments(self, parser):
        parser.add_argument("--versao", required=True, help="Identificador único, ex.: 2026.11.10.3")
        parser.add_argument("--titulo", required=True, help="Título exibido no comunicado")
        parser.add_argument("--texto", required=True, help="Resumo das alterações desta versão")

    def handle(self, *args, **options):
        versao = options["versao"].strip()
        titulo = options["titulo"].strip()
        texto = options["texto"].strip()
        if not versao or not titulo or not texto:
            raise CommandError("Versão, título e texto não podem ficar vazios.")

        try:
            with transaction.atomic():
                registro, criado = ComunicadoSistema.objects.get_or_create(
                    versao=versao,
                    defaults={"titulo": titulo, "texto": texto, "ativo": True},
                )
        except IntegrityError as exc:
            raise CommandError(f"Não foi possível registrar a versão {versao}: {exc}") from exc

        if criado:
            self.stdout.write(self.style.SUCCESS(
                f"Atualização {registro.versao} registrada no histórico do GerEdu."
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f"A versão {versao} já está registrada; nenhum histórico foi sobrescrito."
            ))
