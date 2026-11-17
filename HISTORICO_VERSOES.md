<<<<<<< HEAD
# Histórico de versões do GerEdu


## r27 — 17/11/2026
- Corrigido o registro do app e da rota do Mapeamento da Aprendizagem no projeto principal.
- Link do módulo incluído diretamente na barra lateral para todos os usuários autenticados.
- Nota de atualização publicada pelo mecanismo existente de comunicados com confirmação de leitura.
- Exportação conferida com o modelo original: aba Mapeamento, colunas A:S e campos na ordem exata do cabeçalho.
- Valores de PAEDE, situação, níveis, ano e turno alinhados às listas da planilha; turno Noturno foi acrescentado à validação para compatibilidade com o cadastro do GerEdu.
- Abas auxiliares, formatação e validações originais preservadas.
- Nota TXT: `busca_ativa/atualizacoes/NOTAS_VERSAO_2026-11-17-r27.txt`.
=======
# Histórico de versões

## r13 — Correção do módulo de atualizações
- Corrigida a herança do template de atualização, substituindo a variável `base_template` sem valor por `core/base.html`.
- Movido o acesso **Atualizações do sistema** para o grupo **Administração** da barra lateral.
- Restaurada a publicação via TXT, com criação/atualização do comunicado e confirmação de leitura.
- Cada TXT publicado passa a ser arquivado em `busca_ativa/atualizacoes/` com nome `NOTAS_VERSAO_<versao>.txt`.
- Reunidas nessa pasta as notas históricas existentes no pacote (r3 a r10).
- Incluída listagem e download das notas de versão na tela administrativa.
- Melhorado o layout responsivo da tela e a leitura de nomes longos na barra lateral.
- Sem novas migrations.

## r14 — 13/11/2026
- Reforçado o ciclo de notificação: cada usuário recebe cada comunicado ativo até confirmar a leitura.
- A fila apresenta comunicados pendentes em sequência; após confirmar um, o próximo é exibido.
- Republicar uma versão com título/texto alterado invalida confirmações antigas.
- A migration `0012_comunicado_assistente_r14` publica automaticamente a nota r14 no banco.
- Substituído o assistente sazonal por um Duende GerEdu permanente com corpo ilustrado, gestos animados, janela de diálogo e atalhos contextuais.
- Movimento discreto de esquiva do cursor; respeita `prefers-reduced-motion`.
- Incluída a nota `NOTAS_VERSAO_2026-11-13-r14.txt` na pasta `busca_ativa/atualizacoes`.

## r15 — 13/11/2026
- Adicionada consulta automática de comunicados pendentes por endpoint JSON, com verificação imediata e a cada 10 segundos em todas as telas autenticadas.
- Confirmação assíncrona de leitura; após confirmar, a próxima atualização pendente aparece sem trocar de página.
- Mantida a exigência de rolar até o final e marcar ciência.
- Mascote redesenhado como super-herói original do GerEdu, com corpo, capa, uniforme e gestos.
- Mascote pode ser arrastado e sua posição fica salva no navegador.
- Diálogo do assistente exibe dias letivos restantes e data de encerramento do calendário ativo.
- Incluída nota TXT `2026.11.13.15.txt` e migration `0013_comunicado_global_mascote_r15`.

## r16 — 13/11/2026
- Mascote redesenhado com aparência de criatura fantástica doméstica original, inspirada na referência enviada, sem reproduzir personagem protegido.
- Animação de portal: desaparece periodicamente e retorna com efeitos de energia.
- Balão de fala pode ser fechado pelo botão ou clicando no próprio balão.
- Janela de diálogo fecha pelo botão, tecla Esc ou clique fora.
- Mantida a interação de arrastar e posicionar o mascote.
- Incluída nota TXT `NOTAS_VERSAO_2026-11-13-r16.txt` e migration `0014_comunicado_portal_duende_r16`.

