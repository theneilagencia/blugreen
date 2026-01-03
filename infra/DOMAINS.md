# Domínios e DNS - Blugreen

**Data da última atualização:** 2026-01-03

Este documento detalha a configuração de domínios e DNS para o projeto Blugreen.

## Domínio Principal

- **Domínio:** `blugreen.com.br`
- **Provedor de Registro:** Não especificado (gerenciado pelo cliente)
- **Servidores de Nomes (DNS):** Não especificado (gerenciado pelo cliente)

## Subdomínios e Apontamentos

A tabela abaixo descreve todos os subdomínios configurados e seus respectivos apontamentos DNS.

| Subdomínio | Tipo de Registro | Valor (Apontamento) | Propósito |
| :--- | :--- | :--- | :--- |
| `coolify.blugreen.com.br` | A | `161.97.156.108` | Painel de controle do Coolify. |
| `app.blugreen.com.br` | A | `161.97.156.108` | Aplicação Frontend (Next.js). |
| `api.blugreen.com.br` | A | `161.97.156.108` | Aplicação Backend (FastAPI). |

### Observações

- Todos os subdomínios apontam para o mesmo endereço IP (`161.97.156.108`), que é o IP do servidor de produção na Contabo.
- O Coolify, através do seu proxy reverso integrado (Traefik), é responsável por rotear o tráfego recebido nas portas 80 e 443 para os contêineres corretos com base no hostname da requisição.
- A configuração de HTTPS (certificados SSL/TLS) é gerenciada automaticamente pelo Coolify usando Let's Encrypt para todos os domínios configurados.

## Gerenciamento de DNS

- A criação e alteração de registros DNS são de responsabilidade do cliente e realizadas manualmente no painel do provedor de DNS.
- Para qualquer nova aplicação ou serviço que precise de um subdomínio, um novo registro `A` ou `CNAME` deverá ser criado, apontando para o IP do servidor ou para o serviço correspondente.
