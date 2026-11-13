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
