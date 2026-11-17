from alunos.models import Aluno
from ocorrencias.models import Ocorrencia
from frequencia.models import FrequenciaAluno
from django.db.models import Count, Q
from .models import ConselhoClasse, ConselhoAluno


def contar_ocorrencias(aluno):
    return Ocorrencia.objects.filter(aluno=aluno).count()


def classificar(media, frequencia, ocorrencias):
    if media is None:
        return "sem_dados"

    if media >= 7 and frequencia >= 75 and ocorrencias == 0:
        return "alto"

    if media >= 5:
        return "regular"

    if media < 5 or ocorrencias > 3:
        return "atencao"

    if media < 4 or frequencia < 75 or ocorrencias > 5:
        return "critico"


def diagnostico(media, frequencia, ocorrencias):
    if frequencia and frequencia < 75:
        return "Baixa frequência impactando desempenho."

    if ocorrencias > 5:
        return "Alta incidência de ocorrências."

    if media and media < 5:
        return "Dificuldade de aprendizagem."

    return "Desempenho adequado."


def prioridade(classificacao):
    if classificacao == "critico":
        return "alta"
    if classificacao == "atencao":
        return "media"
    return "baixa"


def sugestao(media, frequencia, ocorrencias):
    if frequencia and frequencia < 75:
        return "Contato com responsáveis."

    if media and media < 5:
        return "Reforço pedagógico."

    if ocorrencias > 3:
        return "Acompanhamento disciplinar."

    return "Manter acompanhamento."


def calcular_frequencia(aluno):
    dados = FrequenciaAluno.objects.filter(aluno=aluno).aggregate(
        total=Count("id"),
        presencas=Count("id", filter=Q(presente=True))
    )

    total = dados["total"] or 0
    presencas = dados["presencas"] or 0

    return round((presencas / total * 100), 1) if total else 0


def gerar_conselho(turma, bimestre, ano, usuario):
    conselho = ConselhoClasse.objects.create(
        turma=turma,
        bimestre=bimestre,
        ano=ano,
        criado_por=usuario
    )

    alunos = turma.alunos.all()

    for aluno in alunos:

        # ❗ média ainda depende do seu sistema
        media = getattr(aluno, "media", None)

        # ✅ CORREÇÃO REAL
        frequencia = calcular_frequencia(aluno)

        ocorrencias = contar_ocorrencias(aluno)

        cls = classificar(media, frequencia, ocorrencias)

        ConselhoAluno.objects.create(
            conselho=conselho,
            aluno=aluno,
            media=media,
            frequencia=frequencia,
            total_ocorrencias=ocorrencias,
            classificacao=cls,
            diagnostico=diagnostico(media, frequencia, ocorrencias),
            prioridade=prioridade(cls),
            sugestao=sugestao(media, frequencia, ocorrencias),
        )

    return conselho