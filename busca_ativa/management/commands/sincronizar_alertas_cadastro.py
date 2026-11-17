from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from alunos.models import Aluno
from busca_ativa.models import SituacaoInfrequencia


class Command(BaseCommand):
    help = "Marca no cadastro alunos com alerta de infrequência (10% ou mais)."

    def add_arguments(self, parser):
        parser.add_argument("--ano", type=int, default=timezone.localdate().year)

    def handle(self, *args, **options):
        ano = options["ano"]
        ids = SituacaoInfrequencia.objects.filter(ano_letivo=ano).filter(
            Q(percentual_geral_final__gte=10)
            | Q(percentual_geral__gte=10)
            | Q(percentual_relatorio_25__gte=10)
        ).values_list("aluno_id", flat=True).distinct()

        atualizados = Aluno.objects.filter(
            id__in=ids, aluno_busca_ativa=False
        ).update(aluno_busca_ativa=True)

        self.stdout.write(self.style.SUCCESS(
            f"{atualizados} cadastro(s) marcado(s) como Busca Ativa para {ano}."
        ))
