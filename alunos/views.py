from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import DocumentoAluno
from .forms import DocumentoAlunoForm
from .models import Aluno
from turmas.models import Turma
from .forms import AlunoForm
from core.utils import render_smart
from django.core.files.storage import default_storage
from ocorrencias.models import Ocorrencia
from frequencia.models import FrequenciaAluno
import boto3
import uuid
from django.conf import settings
import os
import json
import re
import time
from datetime import datetime
from django.http import JsonResponse
from playwright.sync_api import sync_playwright


# ==================================================
# LISTA DE ALUNOS
# ==================================================
@login_required
def lista_alunos(request):

    alunos = (
        Aluno.objects
        .select_related("turma")
        .only(
            "id",
            "nome",
            "matricula",
            "data_nascimento",
            "turma_ano_letivo",
            "turma_ano_escolar",
            "turma_nome",
            "turma__nome",
            "turma__ano_escolar",
            "turma__turno"
        )
    )

    busca = request.GET.get("busca")
    turno = request.GET.get("turno")
    ano = request.GET.get("ano")
    turma = request.GET.get("turma")

    # =========================
    # BUSCA INTELIGENTE
    # =========================

    if busca:
        alunos = alunos.filter(
            Q(nome__icontains=busca) |
            Q(matricula__icontains=busca) |
            Q(turma__nome__icontains=busca) |
            Q(turma__ano_escolar__icontains=busca)
        )

    # =========================
    # FILTROS
    # =========================

    if turno:
        alunos = alunos.filter(turma__turno=turno)

    if ano:
        alunos = alunos.filter(turma__ano_escolar=ano)

    if turma:
        alunos = alunos.filter(turma__nome=turma)

    # =========================
    # ORDENAÇÃO SEGURA
    # =========================

    ordem = request.GET.get("ordem", "nome")

    campos_validos = [
        "nome", "-nome",
        "matricula", "-matricula",
        "data_nascimento", "-data_nascimento"
    ]

    if ordem not in campos_validos:
        ordem = "nome"

    alunos = alunos.order_by(ordem)

    # =========================
    # LIMITE DE REGISTROS
    # =========================

    try:
        limite = int(request.GET.get("limite", 20))
    except ValueError:
        limite = 20

    if limite not in [10, 20, 30, 40, 50]:
        limite = 20

    # =========================
    # PAGINAÇÃO
    # =========================

    paginator = Paginator(alunos, limite)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # =========================
    # FILTROS DINÂMICOS
    # =========================

    turmas_qs = Turma.objects.all()

    if turno:
        turmas_qs = turmas_qs.filter(turno=turno)

    if ano:
        turmas_qs = turmas_qs.filter(ano_escolar=ano)

    turnos = Turma.objects.values_list(
        "turno",
        flat=True
    ).distinct().order_by("turno")

    anos = turmas_qs.values_list(
        "ano_escolar",
        flat=True
    ).distinct().order_by("ano_escolar")

    turmas = turmas_qs.values_list(
        "nome",
        flat=True
    ).distinct().order_by("nome")

    contexto = {
        "page_obj": page_obj,
        "turnos": turnos,
        "anos": anos,
        "turmas": turmas,
        "limite": limite
    }

    template, contexto = render_smart(
        request,
        "alunos/lista_alunos.html",
        contexto
    )

    return render(request, template, contexto)


# ==================================================
# CADASTRAR ALUNO
# ==================================================

@login_required
def cadastrar_aluno(request):

    if request.method == 'POST':

        form = AlunoForm(request.POST, request.FILES)

        if form.is_valid():

            aluno = form.save(commit=False)

            if request.user.is_authenticated:
                aluno.criado_por = request.user
                aluno.atualizado_por = request.user

            aluno.save()

            messages.success(request, "Aluno cadastrado com sucesso!")
            return redirect('lista_alunos')

        else:
            messages.error(request, "Corrija os erros antes de salvar.")

    else:
        form = AlunoForm()

    return render(
        request,
        'alunos/cadastrar_aluno.html',
        {'form': form}
    )