## r17 — 13/11/2026
- Mascote redesenhado com proporções mais harmoniosas, expressão amigável, túnica clara e chapéu pontudo verde.
- Refeito o ciclo do portal com temporização sequencial explícita para corrigir falhas de desaparecimento/reaparecimento.
- Balão de boas-vindas e janela de diálogo possuem botões próprios de fechar.
- Boas-vindas personalizadas com primeiro nome; fallback para username.
- Mantidas a arrastabilidade, posição salva, ajuda e informação do calendário letivo.
- Incluída nota TXT `NOTAS_VERSAO_2026-11-13-r17.txt` e migration `0015_comunicado_duende_boas_vindas_r17`.

## r18 — 13/11/2026
- Mascote ganhou dança contínua, com balanço corporal, pequenos saltos, gestos e movimento de braços e cabeça.
- Portal redimensionado para acompanhar a área ocupada pelo mascote.
- Efeito de moedas douradas durante entrada e saída do portal.
- Seletor de tempo de visibilidade: sempre, 5, 15, 30 minutos, 1 ou 2 horas.
- Ao atingir o limite escolhido, mascote se recolhe e deixa botão mágico para reaparecer.
- Preferência salva localmente por usuário/navegador.
- Calendário apresenta dias letivos restantes e dias corridos até a data final cadastrada.
- Nota TXT `NOTAS_VERSAO_2026-11-13-r18.txt` e migration `0016_comunicado_duende_danca_r18`.

## r19 — 13/11/2026
- Substituído o desenho vetorial anterior por GIF animado original de 16 quadros, em estilo 3D, com dança em loop.
- Adicionada reação ao cursor com inclinação em perspectiva 3D, resposta ao clique e suporte a arrastar.
- Mantidos portal e moedas douradas, preferências de visibilidade, boas-vindas e calendário.
- Mídia: `core/static/img/duende_geredu_danca.gif`.
- Nota TXT `NOTAS_VERSAO_2026-11-13-r19.txt` e migration `0017_comunicado_duende_3d_r19`.

## r20 — 13/11/2026
- Substituído GIF por modelo 3D GLB/GLTF renderizado com Three.js.
- Modelo dividido em partes para animação procedural articulada de cabeça, braços, pernas e pés.
- Interação com cursor, inclinação em perspectiva, olhar direcionado, clique e arraste.
- Rotinas manhã/tarde/noite com iluminação e ritmos de movimento distintos.
- Após inatividade, o mascote passeia pela parte inferior da tela, muda de posição gradualmente e depois descansa/deita; desperta com interação.
- Mantidos portal, moedas, temporizador, boas-vindas, diálogos e calendário.
- Incluídos `core/static/models/duende_geredu.glb`, nota TXT r20 e migration `0018_comunicado_duende_3d_rotinas_r20`.


## r21 — 16/11/2026
- Mascote 3D ampliado com novo enquadramento para evitar corte do personagem e balão de boas-vindas mais largo.
- Boas-vindas agora combinam nome do usuário, dias letivos e dias corridos restantes até o fim do calendário.
- Botão para desaparecer com passe mágico e permanecer como trevo de quatro folhas; trevo reativa o mascote com animação.
- Atalho para convidar o duende a dançar.
- Painel Busca Ativa organizado em abas internas com fila, prazos, prioridade e importações/backup.
- Último upload destacado no painel com arquivo, data, ano letivo e totais de vínculo.
- Fila principal reduzida para 15 estudantes por página.
- Nota TXT `NOTAS_VERSAO_2026-11-16-r21.txt` e migration `0019_comunicado_mascote_busca_ativa_r21`.


## r22 — 16/11/2026
- Reduzido o tamanho do mascote e redesenhado como um guardião da floresta 3D original, mais compacto e arredondado, com chapéu de folha e cachecol.
- O trevo de retorno agora fica no canto inferior direito e mede aproximadamente 30 px.
- Criado dashboard independente da Busca Ativa, com filtros por ano, turno e turma, indicadores de infrequência e providências, distribuição por turma, último upload e filas prioritárias.
- Atalho para o dashboard adicionado ao cabeçalho do painel atual.
- Preservadas as rotinas operacionais e não foram criadas migrations de banco.
- Nota TXT: `NOTAS_VERSAO_2026-11-16-r22.txt`.


