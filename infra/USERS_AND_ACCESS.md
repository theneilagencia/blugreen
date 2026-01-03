# Usuários e Acessos - Blugreen

**Data da última atualização:** 2026-01-03

Este documento descreve os usuários e os níveis de acesso para os diferentes componentes da infraestrutura do projeto Blugreen.

## Servidor (Contabo - 161.97.156.108)

| Usuário | Nível de Acesso | Método de Autenticação | Propósito |
| :--- | :--- | :--- | :--- |
| `root` | Superusuário (total) | Senha | Administração inicial e configuração do servidor. |

### Recomendações de Segurança

- **Desativar Login Root com Senha:** É altamente recomendável desativar o login SSH para o usuário `root` usando senha.
- **Criar Usuário com Sudo:** Criar um usuário dedicado (ex: `ubuntu` ou `blugreen`) com privilégios `sudo` para administração do dia a dia.
- **Autenticação por Chave SSH:** Implementar autenticação baseada em chave SSH para todos os acessos, desativando a autenticação por senha.

## Coolify (Painel de Controle)

| Usuário | Email | Nível de Acesso | Propósito |
| :--- | :--- | :--- | :--- |
| `blugreen` | `vinicius.debian@theneil.com.br` | Administrador (Root Team) | Gerenciamento completo da instância do Coolify, incluindo criação de projetos, aplicações, servidores e configurações. |

### Observações

- Nenhum usuário adicional foi criado no Coolify para manter o gerenciamento centralizado.
- O acesso ao painel do Coolify é feito através do domínio `https://coolify.blugreen.com.br`.

## GitHub

- **Repositório:** `theneilagencia/blugreen`
- **Acesso:** O Coolify acessa o repositório como um repositório público. Não foi necessária a configuração de chaves de deploy SSH ou um GitHub App, pois o código é de leitura pública.
- **Deploy Automático:** O deploy é acionado por polling (verificação periódica) da branch `main`. Alterações (push) na branch `main` serão detectadas e um novo deploy será iniciado automaticamente.
