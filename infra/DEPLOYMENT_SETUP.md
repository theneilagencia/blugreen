# Configuração de Deploy - Blugreen

**Data da última atualização:** 2026-01-03

Este documento descreve a configuração do ambiente de deploy para o projeto Blugreen, utilizando a plataforma Coolify.

## Plataforma de Deploy

- **Plataforma:** Coolify
- **Versão:** v4.0.0-beta.460
- **URL do Painel:** [https://coolify.blugreen.com.br](https://coolify.blugreen.com.br)
- **Servidor Host:** `prod-server-01` (161.97.156.108)

## Fonte do Código

- **Tipo:** Repositório Git Público
- **URL do Repositório:** `https://github.com/theneilagencia/blugreen`
- **Branch para Deploy:** `main`

## Configuração da Aplicação

Uma única aplicação foi criada no Coolify para gerenciar todo o stack do projeto, utilizando o `docker-compose.prod.yml` do repositório.

- **Nome da Aplicação no Coolify:** `theneilagencia/blugreen:main`
- **Build Pack:** Docker Compose
- **Arquivo Docker Compose:** `/docker-compose.prod.yml` (na raiz do repositório)

### Serviços e Domínios

O Coolify identificou os serviços no arquivo `docker-compose.prod.yml` e os seguintes domínios foram configurados:

| Serviço no Compose | Domínio Configurado | Propósito |
| :--- | :--- | :--- |
| `backend` | `https://api.blugreen.com.br` | API FastAPI |
| `frontend` | `https://app.blugreen.com.br` | Aplicação Next.js |
| `ollama` | (Nenhum) | Serviço de LLM |

- **HTTPS:** Habilitado e gerenciado automaticamente pelo Coolify (Let's Encrypt) para todos os domínios.

## Deploy Automático

- **Método:** Polling
- **Gatilho:** O Coolify verifica periodicamente a branch `main` do repositório `theneilagencia/blugreen`.
- **Ação:** Qualquer novo commit na branch `main` iniciará um novo processo de build e deploy automaticamente.

Não foi necessário configurar um webhook no GitHub, pois o repositório é público.

## Resolved Deployment Blockers

### [RESOLVIDO] Blocker: Requisito de GPU para o Serviço Ollama

**Descrição do Problema Original:**
O deploy da aplicação estava falhando porque o serviço `ollama` no `docker-compose.prod.yml` exigia GPU NVIDIA, mas o servidor não possui GPU.

**Erro Original:**
```
Error response from daemon: could not select device driver "nvidia" with capabilities: [[gpu]]
```

**Solução Implementada (2026-01-03):**
A seção `deploy.resources.reservations.devices` foi removida do serviço Ollama, permitindo que ele rode em modo CPU. Esta é a solução recomendada para servidores sem GPU.

**Decisão Técnica:**
- **Opção escolhida:** Ollama em modo CPU
- **Justificativa:** Mantém a funcionalidade LLM sem dependência de hardware especializado
- **Trade-off:** Performance reduzida em comparação com GPU, mas funcional para uso em produção
- **Configuração GPU:** Mantida como comentário no arquivo para fácil reativação se GPU for adicionada no futuro

**Impacto:**
- O Ollama rodará em CPU, o que é mais lento mas funcional
- O modelo `qwen2.5:7b` é compatível com CPU
- Para melhor performance, considerar upgrade para servidor com GPU no futuro

**Configuração Atual do Ollama:**
```yaml
services:
  ollama:
    image: ollama/ollama:latest
    environment:
      - OLLAMA_HOST=0.0.0.0
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
    # GPU support comentado - descomentar se GPU disponível
```