# ==================================================
# EDITAR ALUNO
# ==================================================
@login_required
def editar_aluno(request, id):

    aluno = get_object_or_404(Aluno, id=id)

    # =========================
    # CONTADOR DE LAUDOS PAED
    # =========================
    total_laudos = aluno.documentos.count()

    if request.method == 'POST':

        form = AlunoForm(
            request.POST,
            request.FILES,
            instance=aluno
        )

        if form.is_valid():

            aluno = form.save(commit=False)

            # =========================
            # REMOVER FOTO (SE EXISTIR)
            # =========================
            if request.POST.get("foto-clear"):

                # foto principal
                if aluno.foto:
                    try:
                        if default_storage.exists(aluno.foto.name):
                            default_storage.delete(aluno.foto.name)
                    except Exception:
                        pass

                # thumbnail
                if getattr(aluno, "foto_thumb", None):
                    try:
                        if default_storage.exists(aluno.foto_thumb.name):
                            default_storage.delete(aluno.foto_thumb.name)
                    except Exception:
                        pass

                aluno.foto = None
                aluno.foto_thumb = None

            # =========================
            # AUDITORIA
            # =========================
            if request.user.is_authenticated:
                aluno.atualizado_por = request.user

            aluno.save()

            messages.success(request, "Aluno atualizado com sucesso!")
            return redirect('lista_alunos')

        else:
            messages.error(request, "Corrija os erros antes de salvar.")

    else:
        form = AlunoForm(instance=aluno)

    return render(
        request,
        'alunos/cadastrar_aluno.html',
        {
            'form': form,
            'aluno': aluno,
            'total_laudos': total_laudos
        }
    )

# ==================================================
# EXCLUIR ALUNO
# ==================================================

@require_POST
@login_required
def excluir_aluno(request, pk):

    aluno = get_object_or_404(Aluno, pk=pk)

    try:

        aluno.delete()

        return JsonResponse({
            "success": True,
            "message": "Aluno excluído com sucesso!"
        })

    except Exception:

        return JsonResponse({
            "success": False,
            "error": "Erro interno ao excluir."
        })


# ==================================================
# RELATÓRIO COMPLETO DO ALUNO
# ==================================================
@login_required
def relatorio_aluno_completo(request, aluno_id):

    # =========================
    # BUSCAR ALUNO (ID OU MATRÍCULA)
    # =========================

    aluno = Aluno.objects.select_related("turma").filter(
        id=aluno_id
    ).first()

    if not aluno:
        aluno = Aluno.objects.select_related("turma").filter(
            matricula=aluno_id
        ).first()

    if not aluno:
        raise Http404("Aluno não encontrado")

    # =========================
    # DOCUMENTOS PAED
    # =========================

    documentos_paed = DocumentoAluno.objects.filter(
        aluno=aluno
    ).order_by("-data_laudo")

    # =========================
    # OCORRÊNCIAS
    # =========================

    ocorrencias = Ocorrencia.objects.filter(
        aluno=aluno
    ).order_by("-data")

    total_ocorrencias = ocorrencias.count()

    # =========================
    # FREQUÊNCIA
    # =========================

    frequencias = FrequenciaAluno.objects.filter(
        aluno=aluno
    ).select_related("frequencia")

    total_aulas = frequencias.count()

    total_presencas = frequencias.filter(
        presente=True
    ).count()

    percentual_frequencia = 0

    if total_aulas > 0:
        percentual_frequencia = round(
            (total_presencas / total_aulas) * 100,
            1
        )

    # =========================
    # ÚLTIMO DIA PRESENTE
    # =========================

    ultimo_dia_presente = frequencias.filter(
        presente=True
    ).order_by("-frequencia__data").values_list(
        "frequencia__data",
        flat=True
    ).first()

    # =========================
    # CONTEXTO
    # =========================

    contexto = {
        "aluno": aluno,
        "documentos_paed": documentos_paed,
        "ocorrencias": ocorrencias[:10],  # últimas ocorrências
        "total_ocorrencias": total_ocorrencias,
        "percentual_frequencia": percentual_frequencia,
        "ultimo_dia_presente": ultimo_dia_presente,
    }

    return render(
        request,
        "alunos/relatorio_aluno_completo.html",
        contexto
    )

