from alunos.models import Aluno
from ocorrencias.models import Ocorrencia
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


def gerar_conselho(turma, bimestre, ano, usuario):
    conselho = ConselhoClasse.objects.create(
        turma=turma,
        bimestre=bimestre,
        ano=ano,
        criado_por=usuario
    )

    alunos = turma.alunos.all()

    for aluno in alunos:
        media = getattr(aluno, "media", None)
        frequencia = getattr(aluno, "frequencia", None)

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