# Notas de Segurança - Blugreen

**Data da última atualização:** 2026-01-03

Este documento centraliza as decisões e configurações de segurança implementadas na infraestrutura do projeto Blugreen.

## Firewall do Servidor (UFW)

- **Ferramenta:** UFW (Uncomplicated Firewall)
- **Status:** Ativo

### Regras Aplicadas

As seguintes regras foram configuradas para restringir o tráfego de entrada ao mínimo necessário:

| Porta | Protocolo | Serviço | Ação | Origem | Justificativa |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 22 | TCP | SSH | `ALLOW` | `Any` | Acesso para administração remota do servidor. |
| 80 | TCP | HTTP | `ALLOW` | `Any` | Tráfego web de entrada, gerenciado pelo proxy do Coolify. |
| 443 | TCP | HTTPS | `ALLOW` | `Any` | Tráfego web seguro, gerenciado pelo proxy do Coolify. |

- **Política Padrão:** Todo o tráfego de entrada não explicitamente permitido é **negado** (`DENY`).

## Acesso ao Servidor

- **Usuário `root`:** O acesso SSH direto com o usuário `root` utilizando senha está atualmente habilitado. **Esta é uma configuração de risco** e foi utilizada apenas para o setup inicial.

  - **Recomendação Crítica:** Desativar o login via senha para o usuário `root` e, preferencialmente, desativar o login `root` por completo, utilizando um usuário com privilégios `sudo`.

- **Autenticação por Chave SSH:** A autenticação por senha deve ser desativada em favor da autenticação por chave SSH, que é significativamente mais segura.

## Coolify

- **Acesso ao Painel:** O painel do Coolify está protegido por login e senha e acessível exclusivamente via HTTPS (`https://coolify.blugreen.com.br`).
- **API:** A API do Coolify foi habilitada, mas o acesso foi configurado para permitir conexões de qualquer IP (`0.0.0.0`).

  - **Recomendação:** Para ambientes de produção, é fortemente recomendado restringir o acesso à API a uma lista de IPs confiáveis. Isso pode ser feito em `Settings > Advanced > Allowed IPs for API Access`.

- **Tokens de API:** Foi criado um token com o escopo mínimo (`deploy`) para automação. Tokens devem ser tratados como senhas e armazenados de forma segura.

## Aplicação (Docker Compose)

- **Segredos e Variáveis de Ambiente:** O `docker-compose.prod.yml` faz referência a um arquivo `.env` para carregar variáveis de ambiente. Este arquivo `.env` **NÃO DEVE** ser commitado no repositório Git. O Coolify gerencia a injeção segura de variáveis de ambiente na aplicação.

- **Exposição de Portas:** Os serviços dentro do Docker Compose não expõem portas diretamente para a internet. O proxy reverso do Coolify (Traefik) é o único ponto de entrada, que roteia o tráfego com base no domínio, garantindo que apenas os serviços web sejam acessíveis externamente.

## Repositório GitHub

- **Visibilidade:** O repositório é público. Isso significa que todo o código-fonte (exceto o que estiver no `.gitignore`) é visível para qualquer pessoa.
- **Segredos:** É de importância vital garantir que nenhum segredo (chaves de API, senhas, tokens, etc.) seja commitado no repositório.
