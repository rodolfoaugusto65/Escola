from alunos.models import Aluno


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