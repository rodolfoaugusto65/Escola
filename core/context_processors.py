from alunos.models import Aluno
from core.working_days import eh_dia_letivo


def estatisticas_alunos(request):

    total_alunos = Aluno.objects.count()

    total_vespertino = Aluno.objects.filter(
        turma__turno="VES"
    ).count()

    total_noturno = Aluno.objects.filter(
        turma__turno="NOT"
    ).count()

    return {
        "total_alunos": total_alunos,
        "total_vespertino": total_vespertino,
        "total_noturno": total_noturno,
    }

def alertas_infrequencia(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {"total_alertas_infrequencia": 0}
    from django.db.models import Q
    from busca_ativa.models import SituacaoInfrequencia
    from django.utils import timezone
    from busca_ativa.models import AcaoBuscaAtiva
    hoje = timezone.localdate()
    total = SituacaoInfrequencia.objects.filter(
        ano_letivo=hoje.year
    ).filter(Q(percentual_geral_final__gte=10) | Q(percentual_geral__gte=10) | Q(percentual_relatorio_25__gte=10)).exclude(
        aluno__acoes_busca_ativa__prazo__gte=hoje,
        aluno__acoes_busca_ativa__status__in=["Aberta", "Em andamento", "Aguardando retorno"],
    ).distinct().count()
    return {"total_alertas_infrequencia": total}


def avisos_e_calendario(request):
    """Aviso obrigatório, contador de dias letivos e assistente diário."""
    from datetime import timedelta
    from django.utils import timezone
    from busca_ativa.models import ComunicadoSistema, LeituraComunicado, CalendarioEscolar
    context = {"comunicado_pendente": None, "dias_letivos_restantes": None, "data_fim_letivo": None, "mostrar_assistente_natalino": False}
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        pendentes = (
            ComunicadoSistema.objects.filter(ativo=True)
            .exclude(leituras__usuario=user)
            .order_by("criado_em", "pk")
        )
        context["comunicado_pendente"] = pendentes.first()
        context["total_comunicados_pendentes"] = pendentes.count()
        hoje = timezone.localdate()
        calendario = CalendarioEscolar.objects.filter(ativo=True).order_by("-data_fim_letivo").first()
        if calendario:
            feriados = set(calendario.dias_nao_letivos.values_list("data", flat=True))
            dias = 0
            dia = hoje
            while dia <= calendario.data_fim_letivo:
                if eh_dia_letivo(dia, feriados):
                    dias += 1
                dia += timedelta(days=1)
            context["dias_letivos_restantes"] = dias
            context["data_fim_letivo"] = calendario.data_fim_letivo
        context["mostrar_assistente_natalino"] = request.session.get("assistente_natalino_visto") != hoje.isoformat()
    return context
