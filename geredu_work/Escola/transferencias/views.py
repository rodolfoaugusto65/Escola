from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from .models import Transferencia


# 📋 LISTA
@login_required
def lista_transferencias(request):
    transferencias = Transferencia.objects.all().order_by("-data_lancamento")

    # Atualiza status automaticamente
    for t in transferencias:
        if t.status != "CONCLUIDA" and timezone.now() > t.prazo_limite:
            t.status = "ATRASADA"
            t.save()

    return render(request, "transferencias/lista.html", {
        "transferencias": transferencias
    })


# ➕ CRIAR
@login_required
def criar_transferencia(request):
    if request.method == "POST":
        Transferencia.objects.create(
            aluno=request.POST.get("aluno"),
            tipo=request.POST.get("tipo"),
            escola_origem=request.POST.get("escola_origem"),
            escola_destino=request.POST.get("escola_destino"),
            observacoes=request.POST.get("observacoes"),
            criado_por=request.user
        )
        return redirect("transferencias:lista")

    return render(request, "transferencias/form.html")


# 🔄 MARCAR COMO EM ANÁLISE
@login_required
def assumir_transferencia(request, pk):
    t = get_object_or_404(Transferencia, pk=pk)

    if t.status == "ABERTA":
        t.status = "EM_ANALISE"
        t.save()

    return render(request, "transferencias/partials/linha.html", {"t": t})


# ✅ CONCLUIR (SÓ COORDENADOR)
@login_required
def concluir_transferencia(request, pk):
    t = get_object_or_404(Transferencia, pk=pk)

    if not request.user.groups.filter(name="Coordenador").exists():
        return HttpResponseForbidden("Apenas coordenador pode concluir")

    t.status = "CONCLUIDA"
    t.resolvido_por = request.user
    t.data_conclusao = timezone.now()
    t.save()

    return render(request, "transferencias/partials/linha.html", {"t": t})