# ==================================================
# RELATÓRIO DE ALUNOS
# ==================================================

@login_required
def relatorio_alunos(request):

    alunos = Aluno.objects.select_related("turma").all()

    query = request.GET.get('q')
    tipo = request.GET.get('tipo')

    if query:

        if tipo == 'matricula':
            alunos = alunos.filter(matricula__icontains=query)

        else:
            alunos = alunos.filter(nome__icontains=query)

    turma_id = request.GET.get('turma')

    if turma_id:
        alunos = alunos.filter(turma_id=turma_id)

    if request.GET.get('dependencia') == '1':
        alunos = alunos.filter(possui_dependencia=True)

    if request.GET.get('trabalhador') == '1':
        alunos = alunos.filter(aluno_trabalhador=True)

    if request.GET.get('paed') == '1':
        alunos = alunos.filter(aluno_paed=True)

    if request.GET.get('transferido') == '1':
        alunos = alunos.filter(transferido=True)

    total = alunos.count()
    total_paed = alunos.filter(aluno_paed=True).count()
    total_dependencia = alunos.filter(possui_dependencia=True).count()
    total_transferidos = alunos.filter(transferido=True).count()

    mostrar = request.GET.get("mostrar", 10)

    try:
        mostrar = int(mostrar)
    except:
        mostrar = 10

    paginator = Paginator(
        alunos.order_by("nome"),
        mostrar
    )

    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    turmas = Turma.objects.all().order_by('ano_letivo')

    context = {
        'alunos': alunos.order_by('nome'),
        'page_obj': page_obj,
        'mostrar': mostrar,
        'turmas': turmas,
        'total': total,
        'total_paed': total_paed,
        'total_dependencia': total_dependencia,
        'total_transferidos': total_transferidos
    }

    template, context = render_smart(
        request,
        'alunos/relatorio_alunos.html',
        context
    )

    return render(request, template, context)

from django.urls import reverse



@login_required
def documentos_aluno(request, aluno_id):

    aluno = get_object_or_404(Aluno, id=aluno_id)

    next_url = request.GET.get("next")

    if not next_url:
        next_url = request.META.get("HTTP_REFERER")

    if not next_url or "/editar/" not in next_url:
        next_url = reverse("editar_aluno", args=[aluno.id])

    voltar_aluno = reverse("editar_aluno", args=[aluno.id])

    if not aluno.aluno_paed:
        messages.warning(request, "Este aluno não pertence ao programa PAED.")
        return redirect("relatorio_aluno_completo", aluno.id)

    documentos = aluno.documentos.select_related("aluno").order_by("-data_laudo")

    # =========================
    # SALVAR DOCUMENTO
    # =========================
    if request.method == "POST":

        arquivo_path = request.POST.get("arquivo_path")

        form = DocumentoAlunoForm(request.POST)

        if form.is_valid():

            documento = form.save(commit=False)
            documento.aluno = aluno

            if arquivo_path:
                documento.arquivo.name = arquivo_path

            documento.save()

            messages.success(request, "Laudo anexado com sucesso.")

            return redirect(request.path)

        else:
            messages.error(request, "Erro ao salvar o laudo.")

    else:
        form = DocumentoAlunoForm()

    return render(request, "alunos/documentos_aluno.html", {
        "aluno": aluno,
        "documentos": documentos,
        "form": form,
        "next": next_url,
        "voltar_aluno": voltar_aluno
    })

from django.core.files.storage import default_storage

