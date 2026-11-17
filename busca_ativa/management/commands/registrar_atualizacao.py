from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from busca_ativa.models import ComunicadoSistema


class Command(BaseCommand):
    help = "Publica uma atualização do GerEdu lendo um arquivo TXT versionado."

    def add_arguments(self, parser):
        parser.add_argument("--arquivo", required=True, help="Caminho do arquivo TXT UTF-8 com VERSAO:, TITULO: e TEXTO:")

    def handle(self, *args, **options):
        caminho = Path(options["arquivo"])
        if not caminho.is_file() or caminho.suffix.lower() != ".txt":
            raise CommandError("Informe um arquivo .txt existente.")
        try:
            conteudo = caminho.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            raise CommandError(f"Não foi possível ler o TXT em UTF-8: {exc}") from exc
        campos, corpo, lendo_texto = {}, [], False
        for linha in conteudo.splitlines():
            if not lendo_texto and ":" in linha:
                chave, valor = linha.split(":", 1)
                chave = chave.strip().upper()
                if chave in {"VERSAO", "TITULO"}:
                    campos[chave] = valor.strip()
                    continue
                if chave == "TEXTO":
                    if valor.strip():
                        corpo.append(valor.strip())
                    lendo_texto = True
                    continue
            if lendo_texto:
                corpo.append(linha)
        versao, titulo, texto = campos.get("VERSAO", ""), campos.get("TITULO", ""), "\n".join(corpo).strip()
        if not versao or not titulo or not texto:
            raise CommandError("TXT inválido. Use VERSAO:, TITULO: e TEXTO:, com a descrição após TEXTO:.")
        registro, criado = ComunicadoSistema.objects.update_or_create(
            versao=versao,
            defaults={"titulo": titulo[:180], "texto": texto, "ativo": True},
        )
        acao = "publicada" if criado else "atualizada"
        self.stdout.write(self.style.SUCCESS(f"Atualização {registro.versao} {acao} e disponível para exibição aos usuários."))
