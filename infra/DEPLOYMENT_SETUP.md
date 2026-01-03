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

## Known Deployment Blockers

### Blocker: Requisito de GPU para o Serviço Ollama

**Descrição do Problema:**
O deploy da aplicação está **FALHANDO** de forma controlada e esperada. A causa raiz é que o serviço `ollama`, definido no arquivo `docker-compose.prod.yml`, possui uma configuração que exige a presença de uma GPU NVIDIA no servidor host.

**Trecho do `docker-compose.prod.yml`:**
```yaml
services:
  ollama:
    # ... outras configurações
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              capabilities: [gpu]
```

O servidor provisionado na Contabo (`prod-server-01`) não possui uma GPU NVIDIA, o que leva ao seguinte erro durante a tentativa de deploy pelo Docker:

```
Error response from daemon: could not select device driver "nvidia" with capabilities: [[gpu]]
```

**Decisão de Não Alteração:**
Conforme as diretrizes do projeto, o código da aplicação é **READ-ONLY**. Portanto, nenhuma modificação foi feita no arquivo `docker-compose.prod.yml` para contornar este problema (como remover o serviço Ollama ou adaptá-lo para rodar em CPU).

**Ação Futura (Responsabilidade do Devin):**
A resolução deste blocker é de responsabilidade da equipe de desenvolvimento (Devin). As possíveis soluções incluem:
1.  Remover o serviço Ollama do `docker-compose.prod.yml` se ele não for essencial para a versão inicial.
2.  Modificar a configuração do serviço para rodar em modo CPU, ciente do impacto no desempenho.
3.  Migrar a infraestrutura para um provedor/plano que ofereça instâncias com GPU.
4.  Refatorar a aplicação para consumir um serviço de LLM externo via API.

Até que uma dessas ações seja tomada, o deploy automático continuará a falhar para o serviço de backend.
