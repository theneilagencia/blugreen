# Deploy em Produção

Deploy deve ser:

- Automático
- Repetível
- Versionado
- Com rollback

Passos:
1. Build Docker
2. Executar testes
3. Publicar via Coolify
4. Healthcheck
5. Se falhar, rollback automático

Variáveis de ambiente nunca devem ser hardcoded.

---

## Configuração de Ambiente

### 1. Copiar template de variáveis

```bash
cp .env.example .env
```

### 2. Configurar variáveis obrigatórias

Edite o arquivo `.env` com os valores de produção:

```bash
# Database (PostgreSQL para produção)
DATABASE_URL=postgresql://user:password@host:5432/blugreen

# Ollama
OLLAMA_BASE_URL=http://ollama-server:11434
OLLAMA_MODEL=qwen2.5:7b

# CORS (domínio de produção)
CORS_ORIGINS=["https://seu-dominio.com"]

# Frontend API URL (deve ser acessível pelo browser)
NEXT_PUBLIC_API_URL=https://api.seu-dominio.com

# Coolify (opcional, para deploy automático)
COOLIFY_API_URL=https://coolify.seu-dominio.com
COOLIFY_API_TOKEN=seu-token-aqui
```

---

## Deploy Local (Desenvolvimento)

```bash
# Iniciar todos os serviços
docker-compose -f docker-compose.dev.yml up -d

# Verificar logs
docker-compose -f docker-compose.dev.yml logs -f

# Parar serviços
docker-compose -f docker-compose.dev.yml down
```

---

## Deploy Produção (Docker Compose)

```bash
# Carregar variáveis de ambiente
source .env

# Build e iniciar serviços
docker-compose -f docker-compose.prod.yml up -d --build

# Verificar status
docker-compose -f docker-compose.prod.yml ps

# Verificar logs
docker-compose -f docker-compose.prod.yml logs -f

# Healthcheck
curl http://localhost:8000/health
```

---

## Deploy via Coolify

### Pré-requisitos

1. Coolify instalado e configurado
2. Acesso ao repositório Git
3. Token de API do Coolify

### Passos

1. No Coolify, criar novo projeto
2. Adicionar serviço Docker Compose
3. Apontar para o repositório Git
4. Selecionar `docker-compose.prod.yml`
5. Configurar variáveis de ambiente
6. Ativar deploy automático (webhook)

### Variáveis no Coolify

Configure as seguintes variáveis no painel do Coolify:

| Variável | Descrição |
|----------|-----------|
| `DATABASE_URL` | URL do PostgreSQL |
| `OLLAMA_BASE_URL` | URL do servidor Ollama |
| `CORS_ORIGINS` | Domínios permitidos |
| `NEXT_PUBLIC_API_URL` | URL pública da API |

---

## Rollback

### Manual

```bash
# Listar versões anteriores
docker images | grep blugreen

# Reverter para versão anterior
docker-compose -f docker-compose.prod.yml down
docker tag blugreen-backend:previous blugreen-backend:latest
docker-compose -f docker-compose.prod.yml up -d
```

### Automático (via API)

```bash
# Rollback de deployment específico
curl -X POST http://localhost:8000/product/{id}/rollback
```

---

## Monitoramento

### Healthchecks

- Backend: `GET /health`
- Ollama: `GET /system/ollama/status`
- LLM: `GET /system/llm/health`

### Logs

```bash
# Backend logs
docker-compose -f docker-compose.prod.yml logs -f backend

# Frontend logs
docker-compose -f docker-compose.prod.yml logs -f frontend

# Todos os logs
docker-compose -f docker-compose.prod.yml logs -f
```

---

## Troubleshooting

### Backend não inicia

1. Verificar conexão com PostgreSQL
2. Verificar variáveis de ambiente
3. Verificar logs: `docker-compose logs backend`

### Frontend não conecta ao backend

1. Verificar `NEXT_PUBLIC_API_URL`
2. Verificar CORS_ORIGINS inclui domínio do frontend
3. Verificar se backend está healthy

### Ollama não responde

1. Verificar se container está rodando
2. Verificar se modelo está baixado: `docker exec ollama ollama list`
3. Baixar modelo: `docker exec ollama ollama pull qwen2.5:7b`