## r23 — 16/11/2026
- Dashboard: adicionado comparativo histórico por ano letivo e ano explícito na tabela de turmas.
- Mascote: palco 3D reduzido, câmera reenquadrada e passeio limitado ao palco para impedir que o personagem saia da área visível.
- Ao desaparecer, o trevo fica fixo no extremo inferior direito e foi reduzido para aproximadamente 22 px.
- Busca Ativa: unificação visual de cabeçalho, navegação por abas, cartões, tabelas e controles.
- Sem mudanças no banco de dados; sem migration.
- Nota TXT: `NOTAS_VERSAO_2026-11-16-r23.txt`.


## r24 — 16/11/2026
- Fila de trabalho do relatório 25%+ passou para a primeira posição e recebeu destaque visual.
- Primeira aba interna do painel operacional agora é a fila prioritária 25%+.
- Regra da fila ajustada: somente providências abertas com prazo vigente retiram temporariamente o estudante; ações vencidas ou sem prazo permanecem visíveis para revisão.
- Conclusão posterior à última importação continua sendo respeitada; nova sinalização em importação posterior recoloca o estudante.
- Mascote reduzido e reenquadrado no canvas 3D; removida restauração de posição antiga que causava corte; início fixo no canto inferior direito e arraste preservado.
- Nota TXT: `NOTAS_VERSAO_2026-11-16-r24.txt`.
- Migration `0021_comunicado_fila_prioritaria_r24.py` publica a nota no sistema.


## r24 — 16/11/2026
- Fila de trabalho do relatório 25%+ passou para a primeira posição e recebeu destaque visual.
- Primeira aba interna do painel operacional agora é a fila prioritária 25%+.
- Regra da fila ajustada: somente providências abertas com prazo vigente retiram temporariamente o estudante; ações vencidas ou sem prazo permanecem visíveis para revisão.
- Conclusão posterior à última importação continua sendo respeitada; nova sinalização em importação posterior recoloca o estudante.
- Tela 25%+ reorganizada como central de trabalho, com filtros, status da providência e acesso direto à ficha.
- Mascote reduzido e reenquadrado no canvas 3D; removida restauração de posição antiga que causava corte; início fixo no canto inferior direito e arraste preservado.
- Nota TXT: `NOTAS_VERSAO_2026-11-16-r24.txt`.
- Migration `0021_comunicado_fila_prioritaria_r24.py` publica a nota no sistema.


## r25 — 16/11/2026
- Nova aba "Conferir últimos lançamentos" ao lado da fila 25%+.
- A fila acompanha todos os estudantes vinculados da importação mais recente, independentemente do percentual.
- Cada aluno sai da fila após uma ação não cancelada ser registrada depois do upload atual; ações antigas ou canceladas não contam.
- Nova importação abre uma nova rodada de conferência sem apagar histórico.
- Mascote ampliado após o ajuste excessivo de redução da r24; corpo inteiro continua enquadrado.
- Nota TXT: `NOTAS_VERSAO_2026-11-16-r25.txt`.
- Migration `0022_comunicado_fila_ultimos_lancamentos_r25.py` publica a nota no sistema.
>>>>>>> origin/main

## 2026.11.17-R31 — Dashboard inicial e importação de avaliações diagnósticas
- Tela inicial com indicadores gerais e atalhos de navegação.
- Importação de planilhas diagnósticas LP/MT em lote, com filtro da unidade e correspondência pela matrícula institucional.
- Persistência dos grupos originais e atualização sem duplicidade por estudante/ano/disciplina.
- Comunicado de versão publicado por migração de banco.
