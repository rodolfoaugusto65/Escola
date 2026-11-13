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
