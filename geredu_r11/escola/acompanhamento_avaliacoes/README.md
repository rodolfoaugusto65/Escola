# Acompanhamento de Avaliações

Aplicativo Django para importar planilhas de participação em avaliações, manter snapshots históricos e acompanhar pendências por aluno/turma.

## Integração

O app já está incluído em `INSTALLED_APPS`, em `escola/urls.py` e no menu lateral do GerEdu.

Após publicar os arquivos, execute:

```bash
python manage.py migrate
```

Acesse **Avaliações e Participação** no menu lateral. O acesso está restrito a superusuários e usuários com `pode_gerenciar_usuarios`.

## Importação

Aceita arquivos `.xlsx`, `.xlsm` e `.csv`, inclusive múltiplos arquivos no mesmo envio. São reconhecidas colunas equivalentes a:

- Matrícula / RA
- Aluno / Nome
- Participação / Situação / Status
- Ano/Série, Turma, Avaliação, Prova
- Entregue Em e Tempo de Prova (opcionais)

Cada envio cria um registro `ImportacaoAvaliacao` e linhas `RegistroParticipacao`. Os registros antigos nunca são sobrescritos. O aluno do cadastro GerEdu é associado pela matrícula quando encontrado; se não for encontrado, o registro histórico continua disponível e a divergência é contabilizada.

## Observação sobre evolução

O gráfico compara os percentuais de cada importação registrada. Para comparações consistentes, importe sempre a mesma avaliação quando estiver atualizando o andamento daquela aplicação. Uma nova avaliação ou prova ficará identificada separadamente pelo nome e ano letivo.