@login_required
def editar_documento(request, doc_id):

    documento = get_object_or_404(DocumentoAluno, id=doc_id)
    aluno = documento.aluno

    next_url = request.GET.get("next")

    if request.method == "POST":

        form = DocumentoAlunoForm(request.POST, instance=documento)

        if form.is_valid():

            documento_editado = form.save(commit=False)

            arquivo_antigo = None
            if documento.arquivo:
                arquivo_antigo = documento.arquivo.name

            # arquivo enviado via R2
            arquivo_path = request.POST.get("arquivo_path")

            remover = request.POST.get("remover_arquivo") == "1"

            # =========================
            # NOVO ARQUIVO VIA R2
            # =========================

            if arquivo_path:

                documento_editado.arquivo.name = arquivo_path

                # apagar antigo
                if arquivo_antigo:
                    try:
                        default_storage.delete(arquivo_antigo)
                    except Exception:
                        pass

            # =========================
            # REMOÇÃO MANUAL
            # =========================

            if remover and not arquivo_path:

                messages.error(
                    request,
                    "Após remover o laudo é obrigatório enviar um novo arquivo."
                )

                return render(request, "alunos/editar_documento.html", {
                    "form": form,
                    "documento": documento,
                    "aluno": aluno,
                    "next": next_url
                })

            documento_editado.save()

            messages.success(request, "Laudo atualizado com sucesso.")

            if next_url:
                return redirect(next_url)

            return redirect("documentos_aluno", aluno_id=aluno.id)

    else:
        form = DocumentoAlunoForm(instance=documento)

    return render(request, "alunos/editar_documento.html", {
        "form": form,
        "documento": documento,
        "aluno": aluno,
        "next": next_url
    })

@login_required
def excluir_documento(request, doc_id):

    documento = get_object_or_404(DocumentoAluno, id=doc_id)
    aluno_id = documento.aluno.id

    next_url = request.GET.get("next")

    # apagar arquivo no storage (Cloud / S3 / R2)
    if documento.arquivo:
        documento.arquivo.delete(save=False)

    documento.delete()

    messages.success(request, "Laudo excluído com sucesso.")

    if next_url:
        return redirect(next_url)

    return redirect("documentos_aluno", aluno_id=aluno_id)


@login_required
def detalhe_documento(request, doc_id):

    documento = get_object_or_404(DocumentoAluno, id=doc_id)

    next_url = request.GET.get("next")

    return render(
        request,
        "alunos/detalhe_documento.html",
        {
            "documento": documento,
            "aluno": documento.aluno,
            "next": next_url
        }
    )


@login_required
@require_POST
def atualizar_paed(request, aluno_id):

    aluno = get_object_or_404(Aluno, id=aluno_id)

    valor = request.POST.get("paed") == "true"

    aluno.aluno_paed = valor
    aluno.save(update_fields=["aluno_paed"])

    return JsonResponse({
        "success": True,
        "paed": aluno.aluno_paed
    })

@login_required
def gerar_upload_laudo(request):

    filename = request.GET.get("filename")
    aluno_id = request.GET.get("aluno")

    if not filename or not aluno_id:
        return JsonResponse({"error": "dados inválidos"}, status=400)

    aluno = Aluno.objects.get(id=aluno_id)

    ext = os.path.splitext(filename)[1]

    nome_final = f"alunos/laudos/Laudo-{aluno.matricula}-{uuid.uuid4().hex}{ext}"

    s3 = boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name="auto",
    )

    url = s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
            "Key": nome_final,
        },
        ExpiresIn=1800
    )

    return JsonResponse({
        "upload_url": url,
        "file_key": nome_final
    })


@login_required
def verificar_arquivos_orfaos(request):

    import boto3
    import re
    from django.conf import settings

    s3 = boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name="auto",
    )

    arquivos_bucket = []

    continuation_token = None

    while True:

        if continuation_token:

            response = s3.list_objects_v2(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Prefix="alunos/laudos/",
                ContinuationToken=continuation_token
            )

        else:

            response = s3.list_objects_v2(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Prefix="alunos/laudos/"
            )

        if "Contents" in response:
            arquivos_bucket.extend(response["Contents"])

        if response.get("IsTruncated"):
            continuation_token = response.get("NextContinuationToken")
        else:
            break


    arquivos_db = set(
        DocumentoAluno.objects.exclude(arquivo="")
        .values_list("arquivo", flat=True)
    )


    arquivos_orfaos = []

    for obj in arquivos_bucket:

        key = obj["Key"]

        if key.endswith("/"):
            continue

        if key not in arquivos_db:

            aluno = None

            match = re.search(r"Laudo-(\d+)-", key)

            if match:

                matricula = match.group(1)

                aluno = Aluno.objects.filter(
                    matricula=matricula
                ).only("id","nome","matricula").first()

            presigned_url = s3.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                    "Key": key
                },
                ExpiresIn=3600
            )

            arquivos_orfaos.append({

                "arquivo": key,
                "url": presigned_url,
                "tamanho": obj["Size"],
                "data": obj["LastModified"],
                "aluno": aluno

            })

    arquivos_orfaos.sort(key=lambda x: x["data"], reverse=True)


    total_bucket = len(arquivos_bucket)
    total_db = len(arquivos_db)
    total_orfaos = len(arquivos_orfaos)


    return render(
        request,
        "alunos/arquivos_orfaos.html",
        {
            "arquivos_orfaos": arquivos_orfaos,
            "total_orfaos": total_orfaos,
            "total_bucket": total_bucket,
            "total_db": total_db
        }
    )

