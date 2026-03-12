from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .utils import render_smart
from django.http import JsonResponse
from django.db.models import Q
from alunos.models import Aluno
from django.db.models import Count



@login_required
def home_view(request):
    usuario = request.user

    contexto = {
        'nome_completo': usuario.get_full_name(),
        'perfil': usuario.get_perfil_display() if hasattr(usuario, 'get_perfil_display') else '',
        'cpf': usuario.cpf,
    }

    template, contexto = render_smart(request, "core/home.html", contexto)
    return render(request, template, contexto)


@login_required
def buscar_alunos_autocomplete(request):

    q = request.GET.get("q","").strip()

    if len(q) < 2:
        return JsonResponse({"results":[]})

    alunos = (
        Aluno.objects
        .select_related("turma")
        .annotate(total_ocorrencias=Count("ocorrencias"))
        .only(
            "id",
            "nome",
            "matricula",
            "nome_mae",
            "turma__nome",
            "turma__ano_escolar"
        )
        .filter(
            Q(nome__icontains=q) |
            Q(matricula__icontains=q) |
            Q(nome_mae__icontains=q)
        )
        .order_by("nome")[:8]
    )

    results = []

    for aluno in alunos:

        turma = ""

        if aluno.turma:
            turma = f"{aluno.turma.ano_escolar} - Turma {aluno.turma.nome}"

        results.append({
            "id": aluno.id,
            "nome": aluno.nome,
            "matricula": aluno.matricula,
            "turma": turma,
            "ocorrencias": aluno.total_ocorrencias,

            "url_relatorio": f"/alunos/relatorio/{aluno.matricula}/",
            "url_ocorrencia": f"/ocorrencias/nova/?matricula={aluno.matricula}",
            "url_ocorrencias": f"/ocorrencias/?matricula={aluno.matricula}",
        })

    return JsonResponse({"results":results})