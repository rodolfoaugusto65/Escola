# Histórico de versões GerEdu

## 2026-11-13 — r6 (2026.11.13.6)
- Publicação automática do comunicado r6 por migration de dados, para que a nota de atualização apareça aos usuários após `migrate`.
- Comparativo de aplicações por período, com contagens por situação.
- Filtro adicional por ano letivo.
- Indicadores percentuais e exportação separada de pendentes/ausentes e lista completa filtrada.
- Preservação das importações históricas sem somar snapshots diferentes como estudantes distintos.

## 2026-11-13 — r5 (2026.11.13.5)
- Primeira tela de relatórios por aplicação e atualização TXT.

## 2026-11-13 — r4
- Abas e alertas de Busca Ativa e filtros nos relatórios de avaliação.
## 2026-11-13 — r7 — Acompanhamento ampliado das avaliações
- Lista alternável entre pendências/ausências e todos os estudantes.
- Impressão da lista completa filtrada, sem limitação à página atual.
- Folha de conferência com data de realização e espaço para validação em sala.
- Resumo das pendências por turno e turma.
- Correção do link de análise para abrir a aplicação exata do comparativo.
- Seletor e comparativo ampliados para 500 aplicações.
- Sem migrations e sem exclusão de histórico.
\n## 2026-11-13 — r8\n- Impressão dedicada contendo somente o nome da avaliação e a relação numerada de estudantes, sem indicadores ou painéis.\n- Impressão utiliza todos os registros filtrados, sem paginação.\n- Filtros de data preservam pendentes/ausentes sem data de realização.\n- Consolida as entregas r6 (nota TXT) e r7 (relatórios e acompanhamento).\n

## r9 — 2026-11-13 — Acompanhamento e exportação de avaliações
- Reorganizada a tela de relatórios em blocos recolhíveis, separando filtros, comparativo histórico, indicadores, resumo de pendências e relação de estudantes.
- Impressão simplificada em folha A4: cabeçalho com turma, prova e data da aplicação, seguido somente dos nomes dos estudantes, agrupados por turma.
- Removidos da impressão indicadores, alertas, tabelas gerenciais, matrícula, situação, campos de assinatura e elementos de navegação.
- Exportação CSV preservada para pendências/ausentes e relação completa, respeitando os filtros da aplicação.

## r10 — 2026-11-13 — Relatórios e impressão simplificados
- Reorganizada a área de acompanhamento para reduzir a concentração de indicadores e quadros na tela.
- Indicadores passaram a iniciar recolhidos; histórico comparativo e resumo de pendências permanecem em seções expansíveis.
- Impressão da aplicação isolada em template HTML próprio, sem herdar menu, cabeçalho, rodapé, alertas ou componentes administrativos.
- Folha A4 contém somente prova, data da aplicação, turma e relação nominal dos estudantes, agrupada por turma.
- Incluída nota TXT `busca_ativa/atualizacoes/2026.11.13.10.txt`, publicada automaticamente pela migration `busca_ativa.0010_comunicado_relatorios_impressao_r10`.


## r11 — Lista de chamada para aplicação de avaliações (2026-11-13)
- Impressão organizada como chamada escolar, separada por turma.
- Colunas: número, nome do estudante, presença e falta.
- Cabeçalho contém somente prova e data; cada turma possui identificação própria.
- Numeração reinicia em cada turma; cabeçalho da tabela se repete entre páginas.
- Agrupamento considera ano/série e turma para evitar mesclar turmas homônimas.
- Nota TXT publicada automaticamente pela migration `0011_comunicado_chamada_avaliacoes_r11`.
