# GerEdu — melhorias de Busca Ativa e Avaliações (11/11/2026)

## O que foi atualizado

### Busca Ativa
- Painel reorganizado em filas de trabalho: **Fila para atendimento**, **Sem ação cadastrada**, **Prazo vencido / retorno**, **Em acompanhamento** e **Prioridade da integração**.
- O aluno com ação em andamento e prazo futuro deixa a fila de novos lançamentos e fica visível em **Em acompanhamento**.
- Quando o prazo vence, o aluno volta automaticamente para a fila de revisão/novo atendimento.
- Ações concluídas ou canceladas deixam de bloquear o retorno à fila.
- Uma ação nova sem prazo informado recebe prazo sugerido de 7 dias; o usuário pode alterar a data no formulário.
- Alunos que reaparecem na importação mais recente e ainda não possuem acompanhamento vigente aparecem na fila de prioridade.
- O histórico de importações e de ações anteriores é mantido; nenhuma ação ou fotografia histórica é apagada.
- Na ficha do aluno, os prazos são identificados como acompanhamento vigente ou prazo vencido.

### Avaliações
- Corrigida a classificação de estados negativos: “Não realizado”, “Não realizada”, “Não realizou” e “Não participou” não são classificados como realizados.
- “Não compareceu” é classificado como ausente.
- Mantidos os filtros, gráficos, histórico de importações, acompanhamento por turma e datas de realização.
- Adicionado botão de exportação CSV respeitando os filtros aplicados.

## Arquivos alterados
- `busca_ativa/views.py`
- `busca_ativa/templates/busca_ativa/painel.html`
- `busca_ativa/templates/busca_ativa/acao_form.html`
- `busca_ativa/templates/busca_ativa/ficha.html`
- `acompanhamento_avaliacoes/views.py`
- `acompanhamento_avaliacoes/tests.py`
- `acompanhamento_avaliacoes/templates/acompanhamento_avaliacoes/painel.html`

## Migrações
Não foram adicionados nem alterados campos de banco de dados. Portanto, esta atualização não cria migrações novas.

## Teste local (Windows / PowerShell)

```powershell
python manage.py check
python manage.py test acompanhamento_avaliacoes
python manage.py test busca_ativa
```

Faça os testes com uma cópia/backup do banco antes de publicar.

## Registrar a atualização no aviso do GerEdu

Depois de publicar a versão no Railway, execute no terminal do serviço web:

```bash
python manage.py registrar_atualizacao --versao 2026.11.11.1 --titulo "Melhorias na Busca Ativa e Avaliações" --texto "Nova fila de atendimento da Busca Ativa com controle de prazos, acompanhamento de recorrências e prioridade para alunos reaparecidos na integração. Painel de avaliações aprimorado, exportação de relatórios e correção da classificação de alunos que não realizaram."
```

O comando é idempotente: executar novamente com a mesma versão não sobrescreve o comunicado existente.
