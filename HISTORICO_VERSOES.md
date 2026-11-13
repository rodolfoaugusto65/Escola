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