@login_required
def excluir_arquivo_orfao(request):

    if not (request.user.is_superuser or request.user.groups.filter(name="Gerencial").exists()):
        return JsonResponse({"error": "Sem permissão"}, status=403)

    key = request.POST.get("arquivo")

    if not key:
        return JsonResponse({"error": "Arquivo inválido"}, status=400)

    s3 = boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name="auto",
    )

    s3.delete_object(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
        Key=key
    )

    return JsonResponse({"success": True})


# ==================================================
# RESETAR SENHA SEDUC
# ==================================================

@login_required
@require_POST
def resetar_senha_seduc(request):

    data = json.loads(request.body)
    aluno_id = data.get("aluno_id")

    logs = []

    def log(msg):
        logs.append(msg)

    try:

        aluno = Aluno.objects.get(id=aluno_id)

        matricula = aluno.matricula
        data_nascimento = aluno.data_nascimento.strftime("%d/%m/%Y")
        data_convertida = datetime.strptime(
            data_nascimento, "%d/%m/%Y"
        ).strftime("%Y-%m-%d")

        log("Preparando dados do aluno")
        log(f"Aluno: {aluno.nome}")
        log(f"Matrícula: {matricula}")

        with sync_playwright() as p:

            log("Iniciando navegador seguro")

            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-software-rasterizer",
                    "--disable-extensions",
                    "--disable-background-networking",
                    "--disable-background-timer-throttling",
                    "--disable-renderer-backgrounding",
                    "--disable-features=site-per-process",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-ipc-flooding-protection"
                ]
            )

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                viewport={"width": 1280, "height": 720},
                locale="pt-BR",
                timezone_id="America/Cuiaba"
            )

            page = context.new_page()

            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """)

            log("Abrindo portal estudante")

            page.goto(
                "https://www3.seduc.mt.gov.br/acesso-estudante",
                timeout=120000
            )

            page.wait_for_load_state("networkidle")

            log("Localizando formulário")

            frame = None

            for f in page.frames:

                try:
                    if f.locator("#inputCode").count() > 0:
                        frame = f
                        log("Formulário encontrado")
                        break
                except:
                    pass

            if frame is None:

                browser.close()

                return JsonResponse({
                    "status": "erro",
                    "logs": logs,
                    "erro": "Formulário não encontrado"
                })

            log("Inserindo matrícula")

            frame.fill("#inputCode", matricula)

            log("Inserindo data de nascimento")

            frame.evaluate(f"""
                document.querySelector("#birthDay").value = "{data_convertida}";
            """)

            log("Solicitando nova senha")

            frame.click("#changePass")

            time.sleep(5)

            log("Processando resposta do sistema")

            texto = frame.inner_text("body")

            email = re.search(r"e\d+@edu\.mt\.gov\.br", texto)
            senha = re.search(r"mt\d+", texto)

            browser.close()

            if not email or not senha:

                log("Sistema não retornou credenciais")

                return JsonResponse({
                    "status": "erro",
                    "logs": logs
                })

            log("Credenciais geradas com sucesso")

            return JsonResponse({
                "status": "ok",
                "email": email.group(),
                "senha": senha.group(),
                "logs": logs
            })

    except Exception as e:

        log("Erro interno no processo")

        return JsonResponse({
            "status": "erro",
            "erro": str(e),
            "logs": logs
        })